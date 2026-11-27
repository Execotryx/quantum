"""Measure decoded residual after projection onto smaller subsets of a pinned dictionary."""

import argparse
from importlib import import_module
from pathlib import Path
import sys
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from qcompile.io import sha256, write_json
from tools.chem_shape_resource_budget import CONTROL_SHA256, OFFICIAL


Floats = NDArray[np.float64]
Integers = NDArray[np.int64]
SOURCE_PINS = {
    "scoreinfra/dfthc_math.py": "ae82898d47a7a86b96378fb906e0f8a9f46003065cf19c7c09952a123b5b5af8",
    "scoreinfra/reference.py": "a2d5a63191d655729e29f0fde1e85fe4630bf896a91a63bb894d8d7daf71ed39",
}
BASES_TO_KEEP = (119, 95, 63)
PAIR_LIMIT = 0.020000001  # Keep near-boundary exclusions out of this numerical screen.


class Projection(NamedTuple):
    selected: Integers
    weights: Floats
    total_squared_loss: float


def prune(gram: Floats, weights: Floats, keep: int) -> Projection:
    selected = np.arange(len(weights), dtype=np.int64)
    inverse = np.linalg.solve(gram, np.eye(len(gram)))
    loss = 0.0
    while len(selected) > keep:
        diagonal = np.diag(inverse)
        if not np.all(diagonal > 0):
            raise ValueError("The retained projector Gram is not numerically positive definite")
        incremental = np.sum(weights * weights, axis=1) / diagonal
        removed = int(incremental.argmin())
        loss += float(incremental[removed])
        remaining = np.arange(len(selected)) != removed
        connection = inverse[remaining, removed] / diagonal[removed]
        weights = weights[remaining] - connection[:, None] * weights[removed]
        inverse = inverse[np.ix_(remaining, remaining)] - np.outer(connection, inverse[removed, remaining])
        selected = selected[remaining]
    return Projection(selected, weights, loss)


def pair_colors(dual: Floats, action: Floats, residual: float) -> list[list[int]]:
    overlap = dual.T @ dual
    overlap_squared = 1 - overlap ** 2
    nearly_parallel = overlap_squared < 1e-10
    overlap_squared[nearly_parallel] = 1
    actions = action.T @ action
    projected = dual.T @ action
    diag_a, diag_p = np.diag(actions), np.diag(projected)
    second_action = (diag_a + overlap ** 2 * diag_a[:, None] - 2 * overlap * actions) / overlap_squared
    second_projected = (diag_p + overlap ** 2 * diag_p[:, None] - 2 * overlap * projected) / overlap_squared
    cross_squared = (projected - overlap * diag_p[:, None]) ** 2 / overlap_squared
    pair_error = (residual ** 2 + 2 * (diag_a[:, None] + second_action)
                  - (diag_p[:, None] ** 2 + second_projected ** 2 + 2 * cross_squared))
    # Keep an edge if either ordering makes the rounded result compatible.
    edges = (np.minimum(pair_error, pair_error.T) <= PAIR_LIMIT ** 2) | nearly_parallel
    np.fill_diagonal(edges, False)
    order = np.argsort(-edges.sum(axis=1), kind="stable")
    colors: list[list[int]] = []
    for index in order:
        row = int(index)
        for color in colors:
            if not edges[row, color].any():
                color.append(row)
                break
        else:
            colors.append([row])
    return colors


def omission_bounds(features: Floats, target: Floats, group_width: int) -> dict[str, object]:
    """Bound simultaneous row omissions using relaxed singleton and pair residuals."""
    basis, triangular = np.linalg.qr(features.T, mode="reduced")
    singular = np.linalg.svd(triangular, compute_uv=False)
    rank_tolerance = float(singular[0] * max(features.shape) * np.finfo(np.float64).eps)
    rank = int(np.count_nonzero(singular > rank_tolerance))
    if rank != len(features):
        return {"status": "rank_deficient", "rank": rank, "rows": len(features), "rank_tolerance": rank_tolerance}
    dual = np.linalg.solve(triangular.T, np.eye(len(features)))
    dual /= np.linalg.norm(dual, axis=0)
    reduced = basis.T @ target @ basis
    full_residual = float(np.linalg.norm(target - (basis @ reduced) @ basis.T))
    action = reduced @ dual
    bounds = np.sqrt(np.maximum(0, full_residual ** 2 + 2 * np.sum(action ** 2, axis=0)
                                - np.sum(dual * action, axis=0) ** 2))
    off_diagonal = triangular.T @ dual
    np.fill_diagonal(off_diagonal, 0)
    groups = []
    for start in range(0, len(features), group_width):
        local = bounds[start:start + group_width]
        eligible = np.flatnonzero(local <= PAIR_LIMIT)
        indices = start + eligible
        colors = pair_colors(dual[:, indices], action[:, indices], full_residual)
        groups.append({
            "singleton_residuals": local.tolist(), "singleton_eligible": len(eligible),
            "pair_compatibility_coloring": [[int(eligible[index]) for index in color] for color in colors],
            "pair_compatible_omissions_upper": len(colors),
        })
    return {
        "status": "working_precision", "rank": rank, "smallest_singular_value": float(singular[-1]),
        "condition": float(singular[0] / singular[-1]), "unrestricted_full_span_residual": full_residual,
        "maximum_dual_leakage": float(np.max(np.linalg.norm(off_diagonal, axis=0))),
        "pair_screen_residual_cutoff": PAIR_LIMIT, "groups": groups,
    }


