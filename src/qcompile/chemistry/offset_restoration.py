"""Bounded identity-offset restoration for a fixed continuous factorization."""

import time
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from .factorization import direct_residual, factor_rows, svec

Floats = NDArray[np.float64]
ExactMetrics = Callable[[Floats], dict[str, Any]]


def require_s1(target: Floats, vectors: Floats, weights: Floats, status: str,
               *, residual_limit: float = 0.019) -> float:
    """Independently recompute the continuous S1 gate before later stages."""
    if status != "go" or not np.isfinite(residual_limit) or residual_limit <= 0:
        raise ValueError("S2 requires a go S1 decision and a positive residual limit")
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if not np.all(np.isfinite(lengths)) or np.any(lengths == 0):
        raise ValueError("invalid S1 vectors")
    unit = vectors / lengths
    features = svec(unit[..., :, None] * unit[..., None, :])
    residual = direct_residual(target, factor_rows(features, weights))
    if not np.isfinite(residual) or residual > residual_limit:
        raise ValueError("S1 checkpoint does not pass the continuous residual gate")
    return residual


def restore_offsets(vectors: Floats, weights: Floats, h1_base: Floats, gap_base: float,
                    exact_metrics: ExactMetrics, *, max_evaluations: int, max_seconds: float,
                    offset_bound: float, lambda_floor: float = 49.05, gap_floor: float = 3.916,
                    gap_target: float = 3.9161, epsilon: float = 1e-8) -> dict[str, Any]:
    """Search a bounded offset box and check admission points with pinned metrics.

    The gap is convex in offsets: its variable part is the trace norm minus
    trace of an affine symmetric matrix, plus half the squared offset norm.
    This routine uses a smooth trace-norm derivative for the search and the
    caller's exact evaluator for all decisions. Exhaustion never proves that
    the box, a shape, or the original problem is infeasible.
    """
    if (type(max_evaluations) is not int or max_evaluations < 1 or not np.isfinite(max_seconds)
            or max_seconds <= 0 or not np.isfinite(offset_bound) or offset_bound <= 0
            or not np.isfinite(epsilon) or epsilon <= 0
            or not 0 < gap_floor < gap_target or not 0 < lambda_floor):
        raise ValueError("invalid restoration registration")
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if not np.all(np.isfinite(lengths)) or np.any(lengths == 0):
        raise ValueError("basis vectors must be finite and nonzero")
    unit = vectors / lengths
    x = np.einsum("rbc,rbi,rbj->rcij", weights, unit, unit, optimize=True)
    initial = np.zeros(x.shape[:2], dtype=np.float64)
    deadline = time.monotonic() + max_seconds
    evaluations = 0
    exact_evaluations = 0
    best_gap = float("inf")
    best = initial.copy()

    class LimitReached(Exception):
        pass

    def gap_and_gradient(flat: Floats) -> tuple[float, Floats]:
        nonlocal evaluations, best_gap, best
        if evaluations >= max_evaluations or time.monotonic() >= deadline:
            raise LimitReached
        evaluations += 1
        offsets = flat.reshape(initial.shape)
        h1 = h1_base - np.einsum("rc,rcij->ij", offsets, x, optimize=True)
        eig, rotation = np.linalg.eigh(h1)
        value = float(gap_base + np.sum(np.abs(eig) - eig) + 0.5 * np.sum(offsets * offsets))
        signed = (rotation * (eig / np.sqrt(eig * eig + epsilon * epsilon))) @ rotation.T
        grad = offsets - np.einsum("ij,rcij->rc", signed - np.eye(len(eig)), x, optimize=True)
        if np.isfinite(value) and value < best_gap:
            best_gap, best = value, offsets.copy()
        return value, grad.ravel()

    def check(offsets: Floats) -> tuple[dict[str, Any], bool]:
        nonlocal exact_evaluations
        exact_evaluations += 1
        metrics = exact_metrics(offsets)
        lam, gap = float(metrics["Lambda"]), float(metrics["E_gap"])
        valid = (np.isfinite(lam) and np.isfinite(gap) and lam >= lambda_floor
                 and gap >= gap_floor and 0 < gap <= 2 * lam and bool(metrics["gap_in_domain"]))
        return metrics, bool(valid)

    initial_metrics, valid = check(initial)
    if valid:
        return {"status": "restored", "offsets": initial, "metrics": initial_metrics,
                "evaluations": 0, "exact_evaluations": exact_evaluations}
    try:
        result = minimize(gap_and_gradient, initial.ravel(), method="L-BFGS-B", jac=True,
                          bounds=[(-offset_bound, offset_bound)] * initial.size,
                          options={"maxfun": max_evaluations, "maxiter": max_evaluations})
        optimizer = str(result.message)
    except LimitReached:
        optimizer = "registered evaluation or wall cap"
    best_metrics, valid = check(best)
    if valid:
        return {"status": "restored", "offsets": best, "metrics": best_metrics,
                "evaluations": evaluations, "exact_evaluations": exact_evaluations, "optimizer": optimizer}
    # If the gap minimum lies below the desired margin, continuity allows a
    # bounded segment search from the original offsets to that minimum.
    if (float(initial_metrics["E_gap"]) > gap_target > float(best_metrics["E_gap"])
            and time.monotonic() < deadline):
        lo, hi = 0.0, 1.0
        for _ in range(32):
            if time.monotonic() >= deadline:
                break
            mid = (lo + hi) / 2
            candidate = best * mid
            metrics, valid = check(candidate)
            if valid:
                return {"status": "restored", "offsets": candidate, "metrics": metrics,
                        "evaluations": evaluations, "exact_evaluations": exact_evaluations,
                        "optimizer": optimizer}
            if float(metrics["E_gap"]) > gap_target:
                lo = mid
            else:
                hi = mid
    return {"status": "budget_limited" if evaluations >= max_evaluations or time.monotonic() >= deadline
            else "inconclusive", "offsets": best, "metrics": best_metrics,
            "evaluations": evaluations, "exact_evaluations": exact_evaluations,
            "optimizer": optimizer, "scope": "bounded search; no infeasibility conclusion"}
