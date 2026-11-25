#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Normalize the supplied physical regression corpora without dropping cases.

This is classical fixture preparation, not simulation or a failure-frequency
certificate. Root should run classification-heavy invocations under the shared
guard. Old compiler profiles are provenance only; physical weight is recomputed
from the actual error list. Identical physical/mask cases retain every origin.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import random
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT/'controller_work'
C27 = WORK/'night_c27'
sys.path.insert(0, str(C27/'census'))
sys.path.insert(0, str(ROOT/'pro1_controller_bundle/1_task/tools'))
import reference as Ref
from rare_cases import generate_structured_cases


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def moments(positions, values):
    result = [0]*70
    for position, value in zip(positions, values):
        root = Ref.EXP[position]
        power = root
        for k in range(70):
            result[k] ^= Ref.mul(value, power)
            power = Ref.mul(power, root)
    return result


def validate(row):
    p, v = row['positions'], row['values']
    assert len(p) == len(v) <= 35 and len(set(p)) == len(p)
    assert all(0 <= x < 4095 for x in p) and all(0 < x < 4096 for x in v)
    assert row['mask_mode'] in ('random', 'zero', 'all', 'one_hot', 'recorded')
    if row['mask_mode'] == 'recorded':
        assert len(row['mask_values']) == 4095 and all(0 <= x < 4096 for x in row['mask_values'])
    else:
        assert row.get('mask_values') is None


def legacy_sources():
    return (
        ('M128_all_raw_boundaries', WORK/'work/round2/milestone153/restore_inputs/work/round2/milestone128/logs/raw-boundary-fixtures.json'),
        ('M127_physical_progressive', WORK/'work/round2/milestone152/logs/physical-progressive-fixtures.json'),
        ('M147_zero_history', WORK/'work/round2/milestone152/logs/zero-history-fixtures.json'),
        ('M152_cutoff_author_pool', WORK/'work/round2/milestone152/logs/cutoff17-fixtures.json'),
    )


def collect(fixed_shots_per_weight=0, extra_fixtures=()):
    grouped, source_files, source_counts = {}, {}, Counter()
    def add(row, origin):
        validate(row)
        pairs = list(zip(row['positions'], row['values']))
        # One-hot masks depend on the stated error-list order. Preserve it.
        if row['mask_mode'] != 'one_hot':
            pairs = sorted(pairs)
        key = dict(errors=pairs, mask_mode=row['mask_mode'], mask_values=row.get('mask_values'))
        if origin['panel'] == 'fixed_random_0_to_35':
            # Keep every fixed-suite draw, including repeated weight-zero
            # quantum inputs, so its independent mask fixture is not lost.
            key['fixed_draw'] = [origin['weight'], origin['index']]
        ident = hashlib.sha256(canonical_json(key).encode()).hexdigest()
        if ident not in grouped:
            grouped[ident] = dict(case_id=ident, label=row['label'],
                                 positions=list(row['positions']), values=list(row['values']),
                                 mask_mode=row['mask_mode'], origins=[])
            if row.get('mask_values') is not None:
                grouped[ident]['mask_values'] = list(row['mask_values'])
        grouped[ident]['origins'].append(origin)
        source_counts[origin['panel']] += 1
    for panel, path in legacy_sources():
        source_files[str(path.relative_to(ROOT))] = digest(path)
        for index, old in enumerate(json.loads(path.read_text())):
            positions, values = zip(*[(Ref.LOG[int(a)], int(e)) for a, e in old['errors']]) if old['errors'] else ((), ())
            origin = dict(panel=panel, source=str(path.relative_to(ROOT)), index=index,
                          legacy_terminal=int(old['j']), legacy_gaps=old['gaps'],
                          legacy_contacts=old['contacts'],
                          zero_history_contacts=old.get('zero_history_contacts', []))
            add(dict(label=f'{panel}:{index}', positions=list(positions), values=list(values),
                     mask_mode='random'), origin)
    case_root = ROOT/'pro1_controller_bundle/1_task/cases'
    for name in ('generated_rare_cases.json', 'recovered_historical_rare_cases.json',
                 'official_default_failure.json', 'official_salt3_failure.json'):
        path = case_root/name
        source_files[str(path.relative_to(ROOT))] = digest(path)
        for index, row in enumerate(json.loads(path.read_text())['cases']):
            origin = dict(panel=name.removesuffix('.json'), source=str(path.relative_to(ROOT)),
                          index=index, label=row['label'], certificate=row.get('certificate', {}))
            add(row, origin)
    structured_path = ROOT/'pro1_controller_bundle/1_task/tools/rare_cases.py'
    source_files[str(structured_path.relative_to(ROOT))] = digest(structured_path)
    for index, case in enumerate(generate_structured_cases()):
        row = case.to_dict()
        add(row, dict(panel='structured_0_to_35', source=str(structured_path.relative_to(ROOT)),
                      index=index, label=row['label'], certificate=row['certificate']))
    for path in extra_fixtures:
        path = Path(path).resolve()
        package = json.loads(path.read_text())
        assert package['format'] == 'C27_EXTRA_PHYSICAL_FIXTURES_V1'
        name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        source_files[name] = digest(path)
        for index, row in enumerate(package['cases']):
            add(row, dict(panel=package['panel'], source=name, index=index,
                          label=row['label'], certificate=row.get('certificate', {})))
    if fixed_shots_per_weight:
        rng = random.Random(202611112710)
        for weight in range(36):
            for index in range(fixed_shots_per_weight):
                positions = rng.sample(range(4095), weight)
                values = [rng.randrange(1, 4096) for _ in positions]
                label = f'fixed_weight_{weight}_draw_{index}'
                add(dict(label=label, positions=positions, values=values, mask_mode='random'),
                    dict(panel='fixed_random_0_to_35', seed=202611112710,
                         weight=weight, index=index, label=label))
    cases = list(grouped.values())
    for row in cases:
        row['weight'] = len(row['positions'])
        row['roots'] = [Ref.EXP[p] for p in row['positions']]
        row['syndromes'] = moments(row['positions'], row['values'])
    return cases, source_files, source_counts


