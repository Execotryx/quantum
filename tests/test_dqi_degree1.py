"""Exact radius-one phase decoder against independently generated cases."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
def test_radius_one_native_decoder_and_verifier(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/verifiers/dqi"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_degree1")
    verifier = import_module("verify_submission_dqi")
    output = tmp_path / "decoder"
    tool.build(project_root / "vendor/backend.json", output, m=63)
    circuit = km.Circuit.from_file(str(output / "degree1.kmb"))
    assert circuit.operation_statistics().num_toffoli_like == 462 + 23 * 63
    shots = 128
    field = GF4096()
    rng = np.random.default_rng(6810)
    words = {name: rng.integers(0, 4096, size=shots) for name in circuit.register_data}
    expected = np.zeros(shots, dtype=bool)
    words["S0"].fill(0)
    words["S1"].fill(0)
    for shot in range(1, shots):
        position = (shot - 1) % 63
        value = 1 + (shot * 73) % 4095
        point = field.exp[position]
        words["S0"][shot] = field.mul(value, point)
        words["S1"][shot] = field.mul(int(words["S0"][shot]), point)
        expected[shot] = (int(words[f"E{position}"][shot]) & value).bit_count() % 2 == 1
    bits = np.arange(12)[:, None]
    sim = km.Simulator(batch_size=shots, seed=124)
    sim.use_same_registers_as(circuit)
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((words[name][None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), expected)
    for name, reg in circuit.register_data.items():
        np.testing.assert_array_equal(sim.read_across_shots(reg), ((words[name][None, :] >> bits) & 1))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not len(scratch) or not sim.read_across_shots(scratch).any()
    spec = verifier.ProblemSpecDQI.benchmark_instance(m=63, n=2, degree=12, num_shots=2560)
    result = verifier.verify(circuit, spec, seed=680, batch_size=256, max_workers=1)
    assert result["verified_shots"] == 2560
    assert result["value_errors"] == result["phase_errors"] == 0
