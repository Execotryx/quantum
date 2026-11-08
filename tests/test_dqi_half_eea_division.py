"""Native two-digit EEA division with coherent quotient history."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
def test_native_two_digit_division_and_reverse(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_half_eea_division")
    backend = project_root / "vendor/backend.json"
    tool.build(backend, tmp_path / "forward")
    tool.build(backend, tmp_path / "reverse", adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward/eea-division.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse/eea-division.kmb"))
    assert forward.operation_statistics().num_toffoli_like == 1242
    assert reverse.operation_statistics().num_toffoli_like == 1242
    shots = 128
    rng = np.random.default_rng(3264)
    values = {name: rng.integers(0, 1 << len(reg), size=shots)
              for name, reg in forward.register_data.items()}
    for name in ("quotient_0", "quotient_1", "zero"):
        values[name].fill(0)
    for row in range(3):
        values[f"right_{row}_2"].fill(0)
    values["right_0_1"] = rng.integers(1, 4096, size=shots)
    values["right_0_1"][::8] = 0
    values["right_0_0"][::8] = 0
    values["left_0_2"][1::8] = 0
    field = GF4096()
    # Force a zero low quotient digit as well as the zero-high and zero-divisor cases.
    for shot in range(2, shots, 8):
        high = field.div(int(values["left_0_2"][shot]), int(values["right_0_1"][shot]))
        values["left_0_1"][shot] = field.mul(high, int(values["right_0_0"][shot]))
    expected = {name: words.copy() for name, words in values.items()}
    for shot in range(shots):
        denominator = int(values["right_0_1"][shot])
        expected["zero"][shot] = denominator == 0
        if not denominator:
            continue
        updated = [[int(values[f"left_{row}_{i}"][shot]) for i in range(3)] for row in range(3)]
        right = [[int(values[f"right_{row}_{i}"][shot]) for i in range(3)] for row in range(3)]
        for shift in (1, 0):
            quotient = field.div(updated[0][1 + shift], denominator)
            expected[f"quotient_{shift}"][shot] = quotient
            for row in range(3):
                for i in range(3 - shift):
                    updated[row][i + shift] ^= field.mul(quotient, right[row][i])
        assert updated[0][1:] == [0, 0]
        for row in range(3):
            for i in range(3):
                expected[f"left_{row}_{i}"][shot] = right[row][i]
                expected[f"right_{row}_{i}"][shot] = updated[row][i]
    sim = km.Simulator(batch_size=shots, seed=27)
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


@pytest.mark.official
def test_native_three_digit_constant_divisor(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_half_eea_division")
    backend = project_root / "vendor/backend.json"
    tool.build(backend, tmp_path / "forward", denominator_degree=0)
    tool.build(backend, tmp_path / "reverse", denominator_degree=0, adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward/eea-division.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse/eea-division.kmb"))
    assert forward.operation_statistics().num_toffoli_like == 1458
    assert reverse.operation_statistics().num_toffoli_like == 1458
    shots = 64
    rng = np.random.default_rng(9017)
    values = {name: rng.integers(0, 1 << len(reg), size=shots)
              for name, reg in forward.register_data.items()}
    for name in ("quotient_0", "quotient_1", "quotient_2", "zero"):
        values[name].fill(0)
    for row in range(3):
        values[f"right_{row}_1"].fill(0)
        values[f"right_{row}_2"].fill(0)
    values["right_0_0"] = rng.integers(1, 4096, size=shots)
    values["right_0_0"][::8] = 0
    values["left_0_2"][1::8] = 0
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        denominator = int(values["right_0_0"][shot])
        expected["zero"][shot] = denominator == 0
        if not denominator:
            continue
        updated = [[int(values[f"left_{row}_{i}"][shot]) for i in range(3)] for row in range(3)]
        right = [[int(values[f"right_{row}_{i}"][shot]) for i in range(3)] for row in range(3)]
        for shift in (2, 1, 0):
            quotient = field.div(updated[0][shift], denominator)
            expected[f"quotient_{shift}"][shot] = quotient
            for row in range(3):
                for i in range(3 - shift):
                    updated[row][i + shift] ^= field.mul(quotient, right[row][i])
        assert updated[0] == [0, 0, 0]
        for row in range(3):
            for i in range(3):
                expected[f"left_{row}_{i}"][shot] = right[row][i]
                expected[f"right_{row}_{i}"][shot] = updated[row][i]
    sim = km.Simulator(batch_size=shots, seed=38)
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
