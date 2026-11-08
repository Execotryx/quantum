"""Rank the registered DFTHC grid and evaluate a bounded continuous shape pilot."""

import argparse
import hashlib
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
    clustered_initialize,
    continuation_initialize,
    direct_residual,
    factor_rows,
    gram_residual,
    initialize,
    joint_residual,
    projection_score,
    rank_lower_bound,
    shifted_target,
    svec,
)
from qcompile.chemistry.refit import FixedWordRefit, encode_vectors
from qcompile.chemistry.schema import read_factorization
from qcompile.experiments import screen_outcome
from qcompile.io import read_json, sha256, write_json


def continuation_parent(plan: dict) -> tuple[dict, dict, Path]:
    """Validate a budget-limited S1 checkpoint without changing its evidence."""
    parent = plan["parent"]
    paths = {}
    for name in ("registration", "decision", "checkpoint_receipt", "checkpoint"):
        item = parent[name]
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"parent {name} hash differs")
        paths[name] = path
    registration = read_json(paths["registration"])
    decision = read_json(paths["decision"])
    receipt = read_json(paths["checkpoint_receipt"])
    if decision.get("status") != "budget_limited":
        raise ValueError("continuation requires a budget-limited parent")
    if (registration["plan"]["factorization_sha256"] != plan["factorization_sha256"]
            or registration["plan"]["shape"] != plan["shape"]
            or receipt["continuous_sha256"] != parent["checkpoint"]["sha256"]
            or receipt["evaluations"] != decision["evaluations"]
            or not np.isclose(receipt["continuous_residual"], decision["best_continuous_residual"],
                              rtol=1e-10, atol=1e-12)):
        raise ValueError("parent registration, decision and checkpoint disagree")
    target_hash = plan["target_sha256"]
    if not isinstance(target_hash, str) or len(target_hash) != 64 or any(c not in "0123456789abcdef" for c in target_hash):
        raise ValueError("continuation requires a lowercase SHA-256 target pin")
    return decision, receipt, paths["checkpoint"]


def profile(plan_path: Path, output: Path) -> None:
    """Profile a full-shape joint evaluation and compare the pinned tensor math."""
    plan = read_json(plan_path)
    source = Path(plan["factorization"])
    if sha256(source) != plan["factorization_sha256"]:
        raise ValueError("pinned factorization changed")
    shape = tuple(plan["shape"])
    if len(shape) != 3 or any(type(x) is not int or x < 1 for x in shape):
        raise ValueError("expected a positive R, B, C shape")
    if type(plan["seed"]) is not int:
        raise ValueError("expected an integer seed")
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, source)
    n = inputs.num_orbitals
    rng = np.random.default_rng(plan["seed"])
    vectors = rng.normal(size=(*shape[:2], n))
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    weights = rng.normal(scale=1 / np.sqrt(shape[0] * shape[1] * shape[2]), size=shape)
    target = shifted_target(inputs.ref["tei"], inputs.S)
    started = time.monotonic()
    squared, grad_v, grad_w = joint_residual(target, vectors, weights, float(np.vdot(target, target)))
    elapsed = time.monotonic() - started
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    residual = direct_residual(target, factor_rows(features, weights))
    x = math_api.reconstruct_x(vectors, weights)
    x = np.tril(x) + np.swapaxes(np.tril(x, k=-1), -1, -2)
    delta = math_api.reconstruct_h2(x)
    delta -= inputs.ref["tei"]
    diagonal = np.arange(n)
    delta[:, :, diagonal, diagonal] -= 0.5 * inputs.S[:, :, None]
    delta[diagonal, diagonal, :, :] -= 0.5 * inputs.S[None, :, :]
    native = float(np.linalg.norm(delta.ravel()))
    if not np.isclose(residual, native, rtol=1e-10, atol=1e-10):
        raise ValueError("packed residual differs from pinned tensor reconstruction")
    output.mkdir(parents=True, exist_ok=False)
    resource = import_module("resource")
    write_json(output / "profile.json", {
        "plan": plan, "plan_sha256": sha256(plan_path), "backend": settings,
        "objective_gradient_seconds": elapsed, "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "blas_threads": {k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        "squared_residual": squared, "direct_residual": residual, "pinned_tensor_residual": native,
        "gradient_norms": [float(np.linalg.norm(grad_v)), float(np.linalg.norm(grad_w))],
        "scope": "one seeded full-shape evaluation; peak RSS includes loading and native comparison",
    })


