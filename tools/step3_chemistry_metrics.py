"""Independent matrix/block reconstruction compared with the pinned evaluator."""

import json
import math
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from qcompile.chemistry.representation import reconstruct
from qcompile.io import read_json, sha256
from qcompile.official import validate_backend


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    verifier = import_module("dfthcsos.verify")
    mathematics = import_module("dfthcsos.scoreinfra.dfthc_math")
    words_path = root / "runs/step3-chemistry/recovered-words.npz"
    evidence = read_json(root / "docs/evidence/step3-chemistry-words.json")
    if sha256(words_path) != evidence["words_sha256"]:
        raise ValueError("recovered word evidence changed")
    with np.load(words_path) as archive:
        words, edges = archive["words"], archive["edges"]
    inputs = verifier.load_inputs(root / "vendor/official/sample_submission/dfthcsos/submission.npz")
    vectors = np.array([reconstruct(row, 12, edges, 76, 0, radians_per_unit=math.pi) for row in words])
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    n = 76
    rank, bases, copies = inputs.w.shape
    factors = np.empty((rank, copies, n, n))
    two_body = vectors[n:].reshape(rank, bases, n)
    for r in range(rank):
        for c in range(copies):
            factors[r, c] = two_body[r].T @ (inputs.w[r, :, c, None] * two_body[r])
    for p in range(n):
        for q in range(p):
            factors[:, :, q, p] = factors[:, :, p, q]
    h1 = inputs.ref["oei"].copy()
    for r in range(n):
        h1 -= 0.5 * inputs.ref["tei"][:, r, r, :]
    weighted = np.zeros((n, n))
    for r in range(rank):
        for c in range(copies):
            weighted += inputs.W[r, c] * factors[r, c]
    shift = 0.5 * inputs.ref["electrons"] * inputs.S - inputs.beta_1 * np.eye(n)
    eigenvalues, eigenvectors = np.linalg.eigh(h1 - shift - weighted)
    rows, columns = linear_sum_assignment(-np.abs(vectors[:n] @ eigenvectors))
    matched = np.empty(n)
    matched[rows] = eigenvalues[columns]
    h1_decoded = vectors[:n].T @ (matched[:, None] * vectors[:n]) + shift + weighted
    factors_flat = factors.reshape(rank * copies, n * n)
    symmetry = inputs.S.reshape(-1)
    identity = np.eye(n).reshape(-1)
    integrals = inputs.ref["tei"].reshape(n * n, n * n)
    residual_squares = []
    for start in range(0, n * n, 8):
        stop = min(start + 8, n * n)
        delta = factors_flat[:, start:stop].T @ factors_flat - integrals[start:stop]
        delta -= 0.5 * (symmetry[start:stop, None] * identity + identity[start:stop, None] * symmetry)
        residual_squares.append(float(np.sum(delta * delta)))
    lambda1 = math.fsum(abs(float(value)) for value in eigenvalues)
    lambda2 = 0.25 * math.fsum(
        (
            math.fsum(abs(float(x)) for x in inputs.w[r, :, c])
            + abs(float(inputs.W[r, c]) + math.fsum(float(x) for x in inputs.w[r, :, c]))
        )
        ** 2
        for r in range(rank)
        for c in range(copies)
    )
    energy = (
        inputs.ref["ecore"]
        - inputs.ref["electrons"] * inputs.beta_1
        - lambda1
        + math.fsum(float(x) for x in eigenvalues)
        - 0.5 * math.fsum(float(x) ** 2 for x in inputs.W.flat)
    )
    gap = inputs.energy_upper - energy
    actual = {
        "error_1": float(np.linalg.norm(h1_decoded - h1)),
        "error_2": math.sqrt(math.fsum(residual_squares)),
        "Lambda": lambda1 + lambda2,
        "E_SOS": energy,
        "E_gap": gap,
        "lambda_eff": math.sqrt(gap * (2 * (lambda1 + lambda2) - gap)),
    }
    expected = mathematics.evaluate_dfthc_vectors(
        vectors, inputs.w, inputs.W, inputs.S, inputs.beta_1, inputs.ref, energy_upper=inputs.energy_upper
    )
    for name, value in actual.items():
        if not math.isclose(value, expected[name], rel_tol=2e-9, abs_tol=2e-9):
            raise ValueError(f"{name} disagreement: {value} versus {expected[name]}")
    print(
        json.dumps(
            {
                "independent": actual,
                "official": expected,
                "relative_tolerance": 2e-9,
                "absolute_tolerance": 2e-9,
                "residual_pair_block_rows": 8,
                "words_sha256": sha256(words_path),
            }
        )
    )


if __name__ == "__main__":
    main()
