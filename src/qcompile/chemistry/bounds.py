"""Fixed-basis relaxed lower bounds for continuous DFTHC residuals."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from .factorization import rank_lower_bound, svec

Floats = NDArray[np.float64]


def fixed_basis_rank_bound(target: Floats, vectors: Floats, rank: int, *, block: int = 128) -> dict[str, Any]:
    """Evaluate the global-feature-span, PSD rank relaxation of a fixed basis.

    In exact arithmetic, every factor row lies in the union feature span S.
    Dropping group restrictions yields PSD rank-at-most-``rank`` matrices in
    S. Orthogonal projection separates the target outside S from its best PSD
    rank-``rank`` approximation inside S. QR deliberately keeps all columns,
    including redundant ones, enlarging S rather than truncating small modes.

    Floating-point output is an estimate, not a certified lower bound. It may
    only bound this fixed basis, never a shape whose basis can change.
    """
    if (target.ndim != 2 or target.shape[0] != target.shape[1] or vectors.ndim != 3
            or type(rank) is not int or rank < 1 or type(block) is not int or block < 1
            or not np.isfinite(target).all() or not np.isfinite(vectors).all()
            or not np.allclose(target, target.T, rtol=0, atol=1e-12)):
        raise ValueError("expected finite symmetric target, basis and positive bounds")
    n = vectors.shape[-1]
    if target.shape != (n * (n + 1) // 2,) * 2:
        raise ValueError("target and basis dimensions disagree")
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if np.any(lengths == 0):
        raise ValueError("basis contains a zero vector")
    unit = vectors / lengths
    features = svec(unit[..., :, None] * unit[..., None, :]).reshape(-1, len(target))
    q, _ = np.linalg.qr(features.T, mode="reduced")
    core = q.T @ (target @ q)
    core = (core + core.T) / 2
    spectrum = np.asarray(np.linalg.eigvalsh(core), dtype=np.float64)
    residual_squared = 0.0
    core_qt = core @ q.T
    for start in range(0, len(target), block):
        stop = min(start + block, len(target))
        difference = target[start:stop] - q[start:stop] @ core_qt
        residual_squared += float(np.vdot(difference, difference))
    tail = rank_lower_bound(spectrum, rank)
    orthogonality_error = float(np.linalg.norm(q.T @ q - np.eye(q.shape[1])))
    return {
        "estimate": float(np.sqrt(residual_squared + tail * tail)),
        "outside_span_residual": float(np.sqrt(residual_squared)),
        "inside_psd_rank_residual": tail,
        "relaxed_span_columns": q.shape[1], "feature_rows": len(features), "factor_rank_cap": rank,
        "qr_orthogonality_frobenius": orthogonality_error,
        "scope": "fixed basis only; floating-point estimate is not a certified exclusion bound",
    }
