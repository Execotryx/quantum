import math
import zipfile
from fractions import Fraction

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.representation import (
    batch_words,
    canonical_signs,
    decode_angle,
    encode_angle,
    reconstruct,
    residual_frobenius,
    validate_tree,
    workspace_cost,
)
from qcompile.chemistry.schema import read_factorization
from qcompile.errors import ValidationError


def arrays():
    return {
        "U": np.ones((2, 3, 76), dtype="<f8"),
        "W": np.ones((2, 3, 4)),
        "H2_I": np.ones((2, 4)),
        "H1_I": np.array(1.0),
        "Hsym_lower": np.zeros(2926),
        "tree_edges": np.array([[0, i] for i in range(1, 76)], dtype="<i8"),
    }


def test_pinned_metric_schema_roundtrip_and_byte_determinism(tmp_path):
    original = arrays()
    a, b = tmp_path / "a.npz", tmp_path / "b.npz"
    deterministic_npz(a, original)
    deterministic_npz(b, dict(reversed(list(original.items()))))
    assert a.read_bytes() == b.read_bytes()
    observed = read_factorization(a)
    for key in original:
        np.testing.assert_array_equal(original[key], observed[key])


@pytest.mark.parametrize(
    "key,value",
    [
        ("U", np.ones((2, 3, 75))),
        ("H1_I", np.ones(1)),
        ("W", np.ones((2, 5, 4))),
        ("tree_edges", np.ones((75, 2))),
        ("H1_I", np.array(complex(1, 2))),
    ],
)
def test_bad_npz_schema(tmp_path, key, value):
    data = arrays() | {key: value}
    path = tmp_path / "bad.npz"
    np.savez(path, **data)
    with pytest.raises(ValidationError):
        read_factorization(path)


@pytest.mark.parametrize(
    "value",
    [
        np.array(float("nan")),
        np.array(float("inf")),
        np.array(1, dtype=">f8"),
        np.array({"malicious": "object"}, dtype=object),
    ],
)
def test_nonfinite_endian_and_object_rejected(tmp_path, value):
    path = tmp_path / "bad.npz"
    np.savez(path, **(arrays() | {"H1_I": value}))
    with pytest.raises(ValidationError):
        read_factorization(path)


def test_npz_duplicate_and_allocation_preflight(tmp_path):
    path = tmp_path / "good.npz"
    deterministic_npz(path, arrays())
    with pytest.raises(ValidationError, match="byte limit"):
        read_factorization(path, max_bytes=10)
    with zipfile.ZipFile(path, "a") as archive:
        with pytest.warns(UserWarning):
            archive.writestr("H1_I.npy", b"not an array")
    with pytest.raises(ValidationError, match="exactly one"):
        read_factorization(path)


def test_rooted_ordered_tree_and_known_invalid_order():
    tree = np.array([[0, 1], [1, 2], [0, 3]])
    validate_tree(tree, 4, 0)
    for bad in ([[1, 2], [0, 1], [0, 3]], [[0, 1], [1, 0], [0, 3]], [[0, 1], [0, 2], [0, 4]]):
        with pytest.raises(ValidationError, match="parent-before-child"):
            validate_tree(bad, 4, 0)


def test_angle_rounding_ties_wrap_and_explicit_units():
    assert encode_angle(Fraction(1, 8), 3, rounding="nearest_even") == 0
    assert encode_angle(Fraction(3, 8), 3, rounding="nearest_even") == 2
    assert encode_angle(2, 16, rounding="nearest_even") == 0
    assert encode_angle(Fraction(-1, 4), 3, rounding="floor") == 7
    assert decode_angle(7, 3) == Fraction(7, 4)
    vector = reconstruct([2], 3, np.array([[0, 1]]), 2, 0, radians_per_unit=math.pi)
    np.testing.assert_allclose(vector, [0, 1], atol=1e-15)
    # A legal sign flip preserves the outer product; coordinates needn't match.
    flipped = reconstruct([6], 3, np.array([[0, 1]]), 2, 0, radians_per_unit=math.pi)
    np.testing.assert_allclose(np.outer(vector, vector), np.outer(flipped, flipped), atol=1e-15)


def test_batches_xor_deltas_reverse_and_partial_padding():
    words = np.array([[1, 2, 3, 4, 5], [0, 0, 0, 3, 3]], dtype=np.uint16)
    batches, deltas = batch_words(words, 2, 4)
    state = np.zeros((2, 2), dtype=np.uint16)
    for batch, delta in zip(batches, deltas, strict=True):
        state ^= delta
        np.testing.assert_array_equal(state, batch)
    for delta in reversed(deltas):
        state ^= delta
    assert np.all(state == 0)
    np.testing.assert_array_equal(batches[-1][:, 1], 0)


def test_streamed_shifted_residual_matches_small_dense_reference():
    rng = np.random.default_rng(154)
    a, b, s = rng.normal(size=(3, 7, 7))
    blocks = [(a[i : i + 2], b[i : i + 2], s[i : i + 2]) for i in range(0, 7, 2)]
    assert residual_frobenius(blocks) == pytest.approx(np.linalg.norm(a - b - s))
    assert residual_frobenius([(a, b, s)]) != pytest.approx(np.linalg.norm(a - b))
    assert workspace_cost(500, {"lookup": 128, "givens": 76, "outer": 17}) == 628


def test_deterministic_sign_policy_and_degenerate_subspace():
    vectors = np.array([[-1e-20, -1, 0], [1, 0, 0]])
    canonical = canonical_signs(vectors)
    np.testing.assert_allclose(vectors.T @ vectors, canonical.T @ canonical)
    assert canonical[0, 1] > 0
    base = np.diag([1.0, 1.0, 4.0])
    perturbed = base + np.array([[1e-12, 2e-12, 0], [2e-12, -1e-12, 0], [0, 0, 0]])
    _, u = np.linalg.eigh(base)
    _, v = np.linalg.eigh(perturbed)
    np.testing.assert_allclose(u[:, :2] @ u[:, :2].T, v[:, :2] @ v[:, :2].T, atol=1e-14)
    # Stability checks use invariant subspaces, not falsely smooth eigenvector bytes.
    assert not np.allclose(u[:, :2], v[:, :2])
