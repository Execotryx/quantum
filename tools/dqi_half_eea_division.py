"""Emit fixed-degree half-degree EEA division and its inverse."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.half_eea_division import quotient_division
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, denominator_degree: int = 1, adjoint: bool = False) -> None:
    if not 0 <= denominator_degree <= 2:
        raise ValueError("denominator degree must be 0, 1 or 2")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    left = [[builder.create_quantum_register(12, f"left_{row}_{i}") for i in range(3)] for row in range(3)]
    right = [[builder.create_quantum_register(12, f"right_{row}_{i}") for i in range(3)] for row in range(3)]
    quotients = [builder.create_quantum_register(12, f"quotient_{i}") for i in range(3 - denominator_degree)]
    zero = builder.create_quantum_register(1, "zero")[0]
    quotient_division(builder, left, right, 2, denominator_degree, quotients, zero, adjoint=adjoint)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "eea-division.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "fixed-degree EEA division with retained history",
        "numerator_degree": 2, "denominator_degree": denominator_degree, "adjoint": adjoint,
        "kmb_sha256": sha256(path), "qubits": circuit.num_qubits, "bits": circuit.num_bits,
        "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--denominator-degree", type=int, default=1)
    parser.add_argument("--adjoint", action="store_true")
    args = parser.parse_args()
    build(args.backend, args.output, denominator_degree=args.denominator_degree, adjoint=args.adjoint)
