"""Run a pinned decoded-weight precision ladder from an eligible S2 checkpoint."""

import argparse
import hashlib
import math
import os
import subprocess
import sys
import time
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs
from chem_s2 import json_safe
from invsqrt_direct import run_job

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import shifted_target
from qcompile.chemistry.offset_restoration import require_s1
from qcompile.chemistry.precision import passes_margins, precision_ladder, refit_weights
from qcompile.chemistry.refit import FixedWordRefit, encode_vectors
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.io import read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("factorization", "s2_registration", "s2_decision", "s2_checkpoint_receipt",
          "s2_continuous", "s2_submission", "s2_words")


def validate_registration(plan: dict) -> tuple[dict[str, Path], dict, dict]:
    paths = {}
    for name in INPUTS:
        item = plan[name]
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    registration = read_json(paths["s2_registration"])
    decision = read_json(paths["s2_decision"])
    receipt = read_json(paths["s2_checkpoint_receipt"])
    best = decision.get("best_eligible_checkpoint")
    if (decision.get("stage") != "s2" or not best or receipt.get("eligible") is not True
            or not passes_margins(receipt.get("metrics", {}))):
        raise ValueError("S3 requires a decoded, exact-metric eligible S2 checkpoint")
    try:
        relative = paths["s2_checkpoint_receipt"].parent.resolve().relative_to(paths["s2_decision"].parent.resolve())
    except ValueError as error:
        raise ValueError("S2 checkpoint is outside its terminal run") from error
    if (paths["s2_registration"].parent.resolve() != paths["s2_decision"].parent.resolve()
            or relative.as_posix() != best["checkpoint"] or receipt["evaluation"] != best["evaluation"]
            or not math.isclose(receipt["metrics"]["lambda_eff"], best["lambda_eff"], rel_tol=1e-12)
            or registration["plan"]["factorization"]["sha256"] != plan["factorization"]["sha256"]
            or registration["plan"]["target_sha256"] != plan["target_sha256"]):
        raise ValueError("S2 terminal decision, reference, target and selected checkpoint disagree")
    for name, member in (("s2_continuous", "continuous.npz"), ("s2_submission", "submission.npz"),
                         ("s2_words", "words.npy")):
        if paths[name].parent.resolve() != paths["s2_checkpoint_receipt"].parent.resolve() or (
            receipt["hashes"][member] != plan[name]["sha256"]
        ):
            raise ValueError("S2 checkpoint bytes do not match their receipt")
    limits = plan["limits"]
    if (type(limits["evaluations_per_step"]) is not int or not 1 <= limits["evaluations_per_step"] <= 5000
            or type(limits["wall_seconds"]) not in (int, float) or not 0 < limits["wall_seconds"] <= 86400):
        raise ValueError("invalid precision-ladder budget")
    return paths, registration, receipt


