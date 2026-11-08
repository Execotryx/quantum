"""Bounded S2 optimizer with independently checked S1 and exact checkpoints."""

import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from qcompile.artifacts import deterministic_npz
from qcompile.io import sha256, write_json

from .factorization import direct_residual, factor_rows, svec
from .offset_restoration import require_s1, restore_offsets
from .refit import FixedWordRefit, encode_vectors
from .smooth_objective import augmented_objective, smooth_terms

Floats = NDArray[np.float64]
Evaluator = Callable[[Floats, Floats, Floats], dict[str, Any]]
Checkpoint = Callable[[int, Floats, Floats, Floats, dict[str, Any]], Any]


def checkpoint_writer(directory: Path) -> Checkpoint:
    """Create a fresh store of uniquely numbered, hashed development checkpoints."""
    directory.mkdir(parents=True, exist_ok=False)
    counter = 0

    def save(evaluation: int, vectors: Floats, weights: Floats, offsets: Floats,
             receipt: dict[str, Any]) -> None:
        nonlocal counter
        counter += 1
        artifact = directory / f"checkpoint-{counter:05}.npz"
        deterministic_npz(artifact, {"U": vectors, "W": weights, "offsets": offsets})
        metrics = {key: (bool(value) if isinstance(value, (bool, np.bool_)) else
                         float(value) if np.isfinite(value) else None)
                   for key, value in receipt["metrics"].items()}
        record = {**receipt, "metrics": metrics, "evaluation": evaluation,
                  "checkpoint_sha256": sha256(artifact), "scope": "development; not a release NPZ"}
        write_json(directory / f"checkpoint-{counter:05}.json", record)

    return save


def pinned_checkpoint(api: Any, math_api: Any, inputs: Any, vectors: Floats, weights: Floats,
                      offsets: Floats, brot: int) -> tuple[Any, Any, dict[str, Any]]:
    """Regenerate decoded one-body words and call the pinned evaluator."""
    r, b, n = vectors.shape
    unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
    params = {**inputs.params, "U": unit, "W": weights, "H2_I": offsets + weights.sum(axis=1)}
    native_w, native_offsets, _, _ = api.native_inputs(params)
    candidate = replace(inputs, params=params, w=native_w, W=native_offsets)
    body = encode_vectors(unit.reshape(r * b, n), params["tree_edges"], brot)
    words = np.concatenate((np.zeros((n, n - 1), dtype=np.int64), body))
    return FixedWordRefit(api, math_api, candidate, words, brot).evaluate(1.0, 1.0)


