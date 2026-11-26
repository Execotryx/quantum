"""Measure two reciprocal phase lookup schedules within the checkpoint width."""

import argparse
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

import numpy as np

from invsqrt_opportunity import backend
from qcompile.io import read_json, sha256, write_json


LIVE_WIRES = 31
ADDRESS_BITS = 7
SLICE_BITS = 2
SEED = 61309


def walk(builder: Any, address: Any, path: Any, apply: Callable[[int, Any], None]) -> None:
    """Visit all addresses with sibling CX updates and clean the temporary ANDs."""
    def visit(depth: int, prefix: int, control: Any) -> None:
        if depth == len(address):
            apply(prefix, control)
            return
        bit = address[-1 - depth]
        if not depth:
            builder.x(bit)
            visit(1, 0, bit)
            builder.x(bit)
            visit(1, 1, bit)
            return
        flag = path[depth - 1]
        builder.x(bit)
        builder.init_and(control, bit, flag)
        builder.x(bit)
        visit(depth + 1, 2 * prefix, flag)
        builder.cx(control, flag)
        visit(depth + 1, 2 * prefix + 1, flag)
        builder.del_and(control, bit, flag)

    visit(0, 0, None)


def build(km: Any, rows: list[int], fraction: int, sliced: bool) -> Any:
    builder = km.CircuitBuilder()
    live = builder.create_quantum_register(LIVE_WIRES, "checkpoint")
    address = live[:ADDRESS_BITS]
    path = builder.alloc_qubits(ADDRESS_BITS - 1)
    # Fix the normalization exponent at zero as an optimistic component
    # probe. KMX rotation exponents are half-turns.
    denominator = 1 << (fraction + 9)
    if sliced:
        for shift in range(0, fraction, SLICE_BITS):
            width = min(SLICE_BITS, fraction - shift)
            word = builder.alloc_qubits(width)
            mask = (1 << width) - 1

            def load(index: int, control: Any) -> None:
                builder.gf2_iadd((rows[index] >> shift) & mask, target=word, control=control)

            walk(builder, address, path, load)
            for bit in range(width):
                builder.z_pow(word[bit], Fraction(1 << (shift + bit), denominator))
            walk(builder, address, path, load)
            builder.free(word)
    else:
        walk(builder, address, path, lambda index, control: builder.z_pow(control, Fraction(rows[index], denominator)))
    builder.free(path)
    return builder.finish_circuit()


def run(coefficients: Path, precision: int, output: Path) -> None:
    expected = [((512 << precision) + d // 2) // d for d in range(514, 1023, 4)]
    rows = read_json(coefficients)["reciprocal_rows"]
    if rows != expected:
        raise ValueError("The reciprocal table or precision differs from the integer law")
    km, _, official = backend()
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"coefficient_sha256": sha256(coefficients), "driver_sha256": sha256(Path(__file__)),
        "precision": precision, "live_checkpoint_wires": LIVE_WIRES, "address_bits": ADDRESS_BITS,
        "slice_width": SLICE_BITS, "normalization_exponent": 0, "seed": SEED})
    addresses = np.repeat(np.arange(len(rows), dtype=np.uint64), 8)
    large = np.random.default_rng(SEED).integers(0, 1 << (LIVE_WIRES - ADDRESS_BITS), len(addresses), dtype=np.uint64)
    words = (large << ADDRESS_BITS) | addresses
    target = np.asarray(rows, dtype=np.uint64)[addresses] << (64 - precision - 10)
    results = {}
    for name in ("direct", "sliced"):
        path = output / f"{name}.kmb"
        build(km, rows, precision, name == "sliced").to_file(path, format="kmb")
        circuit = km.Circuit.from_file(path, format="kmb")
        live = km.array([km.q(i) for i in range(LIVE_WIRES)])
        scratch = km.array([km.q(i) for i in range(LIVE_WIRES, circuit.num_qubits)])
        sim = km.Simulator(batch_size=len(words), seed=SEED, counting_operations=True)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(live, official.to_bits(words, LIVE_WIRES))
        sim.do(circuit)
        np.testing.assert_array_equal(official.from_bits(sim.read_across_shots(live)), words)
        np.testing.assert_array_equal([official.half_turns_to_units(sim.read_shot_phase(i))
                                       for i in range(len(words))], target)
        if sim.read_across_shots(scratch).any():
            raise ValueError("The reciprocal lookup left dirty scratch")
        counts = sim.operation_statistics()
        results[name] = {"qubits": circuit.num_qubits, "kmb_sha256": sha256(path), "fixtures": len(words),
                         "executed_mean_toffoli_like": counts.num_toffoli_like / len(words),
                         "executed_mean_fine_rotations": counts.num_z_pow(min_clifford_hierarchy_level=4) / len(words)}
    write_json(output / "native.json", {"registration_sha256": sha256(registration), "lanes": results,
        "scope": "serialized reciprocal phase only; inverse-square-root numerator and exponent routing excluded"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coefficients", type=Path)
    parser.add_argument("precision", type=int)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