def run_worker(plan_path: Path, output: Path, expected_plan_hash: str) -> None:
    if sha256(plan_path) != expected_plan_hash:
        raise ValueError("registered S3 plan hash differs")
    plan = read_json(plan_path)
    paths, _, s2_receipt = validate_registration(plan)
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, paths["factorization"])
    params = read_factorization(paths["s2_submission"])
    arrays = read_factorization(paths["s2_continuous"], spec={
        "U": ("f", ("R", "B", inputs.num_orbitals)), "W": ("f", ("R", "B", "C")),
        "offsets": ("f", ("R", "C")),
    })
    vectors, weights, offsets = arrays["U"], arrays["W"], arrays["offsets"]
    if (not np.array_equal(vectors, params["U"]) or not np.array_equal(weights, params["W"])
            or not np.allclose(offsets, params["H2_I"] - weights.sum(axis=1), rtol=0, atol=1e-12)
            or any(not np.array_equal(params[key], inputs.params[key]) for key in ("H1_I", "Hsym_lower", "tree_edges"))):
        raise ValueError("S2 continuous arrays do not match its strict factorization and pinned reference")
    target = np.ascontiguousarray(shifted_target(inputs.ref["tei"], inputs.S), dtype=np.float64)
    if hashlib.sha256(memoryview(target).cast("B")).hexdigest() != plan["target_sha256"]:
        raise ValueError("registered shifted target hash differs")
    residual = require_s1(target, vectors, weights, "go")
    if not math.isclose(residual, s2_receipt["continuous_residual"], rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("S2 continuous checkpoint residual differs")
    native_w, native_offsets, _, _ = api.native_inputs(params)
    s2_inputs = replace(inputs, params=params, w=native_w, W=native_offsets)
    words = np.load(paths["s2_words"], allow_pickle=False)
    metrics = api.evaluate_words(s2_inputs, words, tree_edges=params["tree_edges"], brot=s2_receipt["brot"])
    if not api.passes_accuracy(metrics) or not passes_margins(metrics):
        raise ValueError("S2 exact decoded metrics no longer pass project margins")
    for key in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff"):
        if not math.isclose(metrics[key], s2_receipt["metrics"][key], rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError(f"S2 exact metric {key} differs from its receipt")
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__).resolve(), ROOT / "src/qcompile/chemistry/precision.py",
               ROOT / "src/qcompile/chemistry/refit.py", ROOT / "src/qcompile/chemistry/factorization.py",
               ROOT / "src/qcompile/chemistry/representation.py", ROOT / "uv.lock")
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": expected_plan_hash, "backend": settings,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        "s2_exact_metrics": json_safe(metrics), "s2_continuous_residual": residual,
        "blas_threads": {key: os.environ.get(key) for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
    })
    r, b, n = vectors.shape
    deadline = time.monotonic() + plan["limits"]["wall_seconds"]
    current = weights.copy()

    def step(bits: int) -> dict:
        nonlocal current
        body = encode_vectors(vectors.reshape(r * b, n), params["tree_edges"], bits)
        initial_words = np.concatenate((np.zeros((n, n - 1), dtype=np.int64), body))
        initial_params = {**params, "W": current, "H2_I": native_offsets + current.sum(axis=1)}
        w0, offsets0, _, _ = api.native_inputs(initial_params)
        candidate = replace(inputs, params=initial_params, w=w0, W=offsets0)
        problem = FixedWordRefit(api, math_api, candidate, initial_words, bits)
        fit = refit_weights(target, problem.two_body, w0,
                            max_evaluations=plan["limits"]["evaluations_per_step"], deadline=deadline)
        fitted = fit.pop("weights")
        final_params = {**params, "W": fitted, "H2_I": native_offsets + fitted.sum(axis=1)}
        w1, offsets1, _, _ = api.native_inputs(final_params)
        if not np.allclose(offsets1, native_offsets, rtol=0, atol=1e-12):
            raise ValueError("precision refit changed pinned identity offsets")
        final_inputs = replace(inputs, params=final_params, w=w1, W=offsets1)
        actual_params, actual_words, actual_metrics = FixedWordRefit(
            api, math_api, final_inputs, initial_words, bits
        ).evaluate(1.0, 1.0)
        eligible = bool(fit["evaluations"] > 0 and api.passes_accuracy(actual_metrics)
                        and passes_margins(actual_metrics))
        directory = output / f"precision-{bits:02}"
        directory.mkdir()
        result = {**fit, "metrics": json_safe(actual_metrics), "eligible": eligible,
                  "expected_coverage": (n + r * b) * 64,
                  "scope": "decoded fixed-basis weight refit; no loader or acceptance claim"}
        if eligible:
            current = w1.copy()
            deterministic_npz(directory / "submission.npz", {key: actual_params[key] for key in SPEC})
            read_factorization(directory / "submission.npz")
            np.save(directory / "words.npy", actual_words, allow_pickle=False)
            result["hashes"] = {name: sha256(directory / name) for name in ("submission.npz", "words.npy")}
        write_json(directory / "result.json", result)
        return {**fit, "metrics": json_safe(actual_metrics), "eligible": eligible,
                "expected_coverage": (n + r * b) * 64,
                "checkpoint": directory.name if eligible else None}

    result = precision_ladder(step)
    validate_registration(plan)
    if sha256(plan_path) != expected_plan_hash:
        raise ValueError("registered S3 plan changed during execution")
    write_json(output / "decision.json", json_safe(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("expected_plan_hash", nargs="?")
    args = parser.parse_args()
    if args.action == "worker":
        if args.expected_plan_hash is None:
            parser.error("worker requires a supervisor-provided plan hash")
        run_worker(args.plan, args.output, args.expected_plan_hash)
        return
    plan = read_json(args.plan)
    validate_registration(plan)
    args.output.mkdir(parents=True, exist_ok=False)
    plan_hash = sha256(args.plan)
    write_json(args.output / "registration.json", {"plan": plan, "plan_sha256": plan_hash})
    try:
        code = run_job([sys.executable, __file__, "worker", str(args.plan), str(args.output / "worker"), plan_hash],
                       args.output, plan["limits"]["wall_seconds"])
        status = "complete" if code == 0 else f"worker_exit_{code}"
    except subprocess.TimeoutExpired:
        status = "timeout"
    write_json(args.output / "status.json", {"status": status, "scope": "execution status, not chemistry acceptance"})


if __name__ == "__main__":
    main()
