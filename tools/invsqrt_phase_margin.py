"""Bound fixed-skeleton phase refits for the source-built 39-qubit control."""

import argparse
from fractions import Fraction
from importlib.util import module_from_spec, spec_from_file_location
from math import lcm
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog

from qcompile.invsqrt.direct_screen import beta_one_targets
from qcompile.io import sha256, write_json


CONTROL = "27ccb62d03bcba70353d382bb94c5dc636acd00b250c83f976df8d1176842146"
SIMULATOR = "2ee284839765dcbd33fa93d7b0c04456674c90c7fa04571bea5dffe7df3bf2a8"
MAX_X = 3_133_452
SCALE = 1 << 32
OFFSET_BOUND = 20 * SCALE


def certify(weights: list[Fraction], matrix: NDArray[np.int8], rhs: NDArray[np.int64]) -> dict:
    """Bound the minimum margin using a nonnegative sum of exact constraints."""
    denominator = lcm(*(w.denominator for w in weights))
    multipliers = [int(w * denominator) for w in weights]
    total = sum(multipliers)
    if not total or any(m < 0 for m in multipliers):
        raise ValueError("The certificate requires nonnegative weights with positive sum")
    carry = [sum(w * int(a) for w, a in zip(multipliers, column, strict=True)) for column in matrix.T]
    weighted_rhs = sum(w * int(b) for w, b in zip(multipliers, rhs, strict=True))
    bound = Fraction(weighted_rhs + OFFSET_BOUND * sum(map(abs, carry)), total)
    return {"multipliers": multipliers, "unmatched_coefficients": carry,
            "upper_margin_phase64": bound.numerator // bound.denominator,
            "uses_offset_bound": any(carry)}


def fit_margin(error: NDArray[np.int64], tolerance: NDArray[np.int64], features: NDArray[np.bool_],
               editable: list[int]) -> dict:
    size = len(error)
    subset = np.union1d(np.argpartition(tolerance - np.abs(error), 384)[:384],
                        np.linspace(0, size - 1, 768, dtype=np.int64))
    width = len(editable)
    editable_columns = np.asarray(editable, dtype=np.intp)
    for _ in range(20):
        f = features[np.ix_(subset, editable_columns)].astype(np.int8)
        matrix = np.concatenate((f, -f), axis=0)
        rhs = np.concatenate((tolerance[subset] - error[subset], tolerance[subset] + error[subset]))
        system = np.column_stack((matrix, np.ones(len(rhs))))
        fit = linprog([0.0] * width + [-1.0], A_ub=system, b_ub=rhs / SCALE,
                      bounds=[(-20, 20)] * width + [(None, None)], method="highs")
        if not fit.success:
            raise ValueError(f"Phase refit failed: {fit.message}")
        offsets = np.rint(fit.x[:-1] * SCALE).astype(np.int64).clip(-OFFSET_BOUND, OFFSET_BOUND)
        residual = error.copy()
        for index, offset in zip(editable, offsets, strict=True):
            residual += features[:, index] * offset
        margin = tolerance - np.abs(residual)
        best = int(margin.min())
        active = np.flatnonzero(fit.ineqlin.marginals < 0)
        weights = [Fraction(float(-fit.ineqlin.marginals[i])).limit_denominator(1_000_000) for i in active]
        certificate = certify(weights, matrix[active], rhs[active])
        certificate["rows"] = [
            {"x": int(subset[i % len(subset)] + 1), "coefficients": matrix[i].tolist(), "rhs": int(rhs[i])}
            for i in active
        ]
        if certificate["upper_margin_phase64"] < 0 or certificate["upper_margin_phase64"] - best <= 64:
            return {"sampled_branch_minimum_margin_phase64": best, "offsets_phase64": offsets.tolist(),
                    "certificate": certificate}
        subset = np.union1d(subset, np.argpartition(margin, 384)[:384])
    raise ValueError("The active-set screen did not reach a conclusive bound")


def verify_rotation_prefix(ops: list[Any], active_lines: set[int]) -> None:
    """Prove that adjustable rotation controls are independent of measurements."""
    last = max(active_lines)
    depth = 0
    for op in ops:
        if op.line > last:
            break
        if op.name == "PUSH_CONDITION":
            depth += 1
        elif op.name == "POP_CONDITION":
            depth -= 1
        if (depth or op.cond is not None) and (
            op.line in active_lines or op.name in {"X", "CX", "CCX", "SWAP", "CSWAP", "HMR", "R"}
        ):
            raise ValueError(f"Measurement-dependent value operation before editable rotation: line {op.line}")


def run(control: Path, simulator: Path, output: Path) -> None:
    if sha256(control) != CONTROL or sha256(simulator) != SIMULATOR:
        raise ValueError("Control or source simulator differs from its reviewed identity")
    spec = spec_from_file_location("tony_li_kmxsim", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not import the pinned source simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, x_register = km.parse_kmx(control)
    rotations = [op for op in ops if op.name == "Z_POW" and km.zpow_class(op.units) == "rotation"]
    rotation_lines = {op.line for op in rotations}
    verify_rotation_prefix(ops, rotation_lines)
    order = sorted(range(len(rotations)), key=lambda i: rotations[i].units)
    registration = output.with_suffix(".registration.json")
    driver_hash = sha256(Path(__file__))
    write_json(registration, {
        "assembly_sha256": CONTROL, "source_simulator_sha256": SIMULATOR, "driver_sha256": driver_hash,
        "inputs": MAX_X, "measurement_branch": "all measurement outcomes zero", "offset_bound_phase64": OFFSET_BOUND,
        "editable_lines": sorted(rotation_lines), "dropped_lines": [rotations[i].line for i in order[:4]],
    })
    sim = km.Sim(39, "zero")
    sim.load_x(x_register)
    captured = []
    for op in ops:
        if op.line in rotation_lines:
            captured.append(km.unpack(sim.Q[op.q[0]])[:MAX_X])
        sim.apply(op)
    if not np.array_equal(sim.word(x_register), sim.xs) or sim.Q[22:].any():
        raise ValueError("The control replay did not restore input and scratch")
    features = np.stack(captured, axis=1)
    target, tolerance = beta_one_targets(np.arange(1, MAX_X + 1, dtype=np.int64))
    error = (sim.theta()[:MAX_X] - target).view(np.int64)
    allowed = tolerance.astype(np.int64)
    margin = allowed - np.abs(error)
    if margin.min() <= 0:
        raise ValueError("The control replay failed its full-domain phase margin")
    lanes = []
    for drop in [None, *order[:4]]:
        edited = [i for i in range(len(rotations)) if i != drop]
        refit_error = error if drop is None else error - features[:, drop] * int(rotations[drop].units)
        lanes.append({"dropped_line": None if drop is None else rotations[drop].line,
                      "editable_lines": [rotations[i].line for i in edited],
                      **fit_margin(refit_error, allowed, features, edited)})
    write_json(output, {
        "classification": "exact_margin_upper_bounds_for_fixed_control_rotation_predicates",
        "assembly_sha256": CONTROL, "source_simulator_sha256": SIMULATOR, "driver_sha256": driver_hash,
        "registration_sha256": sha256(registration),
        "inputs": MAX_X, "measurement_branch": "all measurement outcomes zero", "offset_bound_phase64": OFFSET_BOUND,
        "control_minimum_margin_phase64": int(margin.min()), "control_worst_tolerance_fraction": float((np.abs(error) / allowed).max()),
        "lanes": lanes,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
