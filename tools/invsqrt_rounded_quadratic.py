"""Measure fused rounded products with the frozen 192-interval coefficients."""

import argparse
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from invsqrt_coarse_curvature import MAX_X, NORMALIZED_BITS, PRECISION, fit
from invsqrt_opportunity import ROOT, backend
from qcompile.invsqrt.direct import Words
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.invsqrt.rounded_product import rounded_product, row_sum
from qcompile.io import identity, read_json, sha256, write_json


ADDRESS = 6
LOCAL = 14
TAIL = 12
EXACT = (TAIL, LOCAL)
GUARD = (1, 2, 3, 4, 6)
SEED = 37109


def values(normalized: Words, affine: Words, curvature: Words, guards: tuple[int, int]
           ) -> tuple[Words, Words, Words]:
    inner, outer = guards
    address = (normalized >> LOCAL) - (1 << ADDRESS)
    local = (normalized & ((1 << LOCAL) - 1)) - (1 << (LOCAL - 1))
    c0, c1 = affine[address].T
    c2 = curvature[address]
    slope = (-c1 << inner) + (1 << (inner - 1)) - 1
    slope -= row_sum(c2, local >> (LOCAL - TAIL), TAIL, inner)
    result = (c0 << outer) + (1 << (outer - 1))
    result -= row_sum(slope >> inner, local, LOCAL, outer)
    correction = (result >> outer) - c0
    if np.any((slope < 0) | (slope >= 1 << (22 + inner)) | (result < 0) | (result >= 1 << (30 + outer))):
        raise ValueError("The fused product exceeds its registered accumulator width")
    if np.any((correction < -(1 << 21)) | (correction >= 1 << 21)):
        raise ValueError("The outer product exceeds the signed correction word")
    return c2, slope, result


def phase_model(xs: Words, affine: Words, curvature: Words, guards: tuple[int, int]) -> NDArray[np.uint64]:
    exponent = np.searchsorted([4**k for k in range(11)], xs, side="right") - 1
    normalized = xs << (NORMALIZED_BITS - 2 * exponent)
    _, _, result = values(normalized, affine, curvature, guards)
    return (result >> guards[1]).astype(np.uint64) << (64 - PRECISION - exponent).astype(np.uint64)


