#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Guarded native Q889 component check using the immutable C5 fixture corpus.

This is a component checker, not a DQI verifier or a new failure census.
Root owns execution.  --smoke restricts fixtures, never circuit size.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
import time
import ew_paths
import kickmix as km
import numpy as np
import check_raw_query_extractor as C5
import raw_query_extractor_early as Extract
import rolling_tail_early as Tail
import scalar_seed_padded as Seed
from check_arithmetic import install_events

SEEDS = C5.SEEDS
HERE, WORK = ew_paths.HERE, ew_paths.WORK


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def get_fixtures(corpus, smoke, full_seed):
    relative = ('night_c27/arithmetic/panel_audit/key-boundary-full/fixtures.json'
                if corpus == 'key' else 'night_c27/candidates/compact-panels/fixtures.json')
    path = WORK / relative
    rows = json.loads(path.read_text())
    assert isinstance(rows, list)
    if smoke:
        indices = {next(i for i, row in enumerate(rows) if row['weight'] == j)
                   for j in (15, 16, 35)}
        indices.update(i for i, row in enumerate(rows)
                       if row.get('boundary_oracle', {}).get('gauge') == 1)
        rows = [rows[i] for i in sorted(indices)]
    modulus = C5.public_modulus()
    cases = []
    for row in rows:
        j, roots, magnitudes = row['weight'], row['roots'], row['values']
        raw, syndromes, n, d = C5.raw_from_syndromes(roots, magnitudes, modulus)
        assert syndromes == row['syndromes']
        assert not C5.Ref.active_profile(n, d, j)['bad']
        storage, carry, flags = C5.prefix_reference(raw, j, 35, 15)
        assert flags[-1] == int(j % 2 == 0)
        assert Tail.validate_head_profile(storage, j, 15)
        broken = list(storage)
        broken[0] = 0
        assert not Tail.validate_head_profile(broken, j, 15)
        if j < 35:
            broken = list(storage)
            broken[j] = 1
            assert not Tail.validate_head_profile(broken, j, 15)
        old = row.get('boundary_oracle')
        if old is not None:
            assert raw == old['raw_queries'] and storage == old['heads']
            assert carry == old['raw_carry'] and flags == old['tail_flags']
        if full_seed:
            probe_words, probe_carry, gauge = C5.seed_reference(storage, carry, flags[-1])
            control = gauge
        else:
            probe_words, probe_carry, gauge = storage, carry, None
            control = flags[-1]
        cases.append(dict(label=row.get('label', row.get('case_id', str(len(cases)))),
                          weight=j, raw=raw, prefix_words=storage, prefix_carry=carry,
                          flags=flags, probe_words=probe_words, probe_carry=probe_carry,
                          gauge=gauge, control=control))
    values = np.stack([C5.bits_of_data(c['raw'], 1) for c in cases], axis=1)
    prefix_values = np.stack([C5.bits_of_data(c['prefix_words'], c['prefix_carry'])
                              for c in cases], axis=1)
    probe_values = np.stack([C5.bits_of_data(c['probe_words'], c['probe_carry'])
                             for c in cases], axis=1)
    masks = np.random.default_rng(202611112701).integers(
        0, 2, size=values.shape, dtype=np.int8).astype(bool)
    phase = np.logical_xor.reduce(probe_values & masks, axis=0)
    phase ^= probe_values[0] & probe_values[47]
    phase ^= probe_values[181] & probe_values[863]
    phase ^= probe_values[11] & probe_values[425] & probe_values[841]
    phase ^= probe_values[7] & probe_values[528] & probe_values[852]
    phase ^= probe_values[19] & probe_values[577] & np.array([c['control'] for c in cases], bool)
    return (dict(path=str(path), sha256=digest(path), original_cases=len(json.loads(path.read_text())),
                 used_cases=len(cases), smoke=smoke), cases, values, prefix_values,
            probe_values, masks, phase)


