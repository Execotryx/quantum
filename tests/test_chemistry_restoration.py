"""S1 admission and bounded, exact-checked identity-offset restoration."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from qcompile.chemistry.offset_restoration import require_s1, restore_offsets
from qcompile.chemistry.s2 import checkpoint_writer, optimize_s2, pinned_checkpoint
from qcompile.io import read_json, sha256


def test_s1_gate_checks_status_and_recomputed_residual():
    vectors = np.ones((1, 1, 1))
    weights = np.ones((1, 1, 1))
    assert require_s1(np.ones((1, 1)), vectors, weights, "go") == pytest.approx(0)
    with pytest.raises(ValueError, match="go S1"):
        require_s1(np.ones((1, 1)), vectors, weights, "budget_limited")
    with pytest.raises(ValueError, match="residual gate"):
        require_s1(np.array([[2.0]]), vectors, weights, "go")


def test_bounded_restoration_checks_exact_domain_and_margin():
    vectors = np.ones((1, 1, 1))
    weights = np.ones((1, 1, 1))
    checked = []

    def exact(offsets):
        offset = float(offsets[0, 0])
        gap = 2 * max(0, 5 + offset) + offset**2 / 2
        checked.append(offset)
        return {"Lambda": 4.4, "E_gap": gap, "gap_in_domain": 0 < gap <= 8.8}

    result = restore_offsets(vectors, weights, np.array([[-5.0]]), 0, exact,
                             max_evaluations=40, max_seconds=10, offset_bound=5,
                             lambda_floor=4.0, gap_floor=8.5, gap_target=8.6)
    assert result["status"] == "restored"
    assert 8.5 <= result["metrics"]["E_gap"] <= 8.8
    assert float(result["offsets"][0, 0]) == checked[-1]
    assert result["evaluations"] <= 40


def test_exhaustion_does_not_claim_infeasibility():
    vectors = np.ones((1, 1, 1))
    weights = np.ones((1, 1, 1))

    def impossible_at_registered_domain(offsets):
        return {"Lambda": 4.4, "E_gap": 20 + float(np.sum(offsets**2)) / 2,
                "gap_in_domain": False}

    result = restore_offsets(vectors, weights, np.zeros((1, 1)), 20, impossible_at_registered_domain,
                             max_evaluations=2, max_seconds=10, offset_bound=1,
                             lambda_floor=4.0, gap_floor=8.5, gap_target=8.6)
    assert result["status"] in ("inconclusive", "budget_limited")
    assert result["scope"] == "bounded search; no infeasibility conclusion"


def test_restoration_never_admits_lambda_below_floor():
    vectors = np.ones((1, 1, 1))
    weights = np.ones((1, 1, 1))

    def exact(_offsets):
        return {"Lambda": 1.0, "E_gap": 1.0, "gap_in_domain": True}

    result = restore_offsets(vectors, weights, np.zeros((1, 1)), 1.0, exact,
                             max_evaluations=3, max_seconds=10, offset_bound=1,
                             lambda_floor=2.0, gap_floor=0.5, gap_target=0.6)
    assert result["status"] in ("inconclusive", "budget_limited")


def test_s2_orchestration_requires_s1_and_records_exact_checkpoints(tmp_path):
    vectors = np.ones((1, 1, 1))
    weights = np.full((1, 1, 1), 10.0)
    target = np.full((1, 1), 100.0)
    seen = []
    destination = tmp_path / "checkpoints"
    persist = checkpoint_writer(destination)

    def exact(v, w, offsets):
        weight, offset = float(w[0, 0, 0]), float(offsets[0, 0])
        h1 = -offset * weight
        lam = abs(h1) + (abs(weight) + abs(offset + weight)) ** 2 / 4
        gap = 4 + abs(h1) - h1 + offset**2 / 2
        domain = 0 < gap < 2 * lam
        return {"Lambda": lam, "E_gap": gap, "gap_in_domain": domain,
                "lambda_eff": np.sqrt(gap * (2 * lam - gap)) if domain else np.nan,
                "error_1": 0.0, "error_2": abs(weight**2 - 100)}

    def checkpoint(evaluation, v, w, offsets, receipt):
        seen.append((evaluation, receipt))
        persist(evaluation, v, w, offsets, receipt)

    def run(status):
        return optimize_s2(target, vectors, weights, status, np.zeros((1, 1)), 4, exact, checkpoint,
                           max_evaluations=2, max_seconds=10, restore_evaluations=10, offset_bound=2,
                           checkpoint_interval=1)

    with pytest.raises(ValueError, match="go S1"):
        run("budget_limited")
    assert not seen
    with pytest.raises(ValueError, match="budget"):
        optimize_s2(target, vectors, weights, "go", np.zeros((1, 1)), 4, exact, checkpoint,
                    max_evaluations=2, max_seconds=10, restore_evaluations=10, offset_bound=2,
                    residual_limit=0.02)
    result = run("go")
    assert result["evaluations"] <= 2
    assert seen[0][0] == 0
    assert seen[0][1]["eligible"]
    assert "relative_smoothing_difference" in seen[0][1]
    assert all(np.isfinite(item[1]["metrics"]["Lambda"]) for item in seen)
    assert result["best_eligible_checkpoint"]["lambda_eff"] == pytest.approx(
        min(receipt["metrics"]["lambda_eff"] for _, receipt in seen if receipt["eligible"])
    )
    files = sorted(destination.glob("checkpoint-*.json"))
    assert len(files) == len(seen)
    for record_path in files:
        record = read_json(record_path)
        assert record["checkpoint_sha256"] == sha256(record_path.with_suffix(".npz"))


def test_pinned_checkpoint_regenerates_words_against_pinned_math():
    source = (Path(__file__).resolve().parents[1] / "vendor/official/verifiers/dfthcsos"
              / "scoreinfra/dfthc_math.py")
    if not source.exists():
        pytest.skip("pinned verifier sources unavailable")
    spec = importlib.util.spec_from_file_location("pinned_checkpoint_math", source)
    assert spec and spec.loader
    math_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(math_api)
    ref = {"oei": np.diag([-2.0, 1.0]), "tei": np.zeros((2, 2, 2, 2)), "electrons": 2, "ecore": -1.0}
    edges = np.array([[0, 1]], dtype=np.int64)

    @dataclass
    class Inputs:
        params: dict
        w: np.ndarray
        W: np.ndarray
        S: np.ndarray
        ref: dict
        beta_1: float = 0.0
        num_orbitals: int = 2

        @property
        def num_vectors(self):
            return 2 + self.w.shape[0] * self.w.shape[1]

    class API:
        @staticmethod
        def native_inputs(params):
            w = params["W"]
            return w, params["H2_I"] - w.sum(axis=1), None, None

        @staticmethod
        def load_tree_edges(tree, _):
            return tree

        @staticmethod
        def evaluate_words(inputs, words, *, brot, tree_edges):
            return math_api.evaluate_dfthc_angle_words(words, inputs.w, inputs.W, inputs.S, inputs.beta_1,
                                                      inputs.ref, brot=brot, tree_edges=tree_edges,
                                                      energy_upper=5.0)

    vectors = np.array([[[0.8, 0.6]]])
    weights = np.array([[[1.2]]])
    offsets = np.array([[0.4]])
    inputs = Inputs({"tree_edges": edges}, weights, offsets, np.zeros((2, 2)), ref)
    params, words, metrics = pinned_checkpoint(API, math_api, inputs, vectors, weights, offsets, 12)
    expected = math_api.evaluate_dfthc_angle_words(words, params["W"], params["H2_I"] - params["W"].sum(axis=1),
                                                   inputs.S, inputs.beta_1, ref, brot=12, tree_edges=edges,
                                                   energy_upper=5.0)
    for key in ("Lambda", "E_gap", "error_1", "error_2"):
        assert metrics[key] == pytest.approx(expected[key])
