"""Pinned S2 admission checks for the precision ladder."""

import hashlib
import importlib.util
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.schema import read_factorization
from qcompile.io import sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_s3")


def registration(tmp_path):
    factor = tmp_path / "factor.npz"
    factor.write_bytes(b"pinned reference")
    worker = tmp_path / "s2-worker"
    worker.mkdir()
    folder = worker / "checkpoints/00001"
    folder.mkdir(parents=True)
    contents = {"s2_continuous": "continuous.npz", "s2_submission": "submission.npz", "s2_words": "words.npy"}
    for name in contents.values():
        (folder / name).write_bytes(name.encode())
    metrics = {"error_1": 0.01, "error_2": 0.01, "Lambda": 50.0, "E_gap": 4.0,
               "lambda_eff": 20.0, "gap_in_domain": True}
    receipt = folder / "checkpoint.json"
    write_json(receipt, {"eligible": True, "evaluation": 10, "metrics": metrics,
                         "hashes": {name: sha256(folder / name) for name in contents.values()}})
    decision = worker / "decision.json"
    write_json(decision, {"stage": "s2", "status": "budget_limited",
                          "best_eligible_checkpoint": {"evaluation": 10, "lambda_eff": 20.0,
                                                       "checkpoint": "checkpoints/00001"}})
    reg = worker / "registration.json"
    write_json(reg, {"plan": {"factorization": {"sha256": sha256(factor)}, "target_sha256": "0" * 64}})
    paths = {"factorization": factor, "s2_registration": reg, "s2_decision": decision,
             "s2_checkpoint_receipt": receipt, **{key: folder / value for key, value in contents.items()}}
    return {**{key: {"path": str(path), "sha256": sha256(path)} for key, path in paths.items()},
            "target_sha256": "0" * 64, "limits": {"evaluations_per_step": 3, "wall_seconds": 10}}


def test_registration_accepts_only_hash_bound_eligible_checkpoint(tool, tmp_path):
    plan = registration(tmp_path)
    tool.validate_registration(plan)
    receipt = tmp_path / "s2-worker/checkpoints/00001/checkpoint.json"
    record = import_module("qcompile.io").read_json(receipt)
    receipt.unlink()
    record["metrics"]["error_2"] = 0.0196
    write_json(receipt, record)
    plan["s2_checkpoint_receipt"]["sha256"] = sha256(receipt)
    with pytest.raises(ValueError, match="exact-metric eligible"):
        tool.validate_registration(plan)


def test_registration_rejects_nonselected_or_modified_checkpoint(tool, tmp_path):
    plan = registration(tmp_path)
    item = tmp_path / "s2-worker/checkpoints/00001/words.npy"
    item.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="s2_words hash differs"):
        tool.validate_registration(plan)


def test_registration_rejects_unproven_s2(tool, tmp_path):
    plan = registration(tmp_path)
    decision = tmp_path / "s2-worker/decision.json"
    decision.unlink()
    write_json(decision, {"stage": "restoration", "status": "budget_limited", "best_eligible_checkpoint": None})
    plan["s2_decision"]["sha256"] = sha256(decision)
    with pytest.raises(ValueError, match="eligible S2 checkpoint"):
        tool.validate_registration(plan)


