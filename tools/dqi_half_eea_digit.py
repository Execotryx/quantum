"""Emit a reduced coherent quotient-digit EEA step and exact inverse."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.half_eea_digit import quotient_eea_digit
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, adjoint: bool = False) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    left = [[builder.create_quantum_register(12, f"left_{row}_{i}") for i in range(3)] for row in range(3)]
    right = [[builder.create_quantum_register(12, f"right_{row}_{i}") for i in range(3)] for row in range(3)]
    quotient = builder.create_quantum_register(12, "quotient")
    zero = builder.create_quantum_register(1, "zero")[0]
    quotient_eea_digit(builder, left, right, 2, 1, quotient, zero, adjoint=adjoint)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "eea-digit.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "selected quotient digit with retained history and zero flag",
        "numerator_degree": 2, "shift": 1, "adjoint": adjoint, "kmb_sha256": sha256(path),
        "qubits": circuit.num_qubits, "bits": circuit.num_bits,
        "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--adjoint", action="store_true")
    args = parser.parse_args()
    build(args.backend, args.output, adjoint=args.adjoint)
