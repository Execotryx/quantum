"""Native phase scan including coherent preparation and erasure of the residue."""

import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import _divide, bm_locator, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.scan import (
    derivative_reciprocal, evaluator, prepared_residue_scan, two_bank_residue_scan, two_bank_syndrome_scan,
)
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


@pytest.mark.official
@pytest.mark.parametrize(("positions", "degree", "mode", "projective"), [
    (63, 3, "supplied", False), (63, 3, "residue", False), (63, 7, "syndrome", False),
    pytest.param(4095, 35, "supplied", False, marks=pytest.mark.slow),
    pytest.param(4095, 35, "residue", False, marks=pytest.mark.slow),
    pytest.param(4095, 35, "residue", True, marks=pytest.mark.slow),
    pytest.param(4095, 35, "syndrome", False, marks=pytest.mark.slow),
])
def test_coherent_residue_scan(project_root, monkeypatch, tmp_path, positions, degree, mode, projective):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native Linux backend required")
    validate_backend(read_json(backend))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tensor = tmp_path / "scheme42.txt"
    generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
    subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    multiply, tensor_hash = import_module("dqi_quotient").load_field_product(tensor)
    builder = km.CircuitBuilder()
    names = {"supplied": ("sigma", "omega", "psi"), "residue": ("sigma", "omega"),
             "syndrome": ("sigma", "S")}[mode]
    groups = [[builder.create_quantum_register(12, f"{name}_{i}") for i in range(degree)] for name in names]
    masks = [builder.create_classical_register(12, f"mask_{i}") for i in range(positions)]
    half_chart = tuple(range(degree // 2 - 1, -1, -1))
    if mode == "syndrome":
        two_bank_syndrome_scan(builder, km.GF2Field(12), groups[0], groups[1], masks, half_chart, multiply=multiply)
    elif mode == "residue":
        two_bank_residue_scan(builder, km.GF2Field(12), groups[0], groups[1], masks, half_chart,
                              multiply=multiply, projective=projective)
    else:
        prepared_residue_scan(builder, km.GF2Field(12), groups[0], groups[1], groups[2], masks, multiply=multiply)
    artifact = tmp_path / "prep-scan.kmb"
    builder.finish_circuit().to_file(artifact, format="kmb")
    circuit = km.Circuit.from_file(artifact, format="kmb")
    shots, seed = 32, 36107
    rng = np.random.default_rng(seed + degree)
    field = GF4096()
    values = {name: np.zeros(shots, dtype=np.int64) for name in circuit.register_data}
    expected_phase = np.zeros(shots, dtype=bool)
    shot = 0
    weights: dict[int, int] = {}
    attempts = 0
    for attempts in range(1, 2 * shots + 1):
        weight = degree - (shot % 2 if mode == "residue" else 0)
        support = rng.choice(positions, weight, replace=False)
        if attempts == 1:
            support = np.array([0, positions - 1, *range(1, degree - 1)], dtype=np.int64)
        errors = {int(j): int(rng.integers(1, 4096)) for j in support}
        syndromes = syndrome(errors, field)
        locator = bm_locator(syndromes, field)
        locator = [field.div(v, locator[-1]) for v in locator]
        if weight < degree:
            locator = [0, *locator]  # The zero root is outside the scan.
        payload = ("S", syndromes[:degree]) if mode == "syndrome" else ("omega", evaluator(syndromes, locator, field))
        coefficients_by_register = [("sigma", locator[:-1]), payload]
        if mode != "supplied":
            a, d = locator, [locator[i + 1] if i % 2 == 0 else 0 for i in range(degree)]
            observed = []
            while d != [0]:
                _, remainder = _divide(a, d, field)
                a, d = d, remainder
                if d != [0]:
                    observed.append(len(d) - 1)
            if tuple(observed) != tuple(2 * size for size in half_chart):
                continue
        else:
            coefficients_by_register.append(("psi", derivative_reciprocal(locator, field)))
        for prefix, coefficients in coefficients_by_register:
            for i, coefficient in enumerate(coefficients):
                values[f"{prefix}_{i}"][shot] = coefficient
        for j, mask in enumerate(rng.integers(0, 4096, size=positions)):
            values[f"mask_{j}"][shot] = mask
            expected_phase[shot] ^= bool((int(mask) & errors.get(j, 0)).bit_count() & 1)
        weights[weight] = weights.get(weight, 0) + 1
        shot += 1
        if shot == shots:
            break
    assert shot == shots
    sim = km.Simulator(batch_size=shots, counting_operations=True, seed=seed)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    inputs = {name: ((field_words[None, :] >> bits) & 1).astype(bool) for name, field_words in values.items()}
    for name, wires in circuit.register_data.items():
        sim.write_across_shots(wires, inputs[name])
    sim.do(circuit)
    for name, wires in circuit.register_data.items():
        np.testing.assert_array_equal(sim.read_across_shots(wires), inputs[name])
    np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), expected_phase)
    live = {wire.id for reg in circuit.register_data.values() for wire in reg if isinstance(wire, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not sim.read_across_shots(scratch).any()
    charged = circuit.operation_statistics().num_toffoli_like
    assert sim.operation_statistics().num_toffoli_like == charged * shots
    if degree == 35:
        assert charged < {"supplied": 23 * positions, "residue": 280_000, "syndrome": 225_000}[mode]
        assert circuit.num_qubits <= (1_731 if mode == "supplied" else 888)
    write_json(tmp_path / "composition.json", {
        "scope": {"supplied": "lower monic locator coefficients and derivative reciprocal supplied",
                  "residue": "two-bank fixed chart", "syndrome": "two-bank fixed chart with syndrome prefix"}[mode],
        "circuit_sha256": sha256(artifact), "backend_sha256": sha256(backend), "tensor_sha256": tensor_hash,
        "positions": positions, "degree": degree, "support_weight_counts": {str(k): v for k, v in weights.items()},
        "projective": projective,
        "checked_shots": shots, "half_chart": half_chart if mode != "supplied" else None, "attempts": attempts,
        "seed": seed, "panel_seed": seed + degree, "qubits": circuit.num_qubits,
        "toffoli_like": charged, "operations": dict(circuit.operation_statistics()),
        "phase_restoration_and_cleanup": "pass",
    })
