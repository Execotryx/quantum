"""Symmetric pair coordinates and the continuous DFTHC residual."""

import numpy as np
from numpy.typing import NDArray

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
