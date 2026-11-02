"""Explicit angle encoding policy and full-reference quantized perturbation."""

import json
import math
import sys
from fractions import Fraction
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.chemistry.representation import encode_angle, reconstruct
from qcompile.io import read_json, sha256
from qcompile.official import validate_backend


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    official = import_module("dfthcsos.verify")
    maths = import_module("dfthcsos.scoreinfra.dfthc_math")
    cases = [
        (Fraction(1, 4096), 0),
        (Fraction(3, 4096), 2),
        (Fraction(8191, 4096), 0),
        (Fraction(-1, 2048), 4095),
        (Fraction(2), 0),
        (Fraction(1, 2**50), 0),
    ]
    records = []
    edges = np.array([[0, 1], [1, 2]])
    for angle, expected_word in cases:
        word = encode_angle(angle, 12, rounding="nearest_even")
        if word != expected_word:
            raise ValueError(f"rounding/wrap mismatch for {angle}")
        ours = reconstruct([word, 0], 12, edges, 3, 0, radians_per_unit=math.pi)
        actual = maths.reconstruct_u_vectors(np.array([[word / 2048, 0]]), edges)[0]
        if not np.allclose(ours, actual, rtol=0, atol=2e-15):
            raise ValueError("quantized boundary reconstruction disagrees")
        records.append({"angle_over_pi": str(angle), "word": word, "vector": actual.tolist()})
    path = root / "runs/step3-chemistry/recovered-words.npz"
    if sha256(path) != read_json(root / "docs/evidence/step3-chemistry-words.json")["words_sha256"]:
        raise ValueError("word archive changed")
    with np.load(path) as archive:
        words, tree = archive["words"].copy(), archive["edges"]
    before = int(words[0, 0])
    words[0, 0] = (before + 1) % 4096
    inputs = official.load_inputs(root / "vendor/official/sample_submission/dfthcsos/submission.npz")
    metrics = maths.evaluate_dfthc_angle_words(
        words,
        inputs.w,
        inputs.W,
        inputs.S,
        inputs.beta_1,
        inputs.ref,
        brot=12,
        tree_edges=tree,
        energy_upper=inputs.energy_upper,
    )
    if not all(math.isfinite(float(value)) for value in metrics.values()):
        raise ValueError("nonfinite perturbed metric")
    print(
        json.dumps(
            {
                "encoding_policy": "nearest-even modulo 4096, angle units pi/2048",
                "boundary_controls": records,
                "reference_words_sha256": sha256(path),
                "perturbation": {
                    "row": 0,
                    "column": 0,
                    "before": before,
                    "after": int(words[0, 0]),
                    "metrics": metrics,
                    "passes_accuracy": official.passes_accuracy(metrics),
                },
            }
        )
    )


if __name__ == "__main__":
    main()
