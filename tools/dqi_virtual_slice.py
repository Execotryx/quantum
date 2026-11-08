"""Emit the reduced virtual-template lookup as a development fixture."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.bm_virtual_circuit import shifted_template_xor
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    base = [builder.create_quantum_register(12, f"base_{i}") for i in range(3)]
    target = [builder.create_quantum_register(12, f"output_{i}") for i in range(3)]
    age = builder.create_quantum_register(3, "age")
    enabled = builder.create_quantum_register(1, "enabled")[0]
    shifted_template_xor(builder, base, age, enabled, target)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "virtual-shift.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "three-word virtual shift lookup; not a BM round",
        "kmb_sha256": sha256(path), "qubits": circuit.num_qubits, "bits": circuit.num_bits,
        "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.backend, args.output)
