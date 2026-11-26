"""Screen orthogonal channel gauges with the public decoded ANGLE words fixed."""

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from banked_chemistry import backend
from chem_fixed_dictionary import serializable
from chem_refit import fixed_inputs
from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.fixed_dictionary import Floats
from qcompile.chemistry.schema import read_factorization
from qcompile.io import read_json, sha256, write_json

SWEEPS = 3


def sweep(group: Floats) -> int:
    """Minimize the pair cost on each interval of constant entry signs."""
    moves = 0
    for i in range(group.shape[1] - 1):
        for j in range(i + 1, group.shape[1]):
            a, b = group[:, i], group[:, j]
            cuts = np.unique(np.concatenate(([0.0, np.pi / 2], np.arctan2(-a, b) % (np.pi / 2))))
            mid = ((cuts[:-1] + cuts[1:]) / 2)[:, None]
            c, s = np.cos(mid), np.sin(mid)
            left_sign, right_sign = np.sign(c * a + s * b), np.sign(c * b - s * a)
            u, v = (left_sign * a).sum(axis=1), (left_sign * b).sum(axis=1)
            p, q = (right_sign * b).sum(axis=1), (-right_sign * a).sum(axis=1)
            # On each interval the cost is constant + d*cos(2θ) + e*sin(2θ).
            d, e = (u**2 + p**2 - v**2 - q**2) / 2, u * v + p * q
            stationary = ((np.arctan2(e, d) + np.pi) % (2 * np.pi)) / 2
            interior = (stationary > cuts[:-1]) & (stationary < cuts[1:])
            angles = np.concatenate((cuts, stationary[interior]))
            c, s = np.cos(angles)[:, None], np.sin(angles)[:, None]
            left, right = c * a + s * b, c * b - s * a
            costs = np.abs(left).sum(axis=1)**2 + np.abs(right).sum(axis=1)**2
            choice = int(costs.argmin())
            if costs[choice] < costs[0] - 1e-12:
                group[:, i], group[:, j] = left[choice], right[choice]
                moves += 1
    return moves


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("factorization", "reference", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    anchor = read_json(args.reference)
    expected = anchor["public_comparison"]["member_sha256"]["dfthcsos/submission.npz"]
    settings, _, _, _, api = backend()
    if sha256(args.factorization) != expected or settings["metric_sha256"] != anchor["metric_sha256"]:
        raise ValueError("Unexpected decoded reference or backend")
    params = read_factorization(args.factorization, allow_extra=True)
    inputs = fixed_inputs(api, args.factorization)
    edges = params["tree_edges"]
    with np.load(args.factorization, allow_pickle=False) as raw:
        words = raw["angle_words"]
    control = api.evaluate_words(inputs, words, tree_edges=edges, brot=7)
    if not api.passes_accuracy(control):
        raise ValueError("The decoded reference failed")
    augmented = np.concatenate((inputs.w, params["H2_I"][:, None, :]), axis=1)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "registration.json", {
        "reference_factorization_sha256": expected, "reference_registration_sha256": sha256(args.reference),
        "driver_sha256": sha256(Path(__file__)), "metric_sha256": settings["metric_sha256"],
        "sweeps": SWEEPS, "brot": 7, "objective": "squared column one-norm of weights and total identity",
        "angles": "All entry sign crossings and interior minima of the fixed-sign pair costs",
    })
    best = float(control["lambda_eff"])
    rows = []
    for step in range(1, SWEEPS + 1):
        moves = sum(sweep(group) for group in augmented)
        arrays = {**params, "W": augmented[:, :-1, :], "H2_I": augmented[:, -1, :]}
        w, offsets, _, _ = api.native_inputs(arrays)
        state = replace(inputs, params=arrays, w=w, W=offsets)
        observed = api.evaluate_words(state, words, tree_edges=edges, brot=7)
        if any(abs(observed[key] - control[key]) > 1e-8 for key in ("error_1", "error_2", "E_gap")):
            raise ValueError("Channel rotation failed to preserve the represented Hamiltonian and gap")
        passes = bool(api.passes_accuracy(observed))
        row = {"sweep": step, "rotations": moves, "metrics": serializable(observed), "accuracy_passed": passes}
        if passes and observed["lambda_eff"] < best:
            checkpoint = args.output / f"sweep-{step:02}.npz"
            deterministic_npz(checkpoint, arrays)
            row["checkpoint_sha256"] = sha256(checkpoint)
            best = float(observed["lambda_eff"])
        rows.append(row)
        if not moves:
            break
    write_json(args.output / "decision.json", {
        "classification": "decoded_channel_gauge_screen", "control": serializable(control), "sweeps": rows,
        "best_lambda_eff": best, "candidate_found": best < control["lambda_eff"], "full_native_run": False,
    })


if __name__ == "__main__":
    main()
