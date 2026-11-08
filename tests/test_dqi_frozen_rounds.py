"""Compare native circular rounds with the frozen four-case fixture."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.bm_full_round import full_round
from qcompile.io import read_json, sha256


@pytest.fixture
def pinned(project_root, monkeypatch):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    fixture = project_root / "tests/fixtures/dqi_round_states.json"
    return backend, fixture


@pytest.mark.official
def test_frozen_round_fixture_reproduces(pinned, tmp_path):
    backend, fixture = pinned
    data = read_json(fixture)
    if sha256(backend) != data["backend_sha256"]:
        pytest.skip("fixture byte replay requires its registered backend inventory")
    recomputed = tmp_path / "dqi_round_states.json"
    import_module("dqi_round_states").freeze(backend, recomputed, data["seed"])
    assert recomputed.read_bytes() == fixture.read_bytes()


@pytest.mark.official
@pytest.mark.parametrize("width", [3, 12, 36])
def test_native_forward_and_reverse_match_frozen_rounds(pinned, width):
    backend, fixture = pinned
    _, km, _, _ = import_module("dqi_history_depth").runtime(backend)
    rows = [row for row in read_json(fixture)["synthetic"] if row["active_width"] == width]
    assert len(rows) == 4
    r = rows[0]["r"]

    def build(adjoint):
        builder = km.CircuitBuilder()
        sigma = [builder.create_quantum_register(12, f"sigma_{i}") for i in range(36)]
        template = [builder.create_quantum_register(12, f"template_{i}") for i in range(36)]
        syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
        counter = builder.create_quantum_register(8, "counter")
        branch = builder.create_quantum_register(1, "branch")[0]
        history = builder.create_quantum_register(12, "history")
        full_round(builder, sigma, template, syndromes, r, counter, branch, history, adjoint=adjoint)
        return builder.finish_circuit()

    def values(row, state):
        result = {f"S{i}": value for i, value in enumerate(row["syndromes"])}
        result.update({f"{name}_{i}": value for name in ("sigma", "template")
                       for i, value in enumerate(row[state][name])})
        result.update(counter=row[state]["counter"] % 256, branch=0, history=0)
        if state == "advanced":
            result.update(branch=int(row["history"]["replace"]), history=row["history"]["retained_discrepancy"])
        return result

    forward, reverse = build(False), build(True)
    sim = km.Simulator(batch_size=4, seed=9201)
    sim.use_same_registers_as(forward)
    live = {q.id for register in forward.register_data.values() for q in register}
    scratch = km.array([km.q(i) for i in range(forward.num_qubits) if i not in live])
    for state in ("initial", "advanced", "reversed"):
        expected = [values(row, state) for row in rows]
        if state != "initial":
            sim.do(forward if state == "advanced" else reverse)
        for name, register in forward.register_data.items():
            words = np.asarray([row[name] for row in expected])
            bits = (words[None, :] >> np.arange(len(register))[:, None]) & 1 == 1
            if state == "initial":
                sim.write_across_shots(register, bits)
            else:
                np.testing.assert_array_equal(sim.read_across_shots(register), bits)
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()
