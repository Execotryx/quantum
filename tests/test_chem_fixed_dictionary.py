import numpy as np

from qcompile.chemistry.factorization import factor_rows, gram_residual
from qcompile.chemistry.fixed_dictionary import FixedDictionaryGram, truncate_channels


def test_fixed_dictionary_objective_matches_pair_matrix():
    rng = np.random.default_rng(333)
    features = rng.normal(size=(3, 4, 7))
    weights = rng.normal(size=(3, 4, 2))
    target = rng.normal(size=(7, 7))
    target = target + target.T
    rows = factor_rows(features, weights)
    expected, row_grad = gram_residual(target, rows, float(np.vdot(target, target)))
    actual, weight_grad = FixedDictionaryGram(target, features).objective(weights)
    assert np.isclose(expected, actual)
    assert np.allclose(weight_grad, features @ row_grad.reshape(3, 2, 7).swapaxes(1, 2))


def test_fixed_dictionary_truncation_rotates_offsets_with_physical_channels():
    features = np.eye(3)[None]
    weights = np.diag([1.0, 3.0, 2.0])[None]
    offsets = np.array([[2.0, 4.0, -7.0]])
    shortened, native = truncate_channels(features, weights, offsets, 2)
    assert np.allclose(shortened[0] @ native[0], [0.0, 12.0, -14.0])
    assert np.allclose(shortened[0] @ shortened[0].T, np.diag([0.0, 9.0, 4.0]))
