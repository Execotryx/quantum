"""Run the registered above-36 fixed-dictionary channel continuation."""

import argparse
import math
import time
from dataclasses import replace
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import lstsq
from scipy.optimize import minimize

from banked_chemistry import backend
from chem_refit import fixed_inputs
from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import direct_residual, factor_rows, shifted_target, svec
from qcompile.chemistry.fixed_dictionary import FixedDictionaryGram, Floats, truncate_channels
from qcompile.chemistry.schema import read_factorization
from qcompile.io import read_json, sha256, write_json

STAGES = (40, 36, 35)
SEEDS = (36043, 36047)
ITERATIONS = 200
CHECKPOINT = 25


def serializable(metrics: dict) -> dict:
    return {key: value if math.isfinite(value) else None for key, value in metrics.items()}


def run(factorization: Path, reference_registration: Path, output: Path, wall_seconds: int) -> None:
    if wall_seconds < 1:
        raise ValueError("positive fit wall budget required")
    reference = read_json(reference_registration)
    settings, _, _, _, api = backend()
    expected = reference["public_comparison"]["member_sha256"]["dfthcsos/submission.npz"]
    if sha256(factorization) != expected or settings["metric_sha256"] != reference["metric_sha256"]:
        raise ValueError("fixed-dictionary input differs from the registered reference")
    native_math = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, factorization)
    params = read_factorization(factorization, allow_extra=True)
    with np.load(factorization, allow_pickle=False) as data:
        words = data["angle_words"]
    if inputs.w.shape != (9, 127, 46) or words.shape != (1219, 75):
        raise ValueError("unexpected fixed-dictionary reference shape")
    edges = params["tree_edges"]
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "classification": "fixed_dictionary_channel_continuation",
        "factorization_sha256": expected, "metric_sha256": settings["metric_sha256"],
        "reference_registration_sha256": sha256(reference_registration),
        "driver_sha256": sha256(Path(__file__)),
        "objective_sha256": sha256(Path(__file__).resolve().parents[1] / "src/qcompile/chemistry/fixed_dictionary.py"),
        "stages": STAGES, "seeds": SEEDS, "accepted_iterations_per_start": ITERATIONS,
        "checkpoint_interval": CHECKPOINT, "wall_seconds_per_start": wall_seconds, "brot": 7,
        "initializer": "physical channel truncation, with a deterministic 0.001 RMS weight perturbation for start 2",
    })
    control = api.evaluate_words(inputs, words, tree_edges=edges, brot=7)
    if not api.passes_accuracy(control):
        raise ValueError("frozen decoded reference did not pass")
    write_json(output / "control.json", serializable(control))
    vectors = native_math.reconstruct_u_vectors(words[76:].astype(np.float64) / 64, edges)
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    vectors = vectors.reshape(9, 127, 76)
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    target = shifted_target(inputs.ref["tei"], inputs.S)
    anchor = inputs.W.ravel() @ factor_rows(features, inputs.w)
    transform = np.linalg.cholesky(features @ features.swapaxes(1, 2) + 1e-12 * np.eye(127))
    forward = transform.swapaxes(1, 2)
    inverse = np.linalg.solve(forward, np.broadcast_to(np.eye(127), forward.shape))
    fit = FixedDictionaryGram(target, np.asarray(np.linalg.solve(transform, features), dtype=np.float64))
    parent = (inputs.w, inputs.W)
    parent_pin = expected
    terminal = []

    for copies in STAGES:
        stage = output / f"c{copies}"
        stage.mkdir()
        write_json(stage / "parent.json", {"predecessor_sha256": parent_pin})
        initial, offsets = truncate_channels(features, *parent, copies)
        best: tuple[tuple[bool, float, float], Floats, Floats, str] | None = None
        for index, seed in enumerate(SEEDS):
            lane = stage / f"start-{index + 1}"
            lane.mkdir()
            started, iterations, calls = time.monotonic(), 0, 0
            latest = 0
            best_point = 0
            last_weights = initial.copy()
            if index:
                last_weights += (np.random.default_rng(seed).standard_normal(initial.shape)
                                 * (0.001 * float(np.sqrt(np.mean(initial**2)))))

            def measure(flat: Floats, step: int) -> None:
                nonlocal best, latest, best_point
                native = inverse @ flat.reshape(initial.shape)
                rows = factor_rows(features, native)
                exact = direct_residual(target, rows)
                solution = lstsq(rows.T, anchor, cond=1e-10, lapack_driver="gelsd")
                if solution is None:
                    raise ValueError("Offset restoration did not return a solution")
                restored = np.asarray(solution[0], dtype=np.float64).reshape(offsets.shape)
                observed: list[dict[str, Any]] = []
                for kind, value in (("truncated_offsets", offsets), ("restored_contraction", restored)):
                    arrays = {**params, "W": native, "H2_I": value + native.sum(axis=1)}
                    w, v, shift, beta = api.native_inputs(arrays)
                    state = replace(inputs, params=arrays, w=w, W=v, S=shift, beta_1=beta)
                    metrics = api.evaluate_words(state, words, tree_edges=edges, brot=7)
                    eligible = bool(api.passes_accuracy(metrics))
                    if not math.isclose(exact, metrics["error_2"], abs_tol=1e-9):
                        raise ValueError("packed and official two-body residuals disagree")
                    observed.append({"offset_lane": kind, "accuracy_passed": eligible,
                                     "metrics": serializable(metrics)})
                    key = (not eligible, float(metrics["lambda_eff"]) if eligible else exact,
                           float(metrics["error_1"]))
                    if best is None or key < best[0]:
                        checkpoint = lane / f"i{step:03}-{kind}.npz"
                        deterministic_npz(checkpoint, arrays)
                        read_factorization(checkpoint)
                        best = (key, native.copy(), v.copy(), sha256(checkpoint))
                        best_point = step
                write_json(lane / f"i{step:03}.json", {"iteration": step, "observations": observed})
                latest = step
                print(f"C={copies} start={index + 1} step={step} error_2={exact:.9f}", flush=True)

            def objective(flat: Floats) -> tuple[float, Floats]:
                nonlocal calls
                calls += 1
                if time.monotonic() - started >= wall_seconds:
                    raise TimeoutError("registered wall budget reached")
                value, gradient = fit.objective(flat.reshape(initial.shape))
                return value, gradient.ravel()

            def checkpoint(flat: Floats) -> None:
                nonlocal iterations, last_weights
                iterations += 1
                last_weights = flat.copy()
                if iterations % CHECKPOINT == 0:
                    measure(flat, iterations)

            flat = (forward @ last_weights).ravel()
            last_weights = flat
            measure(flat, 0)
            try:
                result = minimize(objective, flat, jac=True, method="L-BFGS-B", callback=checkpoint,
                                  options={"maxiter": ITERATIONS, "maxfun": 1000, "ftol": 1e-13,
                                           "gtol": 1e-9})
                stop = str(result.message)
            except TimeoutError as error:
                stop = str(error)
            if latest != iterations:
                measure(last_weights, iterations)
            write_json(lane / "result.json", {"iterations": iterations, "evaluations": calls,
                                            "best_replacement_iteration": best_point, "stop": stop,
                                            "elapsed_seconds": time.monotonic() - started})
        assert best is not None
        key, weights, best_offsets, parent_pin = best
        parent = weights, best_offsets
        decision = {"channels": copies, "accuracy_passed": not key[0],
                    "best_metric": key[1], "best_error_1": key[2], "checkpoint_sha256": parent_pin}
        write_json(stage / "decision.json", decision)
        terminal.append(decision)
    write_json(output / "decision.json", {
        "stages": terminal, "native_pricing_pending": any(row["accuracy_passed"] for row in terminal),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("factorization", "reference_registration", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--wall-seconds", type=int, default=300)
    run(**vars(parser.parse_args()))
