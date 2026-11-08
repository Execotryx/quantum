"""Independent finite-difference checks of the joint chemistry objective."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from qcompile.chemistry.factorization import (
    clustered_initialize,
    continuation_initialize,
    direct_residual,
    factor_rows,
    joint_residual,
    projection_score,
    shifted_target,
    svec,
)
from qcompile.chemistry.smooth_objective import augmented_objective, smooth_terms


def test_joint_gradient_all_coordinates():
    rng = np.random.default_rng(184)
    n, r, b, c = 8, 2, 3, 2
    target_rows = rng.normal(size=(5, n * (n + 1) // 2))
    target = target_rows.T @ target_rows
    norm = float(np.vdot(target, target))
    vectors = rng.normal(size=(r, b, n))
    weights = rng.normal(size=(r, b, c))
    _, grad_v, grad_w = joint_residual(target, vectors, weights, norm)
    for values, gradient in ((vectors, grad_v), (weights, grad_w)):
        for index in np.ndindex(values.shape):
            original = values[index]
            step = 1e-5
            values[index] = original + step
            plus = joint_residual(target, vectors, weights, norm)[0]
            values[index] = original - step
            minus = joint_residual(target, vectors, weights, norm)[0]
            values[index] = original
            assert (plus - minus) / (2 * step) == pytest.approx(gradient[index], rel=1e-6, abs=1e-7)


def pinned_math():
    source = (Path(__file__).resolve().parents[1] / "vendor/official/verifiers/dfthcsos"
              / "scoreinfra/dfthc_math.py")
    if not source.exists():
        pytest.skip("pinned verifier sources unavailable")
    spec = importlib.util.spec_from_file_location("pinned_dfthc_math", source)
    assert spec and spec.loader
    math_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(math_api)
    return math_api


def test_packed_residual_matches_pinned_tensor_math():
    math_api = pinned_math()
    rng = np.random.default_rng(93)
    n, r, b, c = 8, 2, 3, 2
    generators = rng.normal(size=(4, n, n))
    generators = generators + generators.swapaxes(-1, -2)
    tei = np.einsum("apq,ars->pqrs", generators, generators)
    shift = np.diag(rng.normal(size=n))
    vectors = rng.normal(size=(r, b, n))
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    weights = rng.normal(size=(r, b, c))
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    packed = direct_residual(shifted_target(tei, shift), factor_rows(features, weights))
    delta = math_api.reconstruct_h2(math_api.reconstruct_x(vectors, weights)) - tei
    diagonal = np.arange(n)
    delta[:, :, diagonal, diagonal] -= 0.5 * shift[:, :, None]
    delta[diagonal, diagonal, :, :] -= 0.5 * shift[None, :, :]
    assert packed == pytest.approx(np.linalg.norm(delta), rel=1e-12)


def test_clustered_and_continuation_initializers():
    rng = np.random.default_rng(98)
    n, r, b, c = 5, 2, 3, 2
    dim = n * (n + 1) // 2
    orthogonal, _ = np.linalg.qr(rng.normal(size=(dim, dim)))
    spectrum = np.arange(1, dim + 1, dtype=np.float64)
    clustered, clustered_w = clustered_initialize(spectrum, orthogonal, n, (r, b, c), 7)
    repeat, repeat_w = clustered_initialize(spectrum, orthogonal, n, (r, b, c), 7)
    assert np.array_equal(clustered, repeat)
    assert np.array_equal(clustered_w, repeat_w)
    assert np.allclose(np.linalg.norm(clustered, axis=-1), 1)
    reference = rng.normal(size=(4, 3, n))
    reference_w = rng.normal(size=(4, 3, c))
    merged, merged_w = continuation_initialize(reference, reference_w, (r, b, c))
    assert merged.shape == (r, b, n)
    assert merged_w.shape == (r, b, c)
    assert np.all(np.isfinite(merged_w))
    assert np.allclose(np.linalg.norm(merged, axis=-1), 1)


def test_balanced_projection_score():
    basis = np.eye(3)[None, :, :]
    features = svec(basis[0, :, :, None] * basis[0, :, None, :])
    assert projection_score(features[:2], basis, 2) == pytest.approx(0, abs=1e-14)
    off_diagonal = svec((np.ones((3, 3)) - np.eye(3))[None, :, :])
    assert projection_score(np.concatenate((features[:1], off_diagonal)), basis, 2) == pytest.approx(np.sqrt(6))


def test_smooth_terms_gradient_and_pinned_formula():
    rng = np.random.default_rng(471)
    vectors = rng.normal(size=(2, 3, 4))
    weights = rng.normal(size=(2, 3, 2))
    offsets = rng.normal(size=(2, 2))
    raw = rng.normal(size=(4, 4))
    base = raw + raw.T
    terms, grad_v, grad_w, grad_offsets = smooth_terms(vectors, weights, offsets, base, 2.5)
    unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
    x = np.einsum("rbc,rbi,rbj->rcij", weights, unit, unit)
    eig = np.linalg.eigvalsh(base - np.einsum("rc,rcij->ij", offsets, x))
    assert terms[0] == pytest.approx(np.sum(np.abs(eig)) + pinned_math().lambda_h2(weights, offsets), rel=1e-12)
    assert terms[1] == pytest.approx(2.5 + np.sum(np.abs(eig) - eig) + np.sum(offsets**2) / 2, rel=1e-12)
    for values, gradient in ((vectors, grad_v), (weights, grad_w), (offsets, grad_offsets)):
        for index in np.ndindex(values.shape):
            original = values[index]
            values[index] = original + 1e-5
            plus = smooth_terms(vectors, weights, offsets, base, 2.5)[0]
            values[index] = original - 1e-5
            minus = smooth_terms(vectors, weights, offsets, base, 2.5)[0]
            values[index] = original
            assert np.allclose((plus - minus) / 2e-5, gradient[(slice(None), *index)], rtol=1e-6, atol=1e-7)


def test_augmented_objective_gradient():
    rng = np.random.default_rng(431)
    n = 4
    vectors = rng.normal(size=(2, 3, n))
    weights = rng.normal(size=(2, 3, 2))
    offsets = rng.normal(size=(2, 2))
    h1 = np.diag([-3.0, -1.0, 2.0, 5.0])
    target_rows = rng.normal(size=(3, n * (n + 1) // 2))
    target = target_rows.T @ target_rows
    terms = smooth_terms(vectors, weights, offsets, h1, 0)[0]
    gap_base = float(terms[0] - terms[1])
    multipliers = np.array([0.2, 0.3, 0.4])
    _, grad_v, grad_w, grad_offsets = augmented_objective(
        target, vectors, weights, offsets, h1, gap_base, multipliers, 0.01
    )
    for values, gradient in ((vectors, grad_v), (weights, grad_w), (offsets, grad_offsets)):
        for index in np.ndindex(values.shape):
            original = values[index]
            values[index] = original + 1e-5
            plus = augmented_objective(target, vectors, weights, offsets, h1, gap_base, multipliers, 0.01)[0]
            values[index] = original - 1e-5
            minus = augmented_objective(target, vectors, weights, offsets, h1, gap_base, multipliers, 0.01)[0]
            values[index] = original
            assert (plus - minus) / 2e-5 == pytest.approx(gradient[index], rel=1e-6, abs=1e-7)


def test_smooth_terms_agree_with_pinned_evaluator():
    rng = np.random.default_rng(701)
    n, electrons = 4, 2
    vectors = rng.normal(size=(2, 3, n))
    weights = rng.normal(size=(2, 3, 2))
    offsets = rng.normal(size=(2, 2))
    oei = np.diag([-2.0, -1.0, 1.0, 3.0])
    tei = np.zeros((n,) * 4)
    shift = np.eye(n) * 0.1
    beta, upper, ecore = 0.3, 5.0, -2.0
    ref = {"oei": oei, "tei": tei, "electrons": electrons, "ecore": ecore}
    pinned = pinned_math().evaluate_dfthc_vectors(
        np.concatenate((np.eye(n), vectors.reshape(-1, n))), weights, offsets, shift, beta, ref,
        energy_upper=upper,
    )
    base = oei - electrons * shift / 2 + beta * np.eye(n)
    terms = smooth_terms(vectors, weights, offsets, base, upper - ecore + electrons * beta)[0]
    assert terms[0] == pytest.approx(pinned["Lambda"], rel=1e-12)
    assert terms[1] == pytest.approx(pinned["E_gap"], rel=1e-12)
