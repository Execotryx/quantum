"""Registered loader input gates and native synthetic worker integration."""

import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from qcompile.io import read_json, sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    if not sys.platform.startswith("linux"):
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_loader_rank")


def test_reference_control_pins_and_archive_tree(tool, project_root):
    plan = read_json(project_root / "tools/chem-loader-reference-control.json")
    if not Path(plan["words"]["path"]).exists() or not Path(plan["factorization"]["path"]).exists():
        pytest.skip("reference chemistry fixture unavailable")
    paths = tool.validate_registration(plan)
    words, edges = tool.load_words(paths["words"])
    assert words.shape == (3976, 75)
    assert edges.shape == (75, 2)
    bad = {**plan, "brot": 11}
    with pytest.raises(ValueError, match="pinned factorization"):
        tool.validate_registration(bad)


def test_s3_handoff_rejects_unselected_or_failed_step(tool, tmp_path):
    worker = tmp_path / "worker"
    directory = worker / "precision-10"
    directory.mkdir(parents=True)
    factor, words = directory / "submission.npz", directory / "words.npy"
    factor.write_bytes(b"factor")
    words.write_bytes(b"words")
    metrics = {"error_1": 0.01, "error_2": 0.01, "Lambda": 50.0, "E_gap": 4.0,
               "lambda_eff": 20.0, "gap_in_domain": True}
    result = directory / "result.json"
    write_json(result, {"eligible": True, "metrics": metrics,
                        "hashes": {"submission.npz": sha256(factor), "words.npy": sha256(words)}})
    decision = worker / "decision.json"
    write_json(decision, {"status": "budget_limited", "last_passing": 10,
                          "steps": [{"brot": 10, "eligible": True,
                                     "result": {"checkpoint": "precision-10"}}]})
    reg = worker / "registration.json"
    write_json(reg, {"plan_sha256": "a" * 64})
    paths = {"factorization": factor, "words": words, "s3_registration": reg,
             "s3_decision": decision, "s3_result": result}
    plan = {"mode": "s3", **{key: {"path": str(value), "sha256": sha256(value)} for key, value in paths.items()},
            "brot": 10, "low_bits": 1, "shots_per_address": 2, "seed": 3, "wall_seconds": 60}
    tool.validate_registration(plan)
    bad = {**plan, "brot": 9}
    with pytest.raises(ValueError, match="terminal S3 passing"):
        tool.validate_registration(bad)


@pytest.mark.official
def test_synthetic_worker_builds_two_identical_native_families(tool, tmp_path, monkeypatch):
    settings, km, api, _, _ = import_module("banked_chemistry").backend()
    factor, words_file = tmp_path / "factor.npz", tmp_path / "words.npy"
    factor.write_bytes(b"synthetic reference bytes")
    words = np.random.default_rng(351).integers(0, 16, size=(7, 4), dtype=np.int64)
    np.save(words_file, words, allow_pickle=False)
    plan = {"mode": "s3", "brot": 4, "low_bits": 1, "shots_per_address": 2,
            "seed": 73, "wall_seconds": 60}
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    metrics = {"error_1": 0.01, "error_2": 0.01, "Lambda": 50.0, "E_gap": 4.0,
               "lambda_eff": 20.0, "gap_in_domain": True}
    result = tmp_path / "s3-result.json"
    write_json(result, {"metrics": metrics})
    paths = {"factorization": factor, "words": words_file, "s3_result": result}
    monkeypatch.setattr(tool, "validate_registration", lambda _: paths)

    class Verifier:
        @staticmethod
        def evaluate_words(*_args, **_kwargs):
            return metrics

        @staticmethod
        def passes_accuracy(_metrics):
            return True

    inputs = SimpleNamespace(num_orbitals=5, w=np.zeros((1, 2, 1)), params={"tree_edges": np.zeros((4, 2))})
    monkeypatch.setattr(tool, "backend", lambda: (settings, km, api, None, Verifier))
    monkeypatch.setattr(tool, "fixed_inputs", lambda *_: inputs)
    monkeypatch.setattr(tool, "rank_complete_cost", lambda _api, _inputs, candidates, _brot, _lam: [
        {"batch": candidates[0][0], "modeled_cost": float(candidates[0][0]), "resources": {}}
    ])
    output = tmp_path / "output"
    tool.run_worker(plan_path, output, sha256(plan_path))
    report = read_json(output / "ranking.json")
    assert report["selected_batch"] == 3
    assert report["independent_build_hashes"][0] == report["independent_build_hashes"][1]
    assert report["nonzero_fixtures"][0]["valid_addresses"] == 7
    assert report["verified_shots_per_candidate"] == 14
