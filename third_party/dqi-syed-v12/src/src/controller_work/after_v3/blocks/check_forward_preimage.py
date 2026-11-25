#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded actual-v3 preimage caller panel for borrowed forward windows.

The four forward calls are the only substituted provider. The unchanged
normalized-v3 source gate, caller, transpose, arithmetic and gauge lifecycle
remain active. The frozen256 fixtures cover both sparse gauge charts and
native continuation flags. No whole decoder or official check is claimed.

Derived as a new file from the accepted same-half flag panel; its oracle,
phase probes and complete source/target/gauge/scratch checks are retained.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys
import time

from collections import Counter
from types import SimpleNamespace
from accepted_runtime import load, recheck, loaded_sources

Runtime = load()
Pipeline = Runtime.pipeline
Binding = Runtime.binding
AFTER = Path(__file__).resolve().parents[2]/'after_c5'
from event_ledger import Events  # noqa: E402
import kickmix as km  # noqa: E402
import numpy as np  # noqa: E402
import night_reference as Ref  # noqa: E402
from quantum_reciprocal import bit_matrix  # noqa: E402
import window_forward_borrowed as Candidate  # noqa: E402

CALLS = []

FIXTURES = AFTER/'converter_width/runs/full/fixtures.json'
FIXTURE_SHA = '6e023eb39758c15cc5e3835bc6bcdb0f8ad08c3ec15185d2c970dfbb201fac73'
RETAINED = 865
SEEDS = (137, 1137, 2137)
EXPECTED_STATIC = 115571
EXPECTED_MEAN = 114860.88131546974
EXPECTED_PREFIX_STATIC = 57208
PROBE_T = 3


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def configure():
    assert Pipeline.Window.tensor is Runtime.reference
    assert Pipeline.Window.transpose_tensor is Runtime.transpose

    def tracked(builder, F, G, q0, q1, rhss, record_flag):
        slots = []
        retained = builder.num_allocated_qubits
        def record(slot, mask):
            slots.append(slot)
            record_flag(slot, mask)
        Candidate.emit(builder, F, G, q0, q1, rhss, record)
        assert slots == [0, 1, 2]
        assert builder.num_allocated_qubits == retained
        CALLS.append(dict(m=len(G)-1, retained_Q=retained,
                          returned_source_mask_slots=slots,
                          core_static_T=168*(len(G)-1)+645))
    Pipeline.Window.tensor = SimpleNamespace(__name__=Candidate.__name__, emit=tracked)
    assert Pipeline.Window.transpose_tensor is Runtime.transpose


def fixture_panel(smoke):
    assert digest(FIXTURES) == FIXTURE_SHA
    rows = json.loads(FIXTURES.read_text())
    assert len(rows) == 256
    used = list(range(8)) if smoke else list(range(256))
    fixtures = [rows[i] for i in used]
    seen = {}
    for row in fixtures:
        assert row['gauge_flag'] in (0, 1)
        assert not row['gauge_flag'] or row['gauge_other'] == 0
        assert Ref.admitted(row['D'])
        key = (tuple(row['D']), tuple(row['O']))
        if key not in seen:
            seen[key] = Ref.full_preimage(row['D'], row['O'])
        assert seen[key] == row['expected']
        assert Ref.profile(row['D']) == row['half_profile']
    assert {r['gauge_flag'] for r in fixtures} == {0, 1}
    return fixtures, dict(path=str(FIXTURES), sha256=FIXTURE_SHA,
                          original_cases=256, used_cases=len(fixtures),
                          selected_indices=used, smoke=smoke,
                          omissions=[] if not smoke else list(range(8, 256)),
                          new_fixtures_or_random_draws=0)


