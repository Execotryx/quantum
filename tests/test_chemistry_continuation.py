"""Immutable lineage checks for continued continuous S1 fits."""

from importlib import import_module
from pathlib import Path

import pytest

from qcompile.io import sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_shape_search")


def registered_parent(tmp_path):
    registration = tmp_path / "registration.json"
    decision = tmp_path / "decision.json"
    receipt = tmp_path / "checkpoint.json"
    checkpoint = tmp_path / "continuous.npz"
    checkpoint.write_bytes(b"immutable checkpoint")
    write_json(registration, {"plan": {"shape": [1, 1, 1], "factorization_sha256": "a" * 64}})
    write_json(decision, {"status": "budget_limited", "evaluations": 7, "best_continuous_residual": 0.08})
    write_json(receipt, {"continuous_sha256": sha256(checkpoint), "evaluations": 7, "continuous_residual": 0.08})
    paths = {"registration": registration, "decision": decision, "checkpoint_receipt": receipt,
             "checkpoint": checkpoint}
    return {"factorization_sha256": "a" * 64, "target_sha256": "b" * 64, "shape": [1, 1, 1],
            "parent": {name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()}}


def test_parent_lineage_and_bytes_are_bound(tool, tmp_path):
    plan = registered_parent(tmp_path)
    tool.continuation_parent(plan)
    Path(plan["parent"]["checkpoint"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="checkpoint hash differs"):
        tool.continuation_parent(plan)


def test_parent_must_be_budget_limited_and_match_terminal_checkpoint(tool, tmp_path):
    plan = registered_parent(tmp_path)
    path = Path(plan["parent"]["decision"]["path"])
    path.unlink()
    write_json(path, {"status": "no_go", "evaluations": 7, "best_continuous_residual": 0.08})
    plan["parent"]["decision"]["sha256"] = sha256(path)
    with pytest.raises(ValueError, match="budget-limited parent"):
        tool.continuation_parent(plan)


def test_real_i3_continuation_registration(tool, project_root):
    path = project_root / "tools/chem-s1-resume-smoke.json"
    from qcompile.io import read_json
    plan = read_json(path)
    if not Path(plan["parent"]["checkpoint"]["path"]).exists():
        pytest.skip("locally retained I3 checkpoint unavailable")
    decision, receipt, _ = tool.continuation_parent(plan)
    assert decision["evaluations"] == receipt["evaluations"] == 1500
    assert decision["best_continuous_residual"] == pytest.approx(0.08139909840093204)
