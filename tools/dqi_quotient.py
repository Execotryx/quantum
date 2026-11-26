"""Emit a bounded native monic-quotient multiplication fixture."""

import argparse
import sys
from functools import partial
from importlib import import_module
from pathlib import Path

from qcompile.dqi.quotient import FieldProduct, quotient_multiply_xor, quotient_prepare
from qcompile.dqi.tower import _product_xor, multiply_xor
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def load_field_product(tensor42: Path | None) -> tuple[FieldProduct, str | None]:
    if tensor42 is None:
        return multiply_xor, None
    source = Path(__file__).resolve().parents[1] / "third_party/dqi-scheme42/SOURCE.json"
    tensor_sha256 = sha256(tensor42)
    if tensor_sha256 != read_json(source)["published_outputs"][0]["sha256"]:
        raise ValueError("Field tensor differs from the admitted rank-42 output")
    terms = []
    for row in tensor42.read_text(encoding="ascii").split():
        a, b, word = (int(part, 16) for part in row.split(","))
        terms.append((a, b, word))
    return partial(_product_xor, terms=tuple(terms)), tensor_sha256


def build(backend_path: Path, output: Path, *, degree: int, tensor42: Path | None = None,
          clean_target: bool = False, adjoint: bool = False) -> None:
    if not 1 <= degree <= 35:
        raise ValueError("degree must be in 1..35")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    groups = [[builder.create_quantum_register(12, f"{name}_{i}") for i in range(degree)]
              for name in ("left", "right", "modulus", "target")]
    multiply, tensor_sha256 = load_field_product(tensor42)
    if clean_target:
        quotient_prepare(builder, groups[0], groups[1], groups[2], groups[3], multiply=multiply, adjoint=adjoint)
    else:
        quotient_multiply_xor(builder, groups[0], groups[1], groups[2], groups[3], multiply=multiply)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "quotient.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "primitive_fixture", "scope": "monic quotient product", "tensor_sha256": tensor_sha256,
        "clean_target": clean_target, "adjoint": adjoint,
        "degree": degree, "kmb_sha256": sha256(path), "qubits": circuit.num_qubits,
        "bits": circuit.num_bits, "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--degree", type=int, required=True)
    parser.add_argument("--tensor42", type=Path)
    parser.add_argument("--clean-target", action="store_true")
    parser.add_argument("--adjoint", action="store_true")
    args = parser.parse_args()
    if args.adjoint and not args.clean_target:
        parser.error("--adjoint requires --clean-target")
    build(args.backend, args.output, degree=args.degree, tensor42=args.tensor42,
          clean_target=args.clean_target, adjoint=args.adjoint)
