import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product
from random import Random
from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest

from qcompile.dqi.decoder import _add, _divide, _multiply, _trim, decode, syndrome
from qcompile.dqi.double_node_pole import (
    forward_local_pole_jet,
    join_local_pole,
    matches_dqi_rational,
    recover_quadratic_tail,
    reverse_local_pole_jet,
    split_local_pole,
    synthesize_pair,
)
from qcompile.dqi.field import GF4096
from qcompile.io import read_json
from qcompile.vendored.dqi_d4 import (
    local_pole_jet,
    paired_external_jet,
    paired_polynomial_synthesis,
    paired_residue_scan,
    xor_regular_tail_coefficients,
    xor_tail_system_solution,
)
from qcompile.vendored.dqi_d4_compact import (
    absorb_compact_pair,
    absorb_incoming_regular_pair,
    absorb_local_pole,
    absorb_projected_outer,
    affine_denominator_banks,
    affine_denominator_jet,
    compact_pair_jet,
    compact_tail_jet,
    escape_normalized_affine_chart,
    extract_compact_heads,
    replay_aligned_chart,
    xor_aligned_history_overflow,
    xor_incoming_degree_certificate,
    xor_monic_basis_coordinates,
    xor_terminated_compact_tail,
    xor_unit_tail_certificate,
    xor_unit_tail_degree31_certificate,
    xor_unit_tail_degree_certificate,
    xor_unit_tail_preshear,
)
from qcompile.vendored.dqi_d4_degree import odd_monic_conversion, projected_monic_scan
from qcompile.vendored.dqi_d4_leading import xor_leading_factor
from qcompile.vendored.dqi_d4_mixed import _with_solution
from qcompile.vendored.dqi_d4_shared import _xor_tail_seed, emit_shared_projected_d4
from qcompile.vendored.dqi_d4_validation import quotient_columns, xor_invalid_rational, xor_quotient
from qcompile.vendored.dqi_open_padding import exchange_padding, selected_padding


def test_genuine_local_pole_and_termination_have_separate_transfers():
    field = GF4096()
    head, denominator, residual = [1, 3], [3, 2], [5, 4, 3]
    numerator, _ = join_local_pole(denominator, residual, head, 2048, field)
    assert split_local_pole(numerator, denominator, head, 2048, field) == (denominator, residual)
    terminated, _ = join_local_pole(denominator, [0], head, 2048, field)
    with pytest.raises(ValueError, match="terminates"):
        split_local_pole(terminated, denominator, head, 2048, field)


def test_local_pole_jet_round_trip_even_when_next_denominator_is_zero():
    field = GF4096()
    head, slope, factor, denominator = 85, 12, 19, 33
    state = (field.mul(head, denominator), denominator, 71)
    forwarded = forward_local_pole_jet(state, head, slope, factor, field)
    assert forwarded[1] == 0 and forwarded[0] != 0
    assert reverse_local_pole_jet(forwarded, head, slope, factor, field) == state


@pytest.mark.official
def test_native_leading_factor_xor_supports_both_charts(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_compact_constraints")
    builder = km.CircuitBuilder()
    sources = [{p: builder.alloc_qubits(12) for p in range(4, 9)} for _ in range(2)]
    targets = [{p: builder.alloc_qubits(12) for p in powers} for powers in ((7, 8, 10), (8, 9, 11))]
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    charts = builder.alloc_qubits(2)
    kappa = 2053
    xor_leading_factor(builder, reference, heads, sources, targets, kappa, charts[1], charts[0])
    forward = builder.finish_circuit()
    builder.cz(targets[0][7][0], targets[1][9][1])
    xor_leading_factor(builder, reference, heads, sources, targets, kappa, charts[1], charts[0])
    closed = builder.finish_circuit()

    rng = np.random.default_rng(4431)
    states = rng.integers(0, 4096, size=(64, 20))
    incoming = np.arange(64) % 2 == 0
    collapse = np.arange(64) % 4 >= 2
    states[collapse, -2:] = 0
    expected = []
    for row, exchange, local in zip(states, incoming, collapse, strict=True):
        a, b, u, v, h0, h1 = [list(map(int, row[start:end])) for start, end in
                              ((0, 5), (5, 10), (10, 13), (13, 16), (16, 18), (18, 20))]
        fold = layout.Fold(h0, h1, [0], [0], kappa, bool(exchange), bool(local))
        n, d = oracle.extend_map([([0] * 4 + a, [0] * 4 + b)], fold, field)[0]
        expected.append([value ^ layout.coefficient(poly, power)
                         for values, poly, bank in ((u, n, targets[0]), (v, d, targets[1]))
                         for value, power in zip(values, bank, strict=True)])
    expected = np.asarray(expected)
    wires = reference.combine([word for bank in sources + targets for word in bank.values()] + heads[0] + heads[1])
    outputs = reference.combine([word for bank in targets for word in bank.values()])
    chart_wires = km.array(charts)
    chart_bits = np.stack((incoming, collapse))
    initial = api.to_bits(states, 12)
    with_outputs = states.copy()
    with_outputs[:, 10:16] = expected
    phase = (expected[:, 0] & (expected[:, 4] >> 1)) & 1
    for seed in (981, 982):
        for circuit, wanted, expected_phase in (
            (forward, api.to_bits(with_outputs, 12), np.zeros(64)), (closed, initial, phase),
        ):
            sim = km.Simulator(batch_size=64, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, initial)
            sim.write_across_shots(chart_wires, chart_bits)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(wires), wanted)
            assert np.array_equal(sim.read_across_shots(chart_wires), chart_bits)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), expected_phase)
            if circuit is forward:
                assert np.array_equal(sim.read_across_shots(outputs), api.to_bits(expected, 12))
            scratch = km.array([km.q(i) for i in range(242, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
@pytest.mark.parametrize(("width", "scalar"), [(12, False), (24, False), (24, True)])
@pytest.mark.parametrize("unit", [False, True])
def test_native_compact_jet_transports_both_charts_and_replays_denominator(native_d4, width, scalar, unit):
    km, api, reference = native_d4
    field = GF4096()
    extension = import_module("dqi_extraction_oracle").ExternalField(field)
    arithmetic = field if width == 12 else extension
    count, factor, coordinate = 64, 19, 12
    rng = np.random.default_rng(699)
    values = rng.integers(0, 1 << width, size=(count, 2 if scalar else 3))
    head_values = rng.integers(0, 4096, size=(count, 4))
    incoming = np.arange(count) % 2 == 0
    if unit:
        values[:, 1] = 1
        incoming[:] = False
    collapse = np.arange(count) % 4 >= 2
    head_values[collapse, 2:] = 0
    expected = np.empty_like(values)
    for i, row in enumerate(values):
        n, d, *slope = map(int, row)
        l_value = slope[0] if slope else 0
        if incoming[i]:
            n, d = d, n
        words = list(map(int, head_values[i]))
        if collapse[i]:
            n ^= arithmetic.mul(factor, d)
            l_value ^= arithmetic.mul(d, d)
            words[2] = 1
        for lo, hi in zip(words[::2], words[1::2], strict=True):
            head = lo if width == 12 else (lo ^ field.mul(coordinate, hi)) | (hi << 12)
            residual = n ^ arithmetic.mul(head, d)
            l_value = arithmetic.mul(factor, l_value ^ arithmetic.mul(hi, arithmetic.mul(d, d))) ^ arithmetic.mul(d, residual)
            n, d = arithmetic.mul(factor, d), residual
        expected[i] = [n, d] if scalar else [n, d, l_value]

    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    words = [builder.alloc_qubits(width) for _ in range(values.shape[1])]
    chart = builder.alloc_qubits(2)
    state = words[0], words[1], None if scalar else words[2]
    pole = None if unit else chart[0]
    compact_pair_jet(builder, reference, heads, state, factor, coordinate, pole, chart[1], unit=unit)
    forward = builder.finish_circuit()
    builder.cz(words[0][1], words[1][2])
    compact_pair_jet(builder, reference, heads, state, factor, coordinate, pole, chart[1], reverse=True, unit=unit)
    closed = builder.finish_circuit()
    state_wires = reference.combine(words)
    head_wires = reference.combine([word for pair in heads for word in pair])
    chart_wires = km.array(chart)
    head_bits = api.to_bits(head_values, 12)
    chart_bits = np.stack((incoming, collapse))
    phase = ((expected[:, 0] >> 1) & (expected[:, 1] >> 2)) & 1
    live = 48 + width * values.shape[1] + 2
    for seed in (991, 992):
        for circuit, target, target_phase in ((forward, expected, np.zeros(count)), (closed, values, phase)):
            sim = km.Simulator(batch_size=count, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(state_wires, api.to_bits(values, width))
            sim.write_across_shots(head_wires, head_bits)
            sim.write_across_shots(chart_wires, chart_bits)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(state_wires), api.to_bits(target, width))
            assert np.array_equal(sim.read_across_shots(head_wires), head_bits)
            assert np.array_equal(sim.read_across_shots(chart_wires), chart_bits)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), target_phase)
            scratch = km.array([km.q(i) for i in range(live, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
@pytest.mark.parametrize("coordinate", [None, 16])
def test_native_affine_denominator_jet_preserves_wronskian_and_phase(native_d4, coordinate):
    km, api, reference = native_d4
    field = GF4096()
    extension = import_module("dqi_extraction_oracle").ExternalField(field)
    arithmetic = field if coordinate is None else extension
    width, count = (12 if coordinate is None else 24), 64
    builder = km.CircuitBuilder()
    n, d, w = (builder.alloc_qubits(width) for _ in range(3))
    flags = builder.alloc_qubits(2)
    live = builder.num_allocated_qubits
    affine_denominator_jet(builder, reference, (n, d, w), coordinate, *flags)
    forward = builder.finish_circuit()
    builder.cz(d[0], w[1])
    affine_denominator_jet(builder, reference, (n, d, w), coordinate, *flags)
    closed = builder.finish_circuit()
    rng = np.random.default_rng(4117)
    values = rng.integers(0, 1 << width, size=(count, 3))
    controls = np.stack((np.arange(count) % 2 == 1, np.arange(count) % 4 >= 2))
    expected = values.copy()
    x = 0 if coordinate is None else coordinate | 4096
    for i, (enable, translate) in enumerate(controls.T):
        if enable:
            numerator = int(values[i, 0])
            expected[i, 1] ^= arithmetic.mul(numerator, x ^ int(translate))
            expected[i, 2] ^= arithmetic.mul(numerator, numerator)
    initial = api.to_bits(values, width)
    wanted = api.to_bits(expected, width)
    phase = (expected[:, 1] & (expected[:, 2] >> 1)) & 1
    wires = reference.combine([n, d, w])
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    for seed in (891, 892):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, initial)
            sim.write_across_shots(flags, controls)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(wires), wanted if circuit is forward else initial)
            assert np.array_equal(sim.read_across_shots(flags), controls)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), phase if circuit is closed else np.zeros(count))
            assert not sim.read_across_shots(scratch).any()
            if circuit is forward:
                print(f"affine jet width={width} seed={seed} scratch={circuit.num_qubits - live} "
                      f"gates={sim.operation_statistics().num_toffoli_like / count}")


@pytest.mark.official
def test_native_affine_denominator_escape_normalizes_captured_local_chart(native_d4, project_root):
    km, api, reference = native_d4
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_extraction_oracle")
    field = GF4096()
    ext = oracle.ExternalField(field)
    capture = read_json(project_root / "docs/evidence/dqi-phase-replay-20261115/results/s2/batch-045312.json")
    coordinate = 12
    node = coordinate | 4096
    kappa = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    values = []
    for row in capture["shots"] + capture["controls"]:
        n, d = oracle.original_pair(decode(row["syndrome"], field), kappa, field)
        for c in range(0, coordinate, 2):
            fold = layout.split_pair(n, d, c, ext)
            n, d = fold.u, fold.v
        x, y = ext.evaluate(n, node), ext.evaluate(d, node)
        reciprocal = ext.inv(y)
        wronskian = ext.mul(x, ext.evaluate(oracle.derivative(d), node)) ^ ext.mul(
            y, ext.evaluate(oracle.derivative(n), node),
        )
        values.append((ext.mul(x, reciprocal), ext.mul(wronskian, ext.mul(reciprocal, reciprocal))))
    singular = ext.inv(node)
    values += [(singular, singular >> 12), (0, 0), (1, 0), (7, 43)]
    expected, flags = [], []
    for n, w in values:
        collapse = w == n >> 12 and n != 0
        translate = n == singular
        q = 1 ^ ext.mul(n, node ^ int(translate)) if collapse else 1
        scale = ext.inv(q)
        new_n = ext.mul(n, scale)
        new_w = ext.mul(w ^ (ext.mul(n, n) if collapse else 0), ext.mul(scale, scale))
        assert not collapse or new_w != new_n >> 12
        expected.append((new_n, new_w))
        flags.append((collapse, translate))
    assert flags[0] == (True, False) and flags[1][0] is False and (True, True) in flags

    builder = km.CircuitBuilder()
    n, w = [builder.alloc_qubits(24) for _ in range(2)]
    live = builder.num_allocated_qubits
    token = escape_normalized_affine_chart(builder, reference, n, w, coordinate)
    assert token is not None
    forward = builder.finish_circuit()
    builder.cz(token[0], w[0])
    escape_normalized_affine_chart(builder, reference, n, w, coordinate, token=token)
    closed = builder.finish_circuit()
    wires = reference.combine([n, w])
    initial = api.to_bits(np.asarray(values), 24)
    wanted = api.to_bits(np.asarray(expected), 24)
    chart_wires = km.array(token[:2])
    controls = np.asarray(flags).T
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    for seed in (895, 896):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=len(values), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, initial)
            sim.do(circuit)
            if circuit is forward:
                assert np.array_equal(sim.read_across_shots(chart_wires), controls)
            else:
                assert not sim.read_across_shots(scratch).any()
                assert np.array_equal(sim.read_phase_flipped_across_shots(), controls[0] & wanted[24])
            assert np.array_equal(sim.read_across_shots(wires), wanted if circuit is forward else initial)
            print(f"normalized affine charts={len(values)} seed={seed} forward={circuit is forward} "
                  f"scratch={circuit.num_qubits - live} gates={sim.operation_statistics().num_toffoli_like / len(values)}")


