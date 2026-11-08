"""Classical reciprocal identities and native phase-only position kernel."""

import random
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import _divide, _multiply, bm_locator, recover_forney, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.scan import (
    derivative_reciprocal,
    evaluator,
    evaluator_xor,
    phase_at_position,
    phase_scan,
    quadratic_reciprocal_xor,
)


@pytest.mark.parametrize("weight", range(36))
def test_reciprocal_and_forney_root_values(weight):
    field = GF4096()
    rng = random.Random(2300 + weight)
    errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
    syndromes = syndrome(errors, field)
    locator = bm_locator(syndromes, field)
    omega = evaluator(syndromes, locator, field)
    psi = derivative_reciprocal(locator, field)
    if not weight:
        assert omega == psi == [0]
        return
    derivative = [locator[i] if i % 2 else 0 for i in range(1, len(locator))]
    assert _divide(_multiply(derivative, psi, field), locator, field)[1] == [1]
    recovered = recover_forney(syndromes, locator, field)
    for j, value in recovered.items():
        root = field.exp[-j % field.order]
        assert field.mul(field.evaluate(omega, root), field.evaluate(psi, root)) == value
    assert recovered == errors


def test_repeated_root_is_rejected():
    with pytest.raises(ValueError, match="not invertible"):
        derivative_reciprocal([1, 0, 1], GF4096())


