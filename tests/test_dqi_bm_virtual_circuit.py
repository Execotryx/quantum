"""Native controlled lookup for a virtual shifted BM template."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.bm_virtual_circuit import shifted_template_xor


@pytest.mark.official
def test_native_virtual_lookup_and_reverse(project_root, monkeypatch):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    base = [builder.create_quantum_register(12, f"base_{i}") for i in range(3)]
    output = [builder.create_quantum_register(12, f"output_{i}") for i in range(3)]
    age = builder.create_quantum_register(3, "age")
    enabled = builder.create_quantum_register(1, "enabled")[0]
    shifted_template_xor(builder, base, age, enabled, output)
    circuit = builder.finish_circuit()
    shots = 128
    rng = np.random.default_rng(1002)
    words = {name: rng.integers(0, 1 << len(reg), size=shots) for name, reg in circuit.register_data.items()}
    words["age"] = np.arange(shots) % 5
    words["enabled"] = (words["age"] < 2).astype(np.int64)
    # Active cases meet the proved support precondition; disabled cases can be arbitrary.
    words["base_2"][words["enabled"] == 1] = 0
    words["base_1"][words["age"] == 1] = 0
    expected = {name: value.copy() for name, value in words.items()}
    for shot in range(shots):
        if words["enabled"][shot]:
            for i in range(2 - int(words["age"][shot])):
                expected[f"output_{i + int(words['age'][shot]) + 1}"][shot] ^= words[f"base_{i}"][shot]
    sim = km.Simulator(batch_size=shots, seed=68)
    sim.use_same_registers_as(circuit)
    for name, reg in circuit.register_data.items():
        bits = np.arange(len(reg))[:, None]
        sim.write_across_shots(reg, ((words[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    for result in (expected, words):
        sim.do(circuit)
        for name, reg in circuit.register_data.items():
            bits = np.arange(len(reg))[:, None]
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((result[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