@pytest.mark.official
def test_native_affine_denominator_polynomial_shear_clears_scratch(native_d4):
    km, api, reference = native_d4
    width, count = 21, 64
    builder = km.CircuitBuilder()
    n = [builder.alloc_qubits(12) for _ in range(width)]
    d = [builder.alloc_qubits(12) for _ in range(width + 1)]
    flags = builder.alloc_qubits(2)
    live = builder.num_allocated_qubits
    affine_denominator_banks(builder, reference, n, d, *flags)
    forward = builder.finish_circuit()
    builder.cz(d[-1][0], d[0][1])
    affine_denominator_banks(builder, reference, n, d, *flags)
    closed = builder.finish_circuit()
    values = np.random.default_rng(441).integers(0, 4096, size=(count, 2 * width + 1))
    controls = np.stack((np.arange(count) % 2 == 1, np.arange(count) % 4 >= 2))
    expected = values.copy()
    expected[controls[0], width + 1:] ^= values[controls[0], :width]
    translated = controls[0] & controls[1]
    expected[translated, width:-1] ^= values[translated, :width]
    initial = api.to_bits(values, 12)
    wanted = api.to_bits(expected, 12)
    phase = (expected[:, -1] & (expected[:, width] >> 1)) & 1
    wires = reference.combine(n + d)
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    for seed in (893, 894):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, initial)
            sim.write_across_shots(flags, controls)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(wires), wanted if circuit is forward else initial)
            assert np.array_equal(sim.read_across_shots(flags), controls)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), phase if circuit is closed else np.zeros(count))
            assert not sim.read_across_shots(scratch).any()
            if circuit is forward:
                print(f"affine coefficient words={width} seed={seed} scratch={circuit.num_qubits - live} "
                      f"gates={sim.operation_statistics().num_toffoli_like / count}")


def test_affine_preshear_at_infinity_keeps_s2_finite_prefix_within_padded_caps(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_extraction_oracle")
    field = GF4096()
    extension = oracle.ExternalField(field)
    capture = read_json(project_root / "docs/evidence/dqi-phase-replay-20261115/results/s2/batch-045312.json")
    support = decode(capture["shots"][0]["syndrome"], field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    original = oracle.original_pair(support, kappas, field)
    n, d = original
    history = []
    quotient = []
    for group in range(17):
        coordinate = 2 * group
        if group == 6:
            ordinary = layout.split_pair(n, d, coordinate, extension)
            assert ordinary.collapse
            quotient, n = _divide(n, d, field)
            assert quotient == [1114, 1167] and len(n) < len(d)
            d = _add(d, _multiply(n, [0, 1], field))
        fold = layout.split_pair(n, d, coordinate, extension)
        history.append(fold)
        n, d = fold.u, fold.v
        if group < 16:
            padding = 35 - len(support)
            assert not fold.incoming_pole and not fold.collapse
            assert n == [0] or len(n) - 1 + padding <= 34 - 2 * group
            assert d == [0] or len(d) - 1 + padding <= 33 - 2 * group
    assert history[-1].incoming_pole and history[-1].collapse and (n, d) == ([1238], [0])
    for group in reversed(range(17)):
        n, d = history[group].join((n, d), field)
        if group == 6:
            d = _add(d, _multiply(n, [0, 1], field))
            n = _add(n, _multiply(quotient, d, field))
    assert (n, d) == original


@pytest.mark.official
@pytest.mark.parametrize("width", [5, 10])
def test_native_aligned_chart_routes_live_flags_and_returns_spills(native_d4, width):
    km, api, reference = native_d4
    aligned = import_module("dqi_compact_aligned")
    layout = import_module("dqi_compact_layout")
    field = GF4096()
    builder = km.CircuitBuilder()
    count, kappa = 64, 2053
    heads = tuple([builder.alloc_qubits(12) for _ in range(2)] for _ in range(2))
    banks = tuple([builder.alloc_qubits(12) for _ in range(width)] for _ in range(2))
    history = [builder.alloc_qubits(12) for _ in range(5)]
    flags = builder.alloc_qubits(3)
    live = builder.num_allocated_qubits
    replay_aligned_chart(builder, reference, heads, banks, history, kappa, *flags)
    forward = builder.finish_circuit()
    builder.cz(banks[0][0][0], history[0][1])
    replay_aligned_chart(builder, reference, heads, banks, history, kappa, *flags, reverse=True)
    closed = builder.finish_circuit()

    rng = np.random.default_rng(8720)
    values = rng.integers(0, 4096, size=(count, 5 + 2 * width))
    charts = np.asarray([[(i >> bit) & 1 for i in range(count)] for bit in range(3)], dtype=bool)
    values[charts[-1], 2:4] = 0
    expected = []
    for row, (incoming, previous, collapse) in zip(values.tolist(), charts.T.tolist(), strict=True):
        fold = layout.Fold(row[:2], row[2:4], [0], [0], kappa, incoming, collapse)
        inputs = row[4:4 + width], row[4 + width:-1]
        (a, b), (lost_b, lost_a) = aligned.update(inputs, (9, 10 + previous), fold, field)
        pool = lost_a + lost_b + [row[-1]]
        expected.append(row[:4] + a + b + pool + [0] * (5 - len(pool)))
    expected = np.asarray(expected)
    initial = api.to_bits(np.pad(values, ((0, 0), (0, 4))), 12)
    wires = reference.combine([*heads[0], *heads[1], *banks[0], *banks[1], *history])
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    phase = (expected[:, 4] & (expected[:, 4 + 2 * width] >> 1)) & 1
    assert phase.any() and not phase.all()
    for seed in (211, 212):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, initial)
            sim.write_across_shots(flags, charts)
            sim.do(circuit)
            wanted = api.to_bits(expected, 12) if circuit is forward else initial
            assert np.array_equal(sim.read_across_shots(wires), wanted)
            assert np.array_equal(sim.read_across_shots(flags), charts)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), phase if circuit is closed else np.zeros(count))
            assert not sim.read_across_shots(scratch).any()
            if circuit is forward:
                gates = sim.operation_statistics().num_toffoli_like / count
                print(f"aligned chart width={width} cases={count} seed={seed} scratch={circuit.num_qubits - live} gates={gates}")


@pytest.mark.official
@pytest.mark.parametrize("row", [0, 1])
def test_native_pooled_aligned_replay_restores_full_chart_sequence(native_d4, project_root, row):
    km, api, reference = native_d4
    aligned = import_module("dqi_compact_aligned")
    field = GF4096()
    capacity = 9
    width = capacity + 2
    evidence = project_root / "docs/evidence/d4-compact-repair-20261115"
    supports = []
    for name in ("multiple-poles.json", "dense-poles.json"):
        supports.extend({int(p): v for p, v in case["support"].items()}
                        for case in read_json(evidence / name)["cases"])
    rng = Random(8935)
    supports += [{p: rng.randrange(1, 4096) for p in rng.sample(range(4095), w)} for w in (0, 20, 35)]
    captures = evidence / "cloud-replay/captures"
    for draw in ("s6", "s7"):
        support = decode(read_json(next((captures / draw).glob("batch-*.json")))["shots"][0]["syndrome"], field)
        supports.append(support)

    prepared = [aligned.prepare(support, field) for support in supports]
    safe, expected = [], []
    builder = km.CircuitBuilder()
    heads = [tuple([builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)) for _ in range(17)]
    charts = [(None if i == 0 else builder.alloc_qubits(1)[0], builder.alloc_qubits(1)[0]) for i in range(17)]
    live = builder.num_allocated_qubits
    overflow = builder.alloc_qubits(1)
    banks = tuple([builder.alloc_qubits(12) for _ in range(width)] for _ in range(2))
    history = [builder.alloc_qubits(12) for _ in range(capacity)]
    for folds, matrix, bounds, _, needed, _ in prepared:
        bands = ([int(row == 0)] + [0] * (width - 1), [int(row == 1)] + [0] * (width - 1))
        pool = []
        for i, fold in enumerate(folds):
            bands, (lost_b, lost_a) = aligned.update(bands, bounds[i], fold, field)
            pool = lost_a + lost_b + pool
        oracle = [v for col in range(2) for v in aligned.band(matrix[row][col], bounds[-1][col], width)]
        assert bands[0] + bands[1] == oracle
        assert needed <= len(pool) + 2
        fits = len(pool) <= capacity
        safe.append(fits)
        expected.append(oracle + (pool[:capacity] + [0] * capacity)[:capacity])
    assert all(safe[:6]) and any(safe) and not all(safe)

    xor_aligned_history_overflow(builder, reference, charts, capacity, overflow[0])
    builder.x(banks[row][0][0])
    for group, (incoming, collapse) in enumerate(charts):
        previous = charts[group - 1][1] if group else None
        replay_aligned_chart(builder, reference, heads[group], banks, history,
                             prepared[0][0][group].kappa, incoming, previous, collapse)
    forward = builder.finish_circuit()
    mask = np.asarray(safe)
    wanted = api.to_bits(np.asarray(expected), 12)
    output = reference.combine([*banks[0], *banks[1], *history])
    fingerprint = next(i for i in range(24 * width) if wanted[i, mask].any() and not wanted[i, mask].all())
    builder.x(overflow[0])
    builder.cz(overflow[0], output[fingerprint])
    builder.x(overflow[0])
    for group in reversed(range(17)):
        incoming, collapse = charts[group]
        previous = charts[group - 1][1] if group else None
        replay_aligned_chart(builder, reference, heads[group], banks, history,
                             prepared[0][0][group].kappa, incoming, previous, collapse, reverse=True)
    builder.x(banks[row][0][0])
    xor_aligned_history_overflow(builder, reference, charts, capacity, overflow[0])
    closed = builder.finish_circuit()

    heads_in = api.to_bits(np.asarray([[v for f in case[0] for v in f.first + f.second] for case in prepared]), 12)
    charts_in = np.asarray([[flag for i, f in enumerate(case[0]) for flag in (
        (f.incoming_pole, f.collapse) if i else (f.collapse,))] for case in prepared], dtype=bool).T
    head_wires = reference.combine([word for group in heads for head in group for word in head])
    chart_wires = km.array([wire for chart in charts for wire in chart if wire is not None])
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    for seed in (301, 302):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=len(supports), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(head_wires, heads_in)
            sim.write_across_shots(chart_wires, charts_in)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(head_wires), heads_in)
            assert np.array_equal(sim.read_across_shots(chart_wires), charts_in)
            if circuit is forward:
                assert np.array_equal(sim.read_across_shots(overflow)[0], ~mask)
                assert np.array_equal(sim.read_across_shots(output)[:, mask], wanted[:, mask])
            else:
                assert not sim.read_across_shots(scratch).any()
            phase = wanted[fingerprint] & mask if circuit is closed else np.zeros(len(supports))
            assert np.array_equal(sim.read_phase_flipped_across_shots(), phase)
            gates = sim.operation_statistics().num_toffoli_like / len(supports)
            print(f"pooled row={row} seed={seed} forward={circuit is forward} eligible={mask.sum()}/{len(supports)} "
                  f"qubits={circuit.num_qubits} gates={gates}")


@pytest.mark.official
def test_native_termination_predicate_preserves_live_charts_and_phase(native_d4):
    km, api, reference = native_d4
    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(68)]
    charts = [(None if i == 0 else builder.alloc_qubits(1)[0], builder.alloc_qubits(1)[0]) for i in range(17)]
    result = builder.alloc_qubits(1)
    live = builder.num_allocated_qubits
    xor_terminated_compact_tail(builder, reference, words, charts, result[0])
    forward = builder.finish_circuit()
    builder.z(result[0])
    xor_terminated_compact_tail(builder, reference, words, charts, result[0])
    closed = builder.finish_circuit()

    rng = np.random.default_rng(8514)
    count = 17 * 32
    inputs = rng.integers(1, 4096, size=(count, 17, 4))
    incoming, collapse = rng.integers(0, 2, size=(2, count, 17), dtype=bool)
    incoming[:, 0] = False
    expected = []
    for row in range(count):
        suffix = row % 17
        prefix = 17 - suffix
        incoming[row, prefix:] = True
        collapse[row, prefix:] = True
        inputs[row, prefix:, :2] = 0
        inputs[row, collapse[row], 2:] = 0
        n, d = 34, 35
        for group in range(prefix):
            if incoming[row, group]:
                n, d = d, n
            if collapse[row, group]:
                n = max(n - 2, d)
                d = max(n, d) - 2
            else:
                n = max(n, d + 1) - 2
                d = max(d, n + 1) - 2
        expected.append(4 * suffix > d)
    expected = np.asarray(expected)
    assert expected.any() and not expected.all()
    assert np.any(expected[5::17]) and not np.all(expected[5::17])
    head_bits = api.to_bits(inputs.reshape(count, 68), 12)
    chart_bits = np.stack([bits for i in range(17)
                           for bits in ((incoming[:, i], collapse[:, i]) if i else (collapse[:, i],))])
    head_wires = reference.combine(words)
    chart_wires = km.array([wire for chart in charts for wire in chart if wire is not None])
    scratch = km.array([km.q(i) for i in range(live, closed.num_qubits)])
    initial = np.arange(count) % 2 == 0
    for seed in (207, 208):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(head_wires, head_bits)
            sim.write_across_shots(chart_wires, chart_bits)
            sim.write_across_shots(result, initial[None, :])
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(head_wires), head_bits)
            assert np.array_equal(sim.read_across_shots(chart_wires), chart_bits)
            want_result = initial ^ expected if circuit is forward else initial
            want_phase = np.zeros(count, dtype=bool) if circuit is forward else initial ^ expected
            assert np.array_equal(sim.read_across_shots(result)[0], want_result)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), want_phase)
            assert not sim.read_across_shots(scratch).any()
            if circuit is forward:
                gates = sim.operation_statistics().num_toffoli_like / count
                print(f"termination cases={count} seed={seed} scratch={circuit.num_qubits - live} gates={gates}")


