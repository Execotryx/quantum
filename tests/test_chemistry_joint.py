"""Independent finite-difference checks of the joint chemistry objective."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from qcompile.chemistry.factorization import (
    direct_residual,
    factor_rows,
    joint_residual,
    shifted_target,
    svec,
)


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


def test_packed_residual_matches_pinned_tensor_math():
    source = (Path(__file__).resolve().parents[1] / "vendor/official/verifiers/dfthcsos"
              / "scoreinfra/dfthc_math.py")
    if not source.exists():
        pytest.skip("pinned verifier sources unavailable")
    spec = importlib.util.spec_from_file_location("pinned_dfthc_math", source)
    assert spec and spec.loader
    math_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(math_api)
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
