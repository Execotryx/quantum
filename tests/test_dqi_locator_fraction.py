"""Native oracle comparison for the in-place regular locator chart."""

import random
import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import _divide, bm_locator, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.locator_fraction import _series_inverse, blocked_quotient_tape, regular_locator_evaluator
from qcompile.dqi.scan import evaluator, two_bank_residue_scan
from qcompile.dqi.tower import ProjectedFieldProduct
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def _ordinary_reciprocal(words: list[int], field: GF4096) -> list[int]:
    reciprocal = [field.inv(words[0])]
    for k in range(1, len(words)):
        accumulated = 0
        for j in range(1, k + 1):
            accumulated ^= field.mul(words[j], reciprocal[k - j])
        reciprocal.append(field.mul(accumulated, reciprocal[0]))
    return reciprocal


@pytest.mark.official
@pytest.mark.parametrize(("degree", "steps"), [(7, 3), pytest.param(35, 9, marks=pytest.mark.slow),
                                                pytest.param(35, 17, marks=pytest.mark.slow)])
def test_native_blocked_quotient_tape(project_root, monkeypatch, tmp_path, degree, steps):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native backend required")
    validate_backend(read_json(backend))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tensor = tmp_path / "scheme42.txt"
    generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
    subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    multiply, tensor_sha = import_module("dqi_quotient").load_field_product(tensor, projected=True)
    assert isinstance(multiply, ProjectedFieldProduct)
    field = GF4096()
    rng = random.Random(36871)
    inputs, outputs = [], []
    for _ in range(24):
        support = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), degree)}
        raw = syndrome(support, field)[:2 * degree]
        result = raw.copy()
        for offset in range(0, 2 * steps, 2):
            if not result[offset]:
                break
            result[offset:] = _ordinary_reciprocal(result[offset:], field)
        else:
            previous, current = 0, 1
            for constant in result[1:2 * steps:2]:
                previous, current = current, field.mul(constant, current) ^ previous
            if current:
                inputs.append(raw)
                outputs.append(result)
        if len(inputs) == 12:
            break
    assert len(inputs) == 12
    observations = {}
    for adjoint in (False, True):
        builder = km.CircuitBuilder()
        words = [builder.create_quantum_register(12, f"S{i}") for i in range(2 * degree)]
        blocked_quotient_tape(builder, words, steps, adjoint=adjoint, multiply=multiply)
        label = "inverse" if adjoint else "forward"
        artifact = tmp_path / f"{label}.kmb"
        builder.finish_circuit().to_file(artifact, format="kmb")
        circuit = km.Circuit.from_file(artifact, format="kmb")
        sim = km.Simulator(batch_size=len(inputs), seed=36873)
        sim.use_same_registers_as(circuit)
        initial, expected = (outputs, inputs) if adjoint else (inputs, outputs)
        bits = np.arange(12)[:, None]
        for wires, column in zip(words, np.asarray(initial).T, strict=True):
            sim.write_across_shots(wires, ((column >> bits) & 1).astype(bool))
        sim.do(circuit)
        for wires, column in zip(words, np.asarray(expected).T, strict=True):
            np.testing.assert_array_equal(sim.read_across_shots(wires), (column >> bits) & 1)
        live = {q.id for word in words for q in word}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()
        observations[label] = {"qubits": circuit.num_qubits, "sha256": sha256(artifact),
                               "toffoli_like": circuit.operation_statistics().num_toffoli_like}
    write_json(tmp_path / "blocked-quotient-tape.json", {
        "scope": "regular raw prefix quotient generation and remaining residual",
        "degree": degree, "steps": steps, "shots": len(inputs),
        "sample_seed": 36871, "native_seed": 36873, "backend_sha256": sha256(backend),
        "tensor_sha256": tensor_sha, "observations": observations,
    })


@pytest.mark.official
@pytest.mark.parametrize(("degree", "reciprocal_steps"),
                         [(3, 0), (7, 0), pytest.param(35, 1, marks=pytest.mark.slow),
                          pytest.param(35, 3, marks=pytest.mark.slow)])
