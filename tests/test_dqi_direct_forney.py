"""Supplied-locator direct Forney integration at reduced and full degree."""

import random
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import bm_locator, syndrome
from qcompile.dqi.field import GF4096


@pytest.mark.official
@pytest.mark.parametrize(("m", "n"), [(63, 4), (127, 12), (70, 70)])
def test_native_direct_forney_all_weights(project_root, monkeypatch, tmp_path, m, n):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_direct_forney")
    output = tmp_path / "scan"
    tool.build(project_root / "vendor/backend.json", output, m=m, n=n)
    circuit = km.Circuit.from_file(str(output / "direct-forney.kmb"))
    t = n // 2
    assert circuit.operation_statistics().num_toffoli_like == 108 * t * (t + 1) // 2 + 227 * m
    shots = t + 1
    rng = random.Random(5920 + n)
    field = GF4096()
    words = {name: np.zeros(shots, dtype=np.int64) for name in circuit.register_data}
    phases = np.zeros(shots, dtype=bool)
    for weight in range(shots):
        errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(m), weight)}
        syndromes = syndrome(errors, field)
        locator = bm_locator(syndromes, field)
        scale = rng.randrange(1, 4096)
        locator = [field.mul(value, scale) for value in locator]
        for i, value in enumerate(locator):
            words[f"sigma_{i}"][weight] = value
        for i in range(n):
            words[f"S{i}"][weight] = syndromes[i]
        for j in range(m):
            mask = rng.randrange(4096)
            words[f"E{j}"][weight] = mask
            phases[weight] ^= bool((mask & errors.get(j, 0)).bit_count() % 2)
    bits = np.arange(12)[:, None]
    sim = km.Simulator(batch_size=shots, seed=55)
    sim.use_same_registers_as(circuit)
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((words[name][None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), phases)
    for name, reg in circuit.register_data.items():
        np.testing.assert_array_equal(sim.read_across_shots(reg), ((words[name][None, :] >> bits) & 1))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not len(scratch) or not sim.read_across_shots(scratch).any()
