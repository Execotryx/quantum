"""Record synthetic banked-loader costs; this does not emit a candidate."""

import argparse
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from banked_chemistry import backend

from qcompile.chemistry.loaders import family, max_batch, rank_complete_cost
from qcompile.io import sha256, write_json


def screen(output: Path) -> None:
    settings, km, api, _, verifier = backend()
    rng = np.random.default_rng(351)
    words = rng.integers(0, 16, size=(82, 75), dtype=np.int64)
    inputs = SimpleNamespace(num_orbitals=76, w=np.empty((2, 3, 2)))
    candidates = []
    for batch in range(3, min(75, max_batch(82, 4, 3)) + 1):
        circuits = family(km, api, words, 4, batch, 3)
        recovered, _, toffoli = api.recover_words_from_circuits(
            circuits, num_vectors=82, num_angles=75, shots_per_address=2, seed=74
        )
        if not np.array_equal(recovered, words):
            raise ValueError("native verifier recovered a different synthetic table")
        candidates.append((batch, circuits, toffoli))
    ranked = rank_complete_cost(verifier, inputs, candidates, 4, 48.0)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "synthetic-ranking.json", {
        "scope": "synthetic only; not an eligible factorization or measured chemistry acceptance",
        "shape": [2, 3, 2], "rows": 82, "brot": 4, "low_bits": 3,
        "lambda_eff_assumed": 48.0, "table_seed": 351, "verification_seed": 74,
        "shots_per_address": 2, "ranked": ranked, "backend": settings,
        "runner_sha256": sha256(Path(__file__)),
        "loader_sha256": sha256(Path(__file__).resolve().parents[1] / "src/qcompile/chemistry/loaders.py"),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    screen(parser.parse_args().output)