def build(events, prefix_path=None, label='a'):
    events.rows.clear()
    CALLS.clear()
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    D = [b.create_quantum_register(12, f'D{i}') for i in range(36)]
    O = [b.create_quantum_register(12, f'O{i}') for i in range(35)]
    other = b.create_quantum_register(12, 'gauge_other')
    flag = b.create_quantum_register(1, 'gauge_flag')
    probe = b.create_classical_register(RETAINED, 'phase_probe')
    stages = []

    def stage(message):
        stages.append(dict(stage=message, allocated_Q=b.num_allocated_qubits))
        print(json.dumps(dict(stage=message, build=label,
                              allocated_Q=b.num_allocated_qubits)), flush=True)

    record = Pipeline.Outer.emit_prefix(b, D, O, gauge_flag=flag[0],
                                       gauge_other=other, stage=stage)
    assert not record.core.local_flags
    assert set(record.core.local_created) == {(False, n) for n in range(2, 18)}
    assert len(record.core.local_created) == len(record.core.local_retired) == 16
    prefix = b.finish_circuit()
    prefix_static = prefix.operation_statistics().num_toffoli_like
    prefix_calls = list(CALLS)
    assert Counter(row['m'] for row in prefix_calls) == {11: 1, 14: 1}, prefix_calls
    prefix_expectation = events.snapshot(prefix_static)
    assert prefix_static == EXPECTED_PREFIX_STATIC, prefix_static
    assert prefix.num_qubits == 889 and b.num_allocated_qubits == RETAINED
    if prefix_path is not None:
        prefix.to_file(prefix_path, format='kmb')
    del prefix

    wires = km.array([q for word in D+O for q in word] + list(other) + list(flag))
    b.cz(probe, wires)
    b.ccz(flag[0], D[0][0], O[0][1])
    b.ccz(other[3], O[17][2], O[34][5])
    b.ccz(D[35][7], O[2][4], O[30][6])
    Pipeline.Outer.emit_closing(b, D, O, (), record, stage=stage)
    assert b.num_allocated_qubits == RETAINED
    assert not record.core.local_flags
    expected = {(closing, n) for closing in (False, True) for n in range(2, 18)}
    assert len(record.core.local_created) == len(record.core.local_retired) == 32
    assert set(record.core.local_created) == set(record.core.local_retired) == expected
    assert not record.core.beta and not record.core.flags
    assert not record.core.quotients and not record.core.outer
    record.core.gauge_carrier.clean_boundary()
    circuit = b.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    assert static - PROBE_T == EXPECTED_STATIC, static
    assert circuit.num_qubits == 889, circuit.num_qubits
    assert Counter(row['m'] for row in CALLS) == {11: 2, 14: 2}, CALLS
    expectation = events.snapshot(static-PROBE_T)
    assert abs(expectation['expected_T'] - EXPECTED_MEAN) < 1e-7, expectation
    carrier = record.core.gauge_carrier
    assert (carrier.parks, carrier.unparks) == (16, 16)
    metrics = dict(
        static_T=static-PROBE_T, circuit_static_T=static, probe_T=PROBE_T,
        Q=circuit.num_qubits, retained_data=RETAINED,
        prefix_static_T=prefix_static, prefix_expectation=prefix_expectation,
        expectation=expectation,
        accepted_v3_preimage_static_T=115627,
        accepted_v3_preimage_HMR_mean_T=114916.88131546974,
        delta_static_T=-56, delta_uniform_fresh_mask_mean_T=-56,
        prefix_delta_static_T=-28,
        prefix_forward_calls=prefix_calls,
        all_forward_calls=list(CALLS),
        transpose_provider=Pipeline.Window.transpose_tensor.__name__,
        created_local_debts=record.core.local_created,
        retired_local_debts=record.core.local_retired,
        maximum_pending_local_masks=record.core.local_max_pending,
        pending_local_masks_after_pair=len(record.core.local_flags),
        gauge_parks=carrier.parks, gauge_unparks=carrier.unparks,
        top16_gauge_requeries=record.core.gauge_h_requeries,
        operations=len(circuit), stages=stages,
    )
    return circuit, metrics


