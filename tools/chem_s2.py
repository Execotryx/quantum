"""Run a pinned S2 experiment only from an independently verified S1 go."""

import argparse
import hashlib
import math
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs
from invsqrt_direct import run_job

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import shifted_target
from qcompile.chemistry.offset_restoration import require_s1
from qcompile.chemistry.s2 import optimize_s2, pinned_checkpoint
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.io import read_json, sha256, write_json

INPUTS = ("factorization", "s1_registration", "s1_decision", "s1_checkpoint_receipt", "s1_checkpoint")
ROOT = Path(__file__).resolve().parents[1]


def validate_registration(plan: dict) -> tuple[dict[str, Path], dict, dict]:
    """Authenticate input bytes and reject a capped or inconsistent S1 receipt."""
    paths = {}
    for name in INPUTS:
        item = plan[name]
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    decision = read_json(paths["s1_decision"])
    if decision.get("status") != "go":
        raise ValueError("S2 requires an S1 go; a capped or inconclusive pilot is not eligible")
    registration = read_json(paths["s1_registration"])
    receipt = read_json(paths["s1_checkpoint_receipt"])
    if (registration["plan"]["factorization_sha256"] != plan["factorization"]["sha256"]
            or receipt["continuous_sha256"] != plan["s1_checkpoint"]["sha256"]
            or receipt["evaluations"] != decision["evaluations"]
            or not math.isclose(receipt["continuous_residual"], decision["best_continuous_residual"],
                                rel_tol=1e-10, abs_tol=1e-12)):
        raise ValueError("S1 registration, terminal decision and checkpoint do not agree")
    limits = plan["limits"]
    if (type(limits["evaluations"]) is not int or not 1 <= limits["evaluations"] <= 20000
            or type(limits["restore_evaluations"]) is not int or not 1 <= limits["restore_evaluations"] <= 5000
            or type(limits["wall_seconds"]) not in (int, float) or not 0 < limits["wall_seconds"] <= 86400
            or type(limits["checkpoint_interval"]) is not int or not 1 <= limits["checkpoint_interval"] <= 500
            or type(limits["outer_iterations"]) is not int or not 1 <= limits["outer_iterations"] <= 100
            or not math.isfinite(limits["offset_bound"]) or limits["offset_bound"] <= 0
            or not math.isfinite(limits["penalty"]) or limits["penalty"] <= 0):
        raise ValueError("invalid registered S2 budget")
    if type(plan["brot"]) is not int or not 1 <= plan["brot"] <= 52:
        raise ValueError("invalid registered checkpoint precision")
    target_hash = plan["target_sha256"]
    if not isinstance(target_hash, str) or len(target_hash) != 64 or any(c not in "0123456789abcdef" for c in target_hash):
        raise ValueError("a lowercase SHA-256 target pin is required")
    return paths, decision, registration


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (int, np.integer)):
        return int(value)
    return value


def target_pin(source: Path, output: Path) -> None:
    source_hash = sha256(source)
    settings, _, _, _, api = backend()
    inputs = fixed_inputs(api, source)
    target = np.ascontiguousarray(shifted_target(inputs.ref["tei"], inputs.S), dtype=np.float64)
    if sha256(source) != source_hash:
        raise ValueError("factorization changed while deriving the target")
    write_json(output, {"factorization_sha256": source_hash,
                        "target_sha256": hashlib.sha256(memoryview(target).cast("B")).hexdigest(),
                        "target_shape": list(target.shape), "dtype": target.dtype.str, "backend": settings,
                        "scope": "pinned packed shifted target, C-contiguous bytes"})