def native(km: Any, affine: Words, curvature: Words, guards: tuple[int, int],
           output: Path, *, measured_rows: bool, roundtrip: bool,
           correction: bool = False, borrowed_carry: bool = False, dirty_upper: bool = False) -> dict:
    inner, outer = guards
    builder = km.CircuitBuilder()
    x = builder.create_quantum_register(22, "x")
    c2 = builder.create_quantum_register(16, "c2")
    slope = builder.create_quantum_register(22 + inner, "slope")
    result = builder.create_quantum_register((22 if correction else 30) + outer, "result")
    work = builder.alloc_qubits(22) if measured_rows else None
    carry = builder.alloc_qubits(2) if borrowed_carry else None
    options = {"negate": True, "scratch": work, "carry": carry, "dirty": x if dirty_upper else None}
    builder.x(x[LOCAL - 1])
    rounded_product(builder, c2, x[LOCAL - TAIL:LOCAL], slope, inner,
                    round_before_negation=True, **options)
    rounded_product(builder, slope[inner:], x[:LOCAL], result, outer, **options)
    if roundtrip:
        rounded_product(builder, slope[inner:], x[:LOCAL], result, outer, adjoint=True, **options)
        rounded_product(builder, c2, x[LOCAL - TAIL:LOCAL], slope, inner,
                        round_before_negation=True, adjoint=True, **options)
    builder.x(x[LOCAL - 1])
    if work is not None:
        builder.free(work)
    if carry is not None:
        builder.free(carry)
    circuit = builder.finish_circuit()
    circuit.to_file(output, format="kmb")
    circuit = km.Circuit.from_file(output, format="kmb")
    addresses = np.repeat(np.arange(64, 256, dtype=np.int64), 8)
    offsets = np.random.default_rng(SEED).integers(0, 1 << LOCAL, size=(len(addresses) // 8, 8))
    offsets[:, :6] = (0, 1, (1 << (LOCAL - 1)) - 1, 1 << (LOCAL - 1), (1 << LOCAL) - 2, (1 << LOCAL) - 1)
    normalized = (addresses << LOCAL) + offsets.ravel()
    base, gradient = affine[addresses - 64].T
    supplied = (normalized, curvature[addresses - 64], -gradient << inner, base << outer)
    _, expected_slope, expected_result = values(normalized, affine, curvature, guards)
    if correction:
        expected_result -= supplied[-1]
        supplied = (*supplied[:3], np.zeros_like(base))
    expected = supplied if roundtrip else (*supplied[:2], expected_slope, expected_result)
    masks = []
    sim = km.Simulator(batch_size=len(normalized), seed=SEED + 1, counting_operations=True)
    sim.use_same_registers_as(circuit)
    registers = (x, c2, slope, result)
    for register, data in zip(registers, supplied, strict=True):
        bits = np.arange(len(register))[:, None]
        masks.append(bits)
        sim.write_across_shots(register, ((data >> bits) & 1).astype(bool))
    sim.do(circuit)
    for register, data, bits in zip(registers, expected, masks, strict=True):
        np.testing.assert_array_equal(sim.read_across_shots(register), (data >> bits) & 1)
    live = {wire.id for register in registers for wire in register}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not sim.read_across_shots(scratch).any() and not sim.read_phase_flipped_across_shots().any()
    toffoli = int(circuit.operation_statistics().num_toffoli_like)
    return {
        "qubits": circuit.num_qubits, "toffoli_like": toffoli, "kmb_sha256": sha256(output),
        "executed_mean": sim.operation_statistics().num_toffoli_like / len(normalized),
        "fixtures": len(normalized), "measured_rows": measured_rows, "roundtrip": roundtrip,
        "guards": guards, "separate_correction": correction, "borrowed_carry": borrowed_carry,
        "dirty_upper": dirty_upper,
    }


def run(output: Path) -> None:
    km, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    anchor = ROOT / "docs/evidence/aggregate36-20261126/invsqrt-coarse-curvature-model.json"
    lane = next(row for row in read_json(anchor)["lanes"] if
                (row["address_bits"], row["curvature_bits"], row["tail_bits"]) == (ADDRESS, ADDRESS, TAIL))
    affine, curvature = fit(ADDRESS, ADDRESS, TAIL)
    if identity(affine.tolist()) != lane["affine_table_sha256"] or identity(curvature.tolist()) != lane["curvature_table_sha256"]:
        raise ValueError("The coefficient tables differ from the frozen model")
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {
        "scope": "native rounded products with supplied normalized input and coefficients",
        "model_sha256": sha256(anchor), "backend_sha256": sha256(ROOT / "vendor/backend.json"),
        "driver_sha256": sha256(Path(__file__)), "seed": SEED,
        "product_sha256": sha256(ROOT / "src/qcompile/invsqrt/rounded_product.py"),
        "guard_pairs": (EXACT, *((guard, guard) for guard in GUARD)),
        "layouts": ["base_accumulator", "separate_correction"],
        "row_adders": ["native_controlled", "measured_products", "borrowed_carry", "dirty_upper"],
    })
    margins = []
    pairs = (EXACT, *((guard, guard) for guard in GUARD))
    for pair in pairs:
        model = partial(phase_model, affine=affine, curvature=curvature, guards=pair)
        result = scan_phase(model, MAX_X, partial(official.reference_values, spec))
        if pair == EXACT and result != lane["margins"]:
            raise ValueError("The exact guard model failed to reproduce the frozen phase screen")
        margins.append({"guards": pair, "margins": result})
    selected = next((row["guards"] for row in margins[1:] if not row["margins"]["above_90_percent"]), EXACT)
    write_json(output / "screen.json", {
        "registration_sha256": sha256(registration), "margins": margins, "selected_guards": selected,
    })
    runs = {}
    for label, guards in (("exact", EXACT), ("selected", selected)):
        for measured_rows in (False, True):
            for roundtrip in (False, True):
                name = f"{label}-{'products' if measured_rows else 'controlled'}-{'roundtrip' if roundtrip else 'forward'}"
                runs[name] = native(km, affine, curvature, guards, output / f"{name}.kmb",
                                    measured_rows=measured_rows, roundtrip=roundtrip)
    for scope in ("correction", "borrowed", "dirty"):
        for measured_rows in (False, True):
            for roundtrip in (False, True):
                method = "products" if measured_rows else "controlled"
                name = f"{scope}-{method}-{'roundtrip' if roundtrip else 'forward'}"
                runs[name] = native(km, affine, curvature, selected, output / f"{name}.kmb",
                                    measured_rows=measured_rows, roundtrip=roundtrip,
                                    correction=True, borrowed_carry=scope != "correction", dirty_upper=scope == "dirty")
    write_json(output / "native.json", {"screen_sha256": sha256(output / "screen.json"), "runs": runs})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
