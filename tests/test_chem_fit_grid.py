"""Grid registrations and initializer ranking are source/profile bound."""

import hashlib
from importlib import import_module

import numpy as np
import pytest

from qcompile.io import read_json, sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_fit_grid")


def profile_receipt(directory, shape, factor_hash, source_hashes=None):
    directory.mkdir(parents=True)
    (directory / "measurement").mkdir()
    plan = {"shape": shape, "factorization_sha256": factor_hash}
    registration = directory / "registration.json"
    report = directory / "measurement/profile.json"
    write_json(registration, {"plan": plan, "plan_sha256": "a" * 64, "source_hashes": source_hashes or {}})
    write_json(report, {"plan": plan, "plan_sha256": "a" * 64, "objective_gradient_seconds": 0.4,
                        "direct_residual": 1.0, "pinned_tensor_residual": 1.0, "process_peak_rss_kib": 1000})
    write_json(directory / "completion.json", {"profile_sha256": sha256(report),
                                               "registration_sha256": sha256(registration)})
    return sha256(report)


def test_manifest_has_24_explicit_lanes_and_blocks_unranked(tool, tmp_path):
    factor = tmp_path / "factor.npz"
    factor.write_bytes(b"pinned")
    factor_hash = sha256(factor)
    profiles = {}
    for r, b, c in tool.SHAPES:
        label = f"r{r}-b{b}-c{c}"
        directory = tmp_path / label
        digest = profile_receipt(directory, [r, b, c], factor_hash)
        profiles[label] = {"profile_directory": str(directory), "profile_sha256": digest,
                           "ranking_path": str(directory / "rank/ranking.json"), "ranking_sha256": None}
    plan = {"factorization": {"path": str(factor), "sha256": factor_hash}, "target_sha256": "b" * 64,
            "seeds": [184, 185], "limits": {"evaluations": 20000, "wall_seconds": 18000}, "shapes": profiles}
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    output = tmp_path / "manifest"
    tool.manifest(plan_path, output)
    report = read_json(output / "manifest.json")
    lanes = report["lanes"]
    assert len(lanes) == len({lane["id"] for lane in lanes}) == 24
    assert sum(lane["seed_semantics"] == "ignored; deterministic repeated execution" for lane in lanes) == 16
    assert all(not lane["ready"] for lane in lanes)
    assert len(list(output.glob("r*.json"))) == 0
    assert len(report["controls"]) == 2
    repeat = tmp_path / "manifest-repeat"
    tool.manifest(plan_path, repeat)
    assert sha256(output / "manifest.json") == sha256(repeat / "manifest.json")

    for r, b, c in tool.SHAPES:
        label = f"r{r}-b{b}-c{c}"
        item = profiles[label]
        rank_directory = tmp_path / label / "rank"
        rank_directory.mkdir()
        ranking = []
        for index, (name, seed) in enumerate((("I1", None), ("I2", 184), ("I2", 185), ("I3", None), ("I4", 184))):
            artifact = rank_directory / f"initializer-{index}.npz"
            artifact.write_bytes(f"artifact {index}".encode())
            ranking.append({"initializer": name, "seed": seed, "checkpoint": artifact.name,
                            "initializer_sha256": sha256(artifact)})
        rank_registration = rank_directory / "registration.json"
        write_json(rank_registration, {"profile_sha256": item["profile_sha256"], "source_hashes": {}})
        write_json(item["ranking_path"], {"shape": [r, b, c], "factorization_sha256": factor_hash,
                                         "target_sha256": plan["target_sha256"],
                                         "profile_sha256": item["profile_sha256"], "ranking": ranking})
        item["ranking_sha256"] = sha256(item["ranking_path"])
        write_json(rank_directory / "completion.json", {"ranking_sha256": item["ranking_sha256"],
                                                        "registration_sha256": sha256(rank_registration)})
    ranked_plan = tmp_path / "ranked-plan.json"
    write_json(ranked_plan, plan)
    ready = tmp_path / "ready"
    tool.manifest(ranked_plan, ready)
    ready_report = read_json(ready / "manifest.json")
    assert all(lane["ready"] for lane in ready_report["lanes"])
    assert len(list(ready.glob("r*.json"))) == 24
    for lane in ready_report["lanes"]:
        actual = read_json(ready / f"{lane['id']}.json")
        assert actual["profile_sha256"] == lane["profile_sha256"]
        assert actual["initializer"] == lane["initializer"]
        assert sha256(ready / f"{lane['id']}.json") == lane["plan_sha256"]
    artifact = tmp_path / "r9-b143-c40/rank/initializer-0.npz"
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="initializer artifact differs"):
        tool.manifest(ranked_plan, tmp_path / "tampered")


def test_synthetic_preoptimization_rank_has_all_initializers(tool, tmp_path, monkeypatch):
    shape = (1, 2, 2)
    monkeypatch.setattr(tool, "SHAPES", (shape,))
    factor = tmp_path / "factor.npz"
    factor.write_bytes(b"pinned")
    factor_hash = sha256(factor)
    directory = tmp_path / "profile"
    profile_receipt(directory, list(shape), factor_hash, tool.source_hashes())
    target = np.diag(np.arange(1, 7, dtype=float))
    rng = np.random.default_rng(5)
    inputs = type("Inputs", (), {"num_orbitals": 3, "params": {"U": rng.normal(size=(2, 2, 3))},
                                 "w": rng.normal(size=(2, 2, 2)), "ref": {"tei": None}, "S": None})()
    monkeypatch.setattr(tool, "backend", lambda: ({"fixture": True}, None, None, None, None))
    monkeypatch.setattr(tool, "fixed_inputs", lambda *_: inputs)
    monkeypatch.setattr(tool, "shifted_target", lambda *_: target)
    plan = {"factorization": {"path": str(factor), "sha256": factor_hash}, "shape": shape,
            "target_sha256": hashlib.sha256(memoryview(target).cast("B")).hexdigest(),
            "profile_directory": str(directory)}
    path = tmp_path / "rank-plan.json"
    write_json(path, plan)
    output = tmp_path / "rank"
    tool.rank_initializers(path, output)
    entries = read_json(output / "ranking.json")["ranking"]
    assert {(entry["initializer"], entry["seed"]) for entry in entries} == {
        ("I1", None), ("I2", 184), ("I2", 185), ("I3", None), ("I4", 184)}
    assert [entry["projection_score"] for entry in entries] == sorted(entry["projection_score"] for entry in entries)
    for entry in entries:
        assert sha256(output / entry["checkpoint"]) == entry["initializer_sha256"]
