"""Small synthetic, native checks for generalized chemistry ANGLE families."""

import sys
from importlib import import_module
from types import SimpleNamespace

import numpy as np
import pytest

from qcompile.chemistry.loaders import banked_circuit, family, max_batch, rank_complete_cost


@pytest.fixture
def backend(monkeypatch, project_root):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("banked_chemistry").backend()


@pytest.mark.official
@pytest.mark.parametrize("low", [1, 2])
def test_banked_xor_all_addresses_and_padding(backend, low):
    _, km, api, _, _ = backend
    table = np.random.default_rng(93).integers(0, 16, size=(5, 2))
    circuit = banked_circuit(km, api, table, 4, low_bits=low)
    layout = api.register_layout([circuit])
    addresses = np.tile(np.arange(8), 32)
    selection = ((addresses[None] >> np.arange(3)[:, None]) & 1).astype(bool)
    initial = np.random.default_rng(46).integers(0, 16, size=(2, len(addresses)))
    bits = np.arange(4)
    sim = km.Simulator(batch_size=len(addresses), seed=671)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(layout.selection, selection)
    for reg, values in zip(layout.words, initial, strict=True):
        sim.write_across_shots(reg, ((values[None] >> bits[:, None]) & 1).astype(bool))
    padded = np.pad(table, ((0, 3), (0, 0)))
    for expected in (initial ^ padded[addresses].T, initial):
        sim.do(circuit)
        api._check_state(sim, circuit, layout, selection, "banked synthetic fixture")
        actual = np.stack([(1 << bits) @ sim.read_across_shots(reg) for reg in layout.words])
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.official
def test_family_mutations_and_complete_cost_ranking(backend):
    _, km, api, _, verifier = backend
    rng = np.random.default_rng(351)
    words = rng.integers(0, 1 << 4, size=(82, 75), dtype=np.int64)
    inputs = SimpleNamespace(num_orbitals=76, w=np.empty((2, 3, 2)))
    candidates = []
    for batch in range(3, min(75, max_batch(82, 4, 3)) + 1):
        circuits = family(km, api, words, 4, batch, 3)
        actual, _, toffoli = api.recover_words_from_circuits(
            circuits, num_vectors=82, num_angles=75, shots_per_address=2, seed=74
        )
        np.testing.assert_array_equal(actual, words)
        candidates.append((batch, circuits, toffoli))
    ranked = rank_complete_cost(verifier, inputs, candidates, 4, 48.0)
    assert [row["modeled_cost"] for row in ranked] == sorted(row["modeled_cost"] for row in ranked)
    for item in ranked:
        resources = item["resources"]
        assert item["modeled_cost"] == pytest.approx(48.0 * resources["toffoli"] * resources["qubits"])
    first_batch, first_circuits, first_toffoli = candidates[0]
    with pytest.raises(ValueError, match="declared shape"):
        rank_complete_cost(verifier, inputs, [(first_batch + 1, first_circuits, first_toffoli)], 4, 48.0)
    mutant = words.copy()
    mutant[31, 2] ^= 1
    circuits = family(km, api, mutant, 4, 5, 3)
    actual, _, _ = api.recover_words_from_circuits(circuits, num_vectors=82, num_angles=75,
                                                    shots_per_address=2, seed=74)
    assert not np.array_equal(actual, words)
    circuits = family(km, api, words, 4, 5, 3)
    circuits[0], circuits[1] = circuits[1], circuits[0]
    try:
        actual, _, _ = api.recover_words_from_circuits(circuits, num_vectors=82, num_angles=75,
                                                        shots_per_address=2, seed=74)
    except api.InvalidCircuits:
        pass
    else:
        assert not np.array_equal(actual, words)


@pytest.mark.official
def test_reject_width_before_emission(backend):
    _, km, api, _, _ = backend
    with pytest.raises(ValueError, match="128-qubit"):
        banked_circuit(km, api, np.zeros((5, 40), dtype=np.int64), 4, low_bits=1)