def test_numerator_row_and_jet_can_admit_an_overdegree_denominator(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    aligned = import_module("dqi_compact_aligned")
    layout = import_module("dqi_compact_layout")
    constraints = import_module("dqi_compact_constraints")
    evidence = project_root / "docs/evidence/d4-compact-repair-20261115/single-row-counterexample.json"
    capture = read_json(evidence)
    support = {int(p): v for p, v in capture["support"].items()}
    field = GF4096()
    assert len(support) == 35 and decode(syndrome(support, field), field) == support
    folds, matrix, _, _, _, (n, d) = aligned.prepare(support, field)
    prefix = folds[:5]
    construction = capture["construction"]
    assert [f.collapse for f in prefix] == construction["collapse_prefix"]
    assert [f.first for f in prefix] == construction["first_heads"]
    assert [f.second for f in prefix] == construction["second_heads"]

    a, b = (bound + 1 for bound in layout.degree_envelope(folds))
    slots = [(bank, i) for bank, cap in enumerate((a, b)) for i in range(cap)]
    rows = []
    for row, limit in zip(matrix, (35, 36), strict=True):
        end = max(len(poly) + cap - 1 for poly, cap in zip(row, (a, b), strict=True))
        rows.append([[layout.coefficient(row[bank], power - i) if power >= i else 0
                      for bank, i in slots] for power in range(limit, end)])
    jets = [
        [int((bank, i) == (0, 0)) for bank, i in slots],
        [int((bank, i) == (1, 0)) for bank, i in slots],
        [(d[0], n[0])[bank] if i == 1 else 0 for bank, i in slots],
    ]
    numerator, reduced = constraints.echelon(rows[0] + jets, range(len(slots)), field)
    both, _ = constraints.echelon(rows[0] + rows[1] + jets, range(len(slots)), field)
    assert len(numerator) == 6 and len(both) == len(slots) == 7
    free = next(i for i in range(len(slots)) if i not in numerator)
    delta = [0] * len(slots)
    delta[free] = 1
    for i, pivot in enumerate(numerator):
        delta[pivot] = reduced[i][free]
    changed = _add(n, delta[:a]), _add(d, delta[a:])
    assert changed[0][0] == n[0] and changed[1][0] == d[0]
    assert field.mul(d[0], layout.coefficient(delta[:a], 1)) == field.mul(n[0], layout.coefficient(delta[a:], 1))
    candidate = layout.reconstruct(changed, folds, field)
    assert len(candidate[0]) <= 35 and len(candidate[1]) > 36


@pytest.mark.official
@pytest.mark.parametrize(("affine_group", "recover_quotient", "unit_first"),
                         [(None, False, False), (6, False, False), (None, True, False), (None, False, True)])
def test_native_compact_extraction_and_scalar_replay_match_actual_d4_poles(
    native_d4, project_root, affine_group, recover_quotient, unit_first,
):
    km, api, reference = native_d4
    field = GF4096()
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_extraction_oracle")
    extension = oracle.ExternalField(field)
    affine_model = import_module("dqi_affine_chart")
    active = project_root / "docs/evidence/d4-compact-repair-20261115/cloud-replay/captures"
    inputs = [
        read_json(project_root / "docs/evidence/dqi-phase-replay-20261115/results/s2/batch-045312.json")["shots"][0]["syndrome"],
        *(read_json(next((active / draw).glob("batch-*.json")))["shots"][0]["syndrome"] for draw in ("s6", "s7")),
        oracle.doubled_node_fixtures()[1]["syndrome"],
        [0] * 70,
        syndrome(layout.forced_outer_pole(35, Random(5515), field), field),
    ]
    coordinates = range(0, 34, 2)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in coordinates for _ in range(2)]
    heads, flags, tail, selected = [], [], [], []
    quotients = []
    for values in inputs:
        root = oracle.original_pair(decode(values, field), kappas, field)
        n, d = root
        if affine_group is not None:
            details = affine_model.trace((n, d), field, affine_group, escape=True)
            results = details["folds"]
            heads.append([word for fold in results for word in fold["heads"]])
            flags.append([bit for i, fold in enumerate(results) for bit in (
                (fold["incoming"], fold["collapse"]) if i else (fold["collapse"],))])
            n, d = details["tail"]
            tail.append((n[0], d[0], field.mul(n[0], layout.coefficient(d, 1))
                         ^ field.mul(d[0], layout.coefficient(n, 1))))
            selected.append(results[affine_group]["translation"] is not None)
            continue
        row, charts, folds = [], [], []
        entering = n, d
        for coordinate in coordinates:
            if coordinate == 12:
                entering = n, d
            fold = layout.split_pair(n, d, coordinate, extension)
            row.extend(fold.first + fold.second)
            charts.extend((fold.incoming_pole, fold.collapse) if coordinate else (fold.collapse,))
            n, d = fold.u, fold.v
            folds.append(fold)
        heads.append(row)
        flags.append(charts)
        tail.append((n[0], d[0], field.mul(n[0], d[1] if len(d) > 1 else 0)
                     ^ field.mul(d[0], n[1] if len(n) > 1 else 0)))
        if recover_quotient:
            pattern = all(not fold.incoming_pole and fold.collapse == (i in (6, 16))
                          for i, fold in enumerate(folds))
            if pattern:
                # Independently certify the whole root pair and recover the
                # exact suffix by polynomial reconstruction, without bands.
                unit_root = layout.reconstruct(([1], [0]), folds, field)
                assert len(unit_root[0]) <= 35 and len(unit_root[1]) <= 36
                u, v = layout.reconstruct(([1], [0]), folds[7:], field)
                valid = bool(n[0]) and not any(tail[-1][1:]) and len(u) == 20 and len(v) <= 17
                if valid:
                    assert _multiply(unit_root[0], root[1], field) == _multiply(root[0], unit_root[1], field)
            else:
                valid = False
            selected.append(valid)
            quotients.append((_divide(*entering, field)[0] + [0, 0])[:2] if valid else [0, 0])
        else:
            start = len(folds)
            while (start and folds[start - 1].incoming_pole and folds[start - 1].collapse
                   and not any(folds[start - 1].first)):
                start -= 1
            selected.append(4 * (len(folds) - start) > layout.degree_envelope(folds[:start])[1])

    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    wires = reference.combine(words)
    reference.linear_words(builder, words, reference.matrix)
    token = extract_compact_heads(builder, reference, words, affine_group=affine_group, unit_first=unit_first)
    chart_rows = [(None if chain is None else chain["pole"], collapse) for collapse, _, chain in token]
    if affine_group is None:
        selector = builder.alloc_qubits(1)
        if not recover_quotient:
            xor_terminated_compact_tail(builder, reference, words[:68], chart_rows, selector[0])
    else:
        selector = km.array([token[affine_group][2]["affine"][0]])
    denominator = compact_tail_jet(builder, reference, words, token, unit_first=unit_first)
    quotient_wires = [builder.alloc_qubits(12) for _ in range(2)] if recover_quotient else None
    jet = words[-2], denominator, words[-1]
    if quotient_wires is not None:
        xor_unit_tail_preshear(builder, reference, words[:68], chart_rows, jet, 6, quotient_wires, selector[0])
    head_wires = reference.combine(words[:68])
    chart_wires = km.array([
        wire for collapse, _, chain in token for wire in ([collapse] if chain is None else [chain["pole"], collapse])
    ])
    tail_wires = reference.combine([words[-2], denominator, words[-1]])
    forward = builder.finish_circuit()
    builder.z(words[12][3])
    builder.z(selector[0])
    if quotient_wires is not None:
        builder.z(quotient_wires[0][1])
        xor_unit_tail_preshear(builder, reference, words[:68], chart_rows, jet, 6, quotient_wires, selector[0])
    compact_tail_jet(builder, reference, words, token, reverse=True, denominator=denominator, unit_first=unit_first)
    if affine_group is None and not recover_quotient:
        xor_terminated_compact_tail(builder, reference, words[:68], chart_rows, selector[0])
    extract_compact_heads(builder, reference, words, reverse=True, token=token, unit_first=unit_first,
                          replay_norms=unit_first)
    reference.linear_words(builder, words, reference.matrix, True)
    closed = builder.finish_circuit()
    initial = api.to_bits(np.asarray(inputs), 12)
    expected_heads = api.to_bits(np.asarray(heads), 12)
    expected_flags = np.asarray(flags).T
    expected_phase = expected_heads[12 * 12 + 3] ^ np.asarray(selected)
    assert any(selected) and not all(selected)
    expected_quotient = api.to_bits(np.asarray(quotients), 12) if recover_quotient else None
    if expected_quotient is not None:
        assert quotients[0] == [1114, 1167] and sum(selected) == 1
        expected_phase ^= expected_quotient[1]
    for seed in (941, 942):
        sim = km.Simulator(batch_size=len(inputs), seed=seed)
        sim.use_same_registers_as(forward)
        sim.write_across_shots(wires, initial)
        sim.do(forward)
        assert np.array_equal(sim.read_across_shots(head_wires), expected_heads)
        assert np.array_equal(sim.read_across_shots(chart_wires), expected_flags)
        assert np.array_equal(sim.read_across_shots(selector)[0], selected)
        if quotient_wires is not None and expected_quotient is not None:
            assert np.array_equal(sim.read_across_shots(reference.combine(quotient_wires)), expected_quotient)
        vectors = sim.read_across_shots(tail_wires).T.reshape(len(inputs), 3, 12) @ (1 << np.arange(12))
        for observed, (n, d, derivative) in zip(vectors, tail, strict=True):
            actual_n, actual_d, actual_l = map(int, observed)
            scale = field.div(actual_d, d) if d else field.div(actual_n, n)
            assert scale and (actual_n, actual_d, actual_l) == (
                field.mul(scale, n), field.mul(scale, d), field.mul(field.mul(scale, scale), derivative),
            )
        sim = km.Simulator(batch_size=len(inputs), seed=seed, counting_operations=True)
        sim.use_same_registers_as(closed)
        sim.write_across_shots(wires, initial)
        sim.do(closed)
        assert np.array_equal(sim.read_across_shots(wires), initial)
        assert np.array_equal(sim.read_phase_flipped_across_shots(), expected_phase)
        scratch = km.array([km.q(i) for i in range(840, closed.num_qubits)])
        assert not sim.read_across_shots(scratch).any()
        print(f"affine extraction group={affine_group} quotient={recover_quotient} first={unit_first} "
              f"seed={seed} qubits={closed.num_qubits} "
              f"gates={sim.operation_statistics().num_toffoli_like / len(inputs)}")


@pytest.mark.official
def test_native_rank_three_tail_basis_solves_separated_poles(native_d4, project_root):
    km, api, reference = native_d4
    field = GF4096()
    basis = import_module("dqi_compact_tail_basis")
    oracle = import_module("dqi_extraction_oracle")
    layout = import_module("dqi_compact_layout")
    witness = read_json(project_root / "docs/evidence/d4-compact-repair-20261115/multiple-poles.json")
    supports = [{int(position): symbol for position, symbol in case["support"].items()} for case in witness["cases"]]
    supports.append(layout.forced_outer_pole(35, Random(5515), field))
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    inputs, expected = [], []
    for index, support in enumerate(supports):
        target = oracle.original_pair(support, kappas, field)
        (n, d), _, matrix = basis.chart_matrix(target, field)
        root, change, _ = basis.reduced_root_basis(matrix, field)
        slope = field.mul(d[0], layout.coefficient(n, 1)) ^ field.mul(n[0], layout.coefficient(d, 1))
        scale = field.exp[271 * (index + 1)]
        columns, rows = basis.jet_equations(
            root, change, field.mul(n[0], scale), field.mul(d[0], scale),
            field.mul(slope, field.mul(scale, scale)), field,
        )
        assert len(columns) == len(rows) == 3
        leading = [layout.coefficient(root[column][1], 35 - power) for column, power in columns]
        inputs.append([value for row in rows for value in row] + leading)
        expected.append((root, columns, target))

    builder = km.CircuitBuilder()
    system = [[builder.alloc_qubits(12) for _ in range(4)] for _ in range(3)]
    leading = [builder.alloc_qubits(12) for _ in range(3)]
    untouched = reference.combine([word for row in system for word in row] + leading)
    targets = [builder.alloc_qubits(12) for _ in range(3)]
    normalized = [builder.alloc_qubits(12) for _ in range(3)]
    outputs = reference.combine(normalized)
    singular = builder.alloc_qubits(1)[0]
    invalid = builder.alloc_qubits(1)[0]
    matrix, rhs = [row[:3] for row in system], [row[3] for row in system]
    xor_tail_system_solution(builder, reference, matrix, rhs, targets, singular)
    xor_monic_basis_coordinates(builder, reference, targets, leading, normalized, invalid)
    solved = builder.finish_circuit()
    builder.z(normalized[0][0])
    builder.cz(normalized[1][1], normalized[2][2])
    xor_monic_basis_coordinates(builder, reference, targets, leading, normalized, invalid)
    xor_tail_system_solution(builder, reference, matrix, rhs, targets, singular)
    closed = builder.finish_circuit()
    input_bits = api.to_bits(np.asarray(inputs), 12)
    for seed in (821, 822):
        sim = km.Simulator(batch_size=len(inputs), seed=seed)
        sim.use_same_registers_as(solved)
        sim.write_across_shots(untouched, input_bits)
        sim.do(solved)
        assert not sim.read_across_shots(km.array([singular, invalid])).any()
        values = sim.read_across_shots(outputs).T.reshape(len(inputs), 3, 12) @ (1 << np.arange(12))
        for row, (root, columns, target) in zip(values, expected, strict=True):
            assert basis.assemble_root(root, columns, list(map(int, row)), field) == target
        wanted_phase = (values[:, 0] ^ ((values[:, 1] >> 1) & (values[:, 2] >> 2))) & 1
        sim = km.Simulator(batch_size=len(inputs), seed=seed)
        sim.use_same_registers_as(closed)
        sim.write_across_shots(untouched, input_bits)
        sim.do(closed)
        assert np.array_equal(sim.read_across_shots(untouched), input_bits)
        scratch = km.array([km.q(i) for i in range(180, closed.num_qubits)])
        assert not sim.read_across_shots(scratch).any()
        assert np.array_equal(sim.read_phase_flipped_across_shots(), wanted_phase)


