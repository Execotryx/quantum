"""Emit a bounded native monic-quotient multiplication fixture."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.quotient import quotient_multiply_xor
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, degree: int) -> None:
    if not 1 <= degree <= 35:
        raise ValueError("degree must be in 1..35")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    groups = [[builder.create_quantum_register(12, f"{name}_{i}") for i in range(degree)]
              for name in ("left", "right", "modulus", "target")]
    quotient_multiply_xor(builder, groups[0], groups[1], groups[2], groups[3])
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "quotient.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "monic quotient product; not a reciprocal",
        "degree": degree, "kmb_sha256": sha256(path), "qubits": circuit.num_qubits,
        "bits": circuit.num_bits, "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--degree", type=int, required=True)
    args = parser.parse_args()
    build(args.backend, args.output, degree=args.degree)
