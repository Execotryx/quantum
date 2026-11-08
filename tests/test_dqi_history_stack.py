"""Verify native history restoration and persistent overflow marking."""

from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.history_stack import HistoryStack


@pytest.mark.official
@pytest.mark.parametrize("depth,excess", [(1, 0), (2, 0), (3, 0), (1, 1), (2, 3)])
def test_history_stack_native_restoration_and_flags(project_root, monkeypatch, depth, excess):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    runtime = import_module("dqi_history_depth").runtime
    _, km, _, _ = runtime(project_root / "vendor/backend.json")
    builder = km.CircuitBuilder()
    stack = HistoryStack(builder, depth)
    values = [1 << i for i in range(depth + excess)]
    for round_number, value in enumerate(values, 1):
        builder.gf2_iadd(value, target=stack.transfer)
        stack.push(builder, round_number)
    for round_number in range(len(values), 0, -1):
        stack.pop(builder, round_number)
        if not excess:
            builder.gf2_iadd(values[round_number - 1], target=stack.transfer)
    circuit = builder.finish_circuit()
    simulator = km.Simulator(batch_size=8, seed=901)
    simulator.use_same_registers_as(circuit)
    simulator.do(circuit)
    overflow = simulator.read_across_shots(stack.overflows)
    expected = ((excess >> np.arange(7)) & 1).astype(bool)
    np.testing.assert_array_equal(overflow, np.broadcast_to(expected[:, None], (7, 8)))
    persistent = {q.id for q in (*stack.occupancy, *stack.transfer, *stack.overflows)}
    for data, tag, valid in stack.entries:
        persistent.update(q.id for q in (*data, *tag, valid))
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if not excess or i not in persistent])
    assert not simulator.read_across_shots(scratch).any()
    assert not simulator.read_phase_flipped_across_shots().any()
