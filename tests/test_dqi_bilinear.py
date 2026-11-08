"""Measurement-based product erasure and an omitted-CZ mutation."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.bilinear import erase_product, product_tensor
from qcompile.dqi.field import GF4096
from qcompile.dqi.tower import multiply_xor


def test_product_tensor_basis_and_masks():
    field = GF4096()
    tensor = product_tensor()
    rng = np.random.default_rng(820)
    for i in range(12):
        for j in range(12):
            assert tensor[i][j] == field.mul(1 << i, 1 << j)
            for mask in (1, 4095, int(rng.integers(4096))):
                assert (tensor[i][j] & mask).bit_count() % 2 == (
                    field.mul(1 << i, 1 << j) & mask
                ).bit_count() % 2


@pytest.mark.official
@pytest.mark.parametrize("drop_cz", [False, True])
def test_native_product_erasure_phase_and_mutation(project_root, monkeypatch, drop_cz):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    left = builder.create_quantum_register(12, "left")
    right = builder.create_quantum_register(12, "right")
    product = builder.create_quantum_register(12, "product")
    multiply_xor(builder, left, right, product)

    class Mutation:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.dropped = False

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def cz(self, a, b):
            if drop_cz and not self.dropped:
                self.dropped = True
            else:
                self.wrapped.cz(a, b)

    erase_product(Mutation(builder), left, right, product)
    circuit = builder.finish_circuit()
    assert circuit.operation_statistics().num_toffoli_like == 54
    shots = 528
    sim = km.Simulator(batch_size=shots, seed=320)
    sim.use_same_registers_as(circuit)
    # Repeat the first basis pair to detect a missing random-outcome fix-up,
    # then exercise every basis pair and dense random words.
    rng = np.random.default_rng(821)
    left_words = np.ones(shots, dtype=np.int64)
    right_words = np.ones(shots, dtype=np.int64)
    for i in range(12):
        for j in range(12):
            index = 256 + 12 * i + j
            left_words[index], right_words[index] = 1 << i, 1 << j
    left_words[400:] = rng.integers(0, 4096, size=128)
    right_words[400:] = rng.integers(0, 4096, size=128)
    bits = np.arange(12)[:, None]
    left_values = (left_words[None, :] >> bits) & 1 == 1
    right_values = (right_words[None, :] >> bits) & 1 == 1
    sim.write_across_shots(left, left_values)
    sim.write_across_shots(right, right_values)
    sim.do(circuit)
    assert np.array_equal(sim.read_across_shots(left), left_values)
    assert np.array_equal(sim.read_across_shots(right), right_values)
    assert not sim.read_across_shots(product).any()
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    assert not len(scratch) or not sim.read_across_shots(scratch).any()
    phases = sim.read_phase_flipped_across_shots()
    assert bool(phases.any()) == drop_cz
