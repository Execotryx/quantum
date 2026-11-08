"""Exhaustively measure native GF(4096) constant-map declared width."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def run(backend_path: Path, output: Path) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    field = km.GF2Field(12)
    results = {}
    for operation in ("gf2_imul", "gf2_idiv"):
        maximum = 0
        witnesses = []
        for value in range(1, 4096):
            builder = km.CircuitBuilder()
            word = builder.create_quantum_register(12, "word")
            getattr(builder, operation)(value, target=word, field=field)
            width = builder.finish_circuit().num_qubits
            if width > maximum:
                maximum, witnesses = width, [value]
            elif width == maximum and len(witnesses) < 8:
                witnesses.append(value)
        results[operation] = {"max_declared_qubits": maximum, "first_max_witnesses": witnesses,
                              "constants_checked": 4095}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "width.json", {
        "role": "development_structural_bound", "baseline_word_qubits": 12,
        "operation_widths": results, "kickmix_sha256": backend["kickmix_files"]["kickmix.so"],
        "tool_sha256": sha256(Path(__file__)),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.backend, args.output)
