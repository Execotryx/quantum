"""Immutable S1-registration gates for the S2 command."""

import hashlib
import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.schema import read_factorization
from qcompile.io import sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_s2")


def registration(tmp_path: Path):
    factor = tmp_path / "factor.npz"
    factor.write_bytes(b"immutable reference fixture")
    checkpoint = tmp_path / "continuous.npz"
    checkpoint.write_bytes(b"immutable checkpoint fixture")
    reg = tmp_path / "registration.json"
    write_json(reg, {"plan": {"factorization_sha256": sha256(factor), "shape": [1, 1, 1]}})
    decision = tmp_path / "decision.json"
    write_json(decision, {"status": "go", "evaluations": 3, "best_continuous_residual": 0.018})
    receipt = tmp_path / "checkpoint.json"
    write_json(receipt, {"evaluations": 3, "continuous_residual": 0.018,
                         "continuous_sha256": sha256(checkpoint)})
    paths = {"factorization": factor, "s1_registration": reg, "s1_decision": decision,
             "s1_checkpoint_receipt": receipt, "s1_checkpoint": checkpoint}
    return {**{key: {"path": str(path), "sha256": sha256(path)} for key, path in paths.items()},
            "target_sha256": "0" * 64, "brot": 12,
            "limits": {"evaluations": 2, "restore_evaluations": 2, "wall_seconds": 10,
                       "checkpoint_interval": 1, "outer_iterations": 2, "offset_bound": 5, "penalty": 1}}


def test_registration_rejects_hash_and_receipt_mutations(tool, tmp_path):
    plan = registration(tmp_path)
    tool.validate_registration(plan)
    Path(plan["s1_checkpoint"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="checkpoint hash differs"):
        tool.validate_registration(plan)


def test_actual_capped_pilot_is_rejected_before_s2(tool, project_root, tmp_path):
    plan = registration(tmp_path)
    source = project_root / "docs/evidence/chem-s1-pilot-20261108/i1/decision.json"
    if not source.exists():
        pytest.skip("local capped pilot receipt unavailable")
    plan["s1_decision"] = {"path": str(source), "sha256": sha256(source)}
    with pytest.raises(ValueError, match="capped or inconclusive"):
        tool.validate_registration(plan)


def test_registration_rejects_mismatched_terminal_receipt(tool, tmp_path):
    plan = registration(tmp_path)
    receipt = Path(plan["s1_checkpoint_receipt"]["path"])
    receipt.unlink()
    write_json(receipt, {"evaluations": 2, "continuous_residual": 0.018,
                         "continuous_sha256": plan["s1_checkpoint"]["sha256"]})
    plan["s1_checkpoint_receipt"]["sha256"] = sha256(receipt)
    with pytest.raises(ValueError, match="terminal decision"):
        tool.validate_registration(plan)


def test_capped_receipt_refuses_cli_before_creating_output(tool, project_root, tmp_path, monkeypatch):
    plan = registration(tmp_path)
    decision = project_root / "docs/evidence/chem-s1-pilot-20261108/i1/decision.json"
    if not decision.exists():
        pytest.skip("local capped pilot receipt unavailable")
    plan["s1_decision"] = {"path": str(decision), "sha256": sha256(decision)}
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    output = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["chem_s2.py", "run", str(plan_path), str(output)])
    with pytest.raises(ValueError, match="capped or inconclusive"):
        tool.main()
    assert not output.exists()


def test_supervisor_keeps_worker_failure_as_execution_status(tool, tmp_path, monkeypatch):
    plan = registration(tmp_path)
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    output = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["chem_s2.py", "run", str(plan_path), str(output)])
    monkeypatch.setattr(tool, "run_job", lambda *_: 17)
    tool.main()
    status = import_module("qcompile.io").read_json(output / "status.json")
    assert status["status"] == "worker_exit_17"
    assert not (output / "worker/decision.json").exists()


