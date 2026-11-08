"""Symmetric pair coordinates and the continuous DFTHC residual."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.cluster.hierarchy import cut_tree, linkage
from scipy.optimize import linear_sum_assignment

Floats = NDArray[np.float64]


def svec(matrices: Floats) -> Floats:
    i, j = np.triu_indices(matrices.shape[-1])
    return matrices[..., i, j] * np.where(i == j, 1.0, np.sqrt(2.0))


def symmetric_matrix(rows: Floats, n: int) -> Floats:
    i, j = np.triu_indices(n)
    result = np.zeros((*rows.shape[:-1], n, n), dtype=np.float64)
    entries = rows / np.where(i == j, 1.0, np.sqrt(2.0))
    result[..., i, j] = result[..., j, i] = entries
    return result


def shifted_target(tei: Floats, shift: Floats) -> Floats:
    n = len(shift)
    if tei.shape != (n,) * 4 or shift.shape != (n, n):
        raise ValueError("invalid tensor or fixed shift dimensions")
    if not np.array_equal(shift, shift.T):
        raise ValueError("expected a symmetric fixed shift")
    for p, slab in enumerate(tei):
        if not (
            np.array_equal(slab, tei[:, p])
            and np.array_equal(slab, slab.swapaxes(1, 2))
            and np.array_equal(slab, tei[:, :, p, :].transpose(2, 0, 1))
        ):
            raise ValueError("cannot compress a tensor without exact pair symmetry")
    i, j = np.triu_indices(n)
    scale = np.where(i == j, 1.0, np.sqrt(2.0))
    target = tei[i[:, None], j[:, None], i, j] * scale[:, None] * scale
    # Symmetric construction avoids roundoff-dependent asymmetry from the two scales.
    target = (target + target.T) * 0.5
    diagonal, packed = svec(np.eye(n)), svec(shift)
    return target + (np.outer(packed, diagonal) + np.outer(diagonal, packed)) * 0.5


def rank_lower_bound(spectrum: Floats, rank: int) -> float:
    """Exact-arithmetic best PSD rank residual from ascending eigenvalues."""
    if type(rank) is not int or rank < 1 or np.any(np.diff(spectrum) < 0):
        raise ValueError("expected ascending eigenvalues and a positive rank")
    keep = min(rank, int(np.count_nonzero(spectrum > 0)))
    tail = spectrum[:len(spectrum) - keep]
    return float(np.linalg.norm(tail))


def gram_residual(target: Floats, rows: Floats, target_norm_squared: float) -> tuple[float, Floats]:
    """Return the squared residual and its derivative with respect to factor rows."""
    products = rows @ target
    gram = rows @ rows.T
    squared = target_norm_squared - 2 * np.vdot(rows, products) + np.vdot(gram, gram)
    return float(squared), 4 * (gram @ rows - products)


def direct_residual(target: Floats, rows: Floats, *, block: int = 128) -> float:
    """Evaluate the residual stably in row blocks for checkpoint decisions."""
    total = 0.0
    for start in range(0, len(target), block):
        stop = min(start + block, len(target))
        delta = rows[:, start:stop].T @ rows - target[start:stop]
        total += float(np.vdot(delta, delta))
    return float(np.sqrt(total))


def initialize(spectrum: Floats, vectors: Floats, n: int, shape: tuple[int, int, int]) -> tuple[Floats, Floats]:
    """Group consecutive positive spectral factors and fit real rank-one features."""
    r, b, c = shape
    if min(shape) < 1 or r * c > np.count_nonzero(spectrum > 0) or b > n * c:
        raise ValueError("requested shape exceeds available positive spectral features")
    groups = (vectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T.reshape(r, c, -1)
    basis = np.empty((r, b, n), dtype=np.float64)
    weights = np.empty((r, b, c), dtype=np.float64)
    for k, group in enumerate(groups):
        eigenvalues, eigenvectors = np.linalg.eigh(symmetric_matrix(group, n))
        order = np.argsort(-np.abs(eigenvalues).ravel(), kind="stable")[:b]
        basis[k] = eigenvectors.swapaxes(-1, -2).reshape(-1, n)[order]
        features = svec(basis[k, :, :, None] * basis[k, :, None, :])
        weights[k] = np.linalg.lstsq(features.T, group.T, rcond=1e-10)[0]
    return basis, weights


def factor_rows(features: Floats, weights: Floats) -> Floats:
    return np.einsum("rbc,rbd->rcd", weights, features, optimize=True).reshape(-1, features.shape[-1])


@dataclass
class AlternatingFit:
    vectors: Floats
    weights: Floats
    residual: float
    rank_floor: float
    trace: list[dict[str, int | float]]


def fit_alternating(
    target: Floats, vectors: Floats, weights: Floats, sweeps: int, record_every: int,
    *, spectrum: tuple[Floats, Floats] | None = None,
    checkpoint: Callable[[dict[str, int | float], Floats, Floats], None] | None = None,
) -> AlternatingFit:
    """Fit spectral rows by exact block updates, retaining the best true residual."""
    if (
        vectors.ndim != 3 or weights.ndim != 3 or vectors.shape[:2] != weights.shape[:2]
        or min(*vectors.shape, *weights.shape) < 1
        or type(sweeps) is not int or type(record_every) is not int or min(sweeps, record_every) < 1
    ):
        raise ValueError("invalid alternating-fit shapes or sweep budget")
    groups, features_per_group, n = vectors.shape
    copies = weights.shape[2]
    pair_width = n * (n + 1) // 2
    if target.shape != (pair_width, pair_width) or not np.isfinite(target).all():
        raise ValueError("invalid packed target")
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms == 0) or not np.isfinite(weights).all():
        raise ValueError("nonfinite or zero starting factors")
    vectors = vectors / norms
    weights = weights.copy()
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    row_count = groups * copies
    values, eigenvectors = np.linalg.eigh(target) if spectrum is None else spectrum
    keep = min(row_count, int(np.count_nonzero(values > 0)))
    spectral = np.zeros((row_count, pair_width))
    if keep:
        spectral[-keep:] = (eigenvectors[:, -keep:] * np.sqrt(values[-keep:])).T

    best = AlternatingFit(vectors.copy(), weights.copy(), direct_residual(target, factor_rows(features, weights)),
                          rank_lower_bound(values, row_count), [])
    trace_start: dict[str, int | float] = {"sweep": 0, "continuous_residual": best.residual}
    best.trace.append(trace_start)
    if checkpoint is not None:
        checkpoint(trace_start, vectors, weights)
    diagonal = np.diag_indices(features_per_group)
    pair_i, pair_j = np.triu_indices(n)
    scale = np.where(pair_i == pair_j, 1.0, np.sqrt(2.0))
    symmetric = np.empty((n, n))
    for sweep in range(1, sweeps + 1):
        rows = factor_rows(features, weights)
        left, _, right = np.linalg.svd(rows @ spectral.T, full_matrices=False)
        aligned = ((left @ right) @ spectral).reshape(groups, copies, pair_width)
        surrogate = 0.0
        for basis, feature, w, goal in zip(vectors, features, weights, aligned, strict=True):
            gram = feature @ feature.T
            gram[diagonal] += 1e-10 * np.trace(gram) / features_per_group
            solved = np.linalg.solve(gram, feature @ goal.T)
            residual = goal - w.T @ feature
            trial_residual = goal - solved.T @ feature
            if np.vdot(trial_residual, trial_residual) <= np.vdot(residual, residual):
                w[:], residual = solved, trial_residual
            for b, column in enumerate(w):
                cross = column @ residual + np.dot(column, column) * feature[b]
                entries = cross / scale
                symmetric[pair_i, pair_j] = symmetric[pair_j, pair_i] = entries
                eigenvalues, directions = np.linalg.eigh(symmetric)
                if eigenvalues[-1] <= 0:
                    continue
                vector = directions[:, -1]
                if vector[np.argmax(np.abs(vector))] < 0:
                    vector = -vector
                new_feature = vector[pair_i] * vector[pair_j] * scale
                residual += column[:, None] * (feature[b] - new_feature)
                basis[b], feature[b] = vector, new_feature
            surrogate += float(np.vdot(residual, residual))
        if sweep % record_every == 0 or sweep == sweeps:
            actual = direct_residual(target, factor_rows(features, weights))
            point = {"sweep": sweep, "continuous_residual": actual, "surrogate_squared": surrogate}
            best.trace.append(point)
            if actual < best.residual:
                best.vectors, best.weights, best.residual = vectors.copy(), weights.copy(), actual
            if checkpoint is not None:
                checkpoint(point, vectors, weights)
    return best


def joint_residual(target: Floats, vectors: Floats, weights: Floats,
                   target_norm_squared: float) -> tuple[float, Floats, Floats]:
    """Squared residual and gradients for unconstrained, normalized basis vectors."""
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if not np.all(np.isfinite(lengths)) or np.any(lengths == 0):
        raise ValueError("basis vectors must have finite nonzero norms")
    unit = vectors / lengths
    features = svec(unit[..., :, None] * unit[..., None, :])
    squared, row_grad = gram_residual(target, factor_rows(features, weights), target_norm_squared)
    row_grad = row_grad.reshape(weights.shape[0], weights.shape[2], -1)
    weight_grad = np.einsum("rcd,rbd->rbc", row_grad, features, optimize=True)
    feature_grad = np.einsum("rbc,rcd->rbd", weights, row_grad, optimize=True)
    unit_grad = 2 * np.einsum("rbij,rbj->rbi", symmetric_matrix(feature_grad, vectors.shape[-1]),
                              unit, optimize=True)
    vector_grad = (unit_grad - unit * np.sum(unit * unit_grad, axis=-1, keepdims=True)) / lengths
    return squared, vector_grad, weight_grad


def pursuit(candidates: Floats, targets: Floats, count: int) -> tuple[Floats, Floats]:
    """Greedily choose independent square features to project the target rows."""
    candidates = candidates / np.linalg.norm(candidates, axis=-1, keepdims=True)
    features = svec(candidates[..., :, None] * candidates[..., None, :])
    orthogonal = features.copy()
    remainder = targets.copy()
    chosen: list[int] = []
    for _ in range(count):
        norms = np.linalg.norm(orthogonal, axis=1)
        valid = norms > 1e-10
        if not np.any(valid):
            raise ValueError("not enough independent candidate square features")
        scores = np.full(len(candidates), -np.inf)
        scores[valid] = np.sum((orthogonal[valid] @ remainder.T) ** 2, axis=1) / norms[valid] ** 2
        index = int(np.argmax(scores))
        direction = orthogonal[index] / norms[index]
        chosen.append(index)
        orthogonal -= (orthogonal @ direction)[:, None] * direction
        remainder -= (remainder @ direction)[:, None] * direction
    basis = candidates[chosen]
    weights = np.asarray(np.linalg.lstsq(features[chosen].T, targets.T, rcond=1e-10)[0], dtype=np.float64)
    return basis, weights


def clustered_initialize(spectrum: Floats, eigenvectors: Floats, n: int,
                         shape: tuple[int, int, int], seed: int) -> tuple[Floats, Floats]:
    """Cluster spectral factors by dominant-vector overlap, then pursue bases."""
    r, b, c = shape
    if min(shape) < 1 or r * c > np.count_nonzero(spectrum > 0) or b > n * c:
        raise ValueError("requested shape exceeds available positive spectral features")
    groups = (eigenvectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T
    values, vectors = np.linalg.eigh(symmetric_matrix(groups, n))
    order = np.argsort(-np.abs(values), axis=1, kind="stable")
    vectors = np.take_along_axis(vectors.swapaxes(-1, -2), order[..., None], axis=1)
    descriptors = svec(vectors[:, 0, :, None] * vectors[:, 0, None, :])
    descriptor_norms = np.sum(descriptors * descriptors, axis=1)
    centers = descriptors[np.random.default_rng(seed).choice(r * c, r, replace=False)].copy()
    assignment = np.full(r * c, -1, dtype=int)
    for _ in range(8):
        distance = descriptor_norms[:, None] + np.sum(centers * centers, axis=1) - 2 * descriptors @ centers.T
        rows, slots = linear_sum_assignment(np.repeat(distance, c, axis=1))
        new_assignment = np.empty(r * c, dtype=int)
        new_assignment[rows] = slots // c
        if np.array_equal(new_assignment, assignment):
            break
        assignment = new_assignment
        centers = np.stack([descriptors[assignment == k].mean(axis=0) for k in range(r)])
    basis = np.empty((r, b, n))
    weights = np.empty((r, b, c))
    per_factor = min(n, max(1, (b + c - 1) // c + 1))
    for k in range(r):
        basis[k], weights[k] = pursuit(vectors[assignment == k, :per_factor].reshape(-1, n),
                                       groups[assignment == k], b)
    return basis, weights


def continuation_initialize(reference_vectors: Floats, reference_weights: Floats,
                            shape: tuple[int, int, int]) -> tuple[Floats, Floats]:
    """Merge reference groups by basis similarity and compress their factor rows."""
    r, b, c = shape
    original_r, original_b, n = reference_vectors.shape
    if not 1 <= r <= original_r or not 1 <= b or not 1 <= c:
        raise ValueError("invalid continuation shape")
    vectors = reference_vectors / np.linalg.norm(reference_vectors, axis=-1, keepdims=True)
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    labels = (np.zeros(original_r, dtype=int) if r == 1 else
              cut_tree(linkage(features.mean(axis=1), method="average"), n_clusters=r).ravel())
    basis = np.empty((r, b, n))
    weights = np.empty((r, b, c))
    for k in range(r):
        selected = labels == k
        rows = factor_rows(features[selected], reference_weights[selected])
        _, singular, right = np.linalg.svd(rows, full_matrices=False)
        if len(singular) < c or original_r * original_b < b:
            raise ValueError("merged group cannot support the requested continuation shape")
        targets = singular[:c, None] * right[:c]
        candidates = vectors[selected].reshape(-1, n)
        if len(candidates) < b:
            candidates = np.concatenate((candidates, vectors[~selected].reshape(-1, n)[:b - len(candidates)]))
        basis[k], weights[k] = pursuit(candidates, targets, b)
    return basis, weights


def projection_score(spectral_rows: Floats, basis: Floats, copies: int) -> float:
    """Best balanced grouped spectral projection error for a fixed basis.

    This is a factor-space diagnostic, not a lower bound on the DFTHC residual:
    factor rotations can change the grouping and improve the represented tensor.
    """
    r, _, _ = basis.shape
    if copies < 1 or len(spectral_rows) != r * copies:
        raise ValueError("spectral row count must equal groups times copies")
    unit = basis / np.linalg.norm(basis, axis=-1, keepdims=True)
    features = svec(unit[..., :, None] * unit[..., None, :])
    distances = np.empty((len(spectral_rows), r))
    for k, feature in enumerate(features):
        coefficients = np.linalg.lstsq(feature.T, spectral_rows.T, rcond=1e-10)[0]
        residual = spectral_rows - (feature.T @ coefficients).T
        distances[:, k] = np.sum(residual * residual, axis=1)
    rows, slots = linear_sum_assignment(np.repeat(distances, copies, axis=1))
    return float(np.sqrt(np.sum(distances[rows, slots // copies])))