@pytest.mark.official
@pytest.mark.parametrize("coordinate", [0, 12])
def test_native_compact_absorber_reuses_head_and_restores_phase(native_d4, coordinate):
    km, api, reference = native_d4
    field = GF4096()
    kappa = reference.K ^ field.mul(coordinate, coordinate) ^ coordinate
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (6, 4))
    inputs = [*heads[0], *heads[1], *v, *u]
    wires = km.array([qubit for word in inputs for qubit in word])
    numerator, denominator = absorb_local_pole(builder, reference, heads[0], heads[1], u, v, coordinate)
    assert [*numerator, *denominator] == inputs
    forward = builder.finish_circuit()
    builder.z(numerator[0][2])
    builder.cz(numerator[-1][1], denominator[-1][3])
    absorb_local_pole(builder, reference, heads[0], heads[1], u, v, coordinate, reverse=True)
    closed = builder.finish_circuit()

    rng = np.random.default_rng(552)
    states = rng.integers(0, 4096, size=(64, len(inputs)))
    states[:, 2:4] = 0
    expected = np.zeros_like(states)
    for index, row in enumerate(states):
        head, v_words, u_words = (list(map(int, part)) for part in (row[:2], row[4:8], row[8:]))
        n, d = join_local_pole(u_words, v_words, head, kappa, field)
        assert split_local_pole(n, d, head, kappa, field) == (u_words, v_words)
        expected[index, :len(n)] = n
        expected[index, 8:] = d
    phase = ((expected[:, 0] >> 2) ^ ((expected[:, 7] >> 1) & (expected[:, -1] >> 3))) & 1
    for seed in (131, 132):
        for circuit, want, want_phase in ((forward, expected, np.zeros(len(states))), (closed, states, phase)):
            sim = km.Simulator(batch_size=len(states), seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, api.to_bits(states, 12))
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(wires), api.to_bits(want, 12))
            assert np.array_equal(sim.read_phase_flipped_across_shots(), want_phase)
            scratch = km.array([km.q(i) for i in range(len(inputs) * 12, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
@pytest.mark.parametrize("defer", [False, True])
def test_native_compact_pair_shares_layout_across_coherent_charts(native_d4, defer):
    km, api, reference = native_d4
    field = GF4096()
    coordinate = 12
    kappa = reference.K ^ field.mul(coordinate, coordinate) ^ coordinate
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (6, 4))
    inputs = [*heads[0], *heads[1], *v, *u]
    wires = km.array([qubit for word in inputs for qubit in word])
    collapse = builder.alloc_qubits(1)[0]
    incoming_pole = builder.alloc_qubits(1)[0]
    phase_masks = [] if defer else None
    numerator, denominator = absorb_compact_pair(builder, reference, heads, u, v, coordinate, collapse,
                                                 incoming_pole=incoming_pole, phase_masks=phase_masks)
    assert numerator == [*heads[0], *u] and denominator == [*heads[1], *v]
    results = km.array([qubit for word in numerator + denominator for qubit in word])
    forward = builder.finish_circuit()
    builder.z(numerator[-1][2])
    builder.cz(numerator[0][3], denominator[-1][1])
    absorb_compact_pair(builder, reference, heads, u, v, coordinate, collapse, incoming_pole=incoming_pole,
                        reverse=True, phase_masks=phase_masks)
    assert not phase_masks
    closed = builder.finish_circuit()

    rng = np.random.default_rng(553)
    states = rng.integers(1, 4096, size=(63, len(inputs)))
    regular = np.arange(len(states)) % 3 == 0
    termination = np.arange(len(states)) % 3 == 2
    incoming = np.arange(len(states)) % 6 == 0
    states[regular, -1] = 0
    states[incoming, -2] = 0
    states[incoming, :2] = 0
    states[~regular, 2:4] = 0
    states[termination, 4:8] = 0
    expected = np.zeros_like(states)
    for index, row in enumerate(states):
        first, second, v_words, u_words = (list(map(int, part)) for part in (row[:2], row[2:4], row[4:8], row[8:]))
        n, d = synthesize_pair((u_words, v_words), (first, second), kappa, not bool(regular[index]), field)
        if incoming[index]:
            assert len(n) <= 6
            n, d = d, n
        expected[index, :len(n)] = n
        expected[index, 8:8 + len(d)] = d
        if not regular[index]:
            correction = _multiply([kappa, 1, 1], v_words, field)
            states[index, 8:8 + len(correction)] ^= correction
    phase = ((expected[:, 7] >> 2) ^ ((expected[:, 0] >> 3) & (expected[:, -1] >> 1))) & 1
    chart_wire = km.array([collapse, incoming_pole])
    chart_bits = np.stack((~regular, incoming))
    for seed in (131, 132):
        for circuit, registers, want, want_phase in (
            (forward, results, expected, np.zeros(len(states))), (closed, wires, states, phase),
        ):
            sim = km.Simulator(batch_size=len(states), seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, api.to_bits(states, 12))
            sim.write_across_shots(chart_wire, chart_bits)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(registers), api.to_bits(want, 12))
            assert np.array_equal(sim.read_across_shots(chart_wire), chart_bits)
            if not defer or circuit is closed:
                assert np.array_equal(sim.read_phase_flipped_across_shots(), want_phase)
            scratch = km.array([km.q(i) for i in range(len(inputs) * 12 + 2, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
def test_native_guarded_pair_counts_two_zero_pivots_and_restores_phase(native_d4):
    km, api, reference = native_d4
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (3, 2))
    words = [*heads[0], *heads[1], *u, *v]
    wires = reference.combine(words)
    count = builder.alloc_qubits(2)
    masks = []
    absorb_compact_pair(builder, reference, heads, u, v, 12, None, phase_masks=masks, zero_pivots=count)
    forward = builder.finish_circuit()
    builder.z(count[1])
    absorb_compact_pair(builder, reference, heads, u, v, 12, None, reverse=True, phase_masks=masks,
                        zero_pivots=count)
    assert not masks
    closed = builder.finish_circuit()
    states = np.zeros((3, len(words)), dtype=np.int64)
    states[:, :4] = [[123, 54, 0, 0], [123, 54, 18, 43], [123, 54, 1, 0]]
    states[2, 4] = 1
    bits = api.to_bits(states, 12)
    scratch = km.array([km.q(i) for i in range(len(words) * 12, closed.num_qubits)])
    for seed in (617, 618):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=len(states), seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, bits)
            sim.do(circuit)
            if circuit is forward:
                assert sim.read_across_shots(count).T.tolist() == [[False, True], [True, False], [False, False]]
            else:
                assert np.array_equal(sim.read_across_shots(wires), bits)
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == [True, False, False]


@pytest.mark.official
def test_native_fused_collapse_restores_overflowed_layout(native_d4):
    km, api, reference = native_d4
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (3, 2))
    wires = reference.combine([*heads[0], *heads[1], *u, *v])
    collapse = builder.alloc_qubits(1)[0]
    failures = builder.alloc_qubits(3)
    masks = []
    absorb_compact_pair(builder, reference, heads, u, v, 12, collapse, phase_masks=masks, zero_pivots=failures)
    forward = builder.finish_circuit()
    builder.z(failures[0])
    absorb_compact_pair(builder, reference, heads, u, v, 12, collapse, reverse=True, phase_masks=masks,
                        zero_pivots=failures)
    assert not masks
    closed = builder.finish_circuit()
    rows = [[123, 54, 0, 0, 1, 0, 0, 211, top] for top in (0, 3356)]
    bits = api.to_bits(np.asarray(rows), 12)
    branch = km.array([collapse])
    branch_values = np.ones((1, len(rows)), dtype=bool)
    scratch = km.array([km.q(i) for i in range(len(wires) + 1, closed.num_qubits)])
    for seed in (619, 620):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=len(rows), seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, bits)
            sim.write_across_shots(branch, branch_values)
            sim.do(circuit)
            if circuit is forward:
                assert sim.read_across_shots(failures).T.tolist() == [[False] * 3, [True, False, False]]
            else:
                assert np.array_equal(sim.read_across_shots(wires), bits)
                assert np.array_equal(sim.read_across_shots(branch), branch_values)
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == [False, True]


def test_shared_fold_exhausts_the_smallest_quadratic_layout():
    # GF(2) coefficients with the irreducible extension modulus X²+X+1.
    field = cast(GF4096, SimpleNamespace(mul=lambda a, b: a & b, div=lambda a, _: a))
    q = [1, 1, 1]
    heads: list[list[int]] = [list(values) for values in product((0, 1), repeat=2)]
    observed = {False: set(), True: set()}

    def split(n, d):
        choices = []
        for head in heads:
            quotient, remainder = _divide(_add(n, _multiply(head, d, field)), q, field)
            if remainder == [0]:
                choices.append((_trim(head[:]), quotient))
        assert len(choices) == 1
        return choices[0]

    for first, second, u_bits, v_bit in product(heads, heads, product((0, 1), repeat=3), (0, 1)):
        u: list[int] = list(u_bits)
        v = [v_bit]
        if _divide(u, q, field)[1] == [0]:
            continue
        collapse = second == [0, 0]
        if not collapse and u[-1]:
            continue
        if collapse:
            sheared = _add(u, _multiply(q, v, field))
            substituted = [1]
        else:
            sheared, substituted = u, second
        n, d = synthesize_pair((sheared, v), (first, substituted), 1, False, field)
        if collapse:
            n = _add(n, _multiply(q, d, field))
        expected_n, expected_d = synthesize_pair((u, v), (first, second), 1, collapse, field)
        assert (n, d) == (_trim(expected_n), _trim(expected_d))
        assert len(n) <= 5 and len(d) <= 3
        key = tuple(n), tuple(d)
        assert key not in observed[collapse]
        observed[collapse].add(key)
        first_back, u_back = split(_add(n, _multiply(q, d, field)) if collapse else n, d)
        second_back, v_back = split(d, u_back)
        if collapse:
            assert second_back == [1]
            u_back = _add(u_back, _multiply(q, v_back, field))
        else:
            assert second_back == _trim(second[:])
        assert (first_back, u_back, v_back) == (_trim(first[:]), _trim(u[:]), v)
    assert tuple(map(len, observed.values())) == (72, 48)


