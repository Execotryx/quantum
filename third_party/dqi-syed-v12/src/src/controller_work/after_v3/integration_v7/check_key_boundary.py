#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""V7 fixed key boundary with the independently checked third-chart carry oracle.

The old fixture loader, independent syndrome/polynomial oracle, and simulator
checks are reused verbatim. The altered key has its own count/width ledger.
No native work is run until the root invokes this script under the guard.
"""
from pathlib import Path
from collections import Counter
import argparse
import gc
import importlib.util
import json
import sys
import time
from v7_paths import WORK, HERE
from v7_binding import atomic_json, digest, verify_preservation
import v7_pipeline as Pipeline


def load_harness():
    path = WORK/'night_c27/arithmetic/panel_audit/check_key_boundary.py'
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('accepted_key_boundary_harness', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def build(args, pipeline, events, harness, label, prefix_path, pair_path):
    import kickmix as km
    events.rows.clear()
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    S = [b.create_quantum_register(12, f'S{i}') for i in range(70)]
    probe = b.create_classical_register(865, 'boundary_probe')
    def stage(message):
        if isinstance(message, dict) and message.get('node',-1) % 8 == 0:
            print(json.dumps(dict(build=label, **message)), flush=True)
        elif str(message).endswith(('04','09','14','19','24','29','34','00')):
            print(json.dumps(dict(build=label, stage=message)), flush=True)
    key = pipeline.emit_key_prefix(b, S, j_min=15, stage=stage)
    boundary = km.array([*(q for word in key['N'] for q in word),
                         *(q for word in key['D'] for q in word),
                         *key['carry'][12:], key['gauge'].flag])
    assert len(boundary) == len(set(boundary)) == 865
    assert b.num_allocated_qubits == 865
    front = b.finish_circuit()
    prefix_T = front.operation_statistics().num_toffoli_like
    expected_prefix = 101884 - (300 if args.first_two_charts else 0) - 418
    if args.nested_norm:
        expected_prefix -= 3*(36 if args.first_two_charts else 35)
    # The fixed matched-prefix provider saves one unconditional T at each
    # of the three special inversions; all original oracle checks remain.
    expected_prefix -= 3
    # The repaired third chart raises the matched prefix by32 fixed T.
    expected_prefix += 32
    assert prefix_T == expected_prefix, (prefix_T, expected_prefix)
    assert front.num_qubits == 889
    front.to_file(prefix_path, format='kmb')
    del front
    gc.collect()
    b.cz(probe, boundary)
    for x,y,z in harness.TRIPLES:
        b.ccz(boundary[x], boundary[y], boundary[z])
    pipeline.emit_key_closing(b, key, stage=stage)
    assert key['closed'] and b.num_allocated_qubits == 840
    circuit = b.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    parts = pipeline.source_ledger()['components_static_T']
    expected_pair = parts['extractor_rolling_gauge_padded_seed'] + parts['synthesis']
    assert static == expected_pair+len(harness.TRIPLES), (static, expected_pair)
    assert circuit.num_qubits == 889
    circuit.to_file(pair_path, format='kmb')
    indices = {km.q(i):i for i in range(circuit.num_qubits)}
    layout = [indices[q] for q in boundary]
    metrics = dict(key_pair_static_T=expected_pair, probe_static_T=len(harness.TRIPLES),
                   full_pair_static_T=static, prefix_static_T=prefix_T, Q=889,
                   exact_source_expectation=events.snapshot(expected_pair),
                   scope='Key only; converter/finish/scan absent')
    del circuit,b
    gc.collect()
    return metrics, layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixtures-file', type=Path)
    parser.add_argument('--extra-fixtures', type=Path, action='append', default=[])
    parser.add_argument('--weights', type=int, nargs='+', default=list(range(15,36)))
    parser.add_argument('--per-weight', type=int, default=1)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--seeds', type=int, nargs='+', default=[147,1147,2147])
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    args.first_two_charts = args.nested_norm = True
    args.j_min = 15
    assert args.start >= 0 and args.batch_size > 0 and args.per_weight > 0
    assert args.seeds and all(15 <= j <= 35 for j in args.weights)
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True, exist_ok=True)
    Pipeline.configure()
    before = verify_preservation(Pipeline.Runtime)
    harness, harness_path = load_harness()
    from boundary_scale_first3 import rescale_boundary
    from v7_events import Events
    events = Events()
    events.install(Pipeline)
    started = time.monotonic()
    selected, excluded, old_oracles, partition = harness.load_cases(args)
    oracles = [rescale_boundary(row) for row in old_oracles]
    assert all(row['changed_carry_variant'] == 'first3_zero_repaired' for row in oracles)
    atomic_json(args.output/'fixtures.json', [dict(row, boundary_oracle=oracle)
                                            for row,oracle in zip(selected,oracles)])
    atomic_json(args.output/'explicit-key-domain-exclusions.json', excluded)
    report = dict(status='RUNNING_NEW_KEY_BOUNDARY', runs=[], **partition,
                  selected_cases=len(selected), key_domain_exclusions=len(excluded),
                  physical_weights=dict(Counter(row['weight'] for row in selected)),
                  gauges=dict(Counter(row['gauge'] for row in oracles)),
                  terminal_seed_flags=dict(Counter(row['terminal_seed_flag'] for row in oracles)),
                  runtime_bindings=Pipeline.runtime_bindings(),
                  reused_harness=dict(path=str(harness_path), sha256=digest(harness_path)),
                  source_adapter=dict(path=str(WORK/'after_v3/blocks/v6/boundary_scale_first3.py'),
                                      sha256=digest(WORK/'after_v3/blocks/v6/boundary_scale_first3.py')),
                  actual_new_gauge1_case_ids=[row['case_id'] for row,oracle in zip(selected,oracles) if oracle['gauge']==1],
                  actual_raw_third_zero_case_ids=[row['case_id'] for row,oracle in zip(selected,oracles) if oracle['third_chart']['raw_zero']],
                  limitations=['The prefix phase intentionally retains HMR debts.',
                               'Every selected key-domain case is checked; half-core exclusions remain eligible.',
                               'The full paired key has arbitrary linear and three cubic phase probes.',
                               'No full decoder or new population-frequency claim is made.'])
    atomic_json(args.output/'report.json', report)
    paths = [args.output/name for name in ('prefix-a.kmb','pair-a.kmb','prefix-b.kmb','pair-b.kmb')]
    try:
        metrics, layout = build(args, Pipeline, events, harness, 'a', paths[0], paths[1])
        again, layout_again = build(args, Pipeline, events, harness, 'b', paths[2], paths[3])
        assert metrics == again and layout == layout_again
        assert digest(paths[0]) == digest(paths[2]) and digest(paths[1]) == digest(paths[3])
        report.update(metrics=metrics, boundary_physical_indices=layout,
                      prefix_sha256=digest(paths[0]), pair_sha256=digest(paths[1]),
                      two_identical_builds=True)
        harness.simulate(args, paths[0], 'prefix', layout, selected, oracles, report)
        harness.simulate(args, paths[1], 'pair', layout, selected, oracles, report)
        Pipeline.assert_bindings()
        assert before == verify_preservation(Pipeline.Runtime)
        report['status'] = 'PASS_NEW_NATIVE_KEY_BOUNDARY_COMPONENT'
        report['accepted_C5_and_frozen_sources_unchanged'] = True
    except BaseException as error:
        report['status'] = 'FAILED_OR_INTERRUPTED_NEW_KEY_BOUNDARY'
        report['failure'] = repr(error)
        atomic_json(args.output/'report.json', report)
        raise
    report['preservation_and_component_gates'] = before
    report['elapsed_seconds'] = time.monotonic()-started
    atomic_json(args.output/'report.json', report)
    if not args.keep_circuits:
        for path in paths:
            path.unlink()
    print(json.dumps({k:v for k,v in report.items() if k != 'runs'}, indent=2))


if __name__ == '__main__':
    main()
