"""Known-invalid angle tables through the pinned official numerical entry point."""

import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.io import read_json
from qcompile.official import validate_backend


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    maths = import_module("dfthcsos.scoreinfra.dfthc_math")
    words = np.zeros((4, 2), dtype=np.int64)
    tree = np.array([[0, 1], [1, 2]])
    records = []
    for name, table, edges, detector in [
        ("floating_words", words.astype(float), tree, "integers"),
        ("word_out_of_range", words + 4096, tree, "[0, 2**brot)"),
        ("missing_angle", words[:, :1], tree, "shape"),
        ("child_before_parent", words, tree[::-1], "parent-before-child"),
        ("cycle", words, np.array([[0, 1], [1, 0]]), "parent-before-child"),
        ("illegal_vertex", words, np.array([[0, 1], [1, 3]]), "[0, N)"),
    ]:
        try:
            maths.evaluate_dfthc_angle_words(
                table,
                np.ones((1, 1, 1)),
                np.zeros((1, 1)),
                np.zeros((3, 3)),
                0,
                {"oei": np.eye(3), "tei": np.zeros((3, 3, 3, 3)), "electrons": 2, "ecore": 0},
                brot=12,
                tree_edges=edges,
                energy_upper=1,
            )
        except ValueError as error:
            if detector not in str(error):
                raise
            records.append({"fixture": name, "expected": detector, "observed": str(error)})
        else:
            raise ValueError(f"known-invalid fixture accepted: {name}")
    print(json.dumps({"entry_point": "evaluate_dfthc_angle_words", "controls": records}))


if __name__ == "__main__":
    main()