def run_worker(plan_path: Path, output: Path, expected_plan_hash: str | None = None) -> None:
    if expected_plan_hash is not None and sha256(plan_path) != expected_plan_hash:
        raise ValueError("registered S2 plan hash differs")
    plan = read_json(plan_path)
    paths, decision, registration = validate_registration(plan)
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, paths["factorization"])
    arrays = read_factorization(paths["s1_checkpoint"], spec={
        "U": ("f", ("R", "B", inputs.num_orbitals)), "W": ("f", ("R", "B", "C")),
    })
    vectors, weights = arrays["U"], arrays["W"]
    if list(weights.shape) != registration["plan"]["shape"]:
        raise ValueError("S1 checkpoint shape differs from registration")
    target = np.ascontiguousarray(shifted_target(inputs.ref["tei"], inputs.S), dtype=np.float64)
    if hashlib.sha256(memoryview(target).cast("B")).hexdigest() != plan["target_sha256"]:
        raise ValueError("registered shifted target hash differs")
    actual = require_s1(target, vectors, weights, decision["status"])
    if not math.isclose(actual, decision["best_continuous_residual"], rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("S1 decision does not match its independently reconstructed target")
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in (
        Path(__file__).resolve(), ROOT / "src/qcompile/chemistry/s2.py",
        ROOT / "src/qcompile/chemistry/offset_restoration.py", ROOT / "src/qcompile/chemistry/smooth_objective.py",
        ROOT / "src/qcompile/chemistry/factorization.py", ROOT / "src/qcompile/chemistry/refit.py", ROOT / "uv.lock",
    )}
    write_json(output / "registration.json", {"plan": plan, "plan_sha256": sha256(plan_path), "backend": settings,
                                               "source_hashes": source_hashes, "s1_residual": actual,
                                               "blas_threads": {key: os.environ.get(key) for key in
                                                                ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}})
    h1 = inputs.ref["oei"] - 0.5 * np.einsum("prrq->pq", inputs.ref["tei"])
    h1_base = h1 - inputs.ref["electrons"] * inputs.S / 2 + inputs.beta_1 * np.eye(inputs.num_orbitals)
    gap_base = inputs.energy_upper - inputs.ref["ecore"] + inputs.ref["electrons"] * inputs.beta_1
    cache = {}
    counter = 0

    def evaluate(v, w, offsets):
        params, words, metrics = pinned_checkpoint(api, math_api, inputs, v, w, offsets, plan["brot"])
        cache.update(params=params, words=words, metrics=metrics)
        return metrics

    def checkpoint(evaluation, v, w, offsets, receipt):
        nonlocal counter
        counter += 1
        directory = output / "checkpoints" / f"{counter:05}"
        directory.mkdir(parents=True, exist_ok=False)
        deterministic_npz(directory / "continuous.npz", {"U": v, "W": w, "offsets": offsets})
        deterministic_npz(directory / "submission.npz", {key: cache["params"][key] for key in SPEC})
        read_factorization(directory / "submission.npz")
        np.save(directory / "words.npy", cache["words"], allow_pickle=False)
        safe_receipt: dict = json_safe(receipt)
        write_json(directory / "checkpoint.json", {
            **safe_receipt, "evaluation": evaluation, "brot": plan["brot"],
            "hashes": {name: sha256(directory / name) for name in ("continuous.npz", "submission.npz", "words.npy")},
            "scope": "decoded S2 development checkpoint; not a release or acceptance",
        })
        return str(directory.relative_to(output))

    limits = plan["limits"]
    result = optimize_s2(target, vectors, weights, decision["status"], h1_base, gap_base, evaluate, checkpoint,
                         max_evaluations=limits["evaluations"], max_seconds=limits["wall_seconds"],
                         restore_evaluations=limits["restore_evaluations"], offset_bound=limits["offset_bound"],
                         checkpoint_interval=limits["checkpoint_interval"], penalty=limits["penalty"],
                         outer_iterations=limits["outer_iterations"])
    validate_registration(plan)
    if expected_plan_hash is not None and sha256(plan_path) != expected_plan_hash:
        raise ValueError("registered S2 plan changed during execution")
    write_json(output / "decision.json", json_safe(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("target", "run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("expected_plan_hash", nargs="?")
    args = parser.parse_args()
    if args.action == "target":
        target_pin(args.plan, args.output)
        return
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