def build(events, full_seed, *, prefix_path=None, seam_path=None, label='a'):
    events.clear()
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    data = b.create_quantum_register(864, 'data')
    probe = b.create_classical_register(864, 'probe')
    words = [data[24*i:24*(i+1)] for i in range(35)]
    carry = data[840:864]
    stages = []
    def stage(message):
        stages.append(dict(stage=message, allocated_Q=b.num_allocated_qubits))
        if message.endswith(('04', '09', '14', '19', '24', '29', '34', '00')):
            print(json.dumps(dict(stage=message, build=label,
                                  allocated_Q=b.num_allocated_qubits)), flush=True)
    record = Extract.emit_prefix(b, words, carry, stage=stage)
    prefix_flag = record.tail.current
    record.tail.release_spare()
    front = b.finish_circuit()
    prefix_static = front.operation_statistics().num_toffoli_like
    assert front.num_qubits == 889
    if prefix_path is not None:
        front.to_file(prefix_path, format='kmb')
    del front
    gauge = seed = None
    if full_seed:
        gauge = Tail.gauge_prefix(b, carry)
        seed = Seed.emit_prefix(b, carry[:12], words[34])
        record.tail.seed_prefix(carry[:12], words[34][12:])
        control = gauge.flag
        if seam_path is not None:
            seam = b.finish_circuit()
            seam.to_file(seam_path, format='kmb')
            del seam
    else:
        control = record.tail.current
    b.cz(probe, data)
    b.cz(data[0], data[47])
    b.cz(data[181], data[863])
    b.ccz(data[11], data[425], data[841])
    b.ccz(data[7], data[528], data[852])
    b.ccz(data[19], data[577], control)
    if full_seed:
        returning = Seed.close_padded(b, carry[:12], words[34], seed)
        record.tail.seed_return(carry[:12], words[34][12:])
        Seed.finish_after_swap(b, carry[:12], words[34], record.tail.current, returning)
        assert returning.closed and seed.closed
        Tail.gauge_return(b, carry, gauge)
    record.tail.resume_return()
    Extract.emit_closing(b, words, carry, record, stage=stage)
    circuit = b.finish_circuit()
    ledger = Extract.source_ledger(35, 15, full_seed_seam=full_seed)
    static = circuit.operation_statistics().num_toffoli_like
    assert static == ledger['total_pair_T'] + 3, (static, ledger)
    assert circuit.num_qubits == 889
    assert b.num_allocated_qubits == 864 and record.closed
    expected_prefix = ledger['arithmetic_prefix_T'] + 69*20 - 22
    assert prefix_static == expected_prefix
    # These classically skipped ladders do not call the arithmetic event hook.
    events.extend(dict(name='rolling_flag_HMR_phase', conditional_T=22,
                       mask_bits=1, uniform_discount=11) for _ in range(39))
    if full_seed:
        events.append(dict(name='gauge_HMR_phase', conditional_T=10,
                           mask_bits=1, uniform_discount=5))
    metrics = dict(static_T_including_probes=static, probe_T=3,
                   component_static_T=static-3, Q=889, retained_data=864,
                   prefix_static_T=prefix_static,
                   uniform_HMR_mean_T_excluding_probes=static-3-sum(
                       e['uniform_discount'] for e in events),
                   uniform_HMR_events=list(events), ledger=ledger, stages=stages)
    return circuit, metrics, prefix_flag, None if gauge is None else gauge.flag


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', choices=('compact', 'key'), default='key')
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--without-seed', action='store_true')
    p.add_argument('--keep-circuits', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    events = []
    install_events(events)
    full_seed = not a.without_seed
    fixture_source, cases, values, prefix_values, probe_values, masks, phase = get_fixtures(
        a.corpus, a.smoke, full_seed)
    print(json.dumps(dict(stage='fixtures_ready', cases=len(cases),
                          fixture_source=fixture_source)), flush=True)
    (a.output/'fixtures-used.json').write_text(json.dumps(cases, indent=2)+'\n')
    prefix_path, seam_path = a.output/'prefix.kmb', a.output/'seam.kmb'
    first, second = a.output/'build-a.kmb', a.output/'build-b.kmb'
    circuit, metrics, prefix_flag, seam_flag = build(events, full_seed,
        prefix_path=prefix_path, seam_path=seam_path, label='a')
    circuit.to_file(first, format='kmb')
    sha = digest(first)
    runs = [C5.simulate(circuit, values, masks, values, phase, seed) for seed in SEEDS]
    del circuit
    gc.collect()
    circuit, again, _, _ = build(events, full_seed, label='b')
    circuit.to_file(second, format='kmb')
    assert metrics == again and sha == digest(second)
    del circuit
    gc.collect()
    front = km.Circuit.from_file(prefix_path, format='kmb')
    flags = np.array([bool(c['flags'][-1]) for c in cases])
    runs += [C5.simulate(front, values, masks, prefix_values, None, seed,
                        live_flag=prefix_flag, flag_values=flags, label='raw_prefix')
             for seed in SEEDS]
    del front
    gc.collect()
    if full_seed:
        front = km.Circuit.from_file(seam_path, format='kmb')
        gauges = np.array([bool(c['gauge']) for c in cases])
        runs += [C5.simulate(front, values, masks, probe_values, None, seed,
                            live_flag=seam_flag, flag_values=gauges, label='padded_seed_prefix')
                 for seed in SEEDS]
        del front
        gc.collect()
    bindings = {p.name:dict(sha256=digest(p), bytes=p.stat().st_size)
                for p in sorted(HERE.glob('*.py'))}
    report = dict(status='PASS_NATIVE_Q889_EXTRACTOR_COMPONENT_ONLY',
                  full_seed_seam=full_seed, fixture_source=fixture_source,
                  cases=len(cases), weights=sorted({c['weight'] for c in cases}),
                  gauge_one_cases=sum(c['gauge'] == 1 for c in cases),
                  seed_parity_one_cases=sum(c['flags'][-1] for c in cases),
                  builds_identical=True, circuit_sha256=sha,
                  metrics=metrics, runs=runs, source_bindings=bindings,
                  elapsed_seconds=time.monotonic()-started,
                  limitations=['No full DQI circuit or official salt was run.',
                               'C5 certificate transfer requires whole admitted-domain equivalence.',
                               'Current C5 production sources remain immutable.'])
    (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','source_bindings')},
                     indent=2), flush=True)
    if not a.keep_circuits:
        for path in (first, second, prefix_path, seam_path):
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
