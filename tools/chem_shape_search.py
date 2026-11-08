"""Rank the registered DFTHC grid and evaluate a bounded continuous shape pilot."""

import argparse
import itertools
import os
import time
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs, rank_layouts
from scipy.optimize import minimize

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import (
    direct_residual,
    factor_rows,
    gram_residual,
    initialize,
    rank_lower_bound,
    shifted_target,
    svec,
)
from qcompile.chemistry.refit import FixedWordRefit, encode_vectors
from qcompile.io import read_json, sha256, write_json


def rank(output: Path) -> None:
    settings, _, _, _, api = backend()
    layouts = [
        dict(r=r, b=b, c=c, brot=brot, batch=batch)
        for r, b, c, brot, batch in itertools.product(
            (8, 9, 10, 11), (120, 129, 136, 143), (36, 39, 40, 42, 45, 48), (7, 8), (3, 5)
        )
    ]
    ranked = []
    for start in range(0, len(layouts), 64):
        ranked.extend(rank_layouts(api, layouts[start:start + 64]))
    ranked.sort(key=lambda v: (not v["within_cap"], v["preparation_rotation_tq"]))
    controls = rank_layouts(api, [
        dict(name="certified-j9", r=65, b=60, c=60, brot=12, batch=9, bank=7),
        dict(name="generalized-j9", r=65, b=60, c=60, brot=12, batch=9, bank=7),
        dict(name="reference-j8", r=65, b=60, c=60, brot=12, batch=8),
        dict(name="wide-rc", r=10, b=129, c=129, brot=12, batch=9, bank=6),
    ])
    write_json(output, {"scope": "structural only", "backend": settings, "ranked": ranked, "controls": controls})


def pilot(plan_path: Path, output: Path) -> None:
    plan = read_json(plan_path)
    source = Path(plan["factorization"])
    if sha256(source) != plan["factorization_sha256"]:
        raise ValueError("pinned factorization changed")
    shapes = [tuple(row) for row in plan["shapes"]]
    if not 1 <= len(shapes) <= 4 or not 2 <= plan["max_evaluations"] <= 20:
        raise ValueError("pilot must have at most four shapes and 20 evaluations per shape")
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, source)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": sha256(plan_path), "backend": settings,
        "blas_threads": {k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")},
        "precision": "float64",
    })
    start = time.monotonic()
    target = shifted_target(inputs.ref["tei"], inputs.S)
    spectrum, eigenvectors = np.linalg.eigh(target)
    norm = float(np.vdot(target, target))
    write_json(output / "spectrum.json", {
        "seconds": time.monotonic() - start, "positive_count": int(np.count_nonzero(spectrum > 0)),
        "rank_lower_bounds": {str(r * c): rank_lower_bound(spectrum, r * c) for r, _, c in shapes},
        "scope": "float64 diagnostic; no pruning certificate",
    })
    pinned_rows = []
    for vectors, weights in zip(inputs.params["U"], inputs.w, strict=True):
        vectors = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
        pinned_rows.append(weights.T @ svec(vectors[..., :, None] * vectors[..., None, :]))
    continuation_residual = direct_residual(target, np.concatenate(pinned_rows))
    write_json(output / "continuation.json", {
        "shape": list(inputs.w.shape), "continuous_two_body_residual": continuation_residual,
        "passes_19_5_mha": continuation_residual <= 0.0195,
    })
    n = inputs.num_orbitals
    for shape in shapes:
        r, b, c = shape
        directory = output / f"r{r}-b{b}-c{c}"
        directory.mkdir()
        basis, weights = initialize(spectrum, eigenvectors, n, shape)
        features = svec(basis[..., :, None] * basis[..., None, :])
        initial = direct_residual(target, factor_rows(features, weights))
        attempts = []
        best = weights.ravel().copy()
        best_residual = initial**2

        class EvaluationLimit(Exception):
            pass

        def objective(flat):
            nonlocal best, best_residual
            if len(attempts) >= plan["max_evaluations"]:
                raise EvaluationLimit
            rows = factor_rows(features, flat.reshape(shape))
            residual, gradient = gram_residual(target, rows, norm)
            attempts.append({"squared_residual": residual, "elapsed_seconds": time.monotonic() - start})
            if 0 <= residual < best_residual:
                best, best_residual = flat.copy(), residual
            grad_w = np.einsum("rcd,rbd->rbc", gradient.reshape(r, c, -1), features, optimize=True)
            return residual, grad_w.ravel()

        try:
            result = minimize(objective, weights.ravel(), method="L-BFGS-B", jac=True,
                              options={"maxiter": plan["max_evaluations"] - 1, "maxfun": plan["max_evaluations"]})
            stop = str(result.message)
        except EvaluationLimit:
            stop = "registered evaluation cap"
        weights = best.reshape(shape)
        final = direct_residual(target, factor_rows(features, weights))
        eligible_continuous = np.isfinite(final) and final <= 0.0195
        record = {
            "shape": shape, "initial_residual": initial, "final_residual": final, "optimizer": stop,
            "attempts": attempts, "status": "decode" if eligible_continuous else "continuous_no_go",
        }
        write_json(directory / "continuous.json", record)
        if not eligible_continuous:
            continue
        # Re-evaluate every decoded checkpoint using the pinned evaluator.
        params = {**inputs.params, "U": basis, "W": weights, "H2_I": weights.sum(axis=1)}
        w, offsets, _, _ = api.native_inputs(params)
        candidate = replace(inputs, params=params, w=w, W=offsets)
        edges = params["tree_edges"]
        for brot in (12, 11, 10, 9, 8):
            body = encode_vectors(basis.reshape(r * b, n), edges, brot)
            initial_words = np.concatenate((np.zeros((n, n - 1), dtype=np.int64), body))
            arrays, words, metrics = FixedWordRefit(api, math_api, candidate, initial_words, brot).evaluate(1, 1)
            eligible = api.passes_accuracy(metrics) and max(metrics["error_1"], metrics["error_2"]) <= 0.0195
            write_json(directory / f"precision-{brot}.json", {
                "eligible": bool(eligible),
                "metrics": {k: v if np.isfinite(v) else None for k, v in metrics.items()},
            })
            if not eligible:
                break
            deterministic_npz(directory / f"factor-{brot}.npz", arrays)
            np.save(directory / f"words-{brot}.npy", words, allow_pickle=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("rank").add_argument("output", type=Path)
    fit = actions.add_parser("pilot")
    fit.add_argument("plan", type=Path)
    fit.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.action == "rank":
        rank(args.output)
    else:
        pilot(args.plan, args.output)