def fit_joint(plan_path: Path, output: Path) -> None:
    """Run one registered S1 fit, retaining continuous and decoded checkpoints."""
    plan = read_json(plan_path)
    source, profile_path = Path(plan["factorization"]), Path(plan["profile"])
    if sha256(source) != plan["factorization_sha256"] or sha256(profile_path) != plan["profile_sha256"]:
        raise ValueError("registered input hash differs")
    shape = tuple(plan["shape"])
    profile_data = read_json(profile_path)
    if (len(shape) != 3 or any(type(x) is not int or x < 1 for x in shape)
            or tuple(profile_data["plan"]["shape"]) != shape
            or profile_data["plan"]["factorization_sha256"] != plan["factorization_sha256"]):
        raise ValueError("shape and input must match the registered full-size profile")
    cap, wall = plan["max_evaluations"], plan["wall_seconds"]
    if type(cap) is not int or not 1 <= cap <= 20000 or type(wall) not in (int, float) or not 0 < wall <= 86400:
        raise ValueError("invalid registered evaluation or wall cap")
    if plan["initializer"] not in ("I1", "I2", "I3", "I4", "I3-resume") or type(plan["seed"]) is not int:
        raise ValueError("expected an I1 through I4 initializer or I3-resume and integer seed")
    parent = continuation_parent(plan) if plan["initializer"] == "I3-resume" else None
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, source)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": sha256(plan_path), "backend": settings,
        "runner_sha256": sha256(Path(__file__)),
        "factorization_module_sha256": sha256(Path(__file__).resolve().parents[1] / "src/qcompile/chemistry/factorization.py"),
        "blas_threads": {key: os.environ.get(key) for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
    })
    start = time.monotonic()
    target = shifted_target(inputs.ref["tei"], inputs.S)
    r, b, c = shape
    n = inputs.num_orbitals
    spectrum = eigenvectors = None
    if parent is not None:
        if hashlib.sha256(memoryview(np.ascontiguousarray(target, dtype=np.float64)).cast("B")).hexdigest() != plan["target_sha256"]:
            raise ValueError("continuation shifted target hash differs")
        parent_decision, _, parent_checkpoint = parent
        data = read_factorization(parent_checkpoint, spec={"U": ("f", ("R", "B", n)), "W": ("f", ("R", "B", "C"))})
        vectors, weights = data["U"], data["W"]
        if tuple(weights.shape) != shape:
            raise ValueError("continuation checkpoint shape differs")
        lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
        if np.any(lengths == 0):
            raise ValueError("continuation checkpoint contains a zero vector")
        unit = vectors / lengths
        features = svec(unit[..., :, None] * unit[..., None, :])
        observed = direct_residual(target, factor_rows(features, weights))
        if not np.isclose(observed, parent_decision["best_continuous_residual"], rtol=1e-10, atol=1e-12):
            raise ValueError("continuation parent fails the independent residual check")
        write_json(output / "continuation.json", {
            "parent_evaluations": parent_decision["evaluations"], "parent_residual": observed,
            "checkpoint_sha256": plan["parent"]["checkpoint"]["sha256"],
            "scope": "new optimizer with reset L-BFGS state; separate continuation, not an uninterrupted run",
        })
    elif plan["initializer"] == "I3":
        vectors, weights = continuation_initialize(inputs.params["U"], inputs.w, shape)
    else:
        spectrum, eigenvectors = np.linalg.eigh(target)
        if plan["initializer"] == "I1":
            vectors, weights = initialize(spectrum, eigenvectors, n, shape)
        elif plan["initializer"] == "I2":
            vectors, weights = clustered_initialize(spectrum, eigenvectors, n, shape, plan["seed"])
        else:
            if r * c > np.count_nonzero(spectrum > 0):
                raise ValueError("insufficient positive spectral factors")
            groups = (eigenvectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T.reshape(r, c, -1)
            vectors = np.random.default_rng(plan["seed"]).normal(size=(r, b, n))
            vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
            weights = np.empty(shape)
            for k, group in enumerate(groups):
                features = svec(vectors[k, :, :, None] * vectors[k, :, None, :])
                weights[k] = np.linalg.lstsq(features.T, group.T, rcond=1e-10)[0]
    split = vectors.size
    initial = np.concatenate((vectors.ravel(), weights.ravel()))
    if plan.get("projection_ranking", False):
        if spectrum is None or eigenvectors is None:
            spectrum, eigenvectors = np.linalg.eigh(target)
        if r * c > np.count_nonzero(spectrum > 0):
            raise ValueError("insufficient positive spectral factors")
        spectral_rows = (eigenvectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T
        score = projection_score(spectral_rows, vectors, c)
        write_json(output / "initial-projection.json", {
            "score": score,
            "scope": "balanced spectral factor projection diagnostic, not a tensor-residual lower bound",
        })
    norm = float(np.vdot(target, target))
    best_value = float("inf")
    best = initial.copy()
    history: list[float] = []
    saved_count = -1
    saved_exact = float("inf")
    deadline = start + wall

    class StopFit(Exception):
        pass

    def checkpoint() -> float:
        nonlocal saved_count, saved_exact
        if saved_count == len(history):
            return saved_exact
        unit = best[:split].reshape(r, b, n)
        unit = unit / np.linalg.norm(unit, axis=-1, keepdims=True)
        w = best[split:].reshape(shape)
        features = svec(unit[..., :, None] * unit[..., None, :])
        exact = direct_residual(target, factor_rows(features, w))
        params = {**inputs.params, "U": unit, "W": w, "H2_I": w.sum(axis=1)}
        native_w, offsets, _, _ = api.native_inputs(params)
        candidate = replace(inputs, params=params, w=native_w, W=offsets)
        body = encode_vectors(unit.reshape(r * b, n), params["tree_edges"], 12)
        words = np.concatenate((np.zeros((n, n - 1), dtype=np.int64), body))
        _, _, metrics = FixedWordRefit(api, math_api, candidate, words, 12).evaluate(1, 1)
        label = f"{len(history):05}"
        artifact = output / f"continuous-{label}.npz"
        deterministic_npz(artifact, {"U": unit, "W": w})
        write_json(output / f"checkpoint-{label}.json", {
            "evaluations": len(history), "continuous_residual": exact, "decoded_brot": 12,
            "continuous_sha256": sha256(artifact),
            "decoded_metrics": {key: float(value) if np.isfinite(value) else None for key, value in metrics.items()},
        })
        saved_count, saved_exact = len(history), exact
        return exact

    def objective(flat):
        nonlocal best, best_value
        if len(history) >= cap or time.monotonic() >= deadline:
            raise StopFit
        value, grad_v, grad_w = joint_residual(target, flat[:split].reshape(r, b, n),
                                               flat[split:].reshape(shape), norm)
        if not np.isfinite(value) or value < 0:
            raise ValueError("non-finite or negative Gram objective; use stable residual to investigate")
        if value < best_value:
            best_value, best = value, flat.copy()
        history.append(float(np.sqrt(best_value)))
        if len(history) % 500 == 0 or history[-1] <= 0.019:
            if checkpoint() <= 0.019:
                raise StopFit
        return value, np.concatenate((grad_v.ravel(), grad_w.ravel()))

    converged = False
    try:
        result = minimize(objective, initial, jac=True, method="L-BFGS-B", options={"maxfun": cap, "maxiter": cap})
        converged = bool(result.success)
        reason = str(result.message)
    except StopFit:
        reason = "gate or registered cap reached"
    if not history:
        write_json(output / "decision.json", {"status": "budget_limited", "evaluations": 0, "reason": "wall cap before evaluation"})
        return
    exact = checkpoint()
    history[-1] = exact
    if parent is not None:
        continuation_parent(plan)
    capped = len(history) >= cap or time.monotonic() >= deadline
    status = screen_outcome(history, 0.019, cap_reached=capped, optimizer_converged=converged)
    if status == "go" and exact > 0.019:
        status = "inconclusive"
    write_json(output / "decision.json", {
        "status": status, "reason": reason, "evaluations": len(history), "best_continuous_residual": exact,
        "elapsed_seconds": time.monotonic() - start, "running_best_residuals": history,
        "scope": "continuous S1 only; decoded checkpoints do not establish eligibility",
    })


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
    profiling = actions.add_parser("profile")
    profiling.add_argument("plan", type=Path)
    profiling.add_argument("output", type=Path)
    joint = actions.add_parser("fit")
    joint.add_argument("plan", type=Path)
    joint.add_argument("output", type=Path)
    fit = actions.add_parser("pilot")
    fit.add_argument("plan", type=Path)
    fit.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.action == "rank":
        rank(args.output)
    elif args.action == "profile":
        profile(args.plan, args.output)
    elif args.action == "fit":
        fit_joint(args.plan, args.output)
    else:
        pilot(args.plan, args.output)