def simulate(circuit, fixtures, seed, prefix=False):
    count = len(fixtures)
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    registers = circuit.register_data
    for letter, length in (('D', 36), ('O', 35)):
        for i in range(length):
            values = np.array([f[letter][i] for f in fixtures], dtype=np.int64)
            sim.write_across_shots(registers[f'{letter}{i}'], bit_matrix(values, 12))
    for name, width in (('gauge_other', 12), ('gauge_flag', 1)):
        values = np.array([f[name] for f in fixtures], dtype=np.int64)
        sim.write_across_shots(registers[name], bit_matrix(values, width))
    masks = np.random.default_rng(202611114502).integers(
        0, 2, size=(RETAINED, count), dtype=np.int8).astype(bool)
    sim.write_across_shots(registers['phase_probe'], masks)
    sim.do(circuit)
    bad = np.zeros(count, dtype=bool)
    for letter, length in (('D', 36), ('O', 35)):
        key = 'expected' if prefix and letter == 'O' else letter
        for i in range(length):
            wanted = bit_matrix(np.array([f[key][i] for f in fixtures]), 12)
            bad |= np.any(sim.read_across_shots(registers[f'{letter}{i}']) != wanted, axis=0)
    for name, width in (('gauge_other', 12), ('gauge_flag', 1)):
        wanted = bit_matrix(np.array([f[name] for f in fixtures]), width)
        bad |= np.any(sim.read_across_shots(registers[name]) != wanted, axis=0)
    scratch = [km.q(i) for i in range(RETAINED, circuit.num_qubits)]
    assert scratch
    bad |= np.any(sim.read_across_shots(scratch), axis=0)
    assert np.array_equal(sim.read_across_shots(registers['phase_probe']), masks)
    phase_bad = np.zeros(count, dtype=bool)
    if not prefix:
        boundary = []
        for f in fixtures:
            row = []
            for word in f['D'] + f['expected'] + [f['gauge_other']]:
                row.extend((word >> i) & 1 for i in range(12))
            row.append(f['gauge_flag'])
            boundary.append(row)
        expected_phase = np.logical_xor.reduce(np.array(boundary, dtype=bool).T & masks, axis=0)
        for i, f in enumerate(fixtures):
            O, D = f['expected'], f['D']
            expected_phase[i] ^= bool(f['gauge_flag'] and D[0] & 1 and O[0] & 2)
            expected_phase[i] ^= bool(f['gauge_other'] & 8 and O[17] & 4 and O[34] & 32)
            expected_phase[i] ^= bool(D[35] & 128 and O[2] & 16 and O[30] & 64)
        phase_bad = sim.read_phase_flipped_across_shots() != expected_phase
    row = dict(seed=seed, shots=count, prefix_values_only=prefix,
               value_restoration_scratch_errors=int(bad.sum()),
               phase_errors=None if prefix else int(phase_bad.sum()),
               sampled_mean_T_including_probes=sim.operation_statistics().num_toffoli_like/count,
               bad_value_indices=np.flatnonzero(bad).tolist(),
               bad_phase_indices=np.flatnonzero(phase_bad).tolist())
    assert not bad.any() and not phase_bad.any(), row
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--keep-circuits', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    started = time.monotonic()
    accepted_before = Binding.verify_accepted_sources()
    configure()
    events = Events()
    events.install(Pipeline)
    fixtures, fixture_source = fixture_panel(args.smoke)
    (args.output/'fixtures-used.json').write_text(json.dumps(fixtures, indent=2)+'\n')
    print(json.dumps(dict(stage='fixtures_ready', fixtures=fixture_source)), flush=True)
    prefix_path = args.output/'prefix-a.kmb'
    prefix_second_path = args.output/'prefix-b.kmb'
    paths = [args.output/f'build-{letter}.kmb' for letter in ('a', 'b')]
    circuit, metrics = build(events, prefix_path, 'a')
    circuit.to_file(paths[0], format='kmb')
    sha = digest(paths[0])
    roundtrip = [simulate(circuit, fixtures, seed) for seed in SEEDS]
    del circuit
    gc.collect()
    circuit, second = build(events, prefix_second_path, label='b')
    circuit.to_file(paths[1], format='kmb')
    assert sha == digest(paths[1]) and metrics == second
    assert digest(prefix_path) == digest(prefix_second_path)
    del circuit
    gc.collect()
    prefix = km.Circuit.from_file(prefix_path, format='kmb')
    prefixes = [simulate(prefix, fixtures, seed, True) for seed in SEEDS]
    del prefix
    gc.collect()
    accepted_after = Binding.verify_accepted_sources()
    assert accepted_before == accepted_after
    report = dict(
        status='PASS_NATIVE_BORROWED_FORWARD_PREIMAGE_COMPONENT_ONLY',
        fixture_source=fixture_source, fixtures=len(fixtures),
        gauge_charts=sorted({f['gauge_flag'] for f in fixtures}),
        forced_top_gap_fixtures=sum(f['forced_top_gap'] for f in fixtures),
        two_identical_builds=True, circuit_sha256=sha,
        metrics=metrics, roundtrip=roundtrip, prefix_values=prefixes,
        source_bindings=loaded_sources(),
        accepted_normalized_runtime_preservation=recheck(Runtime),
        actual_runtime_providers=Pipeline.runtime_bindings(),
        prefix_two_identical_builds=True, prefix_sha256=digest(prefix_path),
        accepted_and_frozen_sources=accepted_after,
        elapsed_seconds=time.monotonic()-started,
        limitations=[
            'Component only; no full candidate, official salts or population draws.',
            'Prefix checks values and clean scratch; inherited arithmetic HMR debts remain open until closing.',
            'The unchanged32 local masks and all returned source-query masks are retired at the caller witnesses.',
            'Only the forward tensor provider changes; the accepted transpose remains active.',
            'All accepted C5/v3/release sources and historical receipts remain unchanged.',
        ],
    )
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], metrics=metrics,
                          fixtures=len(fixtures), circuit_sha256=sha), indent=2), flush=True)
    if not args.keep_circuits:
        for path in [prefix_path, prefix_second_path, *paths]:
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