def test_synthetic_worker_decodes_refits_and_stops_at_first_failed_precision(tool, tmp_path, monkeypatch):
    source = (Path(__file__).resolve().parents[1] / "vendor/official/verifiers/dfthcsos"
              / "scoreinfra/dfthc_math.py")
    if not source.exists():
        pytest.skip("pinned verifier sources unavailable")
    spec = importlib.util.spec_from_file_location("s3_pinned_math", source)
    assert spec and spec.loader
    math_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(math_api)
    plan = registration(tmp_path)
    u = np.array([[[1.0, 0.0]]])
    w = np.array([[[10.0]]])
    offsets = np.zeros((1, 1))
    edges = np.array([[0, 1]], dtype=np.int64)
    params = {"U": u, "W": w, "H2_I": np.array([[10.0]]), "H1_I": np.array(0.0),
              "Hsym_lower": np.zeros(3), "tree_edges": edges}
    folder = tmp_path / "s2-worker/checkpoints/00001"
    (folder / "continuous.npz").unlink()
    deterministic_npz(folder / "continuous.npz", {"U": u, "W": w, "offsets": offsets})
    (folder / "submission.npz").unlink()
    deterministic_npz(folder / "submission.npz", params)
    (folder / "words.npy").unlink()
    np.save(folder / "words.npy", np.zeros((3, 1), dtype=np.int64), allow_pickle=False)
    for key, name in (("s2_continuous", "continuous.npz"), ("s2_submission", "submission.npz"),
                      ("s2_words", "words.npy")):
        plan[key]["sha256"] = sha256(folder / name)
    receipt = folder / "checkpoint.json"
    record = import_module("qcompile.io").read_json(receipt)
    record.update(continuous_residual=0.0, brot=12,
                  hashes={name: sha256(folder / name) for name in ("continuous.npz", "submission.npz", "words.npy")})
    receipt.unlink()
    write_json(receipt, record)
    plan["s2_checkpoint_receipt"]["sha256"] = sha256(receipt)
    target = np.diag([100.0, 0.0, 0.0])
    plan["target_sha256"] = hashlib.sha256(memoryview(target).cast("B")).hexdigest()
    reg = tmp_path / "s2-worker/registration.json"
    reg.unlink()
    write_json(reg, {"plan": {"factorization": {"sha256": plan["factorization"]["sha256"]},
                              "target_sha256": plan["target_sha256"]}})
    plan["s2_registration"]["sha256"] = sha256(reg)
    plan_path = tmp_path / "s3-plan.json"
    write_json(plan_path, plan)
    fixture_spec = {"U": ("f", ("R", "B", 2)), "W": ("f", ("R", "B", "C")),
                    "H2_I": ("f", ("R", "C")), "H1_I": ("f", ()),
                    "Hsym_lower": ("f", (3,)), "tree_edges": ("iu", (1, 2))}
    monkeypatch.setattr(tool, "SPEC", fixture_spec)
    monkeypatch.setattr(tool, "read_factorization", lambda path, spec=None: read_factorization(
        path, spec=spec if spec is not None else fixture_spec))

    @dataclass
    class Inputs:
        params: dict
        w: np.ndarray
        W: np.ndarray
        ref: dict
        S: np.ndarray
        beta_1: float = 0.0
        num_orbitals: int = 2

        @property
        def num_vectors(self):
            return 2 + self.w.shape[0] * self.w.shape[1]

    inputs = Inputs(params, w, offsets, {"oei": np.diag([-1.0, 1.0]), "tei": np.zeros((2,) * 4),
                                          "electrons": 2}, np.zeros((2, 2)))

    class API:
        @staticmethod
        def native_inputs(p):
            return p["W"], p["H2_I"] - p["W"].sum(axis=1), None, None

        @staticmethod
        def load_tree_edges(tree, _):
            return tree

        @staticmethod
        def evaluate_words(_inputs, _words, *, tree_edges, brot):
            return {"error_1": 0.01, "error_2": 0.02 if brot == 9 else 0.01, "Lambda": 50.0,
                    "E_gap": 4.0, "lambda_eff": 20.0, "gap_in_domain": True}

        @staticmethod
        def passes_accuracy(_metrics):
            return True

    monkeypatch.setattr(tool, "backend", lambda: ({"fixture": True}, None, None, None, API))
    monkeypatch.setattr(tool, "import_module", lambda _: math_api)
    monkeypatch.setattr(tool, "fixed_inputs", lambda *_: inputs)
    monkeypatch.setattr(tool, "shifted_target", lambda *_: target)
    output = tmp_path / "output"
    tool.run_worker(plan_path, output, sha256(plan_path))
    result = import_module("qcompile.io").read_json(output / "decision.json")
    assert result["status"] == "step_failed"
    assert result["last_passing"] == 10
    assert not (output / "precision-08").exists()
    assert (output / "precision-10/submission.npz").is_file()
    assert not (output / "precision-09/submission.npz").exists()
