#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded native check of deferred tail masks on actual key arithmetic.

Two identical full35 builds, three HMR seeds, actual first-two/nested-norm
normalizers, and the actual padded scalar seed.  Frozen physical fixtures and
the two explicitly separate algebraic initial-carry cases are inherited from
the independent first-two reference.  No profile is supplied to the circuit.

The raw and seed-prefix panels check values and clean quantum scratch only:
these prefixes have outstanding arithmetic AND tail HMR debts.  The complete
pair checks their full phase with arbitrary linear and nonlinear probes.
This checker does not integrate a DQI circuit, draw a population, or run an
official verifier.  Root owns all native execution and the memory guard.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys
import time

HERE = Path(__file__).resolve().parent
AFTER = HERE.parents[1]
sys.path.insert(0, str(AFTER / 'integration_v2'))
import integration_paths  # noqa: E402,F401
import integrated_pipeline as Pipeline  # noqa: E402
import source_binding as Binding  # noqa: E402
from event_ledger import Events  # noqa: E402
import kickmix as km  # noqa: E402
import numpy as np  # noqa: E402
import check_direct_carry_first2 as Reference  # noqa: E402
import scalar_seed_padded as Seed  # noqa: E402
sys.path.insert(0, str(HERE))
import rolling_tail_deferred as Tail  # noqa: E402

C5 = Reference.C5
SEEDS = C5.SEEDS
EXPECTED_DEBTS = list(range(16, 35))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def configure():
    # Finish choices do not enter this key-only component.  Configure the real
    # first-two and nested arithmetic providers, then substitute only Tail in
    # this process.  No source file or accepted implementation is overwritten.
    Pipeline.configure(Pipeline.Options(first_two_charts=True, nested_norm=True))
    Pipeline.Tail = Tail
    Pipeline.Extractor.Tail = Tail
    Pipeline.Direct.Tail = Tail
    assert Pipeline.Extractor.__name__ == 'direct_carry_first2'
    assert Pipeline.Arithmetic.__name__ == 'gf24_nested_norm'
    assert Pipeline.DirectArithmetic.Prior.__name__ == 'nested_norm_inverse'
    assert Pipeline.Extractor.Tail is Tail


def loaded_bindings():
    records = {}
    root = integration_paths.ROOT
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if not path.is_relative_to(root):
            continue
        if path.suffix == '.pyc':
            path = Path(importlib.util.source_from_cache(str(path))).resolve()
        if not path.is_file():
            continue
        key = str(path.relative_to(root))
        row = records.setdefault(key, dict(path=key, sha256=digest(path),
                                          bytes=path.stat().st_size, modules=[]))
        row['modules'].append(name)
    for row in records.values():
        row['modules'].sort()
    return records


