"""Registration and lineage for the fixed-basis bound diagnostic."""

from importlib import import_module
from pathlib import Path

import pytest

from qcompile.io import read_json, sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_projection_bound")


def test_ranking_and_initializer_hashes_are_bound(tool, tmp_path):
    factor = tmp_path / "factor.npz"
    initializer = tmp_path / "i3.npz"
    factor.write_bytes(b"factor")
    initializer.write_bytes(b"initializer")
    reg = tmp_path / "registration.json"
    rank = tmp_path / "ranking.json"
    completion = tmp_path / "completion.json"
    target_hash = "a" * 64
    write_json(reg, {"plan": {"factorization": {"sha256": sha256(factor)}}})
    write_json(rank, {"shape": [1, 1, 1], "factorization_sha256": sha256(factor), "target_sha256": target_hash,
                      "ranking": [{"initializer": "I3", "seed": None, "checkpoint": "i3.npz",
                                   "initializer_sha256": sha256(initializer)}]})
    write_json(completion, {"ranking_sha256": sha256(rank), "registration_sha256": sha256(reg)})
    paths = {"factorization": factor, "ranking_registration": reg, "ranking": rank,
             "ranking_completion": completion, "initializer": initializer}
    plan = {**{name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()},
            "shape": [1, 1, 1], "target_sha256": target_hash, "initializer_name": "I3", "seed": None,
            "wall_seconds": 30, "block": 2}
    tool.validate_registration(plan)
    initializer.write_bytes(b"changed")
    with pytest.raises(ValueError, match="initializer hash differs"):
        tool.validate_registration(plan)


def test_real_i3_diagnostic_registration(tool, project_root):
    plan = read_json(project_root / "tools/chem-projection-i3-r9-b143-c40.json")
    if not Path(plan["initializer"]["path"]).exists():
        pytest.skip("ignored ranking arrays are not available")
    _, entry = tool.validate_registration(plan)
    assert entry["initializer"] == "I3"
    assert entry["initial_continuous_residual"] == pytest.approx(2.11866730223804)
