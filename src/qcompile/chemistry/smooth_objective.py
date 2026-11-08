"""Smooth derivatives of the pinned DFTHC Lambda and energy-gap terms.

Exact decision metrics remain the responsibility of the pinned evaluator.
"""

import numpy as np
from numpy.typing import NDArray

from .factorization import joint_residual

Floats = NDArray[np.float64]


def smooth_terms(vectors: Floats, weights: Floats, offsets: Floats, h1_base: Floats,
                 gap_base: float, epsilon: float = 1e-8) -> tuple[Floats, Floats, Floats, Floats]:
    """Return (Lambda, gap) and Jacobians wrt vectors, weights, and offsets.

    ``h1_base`` is h1_thc - electrons*S/2 + beta*I; ``gap_base`` is
    energy_upper - ecore + electrons*beta. Both derive from the pinned evaluator.
    """
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if not np.all(np.isfinite(lengths)) or np.any(lengths == 0):
        raise ValueError("basis vectors must be finite and nonzero")
    u = vectors / lengths
    x = np.einsum("rbc,rbi,rbj->rcij", weights, u, u, optimize=True)
    h1 = h1_base - np.einsum("rc,rcij->ij", offsets, x, optimize=True)
    eig, rotation = np.linalg.eigh(h1)
    smooth_eig = np.sqrt(eig * eig + epsilon * epsilon)
    signed = (rotation * (eig / smooth_eig)) @ rotation.T
    smooth_w = np.sqrt(weights * weights + epsilon * epsilon)
    w_b = offsets + weights.sum(axis=1)
    smooth_b = np.sqrt(w_b * w_b + epsilon * epsilon)
    a = smooth_w.sum(axis=1) + smooth_b
    one_norm = float(smooth_eig.sum())
    terms = np.array([one_norm + 0.25 * np.sum(a * a),
                      gap_base + one_norm - eig.sum() + 0.5 * np.sum(offsets * offsets)])
    matrix_grads = np.stack((signed, signed - np.eye(len(eig))))
    grad_x = -matrix_grads[:, None, None, :, :] * offsets[None, :, :, None, None]
    grad_w = np.einsum("trcij,rbi,rbj->trbc", grad_x, u, u, optimize=True)
    grad_u = 2 * np.einsum("trcij,rbc,rbj->trbi", grad_x, weights, u, optimize=True)
    grad_v = (grad_u - u[None] * np.sum(grad_u * u[None], axis=-1, keepdims=True)) / lengths[None]
    grad_offsets = -np.einsum("tij,rcij->trc", matrix_grads, x, optimize=True)
    grad_w[0] += 0.5 * a[:, None, :] * (weights / smooth_w + (w_b / smooth_b)[:, None, :])
    grad_offsets[0] += 0.5 * a * w_b / smooth_b
    grad_offsets[1] += offsets
    return terms, grad_v, grad_w, grad_offsets


def augmented_objective(target: Floats, vectors: Floats, weights: Floats, offsets: Floats,
                        h1_base: Floats, gap_base: float, multipliers: Floats, penalty: float,
                        *, residual_limit: float = 0.019, lambda_floor: float = 49.05,
                        gap_floor: float = 3.916, epsilon: float = 1e-8
                        ) -> tuple[float, Floats, Floats, Floats]:
    """One smooth augmented-Lagrangian objective with fixed multipliers.

    Inequalities are squared residual minus its limit, Lambda floor minus
    Lambda, and gap floor minus gap. The caller updates nonnegative multipliers
    between optimizer runs and evaluates exact checkpoint metrics separately.
    """
    if multipliers.shape != (3,) or np.any(multipliers < 0) or not penalty > 0:
        raise ValueError("expected three nonnegative multipliers and a positive penalty")
    terms, term_v, term_w, term_offsets = smooth_terms(vectors, weights, offsets, h1_base, gap_base, epsilon)
    lam, gap = terms
    radicand = gap * (2 * lam - gap)
    if not np.isfinite(radicand) or gap <= 0 or radicand <= 0:
        raise ValueError("smooth lambda_eff is outside its domain")
    effective = float(np.sqrt(radicand))
    squared, residual_v, residual_w = joint_residual(target, vectors, weights, float(np.vdot(target, target)))
    constraints = np.array([squared - residual_limit**2, lambda_floor - lam, gap_floor - gap])
    active = np.maximum(0, multipliers + penalty * constraints)
    value = effective + float(np.sum(active * active - multipliers * multipliers)) / (2 * penalty)
    term_coefficients = np.array([gap / effective - active[1], (lam - gap) / effective - active[2]])
    grad_v = np.tensordot(term_coefficients, term_v, axes=1) + active[0] * residual_v
    grad_w = np.tensordot(term_coefficients, term_w, axes=1) + active[0] * residual_w
    grad_offsets = np.tensordot(term_coefficients, term_offsets, axes=1)
    return float(value), np.asarray(grad_v, dtype=np.float64), np.asarray(grad_w, dtype=np.float64), np.asarray(grad_offsets, dtype=np.float64)
