"""Exercise the next-round kernels through their native and classical entry points."""

from functools import partial
from importlib import import_module
from math import ceil

import numpy as np
import pytest

from qcompile.chemistry.factorization import factor_rows, fit_alternating, svec
from qcompile.dqi.bm_circular import WIDTH, CircularState, reverse_circular, step_circular
from qcompile.dqi.bm_routed import State, step
from qcompile.dqi.decoder import syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.routed_decoder import routed_decoder
from qcompile.invsqrt.direct import phase64
from qcompile.invsqrt.trimmed import TrimmedFormat, build_circuit
from qcompile.io import identity, read_json, write_json


def test_circular_round_matches_linear_recurrence_and_reverses():
    rng = np.random.default_rng(9201)
    field = GF4096()
    initial = CircularState((1,) + (0,) * 35, (1,) + (0,) * 35, 0)
    for weight in range(36):
        positions = rng.choice(4095, weight, replace=False).tolist()
        symbols = rng.integers(1, 4096, weight).tolist()
        sequence = syndrome(dict(zip(positions, symbols, strict=True)), field)
        state = initial
        linear = State((1,), (1,), 0)
        for r in range(1, 71):
            after, history = step_circular(state, sequence, r, field)
            linear, expected_history = step(linear, sequence, r - 1, field)
            assert history == expected_history
            assert after.sigma == linear.sigma + (0,) * (WIDTH - len(linear.sigma))
            assert after.counter == linear.counter
            assert reverse_circular(after, history, sequence, r, field) == state
            state = after


def test_alternating_projection_retains_an_exact_checkpoint():
    rng = np.random.default_rng(3819)
    vectors = rng.normal(size=(2, 4, 8))
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    weights = rng.normal(size=(2, 4, 3))
    features = svec(vectors[..., :, None] * vectors[..., None, :])
    rows = factor_rows(features, weights)
    result = fit_alternating(rows.T @ rows, vectors, weights, 6, 2)
    assert result.residual < 1e-8
    assert [entry["sweep"] for entry in result.trace] == [0, 2, 4, 6]


def test_history_chunk_receipt_binds_contents(project_root, monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    read_chunk = import_module("dqi_history_depth").read_chunk
    path = tmp_path / "chunk-000.json"
    record = {"registration_sha256": "registered", "chunk": 0, "seed": 9201, "status": "complete"}
    write_json(path, {**record, "content_sha256": identity(record)})
    assert read_chunk(path, "registered", 0, 9201) == record
    with pytest.raises(ValueError, match="chunk identity"):
        read_chunk(path, "registered", 0, 9202)


@pytest.mark.official
def test_s2_settings_accept_the_pinned_reference_npz(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("chem_s2_settings")
    if not tool.REFERENCE.is_file():
        pytest.skip("reference chemistry factorization unavailable")
    settings = tool.settings_record(tool.REFERENCE)
    assert settings["reference_offsets"]["reference"]["sha256"] == tool.REFERENCE_HASH
    assert settings["limits"]["offset_bound"] == max(1.0, ceil(4 * settings["reference_offsets"]["m_ref"]) / 2)
    assert settings["limits"]["penalty"] == 1.0


@pytest.mark.official
def test_sibling_lookup_preserves_native_phase(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    km, primitives, api = tool.backend()
    receipt = read_json(project_root / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json")
    table = tuple(tuple(row) for row in receipt["coefficients"])
    fmt = TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True, sibling_cnot=True)
    circuit = build_circuit(km, primitives, fmt, table)
    spec = api.ProblemSpecInvSqrt.for_n_p(10)
    tool.native_smoke(km, api, circuit, spec, partial(phase64, fmt, table),
                      [1, 2, 3, 4, 15, 16, 940030, 2416632, spec.max_x],
                      {"seed": 9201, "repeat": 8, "batch": 64})


@pytest.mark.official
def test_reduced_routed_decoder_through_verifier(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    runtime = import_module("dqi_history_depth").runtime
    _, km, api, field = runtime(project_root / "vendor/backend.json")
    m, n = 63, 4
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(n)]
    masks = [builder.create_classical_register(12, f"E{i}") for i in range(m)]
    routed_decoder(builder, field, syndromes, masks, depth=3)
    circuit = builder.finish_circuit()
    spec = api.ProblemSpecDQI.benchmark_instance(m=m, n=n, degree=12, num_shots=256)
    result = api.verify(circuit, spec, seed=9201, batch_size=64, log2_delta=-8, max_workers=1)
    assert result["verified_shots"] == 256
    assert result["value_errors"] == result["phase_errors"] == 0
