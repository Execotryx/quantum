"""Native arithmetic, phase and clean-workspace checks for a Booth row slice."""

from importlib import import_module

import numpy as np
import pytest

from qcompile.invsqrt.signed_row import signed_row


@pytest.mark.official
@pytest.mark.parametrize("shift,subtract", [(shift, subtract) for shift in (-4, -2, -1, 0, 1)
                                             for subtract in (False, True)])
def test_booth_row_exhaustive_basis_and_measurement_trajectories(project_root, monkeypatch, shift, subtract):
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    digit = builder.create_quantum_register(3, "digit")
    operand = builder.create_quantum_register(3, "operand")
    target = builder.create_quantum_register(4, "target")
    work = builder.alloc_qubits(4)
    signed_row(builder, digit[0], digit[1], digit[2], operand, target, work, shift, subtract=subtract)
    builder.free(work)
    circuit = builder.finish_circuit()
    # All 8 digit encodings, 8 operands, 16 targets; repeated trajectories.
    inputs = np.tile(np.arange(8 * 8 * 16, dtype=np.int64), 8)
    digits = inputs & 7
    operands = (inputs >> 3) & 7
    targets = (inputs >> 6) & 15
    sim = km.Simulator(batch_size=len(inputs), seed=338 + shift + 2 * subtract)
    sim.use_same_registers_as(circuit)
    def write(register, values):
        bits = np.arange(len(register))[:, None]
        sim.write_across_shots(register, (values[None, :] >> bits) & 1 == 1)
    write(digit, digits)
    write(operand, operands)
    write(target, targets)
    sim.do(circuit)
    def read(register):
        return (sim.read_across_shots(register).astype(np.int64) * (1 << np.arange(len(register)))[:, None]).sum(axis=0)
    decoded = (digits & 1) + ((digits >> 1) & 1) - 2 * ((digits >> 2) & 1)
    product = decoded * operands
    product = product << shift if shift >= 0 else product >> -shift
    expected = (targets + (-1 if subtract else 1) * product) & 15
    assert np.array_equal(read(target), expected)
    assert np.array_equal(read(digit), digits)
    assert np.array_equal(read(operand), operands)
    live = {q.id for register in (digit, operand, target) for q in register}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not sim.read_across_shots(scratch).any()
    assert not sim.read_phase_flipped_across_shots().any()
