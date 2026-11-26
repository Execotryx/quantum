"""Native all-input and measurement-trajectory checks for the gated row."""

from functools import partial
from importlib import import_module
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.mark.official
def test_gated_row_native_all_small_inputs(monkeypatch, project_root):
    pytest.importorskip("resource")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    from qcompile.invsqrt.direct import DirectFormat, build_circuit, coefficient_table, phase64
    from qcompile.invsqrt.gated_row import add_row

    km, primitives, official = tool.backend()
    fmt = DirectFormat(3, 2, (13, 9, 5), fused=True, reuse_lookup=True)
    table = coefficient_table(fmt)
    api = SimpleNamespace(**{name: getattr(primitives, name) for name in
                             ("_normalize", "_denormalize", "_phase_by_bits")}, _add_row=add_row)
    circuit = build_circuit(km, api, fmt, table)
    spec = official.ProblemSpecInvSqrt.for_n_p(3)
    tool.native_smoke(km, official, circuit, spec, partial(phase64, fmt, table),
                      list(range(1, spec.max_x + 1)),
                      {"batch": 64, "repeat": 16, "seed": 131})


@pytest.mark.official
@pytest.mark.parametrize(("source_width", "target_width", "dirty_width"),
                         [(1, 1, 0), (1, 4, 0), (1, 4, 3), (3, 3, 0), (3, 5, 0), (3, 5, 2)])
@pytest.mark.parametrize("controlled", [False, True])
def test_borrowed_carry_native_all_small_inputs(monkeypatch, project_root, source_width, target_width,
                                               dirty_width, controlled):
    pytest.importorskip("resource")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_opportunity")
    from qcompile.invsqrt.rounded_product import add_with_borrowed_carry

    km, _, _ = tool.backend()
    values = np.arange(1 << (source_width + target_width + 1 + dirty_width), dtype=np.int64)
    a = values & ((1 << source_width) - 1)
    b = (values >> source_width) & ((1 << target_width) - 1)
    enabled = (values >> (source_width + target_width)) & 1
    borrowed = values >> (source_width + target_width + 1)
    for subtract in (False, True):
        builder = km.CircuitBuilder()
        source = builder.create_quantum_register(source_width, "source")
        target = builder.create_quantum_register(target_width, "target")
        control = builder.create_quantum_register(1, "control")
        dirty = builder.create_quantum_register(dirty_width, "dirty") if dirty_width else None
        scratch = builder.alloc_qubits(2)
        add_with_borrowed_carry(builder, source, target, scratch,
                                control=control[0] if controlled else None, subtract=subtract, dirty=dirty)
        builder.free(scratch)
        circuit = builder.finish_circuit()
        sim = km.Simulator(batch_size=len(values), seed=37117)
        sim.use_same_registers_as(circuit)
        inputs = ((source, a), (target, b), (control, enabled))
        extra = ((dirty, borrowed),) if dirty is not None else ()
        for wires, word in (*inputs, *extra):
            sim.write_across_shots(wires, ((word >> np.arange(len(wires))[:, None]) & 1).astype(bool))
        sim.do(circuit)
        delta = a * (enabled if controlled else 1)
        expected = ((source, a), (target, b - delta if subtract else b + delta), (control, enabled))
        for wires, word in (*expected, *extra):
            np.testing.assert_array_equal(sim.read_across_shots(wires), (word >> np.arange(len(wires))[:, None]) & 1)
        live = {wire.id for wires, _ in (*inputs, *extra) for wire in wires}
        space = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not sim.read_across_shots(space).any()
        assert not sim.read_phase_flipped_across_shots().any()


@pytest.mark.official
@pytest.mark.parametrize("guard", [1, 4])
def test_signed_digit_product_native(monkeypatch, project_root, guard):
    pytest.importorskip("resource")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_opportunity")
    from qcompile.invsqrt.rounded_product import rounded_product, row_sum

    km, _, _ = tool.backend()
    combinations = np.tile(np.arange(512, dtype=np.int64), 8)
    magnitude = combinations & 15
    signed_word = (combinations >> 4) & 7
    initial = (combinations >> 7) << guard
    delta = row_sum(magnitude, signed_word, 3, guard, signed_digits=True)
    if guard == 4:
        np.testing.assert_array_equal(delta, 2 * magnitude * ((signed_word ^ 4) - 4))
    for negate in (False, True):
        for adjoint in (False, True):
            builder = km.CircuitBuilder()
            operand = builder.create_quantum_register(4, "operand")
            signed = builder.create_quantum_register(3, "signed")
            target = builder.create_quantum_register(guard + 3, "target")
            rounded_product(builder, operand, signed, target, guard, signed_digits=True, negate=negate,
                            round_before_negation=True, adjoint=adjoint)
            circuit = builder.finish_circuit()
            sim = km.Simulator(batch_size=len(combinations), seed=37117)
            sim.use_same_registers_as(circuit)
            bias = (1 << (guard - 1)) - int(negate)
            forward = (initial ^ bias) + (-delta if negate else delta)
            for wires, supplied in ((operand, magnitude), (signed, signed_word),
                                    (target, forward if adjoint else initial)):
                shifts = np.arange(len(wires))[:, None]
                sim.write_across_shots(wires, ((supplied >> shifts) & 1).astype(bool))
            sim.do(circuit)
            for wires, expected in ((operand, magnitude), (signed, signed_word),
                                    (target, initial if adjoint else forward)):
                shifts = np.arange(len(wires))[:, None]
                np.testing.assert_array_equal(sim.read_across_shots(wires), (expected >> shifts) & 1)
            scratch = km.array([km.q(i) for i in range(len(operand) + len(signed) + len(target), circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()
            assert not sim.read_phase_flipped_across_shots().any()
