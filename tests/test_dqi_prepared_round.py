"""Coherent multiplier-prepared routed BM slice and exact inverse."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
def test_prepared_routed_update_and_reverse(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_prepared_slice")
    backend = project_root / "vendor/backend.json"
    tool.build(backend, tmp_path / "forward")
    tool.build(backend, tmp_path / "reverse", adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward/prepared-round.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse/prepared-round.kmb"))
    assert forward.operation_statistics().num_toffoli_like == 558
    assert reverse.operation_statistics().num_toffoli_like == 558
    shots = 256
    rng = np.random.default_rng(5851)
    values = {name: rng.integers(0, 1 << len(reg), size=shots)
              for name, reg in forward.register_data.items()}
    values["sigma_0"] = rng.integers(1, 4096, size=shots)
    values["shifted_0"].fill(0)
    values["delta"][::8] = 0
    values["replace"] = (np.arange(shots) % 2).astype(np.int64)
    values["replace"][values["delta"] == 0] = 0
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        delta, constant = int(values["delta"][shot]), int(values["sigma_0"][shot])
        alpha = field.mul(delta, constant)
        multiplier = field.inv(alpha) if values["replace"][shot] else alpha
        for index in range(3):
            a = int(values[f"sigma_{index}"][shot])
            b = int(values[f"shifted_{index}"][shot])
            if values["replace"][shot]:
                a, b = b, a
            expected[f"sigma_{index}"][shot] = a ^ field.mul(multiplier, b)
            expected[f"shifted_{index}"][shot] = b
    sim = km.Simulator(batch_size=shots, seed=272)
    sim.use_same_registers_as(forward)
    for name, reg in forward.register_data.items():
        bits = np.arange(len(reg))[:, None]
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in forward.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(forward.num_qubits) if i not in live])
    for circuit, outputs in ((forward, expected), (reverse, values)):
        sim.do(circuit)
        for name, reg in forward.register_data.items():
            bits = np.arange(len(reg))[:, None]
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((outputs[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
