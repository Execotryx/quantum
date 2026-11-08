"""Emit an exact radius-one DQI development decoder."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.degree1 import emit
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, m: int) -> None:
    if not 2 <= m <= 4095:
        raise ValueError("m must be in 2..4095")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    field = km.GF2Field(12)
    if field.mul(2048, 2) != 0x53:
        raise ValueError("native field polynomial differs from the pinned DQI field")
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(2)]
    masks = [builder.create_classical_register(12, f"E{j}") for j in range(m)]
    emit(builder, field, syndromes, masks)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "degree1.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "reduced_shape_development", "m": m, "n": 2, "degree": 12,
        "kmb_sha256": sha256(path), "qubits": circuit.num_qubits, "bits": circuit.num_bits,
        "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--m", type=int, default=63)
    args = parser.parse_args()
    build(args.backend, args.output, m=args.m)
