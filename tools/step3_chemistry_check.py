"""Reconstruct every reference angle word and compare independent vector rotations."""

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
    circuits_module = import_module("dfthcsos.scoreinfra.circuits")
    mathematics = import_module("dfthcsos.scoreinfra.dfthc_math")
    directory = root / "vendor/official/sample_submission/dfthcsos"
    with np.load(directory / "submission.npz", allow_pickle=False) as arrays:
        rank, bases, orbitals = arrays["U"].shape
        edges = arrays["tree_edges"].copy()
    circuits = circuits_module.load_circuits(directory)
    words, layout, toffoli = circuits_module.recover_words_from_circuits(
        circuits,
        num_vectors=orbitals + rank * bases,
        num_angles=orbitals - 1,
        shots_per_address=64,
        seed=3103,
    )
    expected = mathematics.reconstruct_u_vectors(words / 2 ** (layout.brot - 1), edges)
    observed = np.array(
        [reconstruct(row, layout.brot, edges, orbitals, 0, radians_per_unit=math.pi) for row in words]
    )
    discrepancy = float(np.max(np.abs(observed - expected)))
    if discrepancy > 2e-14:
        raise ValueError(f"independent vector reconstruction disagrees by {discrepancy}")
    if not np.allclose(np.linalg.norm(observed, axis=1), 1, rtol=0, atol=2e-14):
        raise ValueError("reconstructed vector norm differs from one")
    output = root / "runs/step3-chemistry"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "recovered-words.npz"
    if path.exists():
        raise FileExistsError("retain prior recovered word evidence before rerunning")
    np.savez(path, words=words, edges=edges)
    print(
        json.dumps(
            {
                "vectors": len(words),
                "angles_per_vector": orbitals - 1,
                "shots_per_address": 64,
                "seed": 3103,
                "brot": layout.brot,
                "forward_reverse_mean_toffoli": toffoli,
                "max_vector_discrepancy": discrepancy,
                "words_sha256": sha256(path),
                "factorization_sha256": sha256(directory / "submission.npz"),
            }
        )
    )


if __name__ == "__main__":
    main()
