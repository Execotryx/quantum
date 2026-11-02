"""Representation controls for the pinned full chemistry reference and small degeneracies."""

import json
import math
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.chemistry.representation import reconstruct
from qcompile.io import read_json, sha256
from qcompile.official import validate_backend


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    official = import_module("dfthcsos.verify")
    maths = import_module("dfthcsos.scoreinfra.dfthc_math")
    path = root / "runs/step3-chemistry/recovered-words.npz"
    if sha256(path) != read_json(root / "docs/evidence/step3-chemistry-words.json")["words_sha256"]:
        raise ValueError("recovered words changed")
    with np.load(path) as archive:
        vectors = np.array(
            [
                reconstruct(row, 12, archive["edges"], 76, 0, radians_per_unit=math.pi)
                for row in archive["words"]
            ]
        )
    inputs = official.load_inputs(root / "vendor/official/sample_submission/dfthcsos/submission.npz")
    baseline = read_json(root / "docs/evidence/step3-chemistry-metrics.json")["official"]
    transformed = -vectors.copy()
    transformed[:76] = transformed[:76][::-1]
    perturbed = vectors.copy()
    perturbed[0, 0] += 1e-12
    results = []
    for name, candidate, tolerance in [
        ("sign_and_one_body_permutation", transformed, 2e-9),
        ("single_component_perturbation_1e-12", perturbed, 2e-8),
    ]:
        metrics = maths.evaluate_dfthc_vectors(
            candidate,
            inputs.w,
            inputs.W,
            inputs.S,
            inputs.beta_1,
            inputs.ref,
            energy_upper=inputs.energy_upper,
        )
        differences = {key: abs(metrics[key] - baseline[key]) for key in baseline if key != "gap_in_domain"}
        if not metrics["gap_in_domain"] or any(value > tolerance for value in differences.values()):
            raise ValueError(f"representation instability for {name}: {differences}")
        results.append(
            {
                "transformation": name,
                "absolute_tolerance": tolerance,
                "metric_absolute_differences": differences,
            }
        )
    target = np.diag([1.0, 1.0 + 1e-12])
    near_degenerate = []
    for rows in (np.eye(2), -np.eye(2)[::-1]):
        rebuilt = maths.reconstruct_h1_thc(
            rows, target, np.zeros((2, 2)), 0.0, 2, np.zeros((1, 1)), np.zeros((1, 1, 2, 2))
        )
        error = float(np.max(np.abs(rebuilt - target)))
        if error > 5e-15:
            raise ValueError("nearly degenerate sign/permutation fixture failed")
        near_degenerate.append(error)
    zero_tree = np.array([[0, 1], [1, 2]])
    independent = reconstruct([0, 0], 12, zero_tree, 3, 0, radians_per_unit=math.pi)
    expected = maths.reconstruct_u_vectors(np.zeros((1, 2)), zero_tree)[0]
    if not np.array_equal(independent, expected):
        raise ValueError("zero-component vector fixture disagrees")
    print(
        json.dumps(
            {
                "words_sha256": sha256(path),
                "full_reference_controls": results,
                "near_degenerate_eigenvalue_separation": 1e-12,
                "near_degenerate_reconstruction_errors": near_degenerate,
                "zero_component_vector": independent.tolist(),
            }
        )
    )


if __name__ == "__main__":
    main()
