from functools import partial
from importlib import import_module

import numpy as np
import pytest

from qcompile.invsqrt.direct import DirectFormat
from qcompile.invsqrt.direct_screen import beta_one_targets, scan_phase
from qcompile.invsqrt.two_octave import normalized_indices, phase64, search_table, two_octave_table
from qcompile.invsqrt.two_octave_mapping import permute_address


def test_two_octave_exact_integer_recurrence_on_small_domain():
    fmt = DirectFormat(3, 2, (13, 9, 5))
    table = two_octave_table(fmt)
    xs = np.arange(1, 148, dtype=np.int64)
    _, _, indices = normalized_indices(fmt, xs)
    assert len(table) == 8
    assert set(indices.tolist()) == set(range(8))
    expected = []
    for x in xs.tolist():
        exponent = max(k for k in range(4) if 4**k <= x)
        left = 3 - exponent
        value_x = x << (2 * left)
        upper = value_x >= 128
        low_width = 4 + upper
        index = (value_x >> low_width) - 4 + 4 * upper
        row = table[index]
        value = row[-1]
        for j in (1, 0):
            product = 0
            for bit in range(low_width):
                shift = fmt.fractional[j] - fmt.fractional[j + 1] + bit - 6
                term = value << shift if shift >= 0 else value >> -shift
                product += ((value_x >> bit) & 1) * (term & ((1 << fmt.widths[j]) - 1))
            value = row[j] - product
        expected.append(((value << left) << (64 - fmt.output_fractional)) % (1 << 64))
    assert np.array_equal(phase64(fmt, table, xs), np.asarray(expected, dtype=np.uint64))


def test_two_octave_lattice_search_cannot_increase_small_domain_worst_error():
    fmt = DirectFormat(3, 2, (13, 9, 5))
    table = two_octave_table(fmt)
    identity, offsets = search_table(fmt, table, 147, beta_one_targets, radius=0)
    assert identity == table
    assert all(offset == (0, 0, 0) for offset in offsets)
    searched, _ = search_table(fmt, table, 147, beta_one_targets, radius=1)
    before = scan_phase(partial(phase64, fmt, table), 147)
    after = scan_phase(partial(phase64, fmt, searched), 147)
    assert after["worst_tolerance_fraction"] <= before["worst_tolerance_fraction"]


@pytest.mark.official
@pytest.mark.parametrize("restore", [False, True])
def test_address_mapping_all_basis_inputs(project_root, monkeypatch, restore):
    monkeypatch.syspath_prepend(str(project_root / "vendor/official/kickmix"))
    km = import_module("kickmix")
    builder = km.CircuitBuilder()
    x = builder.create_quantum_register(8, "x")
    permute_address(builder, x, 2)
    if restore:
        permute_address(builder, x, 2, inverse=True)
    circuit = builder.finish_circuit()
    values = np.arange(256, dtype=np.int64)
    bits = np.arange(8)[:, None]
    sim = km.Simulator(batch_size=256, seed=930)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(x, (values[None, :] >> bits) & 1 == 1)
    sim.do(circuit)
    result = (sim.read_across_shots(x).astype(np.int64) * (1 << bits)).sum(axis=0)
    if restore:
        assert np.array_equal(result, values)
    else:
        lower = 4
        selected = (result >> lower) & 3
        upper = (values >> 7) & 1
        assert np.array_equal(selected, np.where(upper, (values >> 5) & 3, (values >> 4) & 3))
        assert np.array_equal((result >> 6) & 1, np.where(upper, (values >> 4) & 1, (values >> 6) & 1))
    assert not sim.read_phase_flipped_across_shots().any()
