"""Native reduced shared-update slice, with caller-supplied metadata."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
def test_native_routed_shared_update_and_adjoint(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_prototype")
    backend = project_root / "vendor/backend.json"
    tool.build("routed-bm", backend, tmp_path / "forward")
    tool.build("routed-bm", backend, tmp_path / "reverse", adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward" / "routed-bm.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse" / "routed-bm.kmb"))
    assert forward.operation_statistics().num_toffoli_like == 198
    shots = 128
    rng = np.random.default_rng(3552)
    values = {name: rng.integers(0, 1 << len(reg), size=shots)
              for name, reg in forward.register_data.items()}
    values["branch"] = np.arange(shots) % 2
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        for index in range(3):
            current = int(values[f"current_{index}"][shot])
            previous = int(values[f"previous_{index}"][shot])
            if values["branch"][shot]:
                current, previous = previous, current
            expected[f"current_{index}"][shot] = current ^ field.mul(int(values["source"][shot]), previous)
            expected[f"previous_{index}"][shot] = previous
    sim = km.Simulator(batch_size=shots, seed=13)
    sim.use_same_registers_as(forward)
    for name, reg in forward.register_data.items():
        bits = np.arange(len(reg))[:, None]
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in forward.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(forward.num_qubits) if i not in live])
    for circuit, result in ((forward, expected), (reverse, values)):
        sim.do(circuit)
        for name, reg in forward.register_data.items():
            bits = np.arange(len(reg))[:, None]
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((result[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