@pytest.mark.official
@pytest.mark.parametrize("t", [2, 6])
def test_native_evaluator_xor_and_reverse(project_root, monkeypatch, t):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    locator = [builder.create_quantum_register(12, f"locator_{i}") for i in range(t + 1)]
    syndromes = [builder.create_quantum_register(12, f"syndrome_{i}") for i in range(t)]
    omega = [builder.create_quantum_register(12, f"omega_{i}") for i in range(t)]
    evaluator_xor(builder, locator, syndromes, omega)
    circuit = builder.finish_circuit()
    assert circuit.operation_statistics().num_toffoli_like == 54 * t * (t + 1) // 2
    shots = 64
    rng = np.random.default_rng(680 + t)
    values = {name: rng.integers(0, 4096, size=shots) for name in circuit.register_data}
    sim = km.Simulator(batch_size=shots, seed=39)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    expected = {name: word.copy() for name, word in values.items()}
    field = GF4096()
    for shot in range(shots):
        for k in range(t):
            for i in range(k + 1):
                expected[f"omega_{k}"][shot] ^= field.mul(
                    int(values[f"locator_{i}"][shot]), int(values[f"syndrome_{k-i}"][shot])
                )
    for output in (expected, values):
        sim.do(circuit)
        for name, reg in circuit.register_data.items():
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((output[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not len(scratch) or not sim.read_across_shots(scratch).any()


@pytest.mark.official
@pytest.mark.parametrize("mutation", ["none", "skip_position", "wrong_mask", "skip_transform_reversal"])
def test_native_position_kernel(project_root, monkeypatch, mutation):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    sigma = builder.create_quantum_register(12, "sigma")
    omega = builder.create_quantum_register(12, "omega")
    psi = builder.create_quantum_register(12, "psi")
    mask = builder.create_classical_register(12, "mask")

    class Mutation:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.conditions = 0
            self.dropped = False

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def push_condition(self, control):
            self.conditions += 1
            self.wrapped.push_condition(control)

        def cx(self, source, target):
            if mutation == "skip_transform_reversal" and self.conditions > 12 and not self.dropped:
                self.dropped = True
            else:
                self.wrapped.cx(source, target)

    if mutation != "skip_position":
        phase_at_position(Mutation(builder), sigma, omega, psi, mask)
    circuit = builder.finish_circuit()
    if mutation == "none":
        assert circuit.operation_statistics().num_toffoli_like == 23
    shots = 512
    rng = np.random.default_rng(343)
    words = {
        "sigma": rng.integers(0, 4096, size=shots),
        "omega": rng.integers(0, 4096, size=shots),
        "psi": rng.integers(0, 4096, size=shots),
        "mask": rng.integers(0, 4096, size=shots),
    }
    words["sigma"][:shots // 2] = 0
    words["omega"][0] = words["psi"][0] = words["mask"][0] = 1
    actual_mask = words["mask"] ^ (1 if mutation == "wrong_mask" else 0)
    sim = km.Simulator(batch_size=shots, seed=49)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    for name, reg in circuit.register_data.items():
        values = actual_mask if name == "mask" else words[name]
        sim.write_across_shots(reg, ((values[None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    for name, reg in (("sigma", sigma), ("omega", omega), ("psi", psi)):
        np.testing.assert_array_equal(sim.read_across_shots(reg), ((words[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    dirty = bool(len(scratch) and sim.read_across_shots(scratch).any())
    field = GF4096()
    expected = np.array([
        not int(words["sigma"][j]) and (
            field.mul(int(words["omega"][j]), int(words["psi"][j])) & int(words["mask"][j])
        ).bit_count() % 2 == 1 for j in range(shots)
    ])
    wrong_phase = bool(np.any(sim.read_phase_flipped_across_shots() != expected))
    if mutation == "none":
        assert not dirty and not wrong_phase
    elif mutation == "skip_transform_reversal":
        assert dirty
    else:
        assert wrong_phase


@pytest.mark.official
@pytest.mark.parametrize(("m", "n"), [(63, 4), (127, 12), pytest.param(4095, 70, marks=pytest.mark.slow)])
def test_native_full_scan(project_root, monkeypatch, tmp_path, m, n):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_prototype")
    tool.build_scan(project_root / "vendor/backend.json", tmp_path / "scan", m=m, n=n)
    circuit = km.Circuit.from_file(str(tmp_path / "scan" / "phase-scan.kmb"))
    assert circuit.operation_statistics().num_toffoli_like == 23 * m
    shots = 2 * (n // 2 + 1)
    rng = random.Random(780 + n)
    field = GF4096()
    values = {name: np.zeros(shots, dtype=np.int64) for name in circuit.register_data}
    expected = np.zeros(shots, dtype=bool)
    for shot in range(shots):
        weight = shot % (n // 2 + 1)
        errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(m), weight)}
        syndromes = syndrome(errors, field)
        locator = bm_locator(syndromes, field)
        for prefix, polynomial in (("sigma", locator), ("omega", evaluator(syndromes, locator, field)),
                                   ("psi", derivative_reciprocal(locator, field))):
            for index, word in enumerate(polynomial):
                if f"{prefix}_{index}" in values:
                    values[f"{prefix}_{index}"][shot] = word
        for j in range(m):
            word = rng.randrange(4096)
            values[f"mask_{j}"][shot] = word
            expected[shot] ^= bool((word & errors.get(j, 0)).bit_count() % 2)
    sim = km.Simulator(batch_size=shots, seed=59)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), expected)
    for name, reg in circuit.register_data.items():
        np.testing.assert_array_equal(sim.read_across_shots(reg), ((values[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not len(scratch) or not sim.read_across_shots(scratch).any()


@pytest.mark.official
def test_native_quadratic_evaluator_reciprocal_scan_composition(project_root, monkeypatch):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    locator = [builder.create_quantum_register(12, f"sigma_{i}") for i in range(3)]
    syndromes = [builder.create_quantum_register(12, f"syndrome_{i}") for i in range(2)]
    masks = [builder.create_classical_register(12, f"mask_{i}") for i in range(63)]
    omega = [builder.alloc_qubits(12) for _ in range(2)]
    psi = [builder.alloc_qubits(12) for _ in range(2)]
    evaluator_xor(builder, locator, syndromes, omega)
    quadratic_reciprocal_xor(builder, locator, psi)
    phase_scan(builder, km.GF2Field(12), locator, omega, psi, masks)
    quadratic_reciprocal_xor(builder, locator, psi)
    evaluator_xor(builder, locator, syndromes, omega)
    for word in (*omega, *psi):
        builder.free(word)
    circuit = builder.finish_circuit()
    assert circuit.operation_statistics().num_toffoli_like == 2 * (162 + 180) + 23 * 63
    shots = 24
    rng = random.Random(441)
    field = GF4096()
    words = {name: np.zeros(shots, dtype=np.int64) for name in circuit.register_data}
    expected = np.zeros(shots, dtype=bool)
    for shot in range(shots):
        errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(63), shot % 3)}
        values = syndrome(errors, field)
        polynomial = bm_locator(values, field)
        for index, value in enumerate(polynomial):
            words[f"sigma_{index}"][shot] = value
        for index in range(2):
            words[f"syndrome_{index}"][shot] = values[index]
        for index in range(63):
            mask = rng.randrange(4096)
            words[f"mask_{index}"][shot] = mask
            expected[shot] ^= bool((mask & errors.get(index, 0)).bit_count() % 2)
    sim = km.Simulator(batch_size=shots, seed=42)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((words[name][None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), expected)
    for name, reg in circuit.register_data.items():
        np.testing.assert_array_equal(sim.read_across_shots(reg), ((words[name][None, :] >> bits) & 1))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not len(scratch) or not sim.read_across_shots(scratch).any()
