"""Native sibling lookup, randomized phase repair, and a dropped-CX control."""

from importlib import import_module

import numpy as np
import pytest

from qcompile.invsqrt.direct import _load_table
from qcompile.invsqrt.unlookup import unlookup


def bits(words, width):
    return ((words[None, :] >> np.arange(width)[:, None]) & 1).astype(bool)


@pytest.mark.official
@pytest.mark.parametrize("repair,shared,mutation", [
    (False, False, False), (False, True, False), (False, True, True),
    (True, False, False), (True, True, False),
])
def test_lookup_siblings_all_addresses(project_root, monkeypatch, repair, shared, mutation):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km, _, _ = import_module("invsqrt_direct").backend()
    rng = np.random.default_rng(2026110804)
    addresses = np.arange(512, dtype=np.uint16)
    table = rng.integers(0, 128, size=(384, 2), dtype=np.uint16)
    payload = np.zeros((512, 2), dtype=np.uint16)
    payload[128:] = table
    values = payload if repair else rng.integers(1, 128, size=(512, 2), dtype=np.uint16)
    expected = np.zeros_like(values) if repair else values ^ payload
    rows = tuple(tuple(int(word) for word in row) for row in table)

    class DropFirstCX:
        def __init__(self, inner):
            self.inner = inner
            self.dropped = False

        def cx(self, *args, **kwargs):
            if self.dropped:
                self.inner.cx(*args, **kwargs)
            self.dropped = True

        def __getattr__(self, name):
            return getattr(self.inner, name)

    builder = km.CircuitBuilder()
    address = builder.create_quantum_register(9, "address")
    words = [builder.create_quantum_register(7, f"word_{i}") for i in range(2)]
    if repair:
        unlookup(builder, address, words, rows, sibling_cnot=shared)
    else:
        path = builder.alloc_qubits(8)
        emitter = DropFirstCX(builder) if mutation else builder
        _load_table(emitter, address, path, words, rows, sibling_cnot=shared)
    circuit = builder.finish_circuit()
    live = {q.id for register in circuit.register_data.values() for q in register}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    for seed in ((7, 97, 299, 701) if repair else (7,)):
        sim = km.Simulator(batch_size=512, seed=seed)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(address, bits(addresses, 9))
        for i, word in enumerate(words):
            sim.write_across_shots(word, bits(values[:, i], 7))
        sim.do(circuit)
        np.testing.assert_array_equal(sim.read_across_shots(address), bits(addresses, 9))
        failed = (any(not np.array_equal(sim.read_across_shots(word), bits(expected[:, i], 7))
                      for i, word in enumerate(words))
                  or bool(sim.read_phase_flipped_across_shots().any())
                  or bool(len(scratch) and sim.read_across_shots(scratch).any()))
        assert failed == mutation
