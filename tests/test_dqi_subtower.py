"""Exhaustive native inverse through the GF(8) subtower."""

import sys
from importlib import import_module

import numpy as np
import pytest

from qcompile.dqi.field import GF4096
from qcompile.dqi.subtower import erase_bilinear, subtower
from qcompile.dqi.tower import _product_xor, linear, tower
from qcompile.reference import field as polynomial


def test_subtower_product_basis():
    maps = subtower()
    field = GF4096()
    generator = field.exp[585]
    basis = (1, generator, field.mul(generator, generator))
    for a in range(8):
        for b in range(8):
            product = 0
            for left, right, out in maps.product8:
                if (a & left).bit_count() & (b & right).bit_count() & 1:
                    product ^= out
            assert linear(basis, product) == field.mul(linear(basis, a), linear(basis, b))
    assert len(set(linear(tower().basis[:6], i) for i in range(64))) == 64


@pytest.mark.official
@pytest.mark.parametrize("width", [3, 6])
@pytest.mark.parametrize("mutation", [False, True])
def test_subtower_product_erasure_native(project_root, monkeypatch, width, mutation):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    left = builder.create_quantum_register(width, "left")
    right = builder.create_quantum_register(width, "right")
    target = builder.create_quantum_register(width, "target")
    terms = subtower().product8 if width == 3 else tower().subfield_terms
    _product_xor(builder, left, right, target, terms)

    class DropCZ:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.dropped = False

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def cz(self, a, b):
            if mutation and not self.dropped:
                self.dropped = True
            else:
                self.wrapped.cz(a, b)

    erase_bilinear(DropCZ(builder), left, right, target, terms)
    circuit = builder.finish_circuit()
    # Repeat all pairs so the three-bit case also samples multiple outcomes.
    shots = 4096
    values = np.arange(shots, dtype=np.int64)
    left_words = values % (1 << width)
    right_words = (values // (1 << width)) % (1 << width)
    bits = np.arange(width)[:, None]
    sim = km.Simulator(batch_size=shots, seed=91)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(left, ((left_words[None, :] >> bits) & 1).astype(bool))
    sim.write_across_shots(right, ((right_words[None, :] >> bits) & 1).astype(bool))
    sim.do(circuit)
    assert not sim.read_across_shots(target).any()
    assert bool(sim.read_phase_flipped_across_shots().any()) == mutation


@pytest.mark.official
def test_native_subtower_inverse_exhaustive(project_root, monkeypatch, tmp_path):
    if not sys.platform.startswith("linux") or not (project_root / "vendor/backend.json").is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    km = import_module("kickmix")
    tool = import_module("dqi_prototype")
    tool.build("subtower-inverse", project_root / "vendor/backend.json", tmp_path / "inverse")
    circuit = km.Circuit.from_file(str(tmp_path / "inverse" / "subtower-inverse.kmb"))
    assert circuit.operation_statistics().num_toffoli_like <= 110
    source = circuit.register_data["source"]
    target = circuit.register_data["target"]
    shots = 4096
    values = np.arange(shots, dtype=np.int64)
    rng = np.random.default_rng(9105)
    target_values = rng.integers(0, 4096, size=shots)
    expected = target_values ^ np.array([0] + [polynomial.inverse(int(v)) for v in values[1:]])
    bits = np.arange(12)[:, None]
    sim = km.Simulator(batch_size=shots, seed=1705)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(source, ((values[None, :] >> bits) & 1).astype(bool))
    sim.write_across_shots(target, ((target_values[None, :] >> bits) & 1).astype(bool))
    live = {q.id for reg in circuit.register_data.values() for q in reg if isinstance(q, km.q)}
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    for output in (expected, target_values):
        sim.do(circuit)
        np.testing.assert_array_equal(sim.read_across_shots(source), ((values[None, :] >> bits) & 1))
        np.testing.assert_array_equal(sim.read_across_shots(target), ((output[None, :] >> bits) & 1))
        assert not sim.read_phase_flipped_across_shots().any()
        assert not len(scratch) or not sim.read_across_shots(scratch).any()