def build(events, *, prefix_path=None, seam_path=None, label='a'):
    events.rows.clear()
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

    Extract = Pipeline.Extractor
    record = Extract.emit_prefix(b, words, carry, stage=stage)
    prefix_flag = record.tail.current
    record.tail.release_spare()
    assert sorted(record.tail.previous_masks) == EXPECTED_DEBTS
    assert record.tail.created_indices == EXPECTED_DEBTS
    assert record.tail.retired_indices == []
    assert record.tail.max_pending_masks == 19
    front = b.finish_circuit()
    prefix_static = front.operation_statistics().num_toffoli_like
    assert front.num_qubits == 889
    if prefix_path is not None:
        front.to_file(prefix_path, format='kmb')
    del front

    gauge = Tail.gauge_prefix(b, carry)
    seed = Seed.emit_prefix(b, carry[:12], words[34])
    record.tail.seed_prefix(carry[:12], words[34][12:])
    assert sorted(record.tail.previous_masks) == EXPECTED_DEBTS
    if seam_path is not None:
        seam = b.finish_circuit()
        seam.to_file(seam_path, format='kmb')
        del seam

    b.cz(probe, data)
    b.cz(data[0], data[47])
    b.cz(data[181], data[863])
    b.ccz(data[11], data[425], data[841])
    b.ccz(data[7], data[528], data[852])
    b.ccz(data[19], data[577], gauge.flag)

    returning = Seed.close_padded(b, carry[:12], words[34], seed)
    record.tail.seed_return(carry[:12], words[34][12:])
    Seed.finish_after_swap(b, carry[:12], words[34], record.tail.current, returning)
    assert returning.closed and seed.closed
    Tail.gauge_return(b, carry, gauge)
    record.tail.resume_return()
    Extract.emit_closing(b, words, carry, record, stage=stage)
    assert not record.tail.previous_masks
    assert record.tail.created_indices == EXPECTED_DEBTS
    assert record.tail.retired_indices == EXPECTED_DEBTS[::-1]
    assert b.num_allocated_qubits == 864 and record.closed

    circuit = b.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    baseline = Pipeline.source_ledger()['components_static_T'][
        'extractor_rolling_gauge_padded_seed']
    assert baseline == 152591
    expected_static = baseline - 418
    assert expected_static == 152173
    assert static == expected_static + 3, (static, expected_static)
    assert circuit.num_qubits == 889
    old_ledger = Extract.source_ledger(35, 15, full_seed_seam=True)
    # Three first-two deferred inverses plus33 generic divisions each contain
    # one nested norm inverse:36 prefix calls save3T each.
    expected_prefix = old_ledger['arithmetic_prefix_T'] + 69*20 - 22 - 36*3 - 418
    assert expected_prefix == 73093
    assert prefix_static == expected_prefix, (prefix_static, expected_prefix)
    expectation = events.snapshot(static - 3)
    flag_events = [e for e in expectation['events']
                   if e['name'] == 'tail_or_gauge_fresh_zero_phase']
    assert sum(e['occurrences'] for e in flag_events if e['conditional_T'] == 22) == 20
    assert sum(e['occurrences'] for e in flag_events if e['conditional_T'] == 10) == 1
    metrics = dict(
        component_static_T=static-3, static_T_including_probes=static, probe_T=3,
        Q=circuit.num_qubits, retained_data=864, prefix_static_T=prefix_static,
        baseline_key_static_T=baseline, delta_static_T=-418,
        delta_uniform_fresh_mask_mean_T=-209,
        expectation=expectation, controller_ledger=Tail.source_ledger(15),
        maximum_pending_tail_masks=record.tail.max_pending_masks,
        created_tail_mask_indices=record.tail.created_indices,
        retired_tail_mask_indices=record.tail.retired_indices,
        pending_tail_masks_after_pair=len(record.tail.previous_masks),
        stages=stages,
    )
    return circuit, metrics, prefix_flag, gauge.flag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', choices=('compact', 'key'), default='key')
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
    source, cases, values, prefix_values, probe_values, masks, phase = (
        Reference.get_fixtures(args.corpus, args.smoke, True))
    print(json.dumps(dict(stage='fixtures_ready', cases=len(cases),
                          fixture_source=source)), flush=True)
    (args.output/'fixtures-used.json').write_text(json.dumps(cases, indent=2)+'\n')
    prefix_path, seam_path = args.output/'prefix.kmb', args.output/'seam.kmb'
    first_path, second_path = args.output/'build-a.kmb', args.output/'build-b.kmb'

    circuit, metrics, prefix_flag, seam_flag = build(
        events, prefix_path=prefix_path, seam_path=seam_path, label='a')
    circuit.to_file(first_path, format='kmb')
    sha = digest(first_path)
    runs = [C5.simulate(circuit, values, masks, values, phase, seed)
            for seed in SEEDS]
    del circuit
    gc.collect()
    circuit, again, _, _ = build(events, label='b')
    circuit.to_file(second_path, format='kmb')
    assert metrics == again and sha == digest(second_path)
    del circuit
    gc.collect()

    front = km.Circuit.from_file(prefix_path, format='kmb')
    flags = np.array([bool(c['flags'][-1]) for c in cases])
    raw_runs = [C5.simulate(front, values, masks, prefix_values, None, seed,
                           live_flag=prefix_flag, flag_values=flags,
                           label='raw_prefix_values_only_open_phase_debts')
                for seed in SEEDS]
    assert all(r['phase_errors'] is None for r in raw_runs)
    runs.extend(raw_runs)
    del front
    gc.collect()
    front = km.Circuit.from_file(seam_path, format='kmb')
    gauges = np.array([bool(c['gauge']) for c in cases])
    seam_runs = [C5.simulate(front, values, masks, probe_values, None, seed,
                            live_flag=seam_flag, flag_values=gauges,
                            label='padded_seed_values_only_open_phase_debts')
                 for seed in SEEDS]
    assert all(r['phase_errors'] is None for r in seam_runs)
    runs.extend(seam_runs)
    del front
    gc.collect()

    accepted_after = Binding.verify_accepted_sources()
    assert accepted_before == accepted_after
    bindings = loaded_bindings()
    physical = [c for c in cases if c['fixture_kind'] == 'immutable_C5_physical_input']
    report = dict(
        status='PASS_NATIVE_DEFERRED_TAIL_KEY_COMPONENT_ONLY',
        variant='first_two_nested_norm_and_padded_seed_with_deferred_previous_tail_masks',
        fixture_source=source, cases=len(cases), physical_cases=len(physical),
        algebraic_initial_carry_cases=len(cases)-len(physical),
        physical_terminals=sorted({c['weight'] for c in physical}),
        gauge_one_cases=sum(c['gauge'] == 1 for c in cases),
        tail_parity_one_cases=sum(c['flags'][-1] for c in cases),
        builds_identical=True, circuit_sha256=sha, metrics=metrics, runs=runs,
        complete_pair_phase_checked=True,
        open_prefix_phase_checked=False,
        open_prefix_phase_reason='Arithmetic and19 explicit indexed tail HMR debts remain; only values, flags and clean quantum scratch are checked there.',
        source_bindings=bindings,
        accepted_and_frozen_sources=accepted_after,
        elapsed_seconds=time.monotonic()-started,
        limitations=[
            'No full DQI candidate, official salt, or population draw was run.',
            'Native panels do not replace the all-admitted-input phase-equivalence proof.',
            'The66 accepted C5 sources,14 frozen census dependencies and84 passed v1 sources were checked unchanged.',
            'The current integration_v2 source files are unchanged; substitution occurred only in this checker process.',
        ],
    )
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('runs','source_bindings','accepted_and_frozen_sources')},
                     indent=2), flush=True)
    if not args.keep_circuits:
        for path in (first_path, second_path, prefix_path, seam_path):
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
