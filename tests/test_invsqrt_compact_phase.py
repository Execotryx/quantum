"""Native controlled-phase slice and complete small-domain model checks."""

from fractions import Fraction
from importlib import import_module

import numpy as np
import pytest

from qcompile.invsqrt.compact_phase import phase_accumulation, phase_product
from qcompile.invsqrt.direct import DirectFormat, coefficient_table, phase64


def test_compact_recurrence_matches_original_on_small_domain():
    fmt = DirectFormat(3, 2, (13, 9, 5), True, True, True, True)
    table = coefficient_table(fmt)
    xs = np.arange(1, 148, dtype=np.int64)
    assert np.array_equal(phase_accumulation(fmt, table, xs), phase64(fmt, table, xs))


@pytest.mark.official
@pytest.mark.parametrize("product", [False, True])
def test_native_phase_slice_all_controls_and_sampled_branches(project_root, monkeypatch, product):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    km, _, official = tool.backend()
    builder = km.CircuitBuilder()
    controls = builder.create_quantum_register(3, "controls")
    scratch = builder.alloc_qubits(2)
    angle = Fraction(-1, 16)
    phase_product(builder, controls[0], controls[1], controls[2] if product else None, scratch, angle)
    builder.free(scratch)
    circuit = builder.finish_circuit()
    values = np.tile(np.arange(8, dtype=np.int64), 64)
    bits = np.arange(3)[:, None]
    sim = km.Simulator(batch_size=len(values), seed=227 + product)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(controls, (values[None, :] >> bits) & 1 == 1)
    sim.do(circuit)
    assert np.array_equal(sim.read_across_shots(controls), (values[None, :] >> bits) & 1 == 1)
    live = {q.id for q in controls}
    work = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not sim.read_across_shots(work).any()
    expected_phase = official.half_turns_to_units(angle)
    for i, value in enumerate(values):
        enabled = (value & (7 if product else 3)) == (7 if product else 3)
        assert official.half_turns_to_units(sim.read_shot_phase(i)) == (expected_phase if enabled else 0)
    stats = circuit.operation_statistics()
    assert stats.num_toffoli_like == (2 if product else 1)
    assert stats.num_z_pow(min_clifford_hierarchy_level=4) == 1