@pytest.mark.official
def test_native_projected_outer_preserves_exact_residue_inputs(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_extraction_oracle")
    extension = oracle.ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    projected, remainder = _divide(oracle.node_polynomial(kappas, field), [2048, 1, 1], field)
    assert remainder == [0]
    assert projected == list(reference.Pscan)
    rng = np.random.default_rng(5513)
    errors = [
        dict(zip(fixture["error_positions"], fixture["error_values"], strict=True))
        for fixture in oracle.doubled_node_fixtures()
    ]
    errors.extend({
        int(position): int(value) for position, value in zip(
            rng.choice(4095, 35, replace=False), rng.integers(1, 4096, size=35), strict=True,
        )
    } for _ in range(4))
    builder = km.CircuitBuilder()
    second = [builder.alloc_qubits(12) for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (36, 34))
    chart = builder.alloc_qubits(1)[0]
    inputs = km.array([wire for word in [*u, *second, *v] for wire in word])
    evaluator, locator = absorb_projected_outer(builder, reference, second, u, v, chart)
    assert evaluator == u and locator == [*second, *v]
    forward = builder.finish_circuit()
    builder.z(evaluator[0][0])
    builder.cz(locator[-1][0], evaluator[2][4])
    absorb_projected_outer(builder, reference, second, u, v, chart, reverse=True)
    closed = builder.finish_circuit()

    states = np.zeros((len(errors), 72), dtype=np.int64)
    expected = np.zeros_like(states)
    collapse = []
    for index, support in enumerate(errors):
        n, d = oracle.original_pair(support, kappas, field)
        fold = layout.split_pair(n, d, 0, extension)
        assert not fold.incoming_pole
        e, remainder = _divide(_add(n, _multiply(fold.first, d, field)), [2048, 1, 1], field)
        assert remainder == [0]
        for position, symbol in support.items():
            beta = field.exp[position]
            derivative_value = field.evaluate(oracle.derivative(d), beta)
            scale = field.mul(beta, field.evaluate(projected, beta))
            assert field.evaluate(e, beta) == field.mul(symbol, field.mul(scale, derivative_value))
        expected[index, :len(e)] = e
        expected[index, 36:36 + len(d)] = d
        states[index, :len(fold.u)] = fold.u
        states[index, 36:38] = fold.second
        states[index, 38:38 + len(fold.v)] = fold.v
        collapse.append(fold.collapse)
    assert any(collapse) and not all(collapse)
    chart_bits = np.asarray([collapse], dtype=bool)
    phase = (expected[:, 0] ^ (expected[:, -1] & (expected[:, 2] >> 4))) & 1
    for seed in (901, 902):
        for circuit, want, want_phase in ((forward, expected, np.zeros(len(errors))), (closed, states, phase)):
            sim = km.Simulator(batch_size=len(errors), seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(inputs, api.to_bits(states, 12))
            sim.write_across_shots(km.array([chart]), chart_bits)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(inputs), api.to_bits(want, 12))
            assert np.array_equal(sim.read_across_shots(km.array([chart])), chart_bits)
            assert np.array_equal(sim.read_phase_flipped_across_shots(), want_phase)
            scratch = km.array([km.q(i) for i in range(72 * 12 + 1, circuit.num_qubits)])
            assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
@pytest.mark.parametrize(
    ("padded", "unit_first", "degree_certificate", "replay_norms", "live_degree"),
    [(True, False, False, False, False), (False, False, False, False, False),
     (False, True, False, False, False), (False, True, True, False, False),
     (False, True, True, True, False), (False, True, True, True, True)],
    ids=["padded", "degree31", "degree31-unit-first", "degree31-degree-certificate",
         "degree31-replayed-norms", "degree31-live-route"],
)
def test_native_certified_unit_tail_synthesis_and_full_scan(
    native_d4, project_root, padded, unit_first, degree_certificate, replay_norms, live_degree,
):
    km, api, reference = native_d4
    field = GF4096()
    oracle = import_module("dqi_extraction_oracle")
    layout = import_module("dqi_compact_layout")
    synthesis = import_module("dqi_compact_synthesis_probe")
    converter = import_module("high_stream").convert_safe
    capture = read_json(project_root / "docs/evidence/dqi-phase-replay-20261115/results/s2/batch-045312.json")
    shot = capture["shots"][0]
    raw = shot["syndrome"]
    support = decode(raw, field)
    weight = len(support)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    n, expected_d = oracle.original_pair(support, kappas, field)
    outer = layout.split_pair(n, expected_d, 0, oracle.ExternalField(field))
    expected_e, remainder = _divide(_add(n, _multiply(outer.first, expected_d, field)), [2048, 1, 1], field)
    assert remainder == [0] and weight == 31

    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    stages = {}
    widths = {}

    def record(name):
        snapshot = builder.finish_circuit()
        stages[name] = snapshot.operation_statistics().num_toffoli_like - sum(stages.values())
        widths[name] = snapshot.num_qubits

    mask_token = reference.baseline.project(builder, words, masks)
    projection = builder.finish_circuit() if live_degree else None
    reference.linear_words(builder, words, reference.matrix)
    token = extract_compact_heads(builder, reference, words, unit_first=unit_first)
    if unit_first:
        record("extract")
    charts = [(None if chain is None else chain["pole"], collapse) for collapse, _, chain in token]
    certified = builder.alloc_qubits(1)
    layout_ok = builder.alloc_qubits(1)[0] if degree_certificate else None
    # Fifteen pairs and the projected outer fold give at most 31 zero pivots.
    zero_pivots = builder.alloc_qubits(5) if live_degree else None

    def toggle_certificate():
        q = compact_tail_jet(builder, reference, words, token, unit_first=unit_first)
        xor_unit_tail_certificate(builder, reference, charts, (words[-2], q, words[-1]), 6, certified[0])
        compact_tail_jet(builder, reference, words, token, reverse=True, denominator=q, unit_first=unit_first)

    if not degree_certificate:
        toggle_certificate()
    if unit_first:
        record("certificate")
    # On the certified unit chart the last inverse pair is (h,1).
    u, v = words[64:66], words[66:67]
    builder.x(v[0][0])
    history = []
    phase_masks = []
    for group in reversed(range(1, 16)):
        start = 4 * group
        heads = words[start:start + 2], words[start + 2:start + 4]
        collapse = charts[group][1] if group == 6 else None
        if group == 6 and layout_ok is not None:
            builder.flip_if_equal(v[-1], 0, target=layout_ok)
        history.append((heads, u, v, 2 * group, collapse))
        u, v = absorb_compact_pair(builder, reference, *history[-1], phase_masks=phase_masks, zero_pivots=zero_pivots)
    e, d = absorb_projected_outer(builder, reference, words[2:4], u, v, None, phase_masks=phase_masks,
                                  zero_pivots=zero_pivots)

    def toggle_degree_certificate():
        if zero_pivots is not None:
            xor_unit_tail_degree31_certificate(builder, reference, charts, 6, e, d, layout_ok, zero_pivots, certified[0])
        elif layout_ok is not None:
            xor_unit_tail_degree_certificate(builder, reference, charts, 6, words[:2], e, d, layout_ok, certified[0])

    toggle_degree_certificate()
    boundary = builder.finish_circuit()
    if unit_first:
        stages["synthesis"] = boundary.operation_statistics().num_toffoli_like - sum(stages.values())
        widths["synthesis"] = boundary.num_qubits
    # The fixed degree here is from the frozen s2 witness.
    pad_words = []
    if padded:
        # Reuse the unused final second-head slope as a clean padding slot.
        e_pad = [builder.alloc_qubits(12) for _ in range(34 - len(e))]
        d_pad = [builder.alloc_qubits(12) for _ in range(36 - len(d))]
        pad_words = e_pad + d_pad
        evaluator, locator = e + [words[67]] + e_pad, d + d_pad
        original_lead = builder.alloc_qubits(12)
    else:
        evaluator, locator = e[:weight], d[:weight + 1]
        original_lead = words[67]
    lead = d[weight]
    lead_zero = reference.zero_flag(builder, lead) if live_degree else None
    if lead_zero is not None:
        builder.cx(lead_zero, lead[0])
    inverse = reference.ar.inverse(builder, lead)
    payload = evaluator + locator[:weight] + locator[weight + 1:]
    for word in payload:
        reference.scale_word(builder, word, inverse, lead)
    if not padded:
        reference.ar.erase_inverse(builder, lead, inverse)
        builder.free(inverse)
    builder.swap(lead, original_lead)
    if padded:
        builder.x(lead[0])
        padding = synthesis.padding_polynomial(weight, field)
        for bank in (evaluator, locator):
            synthesis.apply_padding(builder, reference, bank, padding)
        convert = converter(builder, evaluator, locator[:35], monic_root=True)
        reference.baseline.scan(builder, evaluator, locator[:35], masks,
                                skip_points=reference.baseline.SELECTED, node_polynomial=reference.Pscan)
        converter(builder, evaluator, locator[:35], True, phase_token=convert, monic_root=True)
        for bank in (evaluator, locator):
            synthesis.apply_padding(builder, reference, bank, padding, reverse=True)
    else:
        convert_monic = odd_monic_conversion(converter)
        if unit_first:
            record("normalize")
        convert = convert_monic(builder, evaluator, locator[:-1], history_scratch=lead)
        if unit_first:
            record("convert")
        projected_monic_scan(builder, reference, evaluator, locator[:-1], masks,
                             enable=certified[0] if live_degree else None)
        if unit_first:
            record("scan")
        convert_monic(builder, evaluator, locator[:-1], token=convert, history_scratch=lead)
        if unit_first:
            record("unconvert")
    if padded:
        builder.x(lead[0])
    builder.swap(lead, original_lead)
    if padded:
        builder.free(original_lead)
    else:
        inverse = reference.ar.inverse(builder, lead)
    for word in payload:
        reference.scale_word(builder, word, lead, inverse)
    reference.ar.erase_inverse(builder, lead, inverse)
    builder.free(inverse)
    if lead_zero is not None:
        builder.cx(lead_zero, lead[0])
        reference.clear_flag(builder, lead, lead_zero)
    for word in pad_words:
        builder.free(word)
    if unit_first:
        record("unnormalize")
    toggle_degree_certificate()
    absorb_projected_outer(builder, reference, words[2:4], u, v, None, reverse=True, phase_masks=phase_masks,
                           zero_pivots=zero_pivots)
    for pair in reversed(history):
        absorb_compact_pair(builder, reference, *pair, reverse=True, phase_masks=phase_masks, zero_pivots=zero_pivots)
        if pair[3] == 12 and layout_ok is not None:
            builder.flip_if_equal(pair[2][-1], 0, target=layout_ok)
    assert not phase_masks
    builder.x(words[66][0])
    if unit_first:
        record("unsynthesis")
    if not degree_certificate:
        toggle_certificate()
    if unit_first:
        record("uncertificate")
    if layout_ok is not None:
        builder.free(layout_ok)
    if zero_pivots is not None:
        builder.free(zero_pivots)
    builder.free(certified)
    extract_compact_heads(builder, reference, words, reverse=True, token=token, unit_first=unit_first,
                          replay_norms=replay_norms)
    reference.linear_words(builder, words, reference.matrix, True)
    reference.baseline.restore(builder, masks, mask_token)
    closed = builder.finish_circuit()
    if unit_first:
        stages["unextract"] = closed.operation_statistics().num_toffoli_like - sum(stages.values())
        widths["unextract"] = closed.num_qubits
        print(f"unit-tail static stage counts {stages} cumulative widths {widths}")

    inputs = [raw, raw]
    if live_degree:
        active = project_root / "docs/evidence/d4-compact-repair-20261115/cloud-replay/captures"
        inputs.extend(read_json(next((active / draw).glob("batch-*.json")))["shots"][0]["syndrome"]
                      for draw in ("s6", "s7"))
        inputs.extend(([0] * 70, syndrome(layout.forced_outer_pole(35, Random(5515), field), field)))
    raw_bits = api.to_bits(np.asarray(inputs), 12)
    syndrome_wires = reference.combine(words)
    coefficient_wires = reference.combine(e + d)
    scratch = km.array([km.q(i) for i in range(840, closed.num_qubits)])
    for seed in (715, 716):
        random_masks = np.random.default_rng(seed).integers(0, 4096, size=4095)
        mask_values = np.asarray([shot["mask"], *([random_masks] * (len(inputs) - 1))])
        mask_bits = api.to_bits(mask_values, 12)
        phases = [bool(sum((value & int(mask[position])).bit_count()
                           for position, value in support.items()) % 2) for mask in mask_values[:2]]
        assert phases[0] == shot["expected_phase"] and shot["phase_error"]
        if projection is not None:
            sim = km.Simulator(batch_size=len(inputs), seed=seed)
            sim.use_same_registers_as(projection)
            sim.write_across_shots(syndrome_wires, raw_bits)
            sim.write_across_shots(reference.combine(masks), mask_bits)
            sim.do(projection)
            phases.extend(sim.read_phase_flipped_across_shots().tolist()[2:])
        for circuit in (boundary, closed):
            sim = km.Simulator(batch_size=len(mask_values), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndrome_wires, raw_bits)
            sim.write_across_shots(reference.combine(masks), mask_bits)
            sim.do(circuit)
            if circuit is boundary:
                assert sim.read_across_shots(certified).ravel().tolist() == [True, True, *([False] * (len(inputs) - 2))]
                coefficients = sim.read_across_shots(coefficient_wires).T[:2].reshape(2, -1, 12) @ (1 << np.arange(12))
                for actual in coefficients:
                    scale = int(actual[len(e) + weight])
                    assert scale
                    wanted = [field.mul(scale, value) for value in synthesis.pad(expected_e, len(e))
                              + synthesis.pad(expected_d, len(d))]
                    assert actual.tolist() == wanted
            else:
                assert np.array_equal(sim.read_across_shots(syndrome_wires), raw_bits)
                assert np.array_equal(sim.read_across_shots(reference.combine(masks)), mask_bits)
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == phases
            print(f"unit-tail padded={padded} first={unit_first} degree-cert={degree_certificate} norms={replay_norms} "
                  f"live-degree={live_degree} "
                  f"seed={seed} full={circuit is closed} "
                  f"qubits={circuit.num_qubits} "
                  f"gates={sim.operation_statistics().num_toffoli_like / len(mask_values)}")


@pytest.mark.official
@pytest.mark.parametrize(("draw", "group", "degree"), [("s6", 6, 32), ("s7", 2, 33)])
def test_native_incoming_pole_repair_matches_captured_phase(native_d4, project_root, draw, group, degree):
    km, api, reference = native_d4
    field = GF4096()
    oracle = import_module("dqi_extraction_oracle")
    layout = import_module("dqi_compact_layout")
    converter = odd_monic_conversion(import_module("high_stream").convert_safe)
    root = project_root / "docs/evidence/d4-compact-repair-20261115/cloud-replay/captures"
    shot = read_json(next((root / draw).glob("batch-*.json")))["shots"][0]
    other = read_json(next((root / ("s7" if draw == "s6" else "s6")).glob("batch-*.json")))["shots"][0]
    support = decode(shot["syndrome"], field)
    assert len(support) == degree
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    n, expected_d = oracle.original_pair(support, kappas, field)
    outer = layout.split_pair(n, expected_d, 0, oracle.ExternalField(field))
    expected_e, remainder = _divide(_add(n, _multiply(outer.first, expected_d, field)), [2048, 1, 1], field)
    assert remainder == [0]

    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    phase_masks = []
    mask_token = reference.baseline.project(builder, words, masks)
    projection = builder.finish_circuit()
    reference.linear_words(builder, words, reference.matrix)
    token = extract_compact_heads(builder, reference, words, unit_first=True)
    charts = [(None if chain is None else chain["pole"], collapse) for collapse, _, chain in token]
    count = builder.alloc_qubits(6)
    certified = builder.alloc_qubits(1)
    tail_zero = None

    def scale_slope(denominator, reverse=False):
        inverse = reference.ar.inverse(builder, denominator)
        f, fi = (denominator, inverse) if reverse else (inverse, denominator)
        reference.scale_word(builder, words[-1], f, fi)
        reference.ar.erase_inverse(builder, denominator, inverse)
        builder.free(inverse)

    if degree == 32:
        seed = builder.alloc_qubits(12)
        builder.x(seed[0])
        u, v = [seed], []
    else:
        seed = compact_tail_jet(builder, reference, words, token, unit_first=True)
        tail_zero = reference.zero_flag(builder, seed)
        builder.cx(tail_zero, seed[0])
        scale_slope(seed)
        u, v = words[-2:], [seed]

    def apply_fold(index, heads, a, b, *, reverse=False):
        if index == group:
            return absorb_incoming_regular_pair(builder, reference, heads, a, b, 2 * index,
                                                 reverse=reverse, phase_masks=phase_masks, zero_pivots=count)
        return absorb_compact_pair(builder, reference, heads, a, b, 2 * index, None,
                                   reverse=reverse, phase_masks=phase_masks, zero_pivots=count)

    history = []
    discarded = []
    for index in reversed(range(1, 17)):
        start = 4 * index
        heads = words[start:start + 2], words[start + 2:start + 4]
        history.append((index, heads, u, v))
        u, v = apply_fold(*history[-1])
        if index == group + 1:
            u, discarded = u[:-2], u[-2:]
    e, d = absorb_projected_outer(builder, reference, words[2:4], u, v, None,
                                  phase_masks=phase_masks, zero_pivots=count)

    def toggle_certificate():
        xor_incoming_degree_certificate(builder, reference, charts, group, words[:2], e, d, discarded, count,
                                        certified[0], tail_zero=tail_zero)

    toggle_certificate()
    boundary = builder.finish_circuit()
    lead = d[-1]
    d_zero = reference.zero_flag(builder, lead)
    builder.cx(d_zero, lead[0])

    def normalize(reverse=False):
        inverse = reference.ar.inverse(builder, lead)
        f, fi = (lead, inverse) if reverse else (inverse, lead)
        for word in e + d[:-1]:
            reference.scale_word(builder, word, f, fi)
        reference.ar.erase_inverse(builder, lead, inverse)
        builder.free(inverse)

    normalize()
    # The certified zero spills pad the even-degree pair by X.
    # Off-chart the converter restores both spills with the scan disabled.
    evaluator, locator = ([discarded[0], *e], [discarded[1], *d[:-1]]) if degree == 32 else (e, d[:-1])
    conversion = converter(builder, evaluator, locator)
    projected_monic_scan(builder, reference, evaluator, locator, masks, enable=certified[0])
    converter(builder, evaluator, locator, token=conversion)
    normalize(True)
    builder.cx(d_zero, lead[0])
    reference.clear_flag(builder, lead, d_zero)
    toggle_certificate()
    absorb_projected_outer(builder, reference, words[2:4], u, v, None, reverse=True,
                           phase_masks=phase_masks, zero_pivots=count)
    for row in reversed(history):
        apply_fold(*row, reverse=True)
    assert not phase_masks
    builder.free(certified)
    builder.free(count)
    if tail_zero is None:
        builder.x(seed[0])
        builder.free(seed)
    else:
        scale_slope(seed, True)
        builder.cx(tail_zero, seed[0])
        reference.clear_flag(builder, seed, tail_zero)
        compact_tail_jet(builder, reference, words, token, reverse=True, denominator=seed, unit_first=True)
    extract_compact_heads(builder, reference, words, reverse=True, token=token, unit_first=True, replay_norms=True)
    reference.linear_words(builder, words, reference.matrix, True)
    reference.baseline.restore(builder, masks, mask_token)
    closed = builder.finish_circuit()

    raw_bits = api.to_bits(np.asarray([shot["syndrome"]] * 2 + [other["syndrome"], [0] * 70]), 12)
    syndrome_wires = reference.combine(words)
    mask_wires = reference.combine(masks)
    scratch = km.array([km.q(i) for i in range(840, closed.num_qubits)])
    for seed_value in (747, 748):
        fresh = np.random.default_rng(seed_value).integers(0, 4096, size=4095)
        mask_values = np.asarray([shot["mask"], fresh, other["mask"], fresh])
        mask_bits = api.to_bits(mask_values, 12)
        expected = [bool(sum((value & int(mask[position])).bit_count() for position, value in support.items()) % 2)
                    for mask in mask_values[:2]]
        assert expected[0] == shot["expected_phase"]
        for circuit in (projection, boundary, closed):
            sim = km.Simulator(batch_size=4, seed=seed_value, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndrome_wires, raw_bits)
            sim.write_across_shots(mask_wires, mask_bits)
            sim.do(circuit)
            if circuit is projection:
                expected.extend(sim.read_phase_flipped_across_shots().tolist()[2:])
            elif circuit is boundary:
                assert sim.read_across_shots(certified).ravel().tolist() == [True, True, False, False]
                values = sim.read_across_shots(reference.combine(e + d)).T[:2].reshape(2, -1, 12) @ (
                    1 << np.arange(12)
                )
                e_padded = expected_e + [0] * (len(e) - len(expected_e))
                for actual in values:
                    scale = int(actual[-1])
                    assert scale
                    assert actual.tolist() == [field.mul(scale, coefficient) for coefficient in e_padded + expected_d]
            else:
                assert np.array_equal(sim.read_across_shots(syndrome_wires), raw_bits)
                assert np.array_equal(sim.read_across_shots(mask_wires), mask_bits)
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == expected
                print(f"incoming {draw} degree={degree} seed={seed_value} qubits={closed.num_qubits} "
                      f"mean_gates={sim.operation_statistics().num_toffoli_like / 4}")


@pytest.mark.official
@pytest.mark.parametrize(
    "outer_poles", [(), (0, 1), (0, 2)], ids=["captured-and-regular", "adjacent-outer", "separated-outer"],
)
def test_native_shared_d4_decodes_all_captured_pole_charts(native_d4, project_root, outer_poles):
    km, api, reference = native_d4
    field = GF4096()
    oracle = import_module("dqi_extraction_oracle")
    layout = import_module("dqi_compact_layout")
    converter = import_module("high_stream").convert_safe
    evidence = project_root / "docs/evidence"
    directories = (
        evidence / "dqi-phase-replay-20261115/results",
        evidence / "d4-compact-repair-20261115/cloud-replay/captures",
    )
    rows = []
    for root in directories:
        for path in sorted(root.glob("s*/batch-*.json")):
            capture = read_json(path)
            rows.extend(capture["shots"] + capture["controls"])
    assert len(rows) == 12
    support = [decode(row["syndrome"], field) for row in rows]
    witnesses = read_json(evidence / "d4-compact-repair-20261115/multiple-poles.json")["cases"]

    def append_row(errors, seed):
        raw = syndrome(errors, field)
        mask = np.random.default_rng(seed).integers(0, 4096, size=4095)
        phase = bool(sum((value & int(mask[position])).bit_count() for position, value in errors.items()) % 2)
        rows.append({"syndrome": raw, "mask": mask, "expected_phase": phase})
        support.append(errors)

    if outer_poles:
        rows.clear()
        support.clear()
        generate = import_module("dqi_compact_multi_pole").forced_sequence
        if outer_poles == (0, 1):
            pattern = (True, True)
            prefixes = (None, None, None)
            witness_index = 0
            tail_lengths = [4, 3]
        else:
            pattern = (True, False, True)
            prefixes = (
                None,
                (((17, 11), (0, 1)), ((8, 39), (38, 9)), ((273, 23), (0, 1))),
                (((123, 6), (0, 1)), ((731, 167), (35, 80)), ((363, 17), (0, 1))),
            )
            witness_index = 1
            tail_lengths = [5, 4]
        for seed, heads in enumerate(prefixes, 89342):
            errors = generate(field, pattern, seed=seed, heads=heads)
            profile = layout.audit_input(errors, field)
            assert profile["local_poles"] == list(outer_poles) and not profile["incoming_poles"]
            assert profile["tail_lengths"] == tail_lengths
            append_row(errors, seed)
        assert rows[0]["syndrome"] == witnesses[witness_index]["syndrome"]
        rejected = witnesses[witness_index + 1]
    else:
        rng = np.random.default_rng(2735)
        for index in range(3):
            errors = {int(p): int(v) for p, v in zip(
                rng.choice(4095, 35, replace=False), rng.integers(1, 4096, 35), strict=True,
            )}
            trace = oracle.paired_reference(syndrome(errors, field), field)
            assert not trace["pole_groups"] and len(trace["words"]) == 68 and "tail" in trace
            append_row(errors, 773 + index)
        rejected = witnesses[0]
        assert rejected["tail_lengths"] == [4, 3]
    assert rejected["weight"] == 35
    kappas = [field.mul(c, c)^c^2048 for c in range(0, 34, 2) for _ in range(2)]
    expected = []
    for values in support:
        n, d = oracle.original_pair(values, kappas, field)
        outer = layout.split_pair(n, d, 0, oracle.ExternalField(field))
        e, remainder = _divide(_add(n, _multiply(outer.first, d, field)), [2048, 1, 1], field)
        assert remainder == [0]
        expected.append((e + [0] * (35 - len(e)), d + [0] * (36 - len(d))))

    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    projection = km.CircuitBuilder()
    projection_words = [projection.alloc_qubits(12) for _ in range(70)]
    projection_masks = [projection.alloc_bits(12) for _ in range(4095)]
    projection_token = reference.baseline.project(projection, projection_words, projection_masks)
    reference.baseline.restore(projection, projection_masks, projection_token)
    projection_only = projection.finish_circuit()
    prototypes = []

    def capture_coefficients(e, d, certified):
        prototypes.append((builder.finish_circuit(), reference.combine(e + d), km.array([certified])))

    rejected_wire = builder.alloc_qubits(1)
    emit_shared_projected_d4(
        builder, reference, converter, words, masks, on_coefficients=capture_coefficients, rejected=rejected_wire[0],
        outer_poles=outer_poles,
    )
    boundary, coefficients, certified = prototypes[0]
    closed = builder.finish_circuit()
    syndrome_wires = reference.combine(words)
    mask_wires = reference.combine(masks)
    scratch = km.array([km.q(i) for i in range(841, closed.num_qubits)])
    raw_bits = api.to_bits(np.asarray([row["syndrome"] for row in rows] + [rejected["syndrome"], [0] * 70]), 12)

    for seed in (761, 762):
        fresh = np.random.default_rng(seed).integers(0, 4096, size=4095)
        masks_for_rows = [row["mask"] for row in rows] if seed == 761 else [fresh] * len(rows)
        mask_values = np.asarray([*masks_for_rows, fresh, fresh])
        masks_bits = api.to_bits(mask_values, 12)
        phases = [bool(sum((value & int(mask[position])).bit_count() for position, value in values.items()) % 2)
                  for values, mask in zip(support, mask_values[:len(rows)], strict=True)]
        if seed == 761:
            assert phases == [row["expected_phase"] for row in rows]
        projection_sim = km.Simulator(batch_size=1, seed=seed)
        projection_sim.use_same_registers_as(projection_only)
        projection_sim.write_across_shots(reference.combine(projection_words), raw_bits[:, -2:-1])
        projection_sim.write_across_shots(reference.combine(projection_masks), masks_bits[:, -2:-1])
        projection_sim.do(projection_only)
        phases.extend((bool(projection_sim.read_phase_flipped_across_shots()[0]), False))
        for circuit in (boundary, closed):
            sim = km.Simulator(batch_size=len(mask_values), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndrome_wires, raw_bits)
            sim.write_across_shots(mask_wires, masks_bits)
            sim.do(circuit)
            if circuit is boundary:
                flags = sim.read_across_shots(certified).ravel()
                assert flags[:len(rows)].all() and not flags[-2]
                values = sim.read_across_shots(coefficients).T[:len(rows)].reshape(len(rows), -1, 12) @ (
                    1 << np.arange(12)
                )
                for actual, (e, d) in zip(values, expected, strict=True):
                    index = max(i for i, coefficient in enumerate(d) if coefficient)
                    lead = int(actual[35 + index])
                    assert lead
                    assert actual.tolist() == [field.mul(lead, coefficient) for coefficient in e + d]
            else:
                assert np.array_equal(sim.read_across_shots(syndrome_wires), raw_bits)
                assert np.array_equal(sim.read_across_shots(mask_wires), masks_bits)
                assert sim.read_across_shots(rejected_wire).ravel().tolist() == [False] * len(rows) + [True, False]
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == phases
                print(f"shared D4 outer_poles={outer_poles} seed={seed} qubits={closed.num_qubits} "
                      f"mean_gates={sim.operation_statistics().num_toffoli_like / len(mask_values)}")


@pytest.mark.official
def test_native_mixed_tail_solver_restores_pivoted_and_singular_systems(native_d4):
    km, api, reference = native_d4
    builder = km.CircuitBuilder()
    rows = [[builder.alloc_qubits(12) for _ in range(5)] for _ in range(4)]
    targets = [builder.alloc_qubits(12) for _ in rows]
    valid = builder.alloc_qubits(1)

    def consume(solution, singular):
        active = builder.alloc_qubits(1)[0]
        builder.flip_if_equal(singular, 0, target=active)
        builder.cx(active, valid[0])
        for value, target in zip(solution, targets, strict=True):
            builder.ccx(active, value, target)
        builder.flip_if_equal(singular, 0, target=active)
        builder.free(active)

    _with_solution(builder, reference, rows, consume)
    forward = builder.finish_circuit()
    builder.z(targets[0][0])
    builder.z(valid[0])
    _with_solution(builder, reference, rows, consume)
    closed = builder.finish_circuit()
    field = GF4096()
    solution = [18, 365, 112, 997]
    matrices = np.zeros((2, 4, 5), dtype=np.int64)
    for row, col in enumerate((1, 2, 3, 0)):
        matrices[0, row, col] = row + 21
        matrices[0, row, -1] = field.mul(row + 21, solution[col])
    matrices[1] = matrices[0]
    matrices[1, -1] = matrices[1, -2]
    bits = api.to_bits(matrices.reshape(2, -1), 12)
    wires = reference.combine([word for row in rows for word in row])
    scratch = km.array([km.q(i) for i in range(len(wires), closed.num_qubits)])
    for seed in (811, 812):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=2, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(wires, bits)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(wires), bits)
            if circuit is forward:
                expected = api.to_bits(np.asarray([solution, [0] * 4]), 12)
                assert np.array_equal(sim.read_across_shots(reference.combine(targets)), expected)
                assert sim.read_across_shots(valid).ravel().tolist() == [True, False]
            else:
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == [True, False]


