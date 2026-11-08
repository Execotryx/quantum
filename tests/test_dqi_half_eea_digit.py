"""Native coherent quotient generation and reversible Euclidean digit."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
def test_native_eea_quotient_digit_and_reverse(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_half_eea_digit")
    backend = project_root / "vendor/backend.json"
    tool.build(backend, tmp_path / "forward")
    tool.build(backend, tmp_path / "reverse", adjoint=True)
    forward = km.Circuit.from_file(str(tmp_path / "forward/eea-digit.kmb"))
    reverse = km.Circuit.from_file(str(tmp_path / "reverse/eea-digit.kmb"))
    shots = 128
    rng = np.random.default_rng(7015)
    values = {name: rng.integers(0, 1 << len(reg), size=shots)
              for name, reg in forward.register_data.items()}
    values["quotient"].fill(0)
    values["zero"].fill(0)
    for row in range(3):
        values[f"right_{row}_2"].fill(0)
    values["right_0_1"] = rng.integers(1, 4096, size=shots)
    values["right_0_1"][::8] = 0
    values["right_0_0"][::8] = 0
    values["left_0_2"][1::8] = 0
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        numerator = int(values["left_0_2"][shot])
        denominator = int(values["right_0_1"][shot])
        expected["zero"][shot] = denominator == 0
        quotient = field.div(numerator, denominator) if denominator else 0
        expected["quotient"][shot] = quotient
        if denominator:
            for row in range(3):
                for i in range(3):
                    updated = int(values[f"left_{row}_{i}"][shot])
                    if i:
                        updated ^= field.mul(quotient, int(values[f"right_{row}_{i-1}"][shot]))
                    expected[f"left_{row}_{i}"][shot] = values[f"right_{row}_{i}"][shot]
                    expected[f"right_{row}_{i}"][shot] = updated
            assert expected["right_0_2"][shot] == 0
    sim = km.Simulator(batch_size=shots, seed=73)
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
