"""Native monic-quotient multiplication against independent long division."""

import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096


@pytest.mark.official
@pytest.mark.parametrize(("degree", "rank", "clean"),
                         [(d, 54, False) for d in (1, 2, 3, 5, 6, 11, 35)]
                         + [(35, 42, False), (1, 54, True), (6, 54, True), (35, 42, True)])
def test_native_quotient_product_and_cleanup(project_root, monkeypatch, tmp_path, degree, rank, clean):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_quotient")
    output = tmp_path / "quotient"
    tensor = None
    if rank == 42:
        tensor = tmp_path / "scheme42.txt"
        generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
        subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    backend = project_root / "vendor/backend.json"
    tool.build(backend, output, degree=degree, tensor42=tensor, clean_target=clean)
    circuit = km.Circuit.from_file(str(output / "quotient.kmb"))
    inverse = circuit
    if clean:
        inverse_output = tmp_path / "inverse"
        tool.build(backend, inverse_output, degree=degree, tensor42=tensor, clean_target=True, adjoint=True)
        inverse = km.Circuit.from_file(inverse_output / "quotient.kmb")
        assert inverse.num_qubits == circuit.num_qubits
    charged = circuit.operation_statistics().num_toffoli_like
    assert 0 < charged < 108 * (2 * degree**2 - degree)
    if degree == 35:
        if clean:
            assert charged < 25_000
            assert circuit.num_qubits <= 1_743
        else:
            assert charged == 574 * rank
            assert circuit.num_qubits <= 2_127
    shots = 64
    rng = np.random.default_rng(785 + degree)
    values = {name: rng.integers(0, 4096, size=shots) for name in circuit.register_data}
    # Include zero and reducible moduli and nonzero targets.
    for i in range(degree):
        values[f"left_{i}"][1] = 0
        if clean:
            values[f"target_{i}"].fill(0)
            values[f"modulus_{i}"][2] = int(i == 0)
        else:
            values[f"modulus_{i}"][0] = 0
            if degree >= 2:
                values[f"modulus_{i}"][2] = int(i == degree - 2)
    if clean:
        values["modulus_0"][values["modulus_0"] == 0] = 1
    expected = {name: words.copy() for name, words in values.items()}
    field = GF4096()
    for shot in range(shots):
        product = [0] * (2 * degree - 1)
        for i in range(degree):
            for j in range(degree):
                product[i + j] ^= field.mul(int(values[f"left_{i}"][shot]), int(values[f"right_{j}"][shot]))
        for k in range(2 * degree - 2, degree - 1, -1):
            factor = product[k]
            for i in range(degree):
                product[k - degree + i] ^= field.mul(factor, int(values[f"modulus_{i}"][shot]))
            product[k] = 0
        for i in range(degree):
            expected[f"target_{i}"][shot] ^= product[i]
    sim = km.Simulator(batch_size=shots, seed=333)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12)[:, None]
    for name, reg in circuit.register_data.items():
        sim.write_across_shots(reg, ((values[name][None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    for emitted, outputs in ((circuit, expected), (inverse, values)):
        sim.do(emitted)
        for name, reg in circuit.register_data.items():
            np.testing.assert_array_equal(sim.read_across_shots(reg), ((outputs[name][None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