@pytest.mark.official
def test_native_projected_outer_feeds_banked_converter_and_full_scan(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    layout = import_module("dqi_compact_layout")
    oracle = import_module("dqi_extraction_oracle")
    converter = import_module("high_stream").convert_safe
    extension = oracle.ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    rng = np.random.default_rng(5514)
    supports = [{
        int(position): int(value) for position, value in zip(
            rng.choice(4095, 35, replace=False), rng.integers(1, 4096, size=35), strict=True,
        )
    } for _ in range(8)]
    pole = oracle.doubled_node_fixtures()[0]
    supports.append(dict(zip(pole["error_positions"], pole["error_values"], strict=True)))
    supports.append(layout.forced_outer_pole(35, Random(5515), field))
    builder = km.CircuitBuilder()
    syndrome_words = [builder.alloc_qubits(12) for _ in range(70)]
    second = [builder.alloc_qubits(12) for _ in range(2)]
    u, v = ([builder.alloc_qubits(12) for _ in range(length)] for length in (36, 34))
    chart = builder.alloc_qubits(1)[0]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    polynomial_wires = km.array([wire for word in [*u, *second, *v] for wire in word])
    syndrome_wires = reference.combine(syndrome_words)
    mask_wires = reference.combine(masks)
    phase_masks = []
    evaluator, locator = absorb_projected_outer(builder, reference, second, u, v, chart, phase_masks=phase_masks)
    mask_token = reference.baseline.project(builder, syndrome_words, masks)
    token = converter(builder, evaluator[:35], locator[:35], monic_root=True)
    reference.baseline.scan(
        builder, evaluator[:35], locator[:35], masks,
        skip_points=reference.baseline.SELECTED, node_polynomial=reference.Pscan,
    )
    converter(builder, evaluator[:35], locator[:35], True, phase_token=token, monic_root=True)
    reference.baseline.restore(builder, masks, mask_token)
    absorb_projected_outer(builder, reference, second, u, v, chart, reverse=True, phase_masks=phase_masks)
    assert not phase_masks
    circuit = builder.finish_circuit()
    states = np.zeros((len(supports), 72), dtype=np.int64)
    phases = []
    collapse = []
    mask_values = rng.integers(0, 4096, size=(len(supports), 4095), dtype=np.int64)
    syndromes = []
    for index, support in enumerate(supports):
        n, d = oracle.original_pair(support, kappas, field)
        # The weight-three pole fixture is padded by the other 16
        # distinct irreducible nodes. Their common factor cancels in
        # each base-field residue and gives an implicit monic locator.
        if len(support) == 3:
            for kappa in kappas[2::2]:
                q = [kappa, 1, 1]
                n, d = _multiply(n, q, field), _multiply(d, q, field)
        assert len(d) == 36 and d[-1] == 1
        fold = layout.split_pair(n, d, 0, extension)
        assert not fold.incoming_pole
        states[index, :len(fold.u)] = fold.u
        states[index, 36:38] = fold.second
        states[index, 38:38 + len(fold.v)] = fold.v
        collapse.append(fold.collapse)
        syndromes.append(syndrome(support, field))
        phases.append(sum((symbol & int(mask_values[index, position])).bit_count()
                          for position, symbol in support.items()) % 2)
    assert collapse[-2:] == [True, True]
    expected_masks = api.to_bits(mask_values, 12)
    expected_syndromes = api.to_bits(np.asarray(syndromes), 12)
    expected_polynomials = api.to_bits(states, 12)
    chart_bits = np.asarray([collapse], dtype=bool)
    chart_wire = km.array([chart])
    live = len(polynomial_wires) + len(syndrome_wires) + 1
    scratch = km.array([km.q(index) for index in range(live, circuit.num_qubits)])
    for seed in (903, 904):
        sim = km.Simulator(batch_size=len(supports), seed=seed)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(polynomial_wires, expected_polynomials)
        sim.write_across_shots(syndrome_wires, expected_syndromes)
        sim.write_across_shots(mask_wires, expected_masks)
        sim.write_across_shots(chart_wire, chart_bits)
        sim.do(circuit)
        assert np.array_equal(sim.read_phase_flipped_across_shots(), phases)
        assert np.array_equal(sim.read_across_shots(polynomial_wires), expected_polynomials)
        assert np.array_equal(sim.read_across_shots(syndrome_wires), expected_syndromes)
        assert np.array_equal(sim.read_across_shots(mask_wires), expected_masks)
        assert np.array_equal(sim.read_across_shots(chart_wire), chart_bits)
        assert not sim.read_across_shots(scratch).any()


def test_full_weight_tail_recovers_nonzero_quadratic_and_denominator_slope(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    oracle = import_module("dqi_extraction_oracle")
    field = GF4096()
    rng = np.random.default_rng(2735)
    errors = {int(p): int(v) for p, v in zip(
        rng.choice(4095, 35, replace=False), rng.integers(1, 4096, 35), strict=True,
    )}
    captured = oracle.paired_reference(syndrome(errors, field), field)
    n, d = captured["tail"]
    assert len(n) == 3 and len(d) == 2
    jet = n[0], d[0], field.mul(n[1], d[0]) ^ field.mul(n[0], d[1])
    words = captured["words"]
    pairs = [
        (
            (words[4 * i:4 * i + 2], words[4 * i + 2:4 * i + 4]),
            field.mul(2 * i, 2 * i) ^ (2 * i) ^ 2048,
            i in captured["pole_groups"],
        )
        for i in range(17)
    ]
    assert recover_quadratic_tail(jet, pairs, field) == (n, d)


@pytest.fixture
def native_d4(project_root, monkeypatch):
    backend = project_root / "vendor/backend.json"
    if not sys.platform.startswith("linux") or not backend.is_file():
        pytest.skip("pinned native Linux backend required")
    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    _, km, api, _ = import_module("dqi_history_depth").runtime(backend)
    monkeypatch.setitem(sys.modules, "circ", km)
    path = project_root / "third_party/dqi-d4/src/exp/r-main/stream/decode.py"
    spec = spec_from_file_location("native_pole_jet_test_decoder", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return km, api, module.replay_erase.ref


@pytest.mark.official
@pytest.mark.parametrize("mutation", [None, "flip_guard", "drop_phase"])
def test_native_common_padding_exchange_restores_pair_and_guard(native_d4, mutation):
    km, api, reference = native_d4
    field = GF4096()
    banks = ((1, 3, 5, 7, 9), (1, 4, 6, 8, 10, 12))

    def xor_linear(builder, source, target, columns):
        for wire, column in zip(source, columns, strict=True):
            for bit, output in enumerate(target):
                if column >> bit & 1:
                    builder.cx(wire, output)

    def zero_xor(builder, word, output):
        flag = reference.zero_flag(builder, word)
        builder.cx(flag, output)
        reference.clear_flag(builder, word, flag)

    class WithoutRepayment:
        def __init__(self, builder):
            self.builder = builder

        def __getattr__(self, name):
            return getattr(self.builder, name)

        def del_and(self, left, right, target):
            if hasattr(target, "__len__") and len(target) == 12:
                unrecorded = self.builder.alloc_bits(12)
                self.builder.hmr(target, unrecorded)
                self.builder.free(unrecorded)
            else:
                self.builder.del_and(left, right, target)

    detected = False
    for padding in selected_padding(field, [1]):
        original = [_multiply(list(poly), list(padding.original), field) for poly in banks]
        replacement = [_multiply(list(poly), list(padding.replacement), field) for poly in banks]
        changed_n = original[0][:]
        changed_n[0] ^= 1
        changed_d = original[1][:]
        changed_d[0] ^= 1
        blocked = [[*changed_n, *original[1]], [*original[0], *changed_d]]
        inputs = np.asarray([[*original[0], *original[1]], *blocked])
        expected = np.asarray([[*replacement[0], *replacement[1]], *blocked])

        builder = km.CircuitBuilder()
        words = tuple([builder.alloc_qubits(12) for _ in poly] for poly in original)
        wires = km.array([q for bank in words for word in bank for q in word])
        flag = exchange_padding(builder, words, padding, field, xor_linear, zero_xor)
        assert flag is not None
        prefix = builder.finish_circuit()
        builder.z(flag[0])
        if mutation == "flip_guard":
            builder.x(flag[0])
        inverse = WithoutRepayment(builder) if mutation == "drop_phase" else builder
        exchange_padding(inverse, words, padding, field, xor_linear, zero_xor, flag=flag)
        closed = builder.finish_circuit()
        for seed in (761, 762):
            sim = km.Simulator(batch_size=3, seed=seed)
            sim.use_same_registers_as(prefix)
            sim.write_across_shots(wires, api.to_bits(inputs, 12))
            sim.do(prefix)
            assert np.array_equal(sim.read_across_shots(wires), api.to_bits(expected, 12))
            assert sim.read_across_shots(flag).tolist() == [[True, False, False]]
            assert not sim.read_phase_flipped_across_shots().any()

            sim = km.Simulator(batch_size=3, seed=seed)
            sim.use_same_registers_as(closed)
            sim.write_across_shots(wires, api.to_bits(inputs, 12))
            sim.do(closed)
            restored = np.array_equal(sim.read_across_shots(wires), api.to_bits(inputs, 12))
            scratch = km.array([q for q in map(km.q, range(closed.num_qubits)) if q not in set(wires)])
            clean = not sim.read_across_shots(scratch).any()
            phase = sim.read_phase_flipped_across_shots().tolist() == [True, False, False]
            if mutation is None:
                assert restored and clean and phase
            elif mutation == "drop_phase":
                assert restored and clean
                detected |= not phase
            else:
                detected |= not (restored and clean)
    if mutation is not None:
        assert detected


@pytest.mark.official
@pytest.mark.parametrize("paired", [False, True])
def test_native_local_pole_jet_matches_extension_reference(native_d4, paired):
    km, api, reference = native_d4
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12), builder.alloc_qubits(12)] for _ in range(2 if paired else 1)]
    chart = builder.alloc_qubits(1)[0] if paired else None
    numerator, denominator, derivative = (builder.alloc_qubits(24) for _ in range(3))
    factor, coordinate = 19, 12

    def emit(reverse=False):
        state = numerator, denominator, derivative
        if paired:
            paired_external_jet(builder, reference, heads, chart, state, factor, coordinate, reverse=reverse)
        else:
            local_pole_jet(builder, reference, heads[0], *state, factor, coordinate, reverse=reverse)

    emit()
    forward = builder.finish_circuit()
    emit(reverse=True)
    closed = builder.finish_circuit()

    field = GF4096()
    ext = import_module("dqi_extraction_oracle").ExternalField(field)
    rng = np.random.default_rng(101)
    states = rng.integers(0, 1 << 24, size=(64, 3))
    head_values = rng.integers(0, 4096, size=(64, 2 * len(heads)))
    charts = np.arange(64) % 2

    def evaluate_head(lo, slope):
        return (int(lo) ^ field.mul(int(slope), coordinate)) | (int(slope) << 12)

    pole_shot = 1 if paired else 0
    states[pole_shot, 0] = ext.mul(evaluate_head(*head_values[pole_shot, :2]), int(states[pole_shot, 1]))
    expected = np.empty_like(states)
    for index, (row, words) in enumerate(zip(states, head_values, strict=True)):
        state = int(row[0]), int(row[1]), int(row[2])
        if paired and charts[index] == 0:
            # Apply the two regular rational steps independently.
            for lo, slope in zip(words[::2], words[1::2], strict=True):
                n, d, l_value = state
                s = n ^ ext.mul(evaluate_head(lo, slope), d)
                state = (
                    ext.mul(factor, d), s,
                    ext.mul(factor, l_value ^ ext.mul(int(slope), ext.mul(d, d))) ^ ext.mul(d, s),
                )
        else:
            state = forward_local_pole_jet(state, evaluate_head(*words[:2]), int(words[1]), factor, ext)
        expected[index] = state
    assert expected[pole_shot, 1] == 0
    chart_wires = km.array(numerator + denominator + derivative)
    head_wires = km.array([wire for pair in heads for word in pair for wire in word])
    controls = km.array([chart]) if paired else None
    live = 72 + 24 * len(heads) + int(paired)
    for seed in (177, 178):
        for circuit, want in ((forward, expected), (closed, states)):
            sim = km.Simulator(batch_size=64, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(head_wires, api.to_bits(head_values, 12))
            sim.write_across_shots(chart_wires, api.to_bits(states, 24))
            if controls is not None:
                sim.write_across_shots(controls, charts[None, :].astype(bool))
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(chart_wires), api.to_bits(want, 24))
            assert np.array_equal(sim.read_across_shots(head_wires), api.to_bits(head_values, 12))
            if controls is not None:
                assert np.array_equal(sim.read_across_shots(controls), charts[None, :])
            if circuit.num_qubits > live:
                scratch = km.array([km.q(i) for i in range(live, circuit.num_qubits)])
                assert not sim.read_across_shots(scratch).any()
            assert not sim.read_phase_flipped_across_shots().any()


