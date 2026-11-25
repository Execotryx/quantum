#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Native complete-key boundary panel using the actual production functions.

Tests all35 numerator and36 denominator coefficients, raw retained carry half,
gauge chart bit, arbitrary865-bit diagonal probes and three cubic probes,
original70 syndromes, all probe bits and every scratch wire. Prefix phases
are intentionally open; only the complete paired map is phase-checked.
Root must run this under the shared guard, one heavy job at a time.
"""
from pathlib import Path
from collections import Counter
import argparse
import gc
import hashlib
import json
import random
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT/'controller_work'
C27 = WORK/'night_c27'
for directory in (ROOT/'pro1_controller_bundle/1_task/official',
                  C27/'synthesis', C27/'arithmetic', C27/'controller', C27/'census'):
    sys.path.insert(0, str(directory))
import c27_paths  # noqa: F401
import kickmix as km
import numpy as np
import fixed_pipeline as Pipeline
import raw_query_extractor as Extractor
import physical_boundary_oracle as Oracle
import reference as Ref
from check_arithmetic import install_events
from prepare_panels import digest, moments, classify, validate

SEEDS = (147, 1147, 2147)
TRIPLES = ((0, 420, 840), (11, 431, 863), (17, 632, 864))


def write(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def field_bits(values):
    rows = np.asarray(values, dtype=np.int64)
    assert rows.ndim == 2
    return ((rows[:, :, None] >> np.arange(12)) & 1).astype(bool).reshape(len(rows), -1).T


def boundary_bits(oracles):
    fields = [row['N']+row['D']+[row['other_carry_half']] for row in oracles]
    assert all(len(row) == 72 for row in fields)
    return np.concatenate((field_bits(fields),
                           np.array([[row['gauge'] for row in oracles]], dtype=bool)), axis=0)


def generated_cases(weights, per_weight, j_min):
    rng = random.Random(202611112722)
    cases, rejected = [], []
    for weight in weights:
        kept, attempts = 0, 0
        while kept < per_weight:
            attempts += 1
            assert attempts <= 10000
            roots = rng.sample(range(1, 4096), weight)
            values = [rng.randrange(1, 4096) for _ in roots]
            classification = Ref.classify(roots, values)
            positions = [Ref.LOG[root] for root in roots]
            ident = hashlib.sha256(json.dumps([positions, values]).encode()).hexdigest()
            row = dict(case_id=ident, label=f'generated_key_weight{weight}_{kept}',
                       roots=roots, positions=positions, values=values,
                       syndromes=moments(positions, values), weight=weight,
                       mask_mode='random', origins=[dict(panel='new_key_boundary_generated',
                                                        weight=weight, attempt=attempts)],
                       classification=classify(dict(roots=roots, values=values,
                                                    weight=weight), j_min))
            if classification['finite']['bad']:
                rejected.append(row)
                continue
            cases.append(row)
            kept += 1
    return cases, rejected


def load_cases(args):
    if args.fixtures_file is None:
        cases, rejected = generated_cases(args.weights, args.per_weight, args.j_min)
        manifest_sha = None
    else:
        package = json.loads(args.fixtures_file.read_text())
        assert package['format'] == 'C27_PHYSICAL_PANEL_V1'
        assert package['j_min'] == args.j_min and package['classifications_present']
        assert package['classifier_sha256'] == digest(C27/'census/reference.py')
        cases, rejected = [], []
        for row in package['cases']:
            validate(row)
            assert row['classification'] == classify(row, args.j_min)
            # Half-converter exclusions do not exclude this key-only panel.
            if row['weight'] < args.j_min or row['classification']['exact']['finite']['bad']:
                rejected.append(row)
            else:
                cases.append(row)
        manifest_sha = digest(args.fixtures_file)
    for path in args.extra_fixtures:
        package = json.loads(path.read_text())
        assert package['format'] == 'C27_EXTRA_PHYSICAL_FIXTURES_V1'
        for index, original in enumerate(package['cases']):
            validate(original)
            row = dict(original)
            row['roots'] = [Ref.EXP[p] for p in row['positions']]
            row['weight'] = len(row['positions'])
            row['syndromes'] = moments(row['positions'], row['values'])
            row['case_id'] = hashlib.sha256(json.dumps(
                [row['positions'], row['values']], separators=(',', ':')).encode()).hexdigest()
            row['classification'] = classify(row, args.j_min)
            row['origins'] = [dict(panel=package['panel'], source=str(path.resolve()), index=index)]
            assert row['weight'] >= args.j_min and not row['classification']['exact']['finite']['bad']
            cases.append(row)
    stop = len(cases) if args.count is None else min(len(cases), args.start+args.count)
    selected = cases[args.start:stop]
    assert selected, 'empty key-domain partition'
    oracles = []
    for row in selected:
        assert row['roots'] == [Ref.EXP[p] for p in row['positions']]
        assert row['syndromes'] == moments(row['positions'], row['values'])
        oracles.append(Oracle.boundary(row['roots'], row['values'], j_min=args.j_min))
    return selected, rejected, oracles, dict(total_key_domain_cases=len(cases),
                                           partition_start=args.start, partition_stop=stop,
                                           complete_key_domain=args.start == 0 and stop == len(cases),
                                           fixture_sha256=manifest_sha)


def build(args, events, *, label, prefix_path, pair_path):
    events.clear()
    b = km.CircuitBuilder()
    b.set_max_qubits(890)
    S = [b.create_quantum_register(12, f'S{i}') for i in range(70)]
    probe = b.create_classical_register(865, 'boundary_probe')
    def stage(message):
        if isinstance(message, dict):
            if message.get('node', -1) % 8 == 0:
                print(json.dumps(dict(build=label, **message)), flush=True)
        elif str(message).endswith(('04', '09', '14', '19', '24', '29', '34', '00')):
            print(json.dumps(dict(build=label, stage=message)), flush=True)
    key = Pipeline.emit_key_prefix(b, S, j_min=args.j_min, stage=stage)
    boundary = km.array([*(q for word in key['N'] for q in word),
                         *(q for word in key['D'] for q in word),
                         *key['carry'][12:], key['gauge'].flag])
    assert len(boundary) == 865 and len(set(boundary)) == 865
    assert b.num_allocated_qubits == 865
    front = b.finish_circuit()
    prefix_T = front.operation_statistics().num_toffoli_like
    expected_prefix = 101884 + 69*(15-args.j_min)
    assert prefix_T == expected_prefix, (prefix_T, expected_prefix)
    front.to_file(prefix_path, format='kmb')
    del front
    gc.collect()
    b.cz(probe, boundary)
    for x, y, z in TRIPLES:
        b.ccz(boundary[x], boundary[y], boundary[z])
    Pipeline.emit_key_closing(b, key, stage=stage)
    assert key['closed'] and b.num_allocated_qubits == 840
    events.append(dict(name='scalar_seed_inverse_phase', conditional_T=27,
                       mask_bits=12, uniform_discount=27/4096))
    circuit = b.finish_circuit()
    expected_T = 222595 + 138*(15-args.j_min) + len(TRIPLES)
    actual_T = circuit.operation_statistics().num_toffoli_like
    assert actual_T == expected_T, (actual_T, expected_T)
    assert circuit.num_qubits == 890
    conditional_discount = 0
    if args.conditional_flag_phases:
        conditional_discount = 11*(2*(35-args.j_min)-1)+5
    uniform = actual_T-sum(event['uniform_discount'] for event in events)-conditional_discount
    circuit.to_file(pair_path, format='kmb')
    metrics = dict(key_pair_static_T=actual_T-len(TRIPLES),
                   probe_static_T=len(TRIPLES), full_pair_static_T=actual_T,
                   prefix_static_T=prefix_T, Q=circuit.num_qubits,
                   uniform_fresh_HMR_mean_T=uniform,
                   conditional_flag_discount=conditional_discount,
                   uniform_HMR_events=list(events),
                   scope='Key and boundary probes only; no converter, finish or root scan')
    indices = {km.q(i): i for i in range(circuit.num_qubits)}
    layout = [indices[q] for q in boundary]
    del circuit, b
    gc.collect()
    return metrics, layout


def simulate(args, path, label, layout, selected, oracles, report):
    circuit = km.Circuit.from_file(path, format='kmb')
    syndromes = km.array([q for i in range(70) for q in circuit.register_data[f'S{i}']])
    probe = circuit.register_data['boundary_probe']
    boundary = km.array([km.q(i) for i in layout])
    live = set(layout) if label == 'prefix' else set(range(840))
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits) if i not in live])
    for offset in range(0, len(selected), args.batch_size):
        batch = selected[offset:offset+args.batch_size]
        expected = boundary_bits(oracles[offset:offset+len(batch)])
        inputs = field_bits([row['syndromes'] for row in batch])
        mask_rows = []
        for row in batch:
            seed = int.from_bytes(hashlib.sha256(
                f'202611112723:{row["case_id"]}'.encode()).digest(), 'little')
            mask_rows.append(np.random.default_rng(seed).integers(0, 2, 865, dtype=np.int8).astype(bool))
        masks = np.stack(mask_rows, axis=1)
        phase = np.logical_xor.reduce(expected & masks, axis=0)
        for x, y, z in TRIPLES:
            phase ^= expected[x] & expected[y] & expected[z]
        for seed in args.seeds:
            sim = km.Simulator(batch_size=len(batch), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndromes, inputs)
            sim.write_across_shots(probe, masks)
            sim.do(circuit)
            actual = sim.read_across_shots(boundary if label == 'prefix' else syndromes)
            want = expected if label == 'prefix' else inputs
            bad_value = np.any(actual != want, axis=0)
            bad_probe = np.any(sim.read_across_shots(probe) != masks, axis=0)
            bad_scratch = np.any(sim.read_across_shots(scratch), axis=0)
            bad_phase = (sim.read_phase_flipped_across_shots() != phase
                         if label == 'pair' else np.zeros(len(batch), dtype=bool))
            def ids(which):
                return [batch[k]['case_id'] for k in np.flatnonzero(which)]
            row = dict(panel=label, offset=args.start+offset, count=len(batch), seed=seed,
                       value_error_case_ids=ids(bad_value), probe_error_case_ids=ids(bad_probe),
                       scratch_error_case_ids=ids(bad_scratch),
                       phase_error_case_ids=ids(bad_phase) if label == 'pair' else None,
                       sampled_mean_T=sim.operation_statistics().num_toffoli_like/len(batch))
            if label == 'prefix':
                row.update(numerator_error_case_ids=ids(np.any(actual[:420] != expected[:420], axis=0)),
                           denominator_error_case_ids=ids(np.any(actual[420:852] != expected[420:852], axis=0)),
                           gauge_data_error_case_ids=ids(np.any(actual[852:] != expected[852:], axis=0)))
            report['runs'].append(row)
            write(args.output/'report.json', report)
            print(json.dumps({k:v for k,v in row.items() if not k.endswith('_case_ids')}, sort_keys=True), flush=True)
            del sim
            gc.collect()
            assert not (bad_value | bad_probe | bad_scratch | bad_phase).any(), row
    del circuit
    gc.collect()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fixtures-file', type=Path)
    p.add_argument('--extra-fixtures', type=Path, action='append', default=[])
    p.add_argument('--weights', type=int, nargs='+', default=list(range(15, 36)))
    p.add_argument('--per-weight', type=int, default=1)
    p.add_argument('--j-min', type=int, default=15)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--count', type=int)
    p.add_argument('--batch-size', type=int, default=64)
    p.add_argument('--seeds', type=int, nargs='+', default=list(SEEDS))
    p.add_argument('--conditional-flag-phases', action='store_true')
    p.add_argument('--keep-circuits', action='store_true')
    args = p.parse_args()
    assert args.j_min in (15, 16, 17) and args.start >= 0 and args.batch_size > 0
    assert args.per_weight > 0 and all(args.j_min <= j <= 35 for j in args.weights)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.conditional_flag_phases:
        import rolling_tail_conditional as Conditional
        Pipeline.Tail = Conditional
        Extractor.Tail = Conditional
    events = []
    install_events(events)
    started = time.monotonic()
    selected, excluded, oracles, partition = load_cases(args)
    write(args.output/'fixtures.json', [dict(row, boundary_oracle=oracle)
                                       for row, oracle in zip(selected, oracles)])
    write(args.output/'explicit-key-domain-exclusions.json', excluded)
    key_sources = [C27/'synthesis/fixed_pipeline.py', C27/'synthesis/fused_crt_synthesis.py',
                   C27/'synthesis/public_geometry.py', C27/'arithmetic/raw_query_extractor.py',
                   C27/'arithmetic/gf24_arithmetic.py', C27/'controller/rolling_tail.py',
                   C27/'controller/rolling_tail_conditional.py', C27/'controller/scalar_seed.py',
                   HERE/'physical_boundary_oracle.py', C27/'census/reference.py']
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in key_sources}
    report = dict(status='RUNNING_NATIVE_ACTUAL_KEY_BOUNDARY', runs=[], **partition,
                  selected_cases=len(selected), key_domain_exclusions=len(excluded),
                  physical_weights=dict(sorted(Counter(row['weight'] for row in selected).items())),
                  gauges=dict(sorted(Counter(row['gauge'] for row in oracles).items())),
                  terminal_seed_flags=dict(sorted(Counter(row['terminal_seed_flag'] for row in oracles).items())),
                  conditional_flag_phases=args.conditional_flag_phases, source_sha256=source_hashes,
                  limitations=['Only the key admitted domain is asserted; exclusions are explicitly saved.',
                               'Half-converter exclusions remain eligible for this key-only panel.',
                               'The prefix has intentionally unpaid classical HMR debts and no phase assertion.',
                               'No full decoder or statistical failure certificate is implied.'])
    write(args.output/'report.json', report)
    paths = [args.output/name for name in ('prefix-a.kmb', 'pair-a.kmb', 'prefix-b.kmb', 'pair-b.kmb')]
    try:
        metrics, layout = build(args, events, label='first', prefix_path=paths[0], pair_path=paths[1])
        report.update(metrics=metrics, boundary_physical_indices=layout,
                      prefix_sha256=digest(paths[0]), pair_sha256=digest(paths[1]))
        again, again_layout = build(args, events, label='second', prefix_path=paths[2], pair_path=paths[3])
        assert metrics == again and layout == again_layout
        assert digest(paths[0]) == digest(paths[2]) and digest(paths[1]) == digest(paths[3])
        report['two_identical_builds'] = True
        write(args.output/'report.json', report)
        simulate(args, paths[0], 'prefix', layout, selected, oracles, report)
        simulate(args, paths[1], 'pair', layout, selected, oracles, report)
        assert source_hashes == {str(path.relative_to(ROOT)): digest(path) for path in key_sources}
        report['status'] = 'PASS_NATIVE_ALL_COEFFICIENT_KEY_BOUNDARY_PHASE_AND_RESTORATION'
    except BaseException as error:
        report['status'] = 'FAIL_OR_INTERRUPTED_NATIVE_KEY_BOUNDARY'
        report['failure'] = repr(error)
        report['elapsed_seconds'] = time.monotonic()-started
        write(args.output/'report.json', report)
        raise
    report['elapsed_seconds'] = time.monotonic()-started
    write(args.output/'report.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs', 'boundary_physical_indices', 'source_sha256')}, indent=2), flush=True)
    if not args.keep_circuits:
        for path in paths:
            path.unlink()


if __name__ == '__main__':
    main()
