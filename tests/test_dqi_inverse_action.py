"""Native modular inverse action with a fixed, independently checked degree chart."""

import random
import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.decoder import _add, _divide, _multiply
from qcompile.dqi.field import GF4096
from qcompile.dqi.inverse_action import inverse_action, odd_forney_inplace
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def _inverse_and_chart(modulus, divisor, field):
    a, b = modulus, divisor
    u, v = [0], [1]
    chart = []
    while b != [0]:
        quotient, remainder = _divide(a, b, field)
        a, b = b, remainder
        u, v = v, _add(u, _multiply(quotient, v, field))
        if b != [0]:
            chart.append(len(b) - 1)
    if len(a) != 1 or not a[0]:
        return None
    return [field.div(word, a[0]) for word in u], tuple(chart)


@pytest.mark.official
@pytest.mark.parametrize(("degree", "divisor_degree", "compact", "skip_to_constant", "projective"),
                         [(3, 2, False, False, False), (9, 2, False, False, False), (7, 6, False, False, False),
                          (9, 4, False, True, False), (3, 2, True, False, False), (7, 6, True, False, False),
                          (3, 2, True, False, True), (7, 6, True, False, True),
                          pytest.param(35, 34, True, False, False, marks=pytest.mark.slow),
                          pytest.param(35, 34, True, False, True, marks=pytest.mark.slow)])
def test_euclidean_inverse_action(project_root, monkeypatch, tmp_path, degree, divisor_degree, compact,
                                  skip_to_constant, projective):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native backend required")
    validate_backend(read_json(backend))
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    generator = project_root / "third_party/dqi-scheme42/src/scheme42.py"
    tensor = tmp_path / "scheme42.txt"
    subprocess.run([sys.executable, "-B", str(generator), str(tensor)], check=True)
    multiply, tensor_sha = import_module("dqi_quotient").load_field_product(tensor)

    field, seed = GF4096(), 36131 + degree
    rng = random.Random(seed)
    samples, chart = [], None
    derivative = divisor_degree == degree - 1
    for _ in range(128):
        if derivative:
            modulus = [1]
            for root in rng.sample(range(1, 4096), degree):
                modulus = _multiply(modulus, [root, 1], field)
            divisor = [modulus[i + 1] if i % 2 == 0 else 0 for i in range(degree)]
        elif skip_to_constant:
            divisor = [rng.randrange(4096) for _ in range(divisor_degree)] + [1]
            quotient = [rng.randrange(4096) for _ in range(degree - divisor_degree)] + [1]
            modulus = _add(_multiply(divisor, quotient, field), [rng.randrange(1, 4096)])
        else:
            modulus = [rng.randrange(4096) for _ in range(degree)] + [1]
            divisor = [rng.randrange(4096) for _ in range(divisor_degree)] + [1]
        result = _inverse_and_chart(modulus, divisor, field)
        if result is None:
            continue
        reciprocal, observed_chart = result
        if projective and observed_chart != tuple(range(divisor_degree - 2, -1, -2)):
            continue
        if chart is None:
            chart = observed_chart
        if observed_chart != chart:
            continue
        data = [rng.randrange(4096) for _ in range(degree)]
        expected = _divide(_multiply(reciprocal, data, field), modulus, field)[1]
        expected += [0] * (degree - len(expected))
        samples.append((modulus[:-1], divisor[:-1], data, expected))
        if len(samples) == 12:
            break
    assert chart is not None and len(samples) == 12
    if skip_to_constant:
        assert chart == (0,)
    if compact:
        assert all(value % 2 == 0 for value in chart)
        chart = tuple(value // 2 for value in chart)

    def build(adjoint):
        builder = km.CircuitBuilder()
        a, x = [[builder.create_quantum_register(12, f"{label}_{i}") for i in range(degree)]
                for label in ("a", "x")]
        if compact:
            odd_forney_inplace(builder, a, x, chart, adjoint=adjoint, multiply=multiply, projective=projective)
        else:
            d = [builder.create_quantum_register(12, f"d_{i}") for i in range(divisor_degree)]
            inverse_action(builder, a, d, x, chart, adjoint=adjoint, multiply=multiply)
        return builder.finish_circuit()

    original, expected = {}, {}
    bits = np.arange(12)[:, None]
    for label, field_words in zip(("a", "d", "x", "result"), zip(*samples, strict=True), strict=True):
        for i, value in enumerate(np.asarray(field_words).T):
            matrix = ((value[None, :] >> bits) & 1).astype(bool)
            if label == "result":
                expected[f"x_{i}"] = matrix
            else:
                name = f"{label}_{i}"
                original[name] = matrix
                if label != "x":
                    expected[name] = matrix

    records = {}
    for name, initial, output in (("forward", original, expected), ("inverse", expected, original)):
        circuit = build(adjoint=name == "inverse")
        artifact = tmp_path / f"{name}.kmb"
        circuit.to_file(artifact, format="kmb")
        del circuit
        circuit = km.Circuit.from_file(artifact, format="kmb")
        sim = km.Simulator(batch_size=len(samples), seed=36139, counting_operations=True)
        sim.use_same_registers_as(circuit)
        for register, wires in circuit.register_data.items():
            sim.write_across_shots(wires, initial[register])
        sim.do(circuit)
        for register, wires in circuit.register_data.items():
            np.testing.assert_array_equal(sim.read_across_shots(wires), output[register])
        live = {wire.id for reg in circuit.register_data.values() for wire in reg}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()
        charge = circuit.operation_statistics().num_toffoli_like
        assert sim.operation_statistics().num_toffoli_like == charge * len(samples)
        if degree == 35:
            assert circuit.num_qubits <= 888
        records[name] = {"sha256": sha256(artifact), "qubits": circuit.num_qubits, "toffoli_like": charge}
        del circuit, sim
    write_json(tmp_path / "inverse-action.json", {
        "scope": "implicit derivative" if compact else "supplied monic divisor",
        "degree": degree, "divisor_degree": divisor_degree, "degree_chart": chart,
        "projective": projective,
        "shots": len(samples), "sample_seed": seed, "native_seed": 36139, "backend_sha256": sha256(backend),
        "tensor_sha256": tensor_sha, "observations": records,
    })