def run(factorization: Path, output: Path) -> None:
    verifier = OFFICIAL / "dfthcsos"
    if sha256(factorization) != CONTROL_SHA256 or any(
        sha256(verifier / name) != digest for name, digest in SOURCE_PINS.items()
    ):
        raise ValueError("Unexpected factorization or verifier source")
    sys.path.insert(0, str(OFFICIAL))
    reference = import_module("dfthcsos.scoreinfra.reference")
    math = import_module("dfthcsos.scoreinfra.dfthc_math")
    if Path(reference.__file__ or "").resolve() != verifier / "scoreinfra/reference.py" or Path(
        math.__file__ or ""
    ).resolve() != verifier / "scoreinfra/dfthc_math.py":
        raise ValueError("The imported chemistry evaluator is not the pinned source")
    ref = reference.load_reference(reference.check_fcidump())
    shifts = reference.load_fixed_shifts()
    shift = math.symmetric_from_lower(shifts["Hsym_lower"], 76).astype(np.float64)
    beta = float(shifts["H1_I"]) - 0.5 * float(np.trace(shift))
    with np.load(factorization, allow_pickle=False) as data:
        w = np.asarray(data["W"], dtype=np.float64)
        native_offsets = np.asarray(data["H2_I"], dtype=np.float64) - w.sum(axis=1)
        vectors = math.reconstruct_u_vectors(data["angle_words"] / 64.0, data["tree_edges"])
    body = vectors[76:].reshape(*w.shape[:2], 76)
    unit = body / np.linalg.norm(body, axis=-1, keepdims=True)
    grams = np.square(unit @ unit.swapaxes(-1, -2))

    def evaluate(decoded: Floats, weights: Floats) -> dict[str, float | bool]:
        return math.evaluate_dfthc_vectors(decoded, weights, native_offsets, shift, beta, ref,
                                           energy_upper=reference.UPPER_ENERGY)

    control = evaluate(vectors, w)
    if abs(float(control["error_2"]) - 0.01999999999000222) > 1e-9:
        raise ValueError("The decoded two-body control did not reproduce")
    outcomes = []
    for keep in BASES_TO_KEEP:
        projections = [prune(gram, weights, keep) for gram, weights in zip(grams, w, strict=True)]
        retained = np.concatenate([group[p.selected] for group, p in zip(body, projections, strict=True)])
        metrics = evaluate(np.concatenate((vectors[:76], retained)), np.stack([p.weights for p in projections]))
        outcomes.append({
            "bases_per_group": keep, "metrics_with_retained_one_body": metrics,
            "group_projection_squared_losses": [p.total_squared_loss for p in projections],
            "selected": [p.selected.tolist() for p in projections],
        })
    rows, columns = np.triu_indices(76)
    scale = np.where(rows == columns, 1.0, np.sqrt(2.0))
    physical = unit.reshape(-1, 76)
    features = physical[:, rows] * physical[:, columns] * scale
    target = ref["tei"][rows[:, None], columns[:, None], rows, columns] * scale[:, None] * scale
    identity = (rows == columns).astype(np.float64)
    packed_shift = shift[rows, columns] * scale
    target += (np.outer(packed_shift, identity) + np.outer(identity, packed_shift)) * 0.5
    omission = omission_bounds(features, target, w.shape[1])
    write_json(output, {
        "scope": "fixed decoded dictionary and native offsets; greedy per-group projection, no emitted loader",
        "driver_sha256": sha256(Path(__file__)), "factorization_sha256": CONTROL_SHA256,
        "source_pins": SOURCE_PINS, "fcidump_sha256": reference.FCIDUMP_SHA256,
        "fixed_shifts_sha256": reference.FIXED_SHIFTS_SHA256, "control": control, "outcomes": outcomes,
        "relaxed_omissions": omission,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("factorization", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
