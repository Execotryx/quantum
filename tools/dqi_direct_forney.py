"""Emit a supplied-locator evaluator and direct-derivative Forney scan."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi.direct_forney import evaluator_and_scan
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build(backend_path: Path, output: Path, *, m: int, n: int) -> None:
    if not 2 <= n <= min(m, 70) or n % 2 or m > 4095:
        raise ValueError("require even syndrome count in [2,70] and n <= m <= 4095")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    field = km.GF2Field(12)
    if field.mul(2048, 2) != 0x53:
        raise ValueError("native field polynomial differs from the pinned DQI field")
    builder = km.CircuitBuilder()
    locator = [builder.create_quantum_register(12, f"sigma_{i}") for i in range(n // 2 + 1)]
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(n)]
    masks = [builder.create_classical_register(12, f"E{j}") for j in range(m)]
    evaluator_and_scan(builder, field, locator, syndromes, masks)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "direct-forney.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "role": "development_fixture", "scope": "supplied locator; not a standalone decoder",
        "m": m, "n": n, "kmb_sha256": sha256(path), "qubits": circuit.num_qubits,
        "bits": circuit.num_bits, "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "backend": backend,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--n", type=int, required=True)
    args = parser.parse_args()
    build(args.backend, args.output, m=args.m, n=args.n)
