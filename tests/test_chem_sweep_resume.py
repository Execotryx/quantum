"""Bind the completed sweep series before continuing a chemistry lane."""

from importlib import import_module

import pytest

from qcompile.io import sha256, write_json


def test_completed_sweeps_require_all_hashes_and_keep_first_minimum(project_root, monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("chem_alternating")
    monkeypatch.setattr(tool, "SWEEPS", 20)
    plan = {"lane": "A"}
    write_json(tmp_path / "registration.json", {"plan": plan})
    directory = tmp_path / "sweeps"
    directory.mkdir()
    for step, residual in ((0, 0.04), (10, 0.02), (20, 0.02)):
        artifact = directory / f"sweep-{step:03}.npz"
        artifact.write_bytes(str(step).encode())
        write_json(artifact.with_suffix(".json"), {
            "sweep": step, "continuous_residual": residual, "continuous_sha256": sha256(artifact),
        })
    points, pins, best = tool.completed_sweeps(tmp_path, plan)
    assert [point["sweep"] for point in points] == [0, 10, 20]
    assert len(pins) == 7
    assert best.name == "sweep-010.npz"
    with pytest.raises(ValueError, match="different registered lane"):
        tool.completed_sweeps(tmp_path, {"lane": "B"})
    (directory / "sweep-020.npz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="invalid sweep checkpoint"):
        tool.completed_sweeps(tmp_path, plan)
