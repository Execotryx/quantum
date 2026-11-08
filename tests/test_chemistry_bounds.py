"""The fixed-basis projection is a relaxation, not a joint-shape exclusion."""

import numpy as np
import pytest

from qcompile.chemistry.bounds import fixed_basis_rank_bound
from qcompile.chemistry.factorization import direct_residual, factor_rows, rank_lower_bound, svec


def test_full_span_matches_best_psd_rank_approximation():
    vectors = np.array([[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]])
    target = np.diag([-1.0, 2.0, 3.0])
    result = fixed_basis_rank_bound(target, vectors, rank=1)
    assert result["estimate"] == pytest.approx(np.sqrt(5), abs=1e-12)
    assert result["outside_span_residual"] == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("duplicate", [False, True])
def test_relaxation_never_exceeds_sampled_fixed_basis_residual(duplicate):
    rng = np.random.default_rng(625)
    n, r, b, c = 3, 2, 2, 2
    vectors = rng.normal(size=(r, b, n))
    if duplicate:
        vectors[0, 1] = vectors[0, 0]
    unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
    features = svec(unit[..., :, None] * unit[..., None, :])
    random = rng.normal(size=(n * (n + 1) // 2,) * 2)
    target = (random + random.T) / 2
    bound = fixed_basis_rank_bound(target, vectors, rank=r * c, block=2)
    global_bound = rank_lower_bound(np.asarray(np.linalg.eigvalsh(target), dtype=np.float64), r * c)
    assert bound["estimate"] + 1e-10 >= global_bound
    for _ in range(12):
        weights = rng.normal(size=(r, b, c))
        observed = direct_residual(target, factor_rows(features, weights), block=2)
        assert bound["estimate"] <= observed + 1e-10
    assert "not a certified" in bound["scope"]


def test_invalid_basis_rejected():
    with pytest.raises(ValueError, match="zero vector"):
        fixed_basis_rank_bound(np.eye(3), np.zeros((1, 1, 2)), rank=1)
