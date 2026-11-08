"""Native half-degree polynomial EEA monomial-elimination slice."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
@pytest.mark.parametrize("shift", [0, 1, 2])
def test_native_half_eea_monomial_step(project_root, monkeypatch, tmp_path, shift):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_half_eea_slice")
    backend = project_root / "vendor/backend.json"
    tool.build(backend, tmp_path / "forward", shift=shift)
    tool.build(backend, tmp_path / "reverse", shift=shift, adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward/half-eea.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse/half-eea.kmb"))
    assert forward.operation_statistics().num_toffoli_like == 3 * (3 - shift) * 54
    shots = 64
    rng = np.random.default_rng(991 + shift)
    values = {name: rng.integers(0, 4096, size=shots) for name in forward.register_data}
    for row in range(3):
        for i in range(3 - shift, 3):
            values[f"right_{row}_{i}"].fill(0)
    values["quotient"][0] = 0
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        quotient = int(values["quotient"][shot])
        for row in range(3):
            for i in range(3):
                right = int(values[f"right_{row}_{i}"][shot])
                current = int(values[f"left_{row}_{i}"][shot])
                if i >= shift:
                    current ^= field.mul(quotient, int(values[f"right_{row}_{i-shift}"][shot]))
                expected[f"left_{row}_{i}"][shot] = right
                expected[f"right_{row}_{i}"][shot] = current
    sim = km.Simulator(batch_size=shots, seed=919)
    sim.use_same_registers_as(forward)
    bits = np.arange(12)[:, None]
    for name, reg in forward.register_data.items():
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in forward.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(forward.num_qubits) if i not in live])
    for circuit, outputs in ((forward, expected), (reverse, values)):
        sim.do(circuit)
        for name, reg in forward.register_data.items():
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((outputs[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