def optimize_s2(target: Floats, vectors: Floats, weights: Floats, s1_status: str,
                h1_base: Floats, gap_base: float, evaluate: Evaluator, checkpoint: Checkpoint, *,
                max_evaluations: int, max_seconds: float, restore_evaluations: int,
                offset_bound: float, checkpoint_interval: int = 500, penalty: float = 1.0,
                outer_iterations: int = 3, residual_limit: float = 0.019,
                decoded_limit: float = 0.0195, lambda_floor: float = 49.05,
                gap_floor: float = 3.916, gap_target: float = 3.9161) -> dict[str, Any]:
    """Optimize a passing S1 checkpoint; exact evaluator and persistence are injected.

    Objective evaluations and elapsed-time checks are bounded. Native calls are
    not preempted; production runs need an external process-tree deadline.
    The checkpoint callback must persist arrays and exact metrics as a unit.
    """
    if (type(max_evaluations) is not int or max_evaluations < 1 or type(checkpoint_interval) is not int
            or not 1 <= checkpoint_interval <= 500 or type(outer_iterations) is not int
            or outer_iterations < 1 or not np.isfinite(max_seconds) or max_seconds <= 0
            or not np.isfinite(penalty) or penalty <= 0 or not 0 < residual_limit <= 0.019
            or not 0 < decoded_limit <= 0.0195 or not np.isfinite(lambda_floor) or lambda_floor < 49.05
            or not np.isfinite(gap_floor) or gap_floor < 3.916):
        raise ValueError("invalid S2 budget")
    s1_residual = require_s1(target, vectors, weights, s1_status, residual_limit=residual_limit)
    started = time.monotonic()
    restoration = restore_offsets(
        vectors, weights, h1_base, gap_base, lambda offsets: evaluate(vectors, weights, offsets),
        max_evaluations=restore_evaluations, max_seconds=max_seconds, offset_bound=offset_bound,
        lambda_floor=lambda_floor, gap_floor=gap_floor, gap_target=gap_target,
    )
    if restoration["status"] != "restored":
        return {"status": restoration["status"], "stage": "restoration", "restoration": restoration,
                "s1_residual": s1_residual}
    shape_v, shape_w = vectors.shape, weights.shape
    split_v, split_w = vectors.size, vectors.size + weights.size
    flat = np.concatenate((vectors.ravel(), weights.ravel(), restoration["offsets"].ravel()))
    multipliers = np.zeros(3)
    evaluations = 0
    last_checkpoint = -1
    best = None
    deadline = started + max_seconds
    reason = "iteration limit"

    class Stop(Exception):
        pass

    def unpack(values: Floats) -> tuple[Floats, Floats, Floats]:
        return (values[:split_v].reshape(shape_v), values[split_v:split_w].reshape(shape_w),
                values[split_w:].reshape(shape_w[0], shape_w[2]))

    def emit(values: Floats) -> tuple[dict[str, Any], float]:
        nonlocal last_checkpoint, best
        v, w, offsets = unpack(values)
        unit = v / np.linalg.norm(v, axis=-1, keepdims=True)
        features = svec(unit[..., :, None] * unit[..., None, :])
        residual = direct_residual(target, factor_rows(features, w))
        metrics = evaluate(unit, w, offsets)
        finite = all(np.isfinite(metrics.get(k, float("nan"))) for k in
                     ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff"))
        eligible = bool(finite and residual <= residual_limit and metrics["error_1"] <= decoded_limit
                        and metrics["error_2"] <= decoded_limit and metrics["Lambda"] >= lambda_floor
                        and metrics["E_gap"] >= gap_floor and metrics["gap_in_domain"])
        terms = smooth_terms(unit, w, offsets, h1_base, gap_base)[0]
        radicand = terms[1] * (2 * terms[0] - terms[1])
        smooth_effective = float(np.sqrt(radicand)) if terms[1] > 0 and radicand > 0 else None
        exact_effective = float(metrics["lambda_eff"]) if finite else None
        relative_difference = (abs(smooth_effective - exact_effective) / abs(exact_effective)
                               if smooth_effective is not None and exact_effective not in (None, 0.0) else None)
        receipt = {"continuous_residual": residual, "metrics": metrics, "eligible": eligible,
                   "smooth_lambda_eff": smooth_effective, "relative_smoothing_difference": relative_difference}
        checkpoint_ref = checkpoint(evaluations, unit.copy(), w.copy(), offsets.copy(), receipt)
        last_checkpoint = evaluations
        if eligible and (best is None or metrics["lambda_eff"] < best["lambda_eff"]):
            best = {"evaluation": evaluations, "lambda_eff": float(metrics["lambda_eff"]),
                    "checkpoint": checkpoint_ref}
        return metrics, residual

    def objective(values: Floats) -> tuple[float, Floats]:
        nonlocal evaluations, flat
        if evaluations >= max_evaluations or time.monotonic() >= deadline:
            raise Stop
        v, w, offsets = unpack(values)
        value, gv, gw, go = augmented_objective(
            target, v, w, offsets, h1_base, gap_base, multipliers, penalty,
            residual_limit=residual_limit, lambda_floor=lambda_floor, gap_floor=gap_floor,
        )
        evaluations += 1
        flat = values.copy()
        if evaluations % checkpoint_interval == 0:
            emit(flat)
        return value, np.concatenate((gv.ravel(), gw.ravel(), go.ravel()))

    emit(flat)
    try:
        for _ in range(outer_iterations):
            result = minimize(objective, flat, jac=True, method="L-BFGS-B",
                              bounds=[(None, None)] * split_w + [(-offset_bound, offset_bound)] * (flat.size - split_w),
                              options={"maxiter": max_evaluations, "maxfun": max_evaluations})
            flat = result.x.copy()
            reason = str(result.message)
            metrics, residual = emit(flat)
            constraints = np.array([residual**2 - residual_limit**2, lambda_floor - metrics["Lambda"],
                                    gap_floor - metrics["E_gap"]])
            multipliers = np.maximum(0, multipliers + penalty * constraints)
            if evaluations >= max_evaluations or time.monotonic() >= deadline:
                break
    except Stop:
        reason = "registered evaluation or wall cap"
    except ValueError as error:
        if "outside its domain" not in str(error):
            raise
        reason = "smooth objective left its domain"
    if last_checkpoint != evaluations:
        emit(flat)
    capped = evaluations >= max_evaluations or time.monotonic() >= deadline
    return {"status": "budget_limited" if capped else "inconclusive", "stage": "s2",
            "reason": reason, "evaluations": evaluations, "s1_residual": s1_residual,
            "best_eligible_checkpoint": best, "restoration": restoration,
            "scope": "development checkpoints; no promotion or improvement claim"}