@pytest.mark.official
def test_native_polynomial_pair_matches_both_charts_and_restores(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    width, kappa = 6, 2048
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)]
    chart = builder.alloc_qubits(1)[0]
    banks = tuple([builder.alloc_qubits(12) for _ in range(width)] for _ in range(2))
    paired_polynomial_synthesis(builder, reference, heads, chart, banks, kappa)
    forward = builder.finish_circuit()
    paired_polynomial_synthesis(builder, reference, heads, chart, banks, kappa, reverse=True)
    closed = builder.finish_circuit()
    rng = np.random.default_rng(245)
    states = rng.integers(0, 4096, size=(64, 2 * width))
    head_words = rng.integers(0, 4096, size=(64, 4))
    pole = np.arange(64) % 2 == 1
    expected = np.zeros_like(states)
    for index, row in enumerate(states):
        n, d = synthesize_pair(
            (row[:width].tolist(), row[width:].tolist()),
            (head_words[index, :2].tolist(), head_words[index, 2:].tolist()), kappa, bool(pole[index]), field,
        )
        expected[index, :min(width, len(n))] = n[:width]
        expected[index, width:width + min(width, len(d))] = d[:width]
    bank_wires = km.array([wire for bank in banks for word in bank for wire in word])
    head_wires = km.array([wire for pair in heads for word in pair for wire in word])
    chart_wire = km.array([chart])
    scratch = km.array([km.q(forward.num_qubits - 1)])
    for seed in (104, 105):
        for circuit, want in ((forward, expected), (closed, states)):
            sim = km.Simulator(batch_size=64, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(bank_wires, api.to_bits(states, 12))
            sim.write_across_shots(head_wires, api.to_bits(head_words, 12))
            sim.write_across_shots(chart_wire, pole[None, :])
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(bank_wires), api.to_bits(want, 12))
            assert np.array_equal(sim.read_across_shots(head_wires), api.to_bits(head_words, 12))
            assert np.array_equal(sim.read_across_shots(chart_wire), pole[None, :])
            assert not sim.read_across_shots(scratch).any()
            assert not sim.read_phase_flipped_across_shots().any()


