"""Precision-ladder gates and decoded fixed-basis refitting."""

import time

import numpy as np
import pytest

from qcompile.chemistry.precision import passes_margins, precision_ladder, refit_weights


def metrics(**updates):
    return {"error_1": 0.01, "error_2": 0.01, "Lambda": 50.0, "E_gap": 4.0,
            "lambda_eff": 20.0, "gap_in_domain": True, **updates}


@pytest.mark.parametrize("bad", [
    {"error_1": 0.0196}, {"error_2": 0.0196}, {"Lambda": 49.04}, {"E_gap": 3.915},
    {"gap_in_domain": False}, {"lambda_eff": float("nan")}, {"error_2": -1.0},
])
def test_every_exact_margin_is_required(bad):
    assert passes_margins(metrics())
    assert not passes_margins(metrics(**bad))


def test_ladder_stops_and_preserves_last_passing_precision():
    visited = []

    def stage(bits):
        visited.append(bits)
        return {"metrics": metrics(error_2=0.02 if bits == 9 else 0.01), "capped": False, "converged": True}

    result = precision_ladder(stage)
    assert visited == [12, 11, 10, 9]
    assert result["last_passing"] == 10
    assert result["status"] == "step_failed"


def test_capped_failing_refit_does_not_claim_a_precision_failure():
    result = precision_ladder(lambda _: {"metrics": metrics(error_2=0.02), "capped": True, "converged": False})
    assert result["status"] == "budget_limited"
    assert result["last_passing"] is None


def test_no_completed_refit_cannot_admit_a_passing_metric():
    result = precision_ladder(lambda _: {"metrics": metrics(), "eligible": False,
                                         "capped": True, "converged": False})
    assert result["status"] == "budget_limited"
    assert result["last_passing"] is None


def test_failed_unconverged_refit_is_inconclusive():
    result = precision_ladder(lambda _: {"metrics": metrics(error_2=0.02), "capped": False, "converged": False})
    assert result["status"] == "inconclusive"
    assert result["last_passing"] is None


def test_all_decoded_weights_are_refit():
    decoded = np.eye(2)[None, :, :]
    target = np.diag([4.0, 0.0, 9.0])
    initial = np.array([[[0.8, 0.4], [0.2, 0.7]]])
    result = refit_weights(target, decoded, initial, max_evaluations=300, deadline=time.monotonic() + 10)
    assert result["residual"] < 1e-5
    assert result["evaluations"] <= 300
    assert np.linalg.norm(result["weights"] - initial) > 0.1
