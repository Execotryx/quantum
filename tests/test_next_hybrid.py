"""Regression coverage for shape-derived counters and the new native lanes."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.refit import encode_vectors
from qcompile.chemistry.representation import canonical_signs, reconstruct
from qcompile.chemistry.schema import read_factorization
from qcompile.component_confirmations import candidate_coverage, has_full_hybrid_coverage
from qcompile.dqi.field import GF4096
from qcompile.dqi.reversible import phase_for_position
from qcompile.errors import ValidationError


def test_changed_shape_and_actual_coverage(tmp_path):
    path = tmp_path / "submission.npz"
    deterministic_npz(path, {
        "U": np.zeros((2, 3, 76)), "W": np.zeros((2, 3, 4)), "H2_I": np.zeros((2, 4)),
        "H1_I": np.array(0.0), "Hsym_lower": np.zeros(2926), "tree_edges": np.zeros((75, 2), dtype=int),
        "angle_words": np.zeros((82, 75), dtype=int),
    })
    with pytest.raises(ValidationError, match="unexpected members"):
        read_factorization(path)
    expected = candidate_coverage({"dfthcsos/submission.npz": {"path": str(path)}})
    assert expected == {"invsqrt": 200_540_928, "dqi": 102_400, "dfthcsos": 5_248}
    observed = {
        "coverage_counts": {name: {"expected": n, "completed": n} for name, n in expected.items()},
        "raw_verifier_results": {name: {"status": "PASS", "verified_shots": n} for name, n in expected.items()},
    }
    assert has_full_hybrid_coverage({"official_results": observed}, expected)
    observed["raw_verifier_results"]["dfthcsos"]["verified_shots"] -= 64
    assert not has_full_hybrid_coverage({"official_results": observed}, expected)


def test_vector_encoding_reverses_a_branching_tree():
    edges = np.array([[0, 1], [1, 2], [0, 3], [1, 4]], dtype=np.int64)
    vectors = np.random.default_rng(213).normal(size=(20, 5))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    words = encode_vectors(vectors, edges, 20)
    actual = np.stack([reconstruct(row, 20, edges, 5, 0, radians_per_unit=np.pi) for row in words])
    np.testing.assert_allclose(actual, canonical_signs(vectors), atol=1.2e-5, rtol=0)


@pytest.fixture
def native_tools(monkeypatch, project_root):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    chemistry = import_module("banked_chemistry")
    return chemistry, chemistry.backend(), project_root


@pytest.mark.official
@pytest.mark.parametrize("low", [1, 2])
def test_generic_angle_exact_xor_including_padding(native_tools, low):
    tool, (_, km, api, _, _), _ = native_tools
    table = np.arange(10).reshape(5, 2) ^ 3
    circuit = tool.banked_circuit(km, api, table, 4, low_bits=low)
    layout = api.register_layout([circuit])
    addresses = np.tile(np.arange(8), 8)
    selection = ((addresses[None, :] >> np.arange(3)[:, None]) & 1).astype(bool)
    initial = np.random.default_rng(79).integers(0, 16, size=(2, len(addresses)))
    bits = np.arange(4)
    sim = km.Simulator(batch_size=len(addresses), seed=11)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(layout.selection, selection)
    for reg, words in zip(layout.words, initial, strict=True):
        sim.write_across_shots(reg, ((words[None, :] >> bits[:, None]) & 1).astype(bool))
    padded = np.pad(table, ((0, 3), (0, 0)))
    for expected in (initial ^ padded[addresses].T, initial):
        sim.do(circuit)
        api._check_state(sim, circuit, layout, selection, "generic padding fixture")
        actual = np.stack([(1 << bits) @ sim.read_across_shots(reg) for reg in layout.words])
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.official
@pytest.mark.parametrize("kind", ["multiply", "tower-multiply", "inverse", "phase", "eea", "bm"])
def test_native_dqi_prototype(native_tools, tmp_path, kind):
    _, (_, km, _, _, _), project_root = native_tools
    tool = import_module("dqi_prototype")
    backend = project_root / "vendor/backend.json"
    tool.build(kind, backend, tmp_path / "forward")
    circuit = km.Circuit.from_file(str(tmp_path / "forward" / f"{kind}.kmb"))
    registers = circuit.register_data
    sim = km.Simulator(batch_size=64, seed=17)
    rng = np.random.default_rng(51)
    values = {name: rng.integers(0, 1 << len(reg), size=64) for name, reg in registers.items()}
    values["source"][0] = 0
    if kind == "phase":
        values["denominator"][0] = 0
        values["located"][0] = 1
    if kind == "bm":
        for name in values:
            if name.startswith("saved_"):
                values[name].fill(0)
    def initialize():
        sim.use_same_registers_as(circuit)
        for name, reg in registers.items():
            bits = np.arange(len(reg))
            sim.write_across_shots(reg, ((values[name][None, :] >> bits[:, None]) & 1).astype(bool))

    initialize()
    expected = {name: value.copy() for name, value in values.items()}
    field = GF4096()
    parity = np.zeros(64, dtype=bool)
    for j in range(64):
        source = int(values["source"][j])
        if kind in ("multiply", "tower-multiply"):
            expected["target"][j] ^= field.mul(source, int(values["right"][j]))
        elif kind == "inverse":
            expected["target"][j] ^= field.inv(source) if source else 0
        elif kind == "phase":
            denominator = int(values["denominator"][j])
            if denominator and values["located"][j]:
                parity[j] = (field.div(source, denominator) & int(values["mask"][j])).bit_count() % 2
        else:
            for i in range(1, 4):
                expected[f"current_{i}"][j] ^= field.mul(source, int(values[f"previous_{i-1}"][j]))
            if values["branch"][j]:
                for i in range(4):
                    current, previous = f"current_{i}", f"previous_{i}"
                    if kind == "eea":
                        expected[current][j], expected[previous][j] = expected[previous][j], expected[current][j]
                    else:
                        expected[f"saved_{i}"][j] = values[previous][j]
                        expected[previous][j] = values[current][j]

    def check_outputs(outputs, phases):
        for name, reg in registers.items():
            np.testing.assert_array_equal((1 << np.arange(len(reg))) @ sim.read_across_shots(reg), outputs[name])
        np.testing.assert_array_equal(sim.read_phase_flipped_across_shots(), phases)
        live = {q.id for reg in registers.values() for q in reg if isinstance(q, km.q)}
        scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
        assert not len(scratch) or not sim.read_across_shots(scratch).any()

    sim.do(circuit)
    check_outputs(expected, parity)
    if kind in ("eea", "bm"):
        tool.build(kind, backend, tmp_path / "reverse", adjoint=True)
        circuit = km.Circuit.from_file(str(tmp_path / "reverse" / f"{kind}.kmb"))
    elif kind == "phase":
        # Compose both kernels inside one simulation call to observe their net phase.
        builder = km.CircuitBuilder()
        source = builder.create_quantum_register(12, "source")
        denominator = builder.create_quantum_register(12, "denominator")
        located = builder.create_quantum_register(1, "located")[0]
        mask = builder.create_classical_register(12, "mask")
        native_field = km.GF2Field(12)
        for _ in range(2):
            phase_for_position(builder, native_field, located, source, denominator, mask)
        circuit = builder.finish_circuit()
        registers = circuit.register_data
        sim.clear_for_shot()
        initialize()
    sim.do(circuit)
    check_outputs(values, np.zeros(64, dtype=bool))