def classify(row, j_min):
    result = Ref.classify(row['roots'], row['values'])
    admitted = row['weight'] >= j_min and result['reason_mask'] == 0
    reasons = []
    if row['weight'] < j_min:
        reasons.append('physical_weight_below_public_cutoff')
    for bit, name in ((Ref.FINITE_N, 'active_quadratic_numerator_zero'),
                      (Ref.FINITE_D, 'active_quadratic_denominator_zero'),
                      (Ref.DROP, 'half_Euclid_drop_at_least_three'),
                      (Ref.WINDOW17, 'half_window_17_and_15'),
                      (Ref.WINDOW14, 'half_window_14_and_12'),
                      (Ref.GCD, 'half_gcd_not_constant')):
        if result['reason_mask'] & bit:
            reasons.append(name)
    return dict(admitted=admitted, j_min=j_min, reasons=reasons, exact=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--j-min', type=int, default=15)
    parser.add_argument('--fixed-shots-per-weight', type=int, default=0)
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--extra-fixtures', type=Path, action='append', default=[])
    args = parser.parse_args()
    assert args.j_min in (15, 16, 17) and args.fixed_shots_per_weight >= 0
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    reference_sha = digest(C27/'census/reference.py')
    cases, source_files, counts = collect(args.fixed_shots_per_weight, args.extra_fixtures)
    outcomes = Counter()
    for index, row in enumerate(cases):
        if not args.inventory_only:
            row['classification'] = classify(row, args.j_min)
            outcomes['admitted' if row['classification']['admitted'] else 'declared_excluded'] += 1
            outcomes.update(row['classification']['reasons'])
        if index % 64 == 0:
            print(json.dumps(dict(stage='fixture_classification' if not args.inventory_only else 'inventory',
                                  completed=index+1, total=len(cases))), flush=True)
    assert reference_sha == digest(C27/'census/reference.py'), 'classifier changed during preparation'
    body = dict(format='C27_PHYSICAL_PANEL_V1', j_min=args.j_min, cases=cases,
                classifier_sha256=reference_sha,
                source_files_sha256=source_files,
                classifications_present=not args.inventory_only)
    path = args.output/'cases.json'
    path.write_text(json.dumps(body, indent=2)+'\n')
    legacy_low = sum(origin.get('legacy_terminal', 35) < 16 for row in cases
                     for origin in row['origins'] if origin['panel'] == 'M128_all_raw_boundaries')
    summary = dict(status='PREPARED_PHYSICAL_PANELS_NOT_SIMULATED', cases=len(cases),
                   input_origins=sum(counts.values()), origins_by_panel=dict(counts),
                   physical_weights=dict(sorted(Counter(c['weight'] for c in cases).items())),
                   old_M128_terminal_below16_origins_retained=legacy_low,
                   classification_summary=dict(outcomes), classifier_sha256=reference_sha,
                   cases_sha256=digest(path), source_files_sha256=source_files,
                   fixed_shots_per_weight=args.fixed_shots_per_weight,
                   classifications_present=not args.inventory_only,
                   elapsed_seconds=time.monotonic()-started,
                   limitations=['No quantum circuit was loaded or simulated.',
                                'Targeted/fixed corpora are not a failure-frequency estimate.',
                                'Every source row is retained as an origin; only identical physical/mask cases are coalesced.',
                                'Legacy compiler terminal/gaps/contacts are provenance, not new acceptance inputs.'])
    (args.output/'manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
