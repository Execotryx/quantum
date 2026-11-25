#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Prepare two existing third-chart physical cases, with no new draws.

The root runs this bounded classical preparer under its shared guard. It
reuses exact physical records already covered by the full component panel,
rechecks the unchanged complete classifier and both boundary oracles, and
writes one standard panel for the actual new gauge-one case and another
for the deterministically constructed zero third residue. Recorded case IDs
retain their exact original serialization scheme and mask-seed identity; a
standard physical/mask hash is also recorded without replacing the old ID.
It never calls
collect(), a random generator, a native simulator, or an official verifier.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
ROOT = WORK.parent
PANEL = WORK/'night_c27/arithmetic/panel_audit'
RUNS = HERE/'runs'

GAUGE_ID = '54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a'
ZERO_ID = '6663887a36baed1286a39bd8933a2c4d45a0660ef96a6a2b03ea0460588e00b0'
ZERO_STANDARD_ID = '8359bec906a50537fb2e812301e4cc81a3153c91ee62f1fd4cf83819c8e334a1'
CLASSIFIER_SHA = 'a43a7dbf3ef0cb02f8660067a0067c603cf39fe7a552584c3fc9bc228f501aa6'
PINS = {
    'controller_work/night_c27/arithmetic/panel_audit/check_key_boundary.py': '2a5af18b8b0bd0bc0fef2cacf88dfcf58ce9a88d4c5f8790251f108f2f1a11a2',
    'controller_work/after_v3/blocks/v6/prepare_integration_special_panels.py': '29c9c8dda21774d236caa2f06bc5ddc380cc3bfe9c6e5532489d586537101528',
    'controller_work/after_v3/blocks/v6/runs/integration-special-panels.guard.json': '33e76c120c3220a1429d8bf36f90afecc0cb5795d63f6d0ac56f9e48bcd3aa4b',
    'controller_work/after_v3/blocks/v6/runs/integration-special-panels.stdout': 'fb8470cc85927415294fecebd71c2477c62062bb8c19f5e96780d3221857beb6',
    'controller_work/night_c27/arithmetic/panel_audit/prepared/cases.json': 'eb9216d25bd69f17179533932f0ec6a8704860a366117bd370b6eec35495e339',
    'controller_work/night_c27/arithmetic/panel_audit/prepare_panels.py': '4007bd123f1eb77431acb32c6811d838e30f4455b6f87c537413955533962fa7',
    'controller_work/night_c27/arithmetic/panel_audit/physical_boundary_oracle.py': 'b2d7871501afdb528820c78989e408098ca441153fa16f98d4b5f9697810db99',
    'controller_work/night_c27/census/reference.py': CLASSIFIER_SHA,
    'controller_work/after_c5/extractor_width/direct_carry_scalar_screen.py': '0dd91ca47acab0a466e27e6374f9751e739e0c06f7b973b2d4aa34df034ceb28',
    'controller_work/after_v3/blocks/v6/boundary_scale_first3.py': '03fe157840d2ccd400aab5bf73fdb46c620c416a6007aa530797cb6db524105c',
    'controller_work/after_v3/blocks/v6/prepare_zero_third_fixture.py': 'b34ab50ac470bd66a46b175a45c5382123b8c476b35265d431345d2fd2cd10e0',
    'controller_work/after_v3/blocks/v6/check_first3_retained_norm_adapter.py': '3795553ea5ec70155d443a24d90930b9e32b8727d2f15abb98246edec33b4b17',
    'controller_work/after_v3/blocks/v6/runs/first3-full/report.json': '923df5eb0f79f2090f012cc5286267c1de5b3444177516658c4901fd348f9cb4',
    'controller_work/after_v3/blocks/v6/runs/first3-full/fixtures.json': 'b55d42970ef4572b20f2afc42aa4cabc5d017e0d0476d554e397014babc6e073',
    'controller_work/after_v3/blocks/v6/runs/first3-full.guard.json': '69860f68ff0f61a2e05850d377419337182469c611342af91a7576ef4aa9f85b',
    'controller_work/after_v3/blocks/v6/runs/third-raw-zero/cases.json': '3e7b5f07a0cbfc87e2b12da2ca739c5c70df2a0db2e1d1fa1ca34da4110b0882',
    'controller_work/after_v3/blocks/v6/runs/third-raw-zero/report.json': '6d111797aac57773d6f2838cb5c946a2aa4b70068096dc956c021143f74aece8',
    'controller_work/after_v3/blocks/v6/runs/third-raw-zero.guard.json': '8c72aced0233b70b5d95d1d4e7f0ff0881c08c1c1bb71e15c693705d125f36f4',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic(path, value):
    assert not path.exists(), str(path)
    temporary = path.with_name(path.name+'.tmp')
    assert not temporary.exists(), str(temporary)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def canonical_id(row):
    pairs = list(zip(row['positions'], row['values']))
    if row['mask_mode'] != 'one_hot':
        pairs.sort()
    identity = dict(errors=pairs, mask_mode=row['mask_mode'],
                    mask_values=row.get('mask_values'))
    raw = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def legacy_extra_id(row):
    # Exact immutable check_key_boundary.load_cases convention for extras.
    # List order is retained; mask mode is separately pinned to random.
    raw = json.dumps([row['positions'], row['values']],
                     separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def require_guard(path):
    guard = read(path)
    assert guard['status'] == 'complete' and guard['exit_code'] == 0
    assert guard['stopped'] is False
    return guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert __debug__, 'Assertions must be enabled'
    output = args.output.resolve()
    assert output.is_relative_to(RUNS) and not output.exists()
    for relative, expected in PINS.items():
        assert digest(ROOT/relative) == expected, relative
    require_guard(RUNS/'first3-full.guard.json')
    require_guard(RUNS/'third-raw-zero.guard.json')
    full = read(RUNS/'first3-full/report.json')
    assert full['status'] == 'PASS_PRODUCTION_THIRD_ZERO_REPAIRED_CHART_KEY'
    assert full['selected_cases'] == full['full_available_cases'] == 783
    assert full['complete_key_domain'] and full['two_identical_builds']
    assert full['gauges'] == {'0': 782, '1': 1}
    assert full['actual_new_gauge1_covered'] and full['physical_raw_zero_cases'] == 1
    assert full['metrics']['Q'] == 889
    assert full['metrics']['key_pair_static_T'] == 216928
    assert full['metrics']['prefix_static_T'] == 101087
    fixtures = read(RUNS/'first3-full/fixtures.json')
    assert len(fixtures) == 783 and len({row['case_id'] for row in fixtures}) == 783
    gauge_rows = [row for row in fixtures if row['boundary_oracle']['gauge'] == 1]
    zero_rows = [row for row in fixtures if row['boundary_oracle']['third_chart']['raw_zero']]
    assert len(gauge_rows) == len(zero_rows) == 1
    assert gauge_rows[0]['case_id'] == GAUGE_ID and zero_rows[0]['case_id'] == ZERO_ID

    original = read(PANEL/'prepared/cases.json')
    assert original['format'] == 'C27_PHYSICAL_PANEL_V1' and original['j_min'] == 15
    assert original['classifier_sha256'] == CLASSIFIER_SHA and original['classifications_present']
    prior_gauge = [row for row in original['cases'] if row['case_id'] == GAUGE_ID]
    assert len(prior_gauge) == 1
    zero_package = read(RUNS/'third-raw-zero/cases.json')
    zero_report = read(RUNS/'third-raw-zero/report.json')
    assert zero_package['format'] == 'C27_EXTRA_PHYSICAL_FIXTURES_V1'
    assert zero_package['classifier_sha256'] == CLASSIFIER_SHA and len(zero_package['cases']) == 1
    assert zero_report['status'] == 'PREPARED_ADMITTED_PHYSICAL_THIRD_RAW_ZERO_FIXTURE_NOT_NATIVE'
    assert zero_report['prepared_cases_sha256'] == digest(RUNS/'third-raw-zero/cases.json')
    assert zero_report['new_population_draws'] == 0 and zero_report['unchanged_complete_classifier_admitted']
    prior_zero = zero_package['cases'][0]
    assert legacy_extra_id(prior_zero) == ZERO_ID
    assert canonical_id(prior_zero) == ZERO_STANDARD_ID
    # V1 failed at this distinction before imports and before output creation.
    failed = read(RUNS/'integration-special-panels.guard.json')
    assert failed['status'] == 'complete' and failed['exit_code'] == 1
    assert failed['stopped'] is False

    # Import only after checking the exact unchanged source files. These are
    # the same scalar classifier/oracle APIs used by the native fixtures.
    sys.path.insert(0, str(PANEL))
    sys.path.insert(0, str(HERE))
    import prepare_panels as Panels
    import physical_boundary_oracle as Oracle
    import boundary_scale_first3 as Adapter
    assert Path(Panels.__file__).resolve() == PANEL/'prepare_panels.py'
    assert Path(Oracle.__file__).resolve() == PANEL/'physical_boundary_oracle.py'
    assert Path(Adapter.__file__).resolve() == HERE/'boundary_scale_first3.py'
    assert Path(Panels.Ref.__file__).resolve() == WORK/'night_c27/census/reference.py'
    source_bindings = dict(PINS)
    source_bindings[str(Path(__file__).resolve().relative_to(ROOT))] = digest(__file__)
    prepared = []
    for name, full_row, prior in (
            ('gauge1', gauge_rows[0], prior_gauge[0]),
            ('raw-zero', zero_rows[0], prior_zero)):
        row = copy.deepcopy({k: v for k, v in full_row.items() if k != 'boundary_oracle'})
        Panels.validate(row)
        assert row['mask_mode'] == 'random' and row.get('mask_values') is None
        identity = canonical_id if name == 'gauge1' else legacy_extra_id
        expected_id = GAUGE_ID if name == 'gauge1' else ZERO_ID
        expected_standard = GAUGE_ID if name == 'gauge1' else ZERO_STANDARD_ID
        assert row['case_id'] == identity(row) == identity(prior) == expected_id
        assert canonical_id(row) == canonical_id(prior) == expected_standard
        assert row['weight'] == len(row['positions']) == len(row['values'])
        for field in ('label', 'positions', 'values', 'roots', 'weight', 'mask_mode', 'syndromes'):
            assert row[field] == prior[field], (name, field)
        if name == 'gauge1':
            assert row['origins'] == prior['origins']
        assert row['roots'] == [Panels.Ref.EXP[index] for index in row['positions']]
        assert row['syndromes'] == Panels.moments(row['positions'], row['values'])
        classification = Panels.classify(row, 15)
        assert classification == row['classification']
        assert classification['admitted'] and not classification['reasons']
        assert classification['exact']['reason_mask'] == 0
        assert classification['exact']['union']['15'] is False
        old = Oracle.boundary(row['roots'], row['values'], j_min=15)
        new = Adapter.rescale_boundary(old)
        assert new == full_row['boundary_oracle']
        if name == 'gauge1':
            assert row['case_id'] == GAUGE_ID and row['weight'] == 18
            assert new['gauge'] == 1 and new['raw_carry'] == (2229 << 12)
            assert new['selected_lambda'] == 2229 and new['other_carry_half'] == 0
            assert old['raw_queries'][2] != 0 and not new['third_chart']['raw_zero']
        else:
            assert row['case_id'] == ZERO_ID and row['weight'] == 16
            assert old == prior['C5_boundary'] and new == prior['candidate_boundary']
            assert old['raw_queries'][2] == 0 and new['third_chart']['raw_zero']
            assert new['third_chart']['middle'] == 0 and new['gauge'] == 0
            assert new['third_chart']['queried_numerator'] and new['third_chart']['queried_denominator']
        prepared.append((name, row, dict(case_id=row['case_id'], label=row['label'],
            recorded_case_id_scheme=('prepare_panels_sorted_physical_mask_json' if name == 'gauge1'
                                     else 'key_harness_ordered_positions_values_json'),
            standard_canonical_physical_mask_id=canonical_id(row),
            secondary_hash_changes_recorded_mask_seed=False,
            weight=row['weight'], mask_mode=row['mask_mode'], gauge=new['gauge'],
            raw_carry=new['raw_carry'], selected_lambda=new['selected_lambda'],
            third_raw_query=old['raw_queries'][2], third_chart=new['third_chart'],
            unchanged_complete_classifier_admitted=True,
            exact_completed_key_boundary_match=True)))
    for relative, expected in source_bindings.items():
        assert digest(ROOT/relative) == expected, relative
    output.mkdir(parents=True, exist_ok=False)
    manifests = []
    for name, row, evidence in prepared:
        directory = output/name
        directory.mkdir()
        package = dict(format='C27_PHYSICAL_PANEL_V1', j_min=15, cases=[row],
            classifier_sha256=CLASSIFIER_SHA, source_files_sha256=source_bindings,
            classifications_present=True)
        atomic(directory/'cases.json', package)
        manifest = dict(status='PREPARED_EXACT_V6_SPECIAL_PHYSICAL_PANEL_NOT_NATIVE',
            panel=name, cases=1, new_draws=0, masks_drawn=False,
            recorded_case_id_and_mask_mode_preserved=True, physical_record_preserved=True,
            preparer_revision=2, identity_mapping=evidence['recorded_case_id_scheme'],
            standard_canonical_physical_mask_id=evidence['standard_canonical_physical_mask_id'],
            physical_boundary_checks=[evidence], source_bindings=source_bindings,
            prepared_cases_sha256=digest(directory/'cases.json'),
            existing_component_report_sha256=PINS['controller_work/after_v3/blocks/v6/runs/first3-full/report.json'],
            new_native_execution=False, complete_decoder_checked=False,
            population_claim=False, official_sampling_modified=False,
            mask_scope='Original random mode and canonical ID; unchanged native checker owns its mask seed.',
            scope='One exact existing case. Original corpus and all other gates remain separately required.')
        atomic(directory/'manifest.json', manifest)
        manifests.append(dict(panel=name, case_id=row['case_id'],
            cases_path=str((directory/'cases.json').relative_to(ROOT)),
            cases_sha256=digest(directory/'cases.json'),
            manifest_sha256=digest(directory/'manifest.json')))
    summary = dict(status='PREPARED_TWO_EXACT_V6_SPECIAL_PANELS_NOT_NATIVE',
        preparer_revision=2, recorded_extra_id_preserved=True,
        failed_v1_guard_sha256=PINS['controller_work/after_v3/blocks/v6/runs/integration-special-panels.guard.json'],
        cases=2, panels=manifests, source_bindings=source_bindings,
        new_draws=0, masks_drawn=False, new_native_execution=False,
        complete_decoder_checked=False, population_claim=False)
    atomic(output/'manifest.json', summary)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
