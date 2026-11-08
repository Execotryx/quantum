"""Run or select the four registered alternating-projection fit lanes."""

import argparse
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
from banked_chemistry import ROOT, backend
from chem_refit import fixed_inputs
from chem_s2 import json_safe
from scipy.optimize import minimize

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import (
    Floats,
    continuation_initialize,
    direct_residual,
    factor_rows,
    fit_alternating,
    initialize,
    joint_residual,
    shifted_target,
    svec,
)
from qcompile.chemistry.s2 import pinned_checkpoint
from qcompile.chemistry.schema import read_factorization
from qcompile.experiments import screen_outcome
from qcompile.io import read_json, sha256, write_json

LANES = {"A": (9, 143, 40), "B": (9, 143, 40), "C": (10, 129, 40), "D": (9, 129, 40)}
SWEEPS, INTERVAL, EVALUATIONS = 400, 10, 3000
CONTINUOUS_GATE, DECODED_GATE = 0.019, 0.0195
REFERENCE_HASH = "14d5cc25eb3bf82a9ccb87c811db28d127bef6d28697dd190dc1e875de3bfe69"
REFERENCE = ROOT / "runs/invsqrt-direct-hybrid-20261107-v1/extracted/dfthcsos/submission.npz"
START = ROOT / "runs/chem-s1-resume-5000-20261108/continuous-05000.npz"
START_RECEIPT = ROOT / "docs/evidence/chem-s1-resume-5000-20261108/checkpoint-05000.json"
THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def bind(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256(path)}


def polish(target: Floats, vectors: Floats, weights: Floats) -> tuple[Floats, Floats, int, list[float], bool]:
    split = vectors.size
    initial = np.concatenate((vectors.ravel(), weights.ravel()))
    norm = float(np.vdot(target, target))
    best_vectors, best_weights = vectors, weights
    best = direct_residual(target, factor_rows(svec(vectors[..., :, None] * vectors[..., None, :]), weights))
    trace = [best]
    evaluations = 0

    class EvaluationLimit(Exception):
        pass

    def objective(flat: Floats) -> tuple[float, Floats]:
        nonlocal evaluations
        if evaluations == EVALUATIONS:
            raise EvaluationLimit
        evaluations += 1
        value, gv, gw = joint_residual(target, flat[:split].reshape(vectors.shape),
                                        flat[split:].reshape(weights.shape), norm)
        if not np.isfinite(value):
            raise ValueError("nonfinite polish objective")
        return value, np.concatenate((gv.ravel(), gw.ravel()))

    def checkpoint(flat: Floats) -> None:
        nonlocal best_vectors, best_weights, best
        v, w = flat[:split].reshape(vectors.shape), flat[split:].reshape(weights.shape)
        v = v / np.linalg.norm(v, axis=-1, keepdims=True)
        actual = direct_residual(target, factor_rows(svec(v[..., :, None] * v[..., None, :]), w))
        if actual < best:
            best_vectors, best_weights, best = v, w.copy(), actual
        trace.append(best)

    try:
        result = minimize(objective, initial, jac=True, method="L-BFGS-B", callback=checkpoint,
                          options={"maxfun": EVALUATIONS, "maxiter": EVALUATIONS})
        checkpoint(result.x)
        converged = bool(result.success)
    except EvaluationLimit:
        converged = False
    return best_vectors, best_weights, evaluations, trace, converged