def test_native_regular_locator(project_root, monkeypatch, tmp_path, degree, reciprocal_steps):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native backend required")
    validate_backend(read_json(backend))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tensor = tmp_path / "scheme42.txt"
    generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
    subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    multiply, tensor_sha = import_module("dqi_quotient").load_field_product(tensor)
    field = GF4096()
    seed = 36151 + degree
    rng = random.Random(seed)
    shots = 12
    inputs, outputs, supports = [], [], []
    positions = 63 if degree == 3 else 4095
    for _ in range(2 * shots):
        errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(positions), degree)}
        full_syndrome = syndrome(errors, field)
        locator = bm_locator(full_syndrome, field)
        values = full_syndrome[:2 * degree]
        omega = evaluator(values, locator, field)
        numerator = [*omega, *([0] * (degree - len(omega)))][::-1]
        a, b = locator[::-1], numerator
        chart = []
        while b != [0]:
            quotient, remainder = _divide(a, b, field)
            chart.append(len(quotient) - 1)
            a, b = b, remainder
        if chart != [1] * degree:
            continue
        locator = [field.div(v, locator[-1]) for v in locator]
        inputs.append(values)
        supports.append(errors)
        prefix = evaluator(values, locator, field)
        outputs.append(locator[:-1] + prefix + [0] * (degree - len(prefix)))
        if len(inputs) == shots:
            break
    assert len(inputs) == shots

    offsets = tuple(range(0, 2 * reciprocal_steps, 2))
    if offsets:
        outputs = [row[:] for row in inputs]
        for row in outputs:
            for offset in offsets:
                row[offset:] = _ordinary_reciprocal(row[offset:], field)
    receipts = {}
    for reverse in (False, True):
        builder = km.CircuitBuilder()
        words = [builder.create_quantum_register(12, f"S{i}") for i in range(2 * degree)]
        if offsets:
            for offset in reversed(offsets) if reverse else offsets:
                _series_inverse(builder, words[offset:], multiply)
            output_order = words
        else:
            locator_wires, evaluator_wires = regular_locator_evaluator(builder, words, adjoint=reverse,
                                                                     multiply=multiply)
            output_order = [*locator_wires, *evaluator_wires]
        label = "inverse" if reverse else "forward"
        artifact = tmp_path / f"{label}.kmb"
        builder.finish_circuit().to_file(artifact, format="kmb")
        circuit = km.Circuit.from_file(artifact, format="kmb")
        sim = km.Simulator(batch_size=shots, seed=36161, counting_operations=True)
        sim.use_same_registers_as(circuit)
        quantum_in, quantum_out = (output_order, words) if reverse else (words, output_order)
        values_in, values_out = (outputs, inputs) if reverse else (inputs, outputs)
        bits = np.arange(12)[:, None]
        for wires, column in zip(quantum_in, np.asarray(values_in).T, strict=True):
            sim.write_across_shots(wires, ((column[None, :] >> bits) & 1).astype(bool))
        sim.do(circuit)
        for wires, column in zip(quantum_out, np.asarray(values_out).T, strict=True):
            np.testing.assert_array_equal(sim.read_across_shots(wires), (column[None, :] >> bits) & 1)
        live = {q.id for word in words for q in word}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()
        charge = int(circuit.operation_statistics().num_toffoli_like)
        assert sim.operation_statistics().num_toffoli_like == shots * charge
        if offsets:
            assert charge <= 36_354 * reciprocal_steps
            assert circuit.num_qubits <= 888
        receipts[label] = {"sha256": sha256(artifact), "qubits": circuit.num_qubits, "toffoli_like": charge}
    if degree == 3:
        builder = km.CircuitBuilder()
        words = [builder.create_quantum_register(12, f"S{i}") for i in range(2 * degree)]
        masks = [builder.create_classical_register(12, f"E{i}") for i in range(positions)]
        locator_wires, evaluator_wires = regular_locator_evaluator(builder, words, multiply=multiply)
        two_bank_residue_scan(builder, km.GF2Field(12), locator_wires, evaluator_wires, masks, (0,), multiply=multiply)
        regular_locator_evaluator(builder, words, adjoint=True, multiply=multiply)
        circuit = builder.finish_circuit()
        sim = km.Simulator(batch_size=shots, seed=36167)
        sim.use_same_registers_as(circuit)
        mask_words = np.random.default_rng(seed).integers(0, 4096, size=(shots, positions))
        for wires, column in zip([*words, *masks], np.concatenate((inputs, mask_words), axis=1).T, strict=True):
            sim.write_across_shots(wires, ((column[None, :] >> bits) & 1).astype(bool))
        sim.do(circuit)
        for wires, column in zip([*words, *masks], np.concatenate((inputs, mask_words), axis=1).T, strict=True):
            np.testing.assert_array_equal(sim.read_across_shots(wires), (column[None, :] >> bits) & 1)
        phases = [sum((word & int(mask_words[i, j])).bit_count() for j, word in errors.items()) % 2
                  for i, errors in enumerate(supports)]
        np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), phases)
        live = {q.id for word in words for q in word}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not sim.read_across_shots(scratch).any()
        artifact = tmp_path / "composed.kmb"
        circuit.to_file(artifact, format="kmb")
        receipts["composed"] = {"sha256": sha256(artifact), "qubits": circuit.num_qubits, "positions": positions,
                                "toffoli_like": int(circuit.operation_statistics().num_toffoli_like)}
    write_json(tmp_path / "locator.json", {
        "scope": "initial reciprocals" if offsets else "complete regular locator and evaluator",
        "degree": degree, "reciprocal_steps": reciprocal_steps, "shots": shots,
        "sample_seed": seed, "native_seed": 36161,
        "backend_sha256": sha256(backend), "tensor_sha256": tensor_sha, "observations": receipts,
    })
