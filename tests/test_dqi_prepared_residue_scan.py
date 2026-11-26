"""Native phase scan including coherent preparation and erasure of the residue."""

import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import bm_locator, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.scan import derivative_reciprocal, evaluator, prepared_residue_scan
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


@pytest.mark.official
@pytest.mark.parametrize(("positions", "degree"), [(63, 3), pytest.param(4095, 35, marks=pytest.mark.slow)])
def test_coherent_residue_scan(project_root, monkeypatch, tmp_path, positions, degree):
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
    groups = [[builder.create_quantum_register(12, f"{name}_{i}") for i in range(degree)]
              for name in ("sigma", "omega", "psi")]
    masks = [builder.create_classical_register(12, f"mask_{i}") for i in range(positions)]
    prepared_residue_scan(builder, km.GF2Field(12), groups[0], groups[1], groups[2], masks, multiply=multiply)
    artifact = tmp_path / "prep-scan.kmb"
    builder.finish_circuit().to_file(artifact, format="kmb")
    circuit = km.Circuit.from_file(artifact, format="kmb")
    shots, seed = 32, 36107
    rng = np.random.default_rng(seed + degree)
    field = GF4096()
    values = {name: np.zeros(shots, dtype=np.int64) for name in circuit.register_data}
    expected_phase = np.zeros(shots, dtype=bool)
    for shot in range(shots):
        support = rng.choice(positions, degree, replace=False)
        if shot == 0:
            support = np.array([0, positions - 1, *range(1, degree - 1)], dtype=np.int64)
        errors = {int(j): int(rng.integers(1, 4096)) for j in support}
        syndromes = syndrome(errors, field)
        locator = bm_locator(syndromes, field)
        locator = [field.div(v, locator[-1]) for v in locator]
        for prefix, coefficients in (("sigma", locator[:-1]), ("omega", evaluator(syndromes, locator, field)),
                                     ("psi", derivative_reciprocal(locator, field))):
            for i, coefficient in enumerate(coefficients):
                values[f"{prefix}_{i}"][shot] = coefficient
        for j, mask in enumerate(rng.integers(0, 4096, size=positions)):
            values[f"mask_{j}"][shot] = mask
            expected_phase[shot] ^= bool((int(mask) & errors.get(j, 0)).bit_count() & 1)
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
        assert charged < 23 * positions
        assert circuit.num_qubits <= 1_731
    write_json(tmp_path / "composition.json", {
        "scope": "lower monic locator coefficients and derivative reciprocal supplied",
        "circuit_sha256": sha256(artifact), "backend_sha256": sha256(backend), "tensor_sha256": tensor_hash,
        "positions": positions, "degree": degree, "fixed_support_weight": degree, "checked_shots": shots,
        "seed": seed, "panel_seed": seed + degree, "qubits": circuit.num_qubits,
        "toffoli_like": charged, "operations": dict(circuit.operation_statistics()),
        "phase_restoration_and_cleanup": "pass",
    })
