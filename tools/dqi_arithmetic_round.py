"""Emit a three-word BM arithmetic round with explicit retain history."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.bm_arithmetic_round import arithmetic_round
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, adjoint: bool = False) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    sigma = [builder.create_quantum_register(12, f"sigma_{i}") for i in range(3)]
    shifted = [builder.create_quantum_register(12, f"shifted_{i}") for i in range(3)]
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(3)]
    history = builder.create_quantum_register(12, "history")
    replace = builder.create_quantum_register(1, "replace")[0]
    arithmetic_round(builder, sigma, shifted, syndromes, 2, replace, history, adjoint=adjoint)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "arithmetic-round.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "three-word arithmetic round; branch and shifted template supplied",
        "adjoint": adjoint, "kmb_sha256": sha256(path), "qubits": circuit.num_qubits,
        "bits": circuit.num_bits, "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--adjoint", action="store_true")
    args = parser.parse_args()
    build(args.backend, args.output, adjoint=args.adjoint)
