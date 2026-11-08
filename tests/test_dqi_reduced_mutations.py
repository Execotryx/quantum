"""Exercise reduced native decoding at every weight and reject deliberate defects."""

from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.bm_routed import forward
from qcompile.dqi.decoder import syndrome
from qcompile.dqi.field import GF4096


@pytest.mark.official
@pytest.mark.parametrize("m,n,mutation", [(63, 4, None), (127, 12, None), *[
    (127, 12, name) for name in ("branch", "tag", "history", "mask")
]])
def test_reduced_routed_coverage_and_mutations(project_root, monkeypatch, m, n, mutation):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    runtime = import_module("dqi_history_depth").runtime
    _, km, api, native_field = runtime(project_root / "vendor/backend.json")
    routed = import_module("qcompile.dqi.routed_decoder")
    field = GF4096()
    rng = np.random.default_rng(2026110803)
    count = 256
    states = np.empty((count, n), dtype=np.int64)
    mask_words = rng.integers(0, 4096, size=(count, m))
    phases = np.empty(count, dtype=bool)
    for i, masks in enumerate(mask_words):
        if mutation is not None:
            value = int(rng.integers(1, 4096))
            # Cancel S1 so the next replace makes the signed counter negative.
            errors = {0: field.mul(value, 2), 1: value}
        else:
            weight = i % (n // 2 + 1)
            positions = rng.choice(m, size=weight, replace=False).tolist()
            symbols = rng.integers(1, 4096, size=weight).tolist()
            errors = dict(zip(positions, symbols, strict=True))
        row = syndrome(errors, field, count=n)
        if mutation in ("tag", "history"):
            assert any(entry.retained_discrepancy for entry in forward(row, field)[1])
        states[i] = row
        phases[i] = bool(sum((symbol & int(masks[position])).bit_count()
                             for position, symbol in errors.items()) & 1)

    if mutation == "branch":
        original = routed.full_round

        def flip_branch(builder, locator, template, syndromes, r, counter, branch, history, *, adjoint=False):
            if adjoint and r == 1:
                builder.x(branch)
            original(builder, locator, template, syndromes, r, counter, branch, history, adjoint=adjoint)

        monkeypatch.setattr(routed, "full_round", flip_branch)
    elif mutation in ("tag", "history"):
        original_stack = routed.HistoryStack

        class FaultyStack(original_stack):
            def push(self, builder, r):
                if mutation == "tag":
                    super().push(builder, r + 1)

        monkeypatch.setattr(routed, "HistoryStack", FaultyStack)

    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(n)]
    masks = [builder.create_classical_register(12, f"E{i}") for i in range(m)]
    if mutation == "mask":
        masks[0], masks[1] = masks[1], masks[0]
    routed.routed_decoder(builder, native_field, syndromes, masks, depth=3)
    circuit = builder.finish_circuit()
    spec = api.ProblemSpecDQI.benchmark_instance(m=m, n=n, degree=12, num_shots=count)
    try:
        result = api.verify(circuit, spec, seed=9201, shots=(states, mask_words, phases), batch_size=64,
                            log2_delta=-8, max_workers=1)
    except AssertionError as error:
        if mutation is None or "Effective error rate" not in str(error):
            raise
    else:
        errors_found = result["value_errors"] + result["phase_errors"]
        assert result["verified_shots"] == count
        assert (errors_found > 0) == (mutation is not None)