@pytest.mark.official
def test_native_explicit_bank_scan_phase_and_restoration(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    builder = km.CircuitBuilder()
    banks = tuple([builder.alloc_qubits(12) for _ in range(3)] for _ in range(2))
    points = (7, 10)
    masks = {point: builder.alloc_bits(12) for point in points}
    paired_residue_scan(builder, reference, banks, masks, points)
    circuit = builder.finish_circuit()
    rng = np.random.default_rng(570)
    states = rng.integers(0, 4096, size=(64, 6))
    mask_words = rng.integers(0, 4096, size=(64, 2))
    expected = np.zeros(64, dtype=bool)
    for index, row in enumerate(states):
        a = row[:3].tolist()
        d = row[3:].tolist()
        if index % 3 != 0:
            beta = field.exp[points[index % 2]]
            d[0] = field.evaluate([0, *d[1:]], beta)
            row[3] = d[0]
        for point, mask in zip(points, mask_words[index], strict=True):
            beta = field.exp[point]
            if field.evaluate(d, beta) == 0 and d[1]:
                divisor = field.mul(field.mul(d[1], beta), field.evaluate(reference.P, beta))
                recovered = field.div(field.evaluate(a, beta), divisor)
                expected[index] ^= bool((recovered & int(mask)).bit_count() % 2)
    bank_wires = km.array([wire for bank in banks for word in bank for wire in word])
    mask_wires = km.array([wire for point in points for wire in masks[point]])
    scratch = km.array([km.q(i) for i in range(len(bank_wires), circuit.num_qubits)])
    for seed in (507, 508):
        sim = km.Simulator(batch_size=64, seed=seed)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(bank_wires, api.to_bits(states, 12))
        sim.write_across_shots(mask_wires, api.to_bits(mask_words, 12))
        sim.do(circuit)
        assert np.array_equal(sim.read_phase_flipped_across_shots(), expected)
        assert np.array_equal(sim.read_across_shots(bank_wires), api.to_bits(states, 12))
        assert np.array_equal(sim.read_across_shots(mask_wires), api.to_bits(mask_words, 12))
        assert not sim.read_across_shots(scratch).any()


@pytest.mark.official
def test_native_tail_system_retains_singularity_and_clears_products(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    builder = km.CircuitBuilder()
    matrix = [[builder.alloc_qubits(12) for _ in range(3)] for _ in range(3)]
    rhs = [builder.alloc_qubits(12) for _ in range(3)]
    outputs = [builder.alloc_qubits(12) for _ in range(3)]
    singular = builder.alloc_qubits(1)[0]
    xor_tail_system_solution(builder, reference, matrix, rhs, outputs, singular)
    forward = builder.finish_circuit()
    xor_tail_system_solution(builder, reference, matrix, rhs, outputs, singular)
    closed = builder.finish_circuit()
    rng = np.random.default_rng(3315)
    inputs = np.triu(rng.integers(1, 4096, size=(64, 3, 3)))
    inputs[::4, 2] = inputs[::4, 1]
    planted = rng.integers(0, 4096, size=(64, 3))
    right = np.array([
        [field.mul(int(a), int(x)) ^ field.mul(int(b), int(y)) ^ field.mul(int(c), int(z)) for a, b, c in mat]
        for mat, (x, y, z) in zip(inputs, planted, strict=True)
    ])
    bad = np.arange(64) % 4 == 0
    planted[bad] = 0
    wires = km.array([wire for row in matrix for word in row for wire in word] + [wire for word in rhs for wire in word])
    targets = km.array([wire for word in outputs for wire in word])
    payload = api.to_bits(np.concatenate((inputs.reshape(64, 9), right), axis=1), 12)
    target_seed = rng.integers(0, 4096, size=(64, 3))
    for circuit, expected, predicate in (
        (forward, target_seed ^ planted, bad), (closed, target_seed, np.zeros_like(bad)),
    ):
        sim = km.Simulator(batch_size=64, seed=618)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(wires, payload)
        sim.write_across_shots(targets, api.to_bits(target_seed, 12))
        sim.do(circuit)
        assert np.array_equal(sim.read_across_shots(wires), payload)
        assert np.array_equal(sim.read_across_shots(targets), api.to_bits(expected, 12))
        assert np.array_equal(sim.read_across_shots(km.array([singular]))[0], predicate)
        scratch = km.array([km.q(i) for i in range(len(wires) + len(targets) + 1, circuit.num_qubits)])
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()


@pytest.mark.official
def test_native_regular_tail_from_live_full_weight_heads(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    oracle = import_module("dqi_extraction_oracle")
    rng = np.random.default_rng(2735)
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(34)]
    jet = [builder.alloc_qubits(12) for _ in range(3)]
    outputs = [builder.alloc_qubits(12) for _ in range(3)]
    singular = builder.alloc_qubits(1)[0]
    xor_regular_tail_coefficients(builder, reference, heads, jet, outputs, singular)
    circuit = builder.finish_circuit()
    head_data, jet_data, expected = [], [], []
    for weight in (35, 35, 34, 35):
        errors = {int(p): int(v) for p, v in zip(
            rng.choice(4095, weight, replace=False), rng.integers(1, 4096, weight), strict=True,
        )}
        captured = oracle.paired_reference(syndrome(errors, field), field)
        assert not captured["pole_groups"]
        head_data.append(captured["words"])
        n, d = captured["tail"]
        n += [0] * (3 - len(n))
        d += [0] * (2 - len(d))
        jet_data.append([n[0], d[0], field.mul(n[1], d[0]) ^ field.mul(n[0], d[1])])
        expected.append([n[1], n[2], d[1]])
    mask = km.array([wire for head in heads for reg in head for wire in reg] + [wire for reg in jet for wire in reg])
    target = km.array([wire for word in outputs for wire in word])
    one = km.array([singular])
    scratch = km.array([km.q(i) for i in range(len(mask) + len(target) + 1, circuit.num_qubits)])
    payload = api.to_bits(np.concatenate((np.array(head_data), np.array(jet_data)), axis=1), 12)
    sim = km.Simulator(batch_size=4, seed=437)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(mask, payload)
    sim.do(circuit)
    singular_shots = sim.read_across_shots(one)[0]
    assert singular_shots.tolist() == [False, False, True, False]
    solved = np.array(expected)
    solved[singular_shots] = 0
    assert np.array_equal(sim.read_across_shots(target), api.to_bits(solved, 12))
    # The weight-34 chart is still valid. Its one-sided seed is the
    # fallback used when the regular degree constraints are singular.
    assert expected[2] == [field.div(jet_data[2][2], jet_data[2][1]), 0, 0]
    assert np.array_equal(sim.read_across_shots(mask), payload)
    assert not sim.read_across_shots(scratch).any()
    assert not sim.read_phase_flipped_across_shots().any()


@pytest.mark.official
def test_native_regular_tail_determinant_handles_zero_denominator(native_d4):
    km, api, reference = native_d4
    field = GF4096()
    oracle = import_module("dqi_extraction_oracle")
    rng = np.random.default_rng(2735)
    support = {int(position): int(value) for position, value in zip(
        rng.choice(4095, 35, replace=False), rng.integers(1, 4096, 35), strict=True,
    )}
    trace = oracle.paired_reference(syndrome(support, field), field)
    heads = trace["words"]
    assert len(heads) == 68
    a, c, b, d = 0, 0, 1, 0
    for low, high in zip(heads[::2], heads[1::2], strict=True):
        a, c, b, d = b, d, a, c
        d ^= field.mul(high, c) ^ field.mul(low, a)
        b ^= field.mul(high, a)
        d ^= b
    n0, t = 123, 351
    assert b
    s = field.div(field.mul(d, t), b)
    wanted = [field.mul(c, t) ^ field.mul(a, s), field.mul(a, t), field.mul(b, t)]
    wronskian = field.mul(n0, wanted[-1])
    assert wronskian

    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    denominator = builder.alloc_qubits(12)
    charts = builder.alloc_qubits(33)
    extraction = [(charts[i], None, {"pole": charts[16 + i]} if i else None) for i in range(17)]
    tail = [builder.alloc_qubits(12) for _ in range(3)]
    failures = builder.alloc_qubits(7)
    _xor_tail_seed(builder, reference, words, denominator, extraction, failures, targets=tail)
    forward = builder.finish_circuit()
    builder.z(tail[0][0])
    builder.z(failures[0])
    phase_masks = []
    for word in tail:
        mask = builder.alloc_bits(12)
        builder.hmr(word, mask)
        builder.free(word)
        phase_masks.append(mask)
    _xor_tail_seed(builder, reference, words, denominator, extraction, failures, reverse=True, phase_masks=phase_masks)
    for mask in phase_masks:
        builder.free(mask)
    closed = builder.finish_circuit()
    inputs = reference.combine([*words, denominator])
    values = api.to_bits(np.asarray([[*heads, n0, wronskian, 0]] * 2), 12)
    chart_values = np.zeros((33, 2), dtype=bool)
    chart_values[0, 1] = True
    scratch = km.array([km.q(i) for i in range(len(inputs) + len(charts), closed.num_qubits)])
    for seed in (775, 776):
        for circuit in (forward, closed):
            sim = km.Simulator(batch_size=2, seed=seed)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(inputs, values)
            sim.write_across_shots(charts, chart_values)
            sim.do(circuit)
            assert np.array_equal(sim.read_across_shots(inputs), values)
            assert np.array_equal(sim.read_across_shots(charts), chart_values)
            if circuit is forward:
                expected = api.to_bits(np.asarray([wanted, [0, 0, 0]]), 12)
                assert np.array_equal(sim.read_across_shots(reference.combine(tail)), expected)
                assert sim.read_across_shots(failures).T.tolist() == [[False] * 7, [True] + [False] * 6]
            else:
                assert not sim.read_across_shots(scratch).any()
                assert sim.read_phase_flipped_across_shots().tolist() == [bool(wanted[0] & 1), True]


def _small_rational_fixture():
    field = GF4096()
    geometry = (0, 0, field.mul(2048, 2048), 0, 1, 0, 1)
    errors = {5: 11, 9: 7}
    a, b = (field.exp[position] for position in errors)
    first, second = (field.mul(field.mul(v, field.exp[i]), field.evaluate(geometry, field.exp[i]))
                     for i, v in errors.items())
    numerator = [field.mul(first, b) ^ field.mul(second, a), first ^ second]
    denominator = [field.mul(a, b), a ^ b, 1]
    return field, geometry, syndrome(errors, field, count=6), numerator, denominator


def test_moment_certificate_accepts_exact_ratio_and_rejects_perturbation():
    field, geometry, moments, n, d = _small_rational_fixture()
    assert matches_dqi_rational(n, d, moments, geometry, field)
    assert not matches_dqi_rational([n[0] ^ 1, n[1]], d, moments, geometry, field)
    assert not matches_dqi_rational(n, [0], moments, geometry, field)
    assert len(quotient_columns(geometry)) == len(moments)


def test_emitted_moment_guard_agrees_with_arithmetic_and_cleans_its_scratch():
    field, geometry, moments, n, d = _small_rational_fixture()

    @dataclass
    class Wire:
        value: int = 0

    def word(value):
        return [Wire((value >> i) & 1) for i in range(12)]

    def read(register):
        return sum(wire.value << i for i, wire in enumerate(register))

    def xor(register, value):
        for i, wire in enumerate(register):
            wire.value ^= (value >> i) & 1

    class LogicalBuilder:
        def alloc_qubits(self, count):
            return [Wire() for _ in range(count)]

        def free(self, register):
            assert read(register) == 0

        def x(self, operand):
            for wire in [operand] if isinstance(operand, Wire) else operand:
                wire.value ^= 1

        def cx(self, source, target):
            if isinstance(source, Wire):
                target.value ^= source.value
            else:
                xor(target, read(source))

        def ccx(self, a, b, target):
            target.value ^= a.value & b.value

    def clear_zero(_builder, register, flag):
        assert flag.value == int(not read(register))
        flag.value = 0

    reference = SimpleNamespace(
        zero_flag=lambda _b, register: Wire(int(not read(register))),
        clear_flag=clear_zero, inv=field.inv,
        scale=lambda _b, register, k: xor(register, read(register) ^ field.mul(read(register), k)),
        cx=lambda _b, a, target, k: xor(target, field.mul(read(a), k)),
        ar=SimpleNamespace(mul_xor0=lambda _b, a, b, target: xor(target, field.mul(read(a), read(b)))),
    )
    random = np.random.default_rng(1538)
    for index in range(60):
        values = moments[:]
        a, b = n + [0] * (5 - len(n)), d + [0] * (5 - len(d))
        delta = int(random.integers(1, 4096))
        mode = index % 6
        if mode == 1:
            a[0] ^= delta
        elif mode == 2:
            b[1] ^= delta
        elif mode == 3:
            b = [0] * len(b)
        elif mode == 4:
            b[-1] ^= delta
        elif mode == 5:
            values[-1] ^= delta
        builder = LogicalBuilder()
        input_words, banks = list(map(word, values)), (list(map(word, a)), list(map(word, b)))
        quotient = [word(0) for _ in values]
        output = Wire(index % 2)
        xor_quotient(builder, reference, input_words, quotient, geometry)
        xor_invalid_rational(builder, reference, quotient, banks, geometry, output)
        xor_quotient(builder, reference, input_words, quotient, geometry)
        assert output.value == (index % 2) ^ int(not matches_dqi_rational(a, b, values, geometry, field))
        assert not any(map(read, quotient))
        assert list(map(read, input_words)) == values
        assert list(map(read, banks[0])) == a and list(map(read, banks[1])) == b


@pytest.mark.official
def test_native_rational_certificate_preserves_only_the_rejection_bit(native_d4):
    km, api, reference = native_d4
    field, geometry, moments, n, d = _small_rational_fixture()
    builder = km.CircuitBuilder()
    multiplicity = len(moments)
    input_wires = [builder.alloc_qubits(12) for _ in moments]
    banks = tuple([builder.alloc_qubits(12) for _ in range(5)] for _ in range(2))
    output = builder.alloc_qubits(1)[0]
    quotient = [builder.alloc_qubits(12) for _ in moments]
    xor_quotient(builder, reference, input_wires, quotient, geometry)
    xor_invalid_rational(builder, reference, quotient, banks, geometry, output)
    xor_quotient(builder, reference, input_wires, quotient, geometry)
    for word in quotient:
        builder.free(word)
    circuit = builder.finish_circuit()
    numerator = np.tile(np.array(n + [0] * (5 - len(n))), (4, 1))
    denominator = np.tile(np.array(d + [0] * (5 - len(d))), (4, 1))
    numerator[1, 0] ^= 1
    numerator[2, 4] ^= 1
    denominator[3] = 0
    data = np.concatenate((np.tile(moments, (4, 1)), numerator, denominator), axis=1)
    wires = km.array([wire for word in input_wires + banks[0] + banks[1] for wire in word])
    scratch = km.array([
        km.q(index) for index in range(12 * (multiplicity + 10) + 1, circuit.num_qubits)
    ])
    for seed in (991, 992):
        sim = km.Simulator(batch_size=4, seed=seed)
        sim.use_same_registers_as(circuit)
        bits = api.to_bits(data, 12)
        sim.write_across_shots(wires, bits)
        sim.do(circuit)
        expected = [not matches_dqi_rational(a, b, moments, geometry, field)
                    for a, b in zip(numerator.tolist(), denominator.tolist(), strict=True)]
        assert np.array_equal(sim.read_across_shots(km.array([output]))[0], expected)
        assert np.array_equal(sim.read_across_shots(wires), bits)
        assert not sim.read_across_shots(scratch).any()
        assert not sim.read_phase_flipped_across_shots().any()
