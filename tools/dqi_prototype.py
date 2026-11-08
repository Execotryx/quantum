"""Emit isolated reversible DQI primitive and runtime-mask phase slices."""

import argparse
import sys
from importlib import import_module
from pathlib import Path

from qcompile.dqi import subtower, tower
from qcompile.dqi.bm_circuit import routed_update
from qcompile.dqi.field import GF4096
from qcompile.dqi.reversible import (
    bm_locator_slice,
    eea_locator_slice,
    inverse_xor,
    multiply_xor,
    phase_for_position,
)
from qcompile.dqi.scan import phase_scan
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def build_scan(backend_path: Path, output: Path, *, m: int, n: int) -> None:
    """Emit a standalone scan with precomputed polynomial coefficient inputs."""
    if not 2 <= n <= min(m, 70) or n % 2 or m > 4095:
        raise ValueError("require even syndrome count in [2, 70] and n <= m <= 4095")
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    t = n // 2
    locator = [builder.create_quantum_register(12, f"sigma_{i}") for i in range(t + 1)]
    omega = [builder.create_quantum_register(12, f"omega_{i}") for i in range(t)]
    reciprocal = [builder.create_quantum_register(12, f"psi_{i}") for i in range(t)]
    masks = [builder.create_classical_register(12, f"mask_{i}") for i in range(m)]
    phase_scan(builder, km.GF2Field(12), locator, omega, reciprocal, masks)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / "phase-scan.kmb"
    circuit.to_file(str(path), format="kmb")
    write_json(output / "slice.json", {
        "kind": "phase-scan", "m": m, "n": n, "sha256": sha256(path), "backend": backend,
        "qubits": circuit.num_qubits, "bits": circuit.num_bits,
        "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "operations": dict(circuit.operation_statistics()), "role": "primitive_fixture",
    })


def build(kind: str, backend_path: Path, output: Path, *, adjoint: bool = False) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    sys.path.insert(0, backend["kickmix_root"])
    km = import_module("kickmix")
    field = km.GF2Field(12)
    if field.mul(2048, 2) != (GF4096.modulus ^ 4096):
        raise ValueError("native field polynomial differs from the pinned DQI field")
    builder = km.CircuitBuilder()
    source = builder.create_quantum_register(12, "source")
    if kind in ("multiply", "tower-multiply"):
        right = builder.create_quantum_register(12, "right")
        target = builder.create_quantum_register(12, "target")
        if kind == "tower-multiply":
            tower.multiply_xor(builder, source, right, target)
        else:
            multiply_xor(builder, field, source, right, target)
    elif kind in ("inverse", "native-inverse", "tower-inverse", "subtower-inverse"):
        target = builder.create_quantum_register(12, "target")
        if kind == "subtower-inverse":
            subtower.inverse_xor(builder, source, target)
        elif kind == "tower-inverse":
            tower.inverse_xor(builder, source, target)
        elif kind == "native-inverse":
            scratch = builder.alloc_qubits(12)
            _, scaffold = builder.init_gf2_inverse_with_scaffold(source, target=scratch, field=field)
            for src, dst in zip(scratch, target, strict=True):
                builder.cx(src, dst)
            builder.del_gf2_inverse_with_scaffold(source, target=scratch, scaffold=scaffold, field=field)
            builder.free(scaffold)
            builder.free(scratch)
        else:
            inverse_xor(builder, field, source, target)
    elif kind == "phase":
        denominator = builder.create_quantum_register(12, "denominator")
        located = builder.create_quantum_register(1, "located")
        mask = builder.create_classical_register(12, "mask")
        phase_for_position(builder, field, located[0], source, denominator, mask)
    elif kind == "routed-bm":
        current = [builder.create_quantum_register(12, f"current_{i}") for i in range(3)]
        previous = [builder.create_quantum_register(12, f"previous_{i}") for i in range(3)]
        branch = builder.create_quantum_register(1, "branch")[0]
        routed_update(builder, current, previous, source, branch, adjoint=adjoint)
    else:
        current = [builder.create_quantum_register(12, f"current_{i}") for i in range(4)]
        previous = [builder.create_quantum_register(12, f"previous_{i}") for i in range(4)]
        branch = builder.create_quantum_register(1, "branch")[0]
        if kind == "eea":
            eea_locator_slice(builder, field, current, previous, source, 1, branch, adjoint=adjoint)
        else:
            saved = [builder.create_quantum_register(12, f"saved_{i}") for i in range(4)]
            bm_locator_slice(builder, field, current, previous, saved, source, 1, branch, adjoint=adjoint)
    circuit = builder.finish_circuit()
    output.mkdir(parents=True, exist_ok=False)
    path = output / f"{kind}.kmb"
    with path.open("xb") as stream:
        circuit.to_file(stream, format="kmb")
    write_json(output / "slice.json", {
        "kind": kind, "sha256": sha256(path), "backend": backend, "qubits": circuit.num_qubits,
        "bits": circuit.num_bits, "toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "role": "primitive_fixture", "adjoint": adjoint,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=(
        "multiply", "tower-multiply", "inverse", "native-inverse", "tower-inverse", "subtower-inverse",
        "phase", "eea", "bm", "routed-bm",
        "phase-scan",
    ))
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--adjoint", action="store_true")
    parser.add_argument("--m", type=int, default=63)
    parser.add_argument("--n", type=int, default=4)
    args = parser.parse_args()
    if args.kind == "phase-scan":
        if args.adjoint:
            parser.error("phase-scan is self-inverse and does not accept --adjoint")
        build_scan(args.backend, args.output, m=args.m, n=args.n)
    else:
        build(args.kind, args.backend, args.output, adjoint=args.adjoint)