def test_worker_runs_gated_synthetic_with_hashed_exact_outputs(tool, tmp_path, monkeypatch):
    plan = registration(tmp_path)
    vectors = np.array([[[1.0, 0.0]]])
    weights = np.array([[[10.0]]])
    checkpoint = Path(plan["s1_checkpoint"]["path"])
    checkpoint.unlink()
    deterministic_npz(checkpoint, {"U": vectors, "W": weights})
    plan["s1_checkpoint"]["sha256"] = sha256(checkpoint)
    decision_path = Path(plan["s1_decision"]["path"])
    decision_path.unlink()
    write_json(decision_path, {"status": "go", "evaluations": 3, "best_continuous_residual": 0.0})
    plan["s1_decision"]["sha256"] = sha256(decision_path)
    receipt_path = Path(plan["s1_checkpoint_receipt"]["path"])
    receipt_path.unlink()
    write_json(receipt_path, {"evaluations": 3, "continuous_residual": 0.0,
                              "continuous_sha256": sha256(checkpoint)})
    plan["s1_checkpoint_receipt"]["sha256"] = sha256(receipt_path)
    target = np.diag([100.0, 0.0, 0.0])
    plan["target_sha256"] = hashlib.sha256(memoryview(target).cast("B")).hexdigest()
    plan_path = tmp_path / "synthetic-plan.json"
    write_json(plan_path, plan)
    fixture_spec = {"U": ("f", ("R", "B", 2)), "W": ("f", ("R", "B", "C")),
                    "H2_I": ("f", ("R", "C")), "H1_I": ("f", ()),
                    "Hsym_lower": ("f", (3,)), "tree_edges": ("iu", (1, 2))}
    monkeypatch.setattr(tool, "SPEC", fixture_spec)
    monkeypatch.setattr(tool, "read_factorization", lambda path, spec=None: read_factorization(
        path, spec=spec if spec is not None else fixture_spec))
    monkeypatch.setattr(tool, "backend", lambda: ({"fixture": True}, None, None, None, None))
    monkeypatch.setattr(tool, "import_module", lambda _: None)
    monkeypatch.setattr(tool, "fixed_inputs", lambda *_: SimpleNamespace(
        num_orbitals=2, ref={"oei": np.zeros((2, 2)), "tei": np.zeros((2, 2, 2, 2)),
                             "electrons": 0, "ecore": 0.0},
        S=np.zeros((2, 2)), beta_1=0.0, energy_upper=4.0))
    monkeypatch.setattr(tool, "shifted_target", lambda *_: target)

    def evaluate(_api, _math, _inputs, v, w, offsets, _brot):
        weight, offset = float(w[0, 0, 0]), float(offsets[0, 0])
        h1 = -offset * weight
        lam = abs(h1) + (abs(weight) + abs(offset + weight)) ** 2 / 4
        gap = 4 + abs(h1) - h1 + offset**2 / 2
        valid = 0 < gap < 2 * lam
        metrics = {"Lambda": lam, "E_gap": gap, "gap_in_domain": valid,
                   "lambda_eff": float(np.sqrt(gap * (2 * lam - gap))) if valid else float("nan"),
                   "error_1": 0.0, "error_2": abs(weight**2 - 100)}
        params = {"U": v, "W": w, "H2_I": offsets + w.sum(axis=1), "H1_I": np.array(0.0),
                  "Hsym_lower": np.zeros(3), "tree_edges": np.array([[0, 1]], dtype=np.int64)}
        return params, np.zeros((3, 1), dtype=np.int64), metrics

    monkeypatch.setattr(tool, "pinned_checkpoint", evaluate)
    wrong_plan = tmp_path / "wrong-target-plan.json"
    write_json(wrong_plan, {**plan, "target_sha256": "0" * 64})
    with pytest.raises(ValueError, match="plan hash differs"):
        tool.run_worker(plan_path, tmp_path / "wrong-plan-output", "0" * 64)
    with pytest.raises(ValueError, match="target hash differs"):
        tool.run_worker(wrong_plan, tmp_path / "wrong-target-output")
    assert not (tmp_path / "wrong-target-output").exists()
    output = tmp_path / "output"
    tool.run_worker(plan_path, output)
    record = import_module("qcompile.io").read_json(output / "decision.json")
    assert record["status"] in ("inconclusive", "budget_limited")
    assert (output / record["best_eligible_checkpoint"]["checkpoint"] / "checkpoint.json").is_file()
    files = sorted((output / "checkpoints").glob("*/checkpoint.json"))
    assert files
    for item in files:
        data = import_module("qcompile.io").read_json(item)
        assert all(sha256(item.parent / name) == digest for name, digest in data["hashes"].items())