def run_lane(lane: str, factorization: Path, start: Path, output: Path) -> None:
    if sha256(factorization) != REFERENCE_HASH:
        raise ValueError("alternating fit requires the pinned reference factorization")
    if any(os.environ.get(name) != "1" for name in THREADS):
        raise ValueError("run the lane through the one-thread supervisor")
    shape = LANES[lane]
    output.mkdir(parents=True, exist_ok=False)
    checkpoint_dir = output / "sweeps"
    checkpoint_dir.mkdir()
    start_pin = None
    start_mode = "I1"
    if lane == "A":
        start_mode = "I3-regenerated"
        if start.is_file():
            start_pin = bind(start)
            if start_pin["sha256"] != read_json(START_RECEIPT)["continuous_sha256"]:
                raise ValueError("lane A checkpoint differs from the recorded 5,000-evaluation start")
            start_mode = "I3-checkpoint"
    registration = output / "registration.json"
    write_json(registration, {
        "plan": {"lane": lane, "shape": shape, "factorization": str(factorization.resolve()),
                 "factorization_sha256": REFERENCE_HASH, "sweeps": SWEEPS,
                 "record_every": INTERVAL, "polish_evaluations": EVALUATIONS,
                 "start_mode": start_mode, "start": start_pin},
        "runner_sha256": sha256(Path(__file__)), "blas_threads": 1,
    })
    _, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, factorization)
    n = inputs.num_orbitals
    target = shifted_target(inputs.ref["tei"], inputs.S)
    eigenvalues, eigenvectors = np.linalg.eigh(target)
    if start_pin is not None:
        arrays = read_factorization(start, spec={"U": ("f", ("R", "B", n)), "W": ("f", ("R", "B", "C"))})
        vectors, weights = arrays["U"], arrays["W"]
        if weights.shape != shape or sha256(start) != start_pin["sha256"]:
            raise ValueError("lane A checkpoint shape or bytes changed")
    elif lane == "A":
        vectors, weights = continuation_initialize(inputs.params["U"], inputs.w, shape)
    else:
        vectors, weights = initialize(eigenvalues, eigenvectors, n, shape)

    def checkpoint(point: dict[str, int | float], v: Floats, w: Floats) -> None:
        prefix = f"sweep-{int(point['sweep']):03}"
        artifact = checkpoint_dir / f"{prefix}.npz"
        deterministic_npz(artifact, {"U": v, "W": w})
        write_json(checkpoint_dir / f"{prefix}.json", {**point, "continuous_sha256": sha256(artifact)})

    fit = fit_alternating(target, vectors, weights, SWEEPS, INTERVAL,
                          spectrum=(eigenvalues, eigenvectors), checkpoint=checkpoint)
    v, w, count, trace, converged = polish(target, fit.vectors, fit.weights)
    residual = trace[-1]
    status = screen_outcome(trace, CONTINUOUS_GATE, cap_reached=count == EVALUATIONS,
                            optimizer_converged=converged)
    metrics, decoded, decoded_brot = {}, None, None
    if residual <= CONTINUOUS_GATE:
        decoded_brot = 12
        _, _, metrics = pinned_checkpoint(api, math_api, inputs, v, w, np.zeros((shape[0], shape[2])), decoded_brot)
        decoded = json_safe(metrics["error_2"])
        status = "go" if decoded is not None and 0 <= decoded <= DECODED_GATE else "no_go"
    if sha256(factorization) != REFERENCE_HASH or (start_pin is not None and bind(start) != start_pin):
        raise ValueError("lane inputs changed while fitting")
    artifact = output / f"continuous-{count:05}.npz"
    receipt = output / f"checkpoint-{count:05}.json"
    deterministic_npz(artifact, {"U": v, "W": w})
    write_json(receipt, {"evaluations": count, "continuous_residual": residual, "decoded_brot": decoded_brot,
                         "continuous_sha256": sha256(artifact), "decoded_metrics": json_safe(metrics)})
    write_json(output / "decision.json", {
        "status": status, "evaluations": count, "best_continuous_residual": residual,
        "decoded_two_body_residual": decoded, "rank_floor": fit.rank_floor,
        "sweep_trace": fit.trace, "polish_running_best_residuals": trace,
        "registration_sha256": sha256(registration), "checkpoint_receipt_sha256": sha256(receipt),
    })


def collect_lanes(directory: Path) -> tuple[dict, dict[str, float]]:
    lanes = {}
    eligible = {}
    for lane, shape in LANES.items():
        run = directory / lane
        decision_path = run / "decision.json"
        decision = read_json(decision_path)
        registration = bind(run / "registration.json")
        plan = read_json(run / "registration.json")["plan"]
        count = decision["evaluations"]
        receipt_path = run / f"checkpoint-{count:05}.json"
        receipt = bind(receipt_path)
        check = read_json(receipt_path)
        checkpoint = bind(run / f"continuous-{count:05}.npz")
        if (
            plan["lane"] != lane or tuple(plan["shape"]) != shape
            or plan["sweeps"] != SWEEPS or plan["polish_evaluations"] != EVALUATIONS
            or registration["sha256"] != decision["registration_sha256"]
            or receipt["sha256"] != decision["checkpoint_receipt_sha256"]
            or checkpoint["sha256"] != check["continuous_sha256"]
            or check["evaluations"] != count
            or check["continuous_residual"] != decision["best_continuous_residual"]
            or check["decoded_brot"] != (12 if check["continuous_residual"] <= CONTINUOUS_GATE else None)
            or check["decoded_metrics"].get("error_2") != decision["decoded_two_body_residual"]
            or decision["status"] not in ("go", "no_go", "budget_limited", "inconclusive")
        ):
            raise ValueError(f"lane {lane} does not bind its registered terminal checkpoint")
        factorization = bind(Path(plan["factorization"]))
        if factorization["sha256"] != plan["factorization_sha256"] or factorization["sha256"] != REFERENCE_HASH:
            raise ValueError(f"lane {lane} reference factorization changed")
        lanes[lane] = {"factorization": factorization, "s1_registration": registration,
                       "s1_decision": bind(decision_path), "s1_checkpoint_receipt": receipt,
                       "s1_checkpoint": checkpoint}
        decoded = decision["decoded_two_body_residual"]
        if (decision["status"] == "go" and 0 <= decision["best_continuous_residual"] <= CONTINUOUS_GATE
                and decoded is not None and 0 <= decoded <= DECODED_GATE):
            eligible[lane] = decoded
    return lanes, eligible


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "worker"):
        command = commands.add_parser(action)
        command.add_argument("lane", choices=LANES)
        command.add_argument("output", type=Path)
        command.add_argument("--factorization", type=Path, default=REFERENCE)
        command.add_argument("--start", type=Path, default=START)
    selection = commands.add_parser("select")
    selection.add_argument("directory", type=Path)
    selection.add_argument("output", type=Path)
    selection.add_argument("--settings", type=Path, required=True)
    selection.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    if args.action == "select":
        from chem_shape_selection import select_lanes

        select_lanes(args.directory, args.output, args.settings, args.seed)
    elif args.action == "run":
        subprocess.run([sys.executable, __file__, "worker", args.lane, str(args.output),
                        "--factorization", str(args.factorization), "--start", str(args.start)],
                       check=True, env={**os.environ, **dict.fromkeys(THREADS, "1")})
    else:
        run_lane(args.lane, args.factorization, args.start, args.output)


if __name__ == "__main__":
    main()
