#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Create a v5b component manifest only from completed full native receipts.

This is a pure receipt/source reader. It launches no native job, sampler,
classifier or compiler. A missing gate aborts before the destination exists.
Only root invokes it after the fixed full component runs have completed.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import os
import sys

from v5b_binding import (ADDITIONAL_COMPONENTS, HERE, ROOT, canonical_digest,
                        checked_path, digest, verify_frozen_v4, verify_frozen_initial_v5)

DEST = HERE/'NATIVE_COMPONENT_GATES.json'
PLAN = HERE/'COMPONENT_GATE_PLAN.json'
PY = '/usr/bin/python3.13'
SEEDS_KEY = [147,1147,2147]
SEEDS_PREIMAGE = [137,1137,2137]
BASE_PREIMAGE = ROOT/'controller_work/after_v3/blocks/runs/quotient63-preimage-full/report.json'
BASE_PREIMAGE_SHA = '461bb69e8825e211ae7ba7a547fe92ce4a4969361c140b52ee71f8bf416d8ebb'
PREIMAGE_FIXTURES = 'controller_work/after_c5/converter_width/runs/full/fixtures.json'
PREIMAGE_FIXTURES_SHA = '6e023eb39758c15cc5e3835bc6bcdb0f8ad08c3ec15185d2c970dfbb201fac73'
SUPPLEMENT = 'controller_work/after_v3/k24/v5_transpose14/EXISTING_PROFILE_SUPPLEMENT.json'
SUPPLEMENT_SHA = '58303e050c3caa104bf5538ba76fd159cfb3b054addbfc5a02f343b0d1edd3dc'
SAVED_PHYSICAL = 'controller_work/night_c27/arithmetic/panel_audit/fixed-prepared/cases.json'
SAVED_PHYSICAL_SHA = 'abcd3a243eae059312a3d39b5fce19be75e0d692beec20cbd5197d30588932a7'
REFERENCE = 'controller_work/night_c27/census/reference.py'
REFERENCE_SHA = 'a43a7dbf3ef0cb02f8660067a0067c603cf39fe7a552584c3fc9bc228f501aa6'


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Inputs:
    def __init__(self):
        self.files = {}

    def add(self, path, expected=None):
        path = Path(path)
        path = path.resolve() if path.is_absolute() else (ROOT/path).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), 'Missing or outside input: '+str(path))
        sha = digest(path)
        require(expected is None or sha == expected, 'Input hash changed: '+str(path))
        name = str(path.relative_to(ROOT))
        row = dict(bytes=path.stat().st_size, sha256=sha)
        require(name not in self.files or self.files[name] == row, 'Input changed during reading: '+name)
        self.files[name] = row
        return name

    def read(self, path, expected=None):
        path = Path(path)
        path = path.resolve() if path.is_absolute() else (ROOT/path).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), 'Missing or outside JSON: '+str(path))
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        require(expected is None or sha == expected, 'JSON hash changed: '+str(path))
        name = str(path.relative_to(ROOT))
        row = dict(bytes=len(raw), sha256=sha)
        require(name not in self.files or self.files[name] == row, 'JSON changed during reading: '+name)
        self.files[name] = row
        return json.loads(raw)

    def report_sources(self, report):
        for field in ('source_bindings','loaded_sources','source_sha256','original_sources'):
            for name, row in report.get(field, {}).items():
                if isinstance(row, dict):
                    self.add(row.get('path',name), row['sha256'])
                else:
                    require(isinstance(row,str) and len(row) == 64, 'Invalid declared source hash')
                    self.add(name,row)

    def recheck(self):
        for name, row in self.files.items():
            path = checked_path(name)
            require(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'],
                    'Input changed before manifest write: '+name)


def check_guard(guard, planned):
    require(guard['status'] == 'complete' and guard['stopped'] is False
            and type(guard['exit_code']) is int and guard['exit_code'] == 0,
            'Component guard is incomplete, stopped or unsuccessful')
    cwd = Path(guard['cwd']).resolve()
    command = guard['command']
    require(cwd == ROOT and command[:2] == [PY,'-B'] and len(command) >= 5,
            'Component guard used another runtime or workspace')
    def resolved(name):
        path = Path(name)
        return path.resolve() if path.is_absolute() else (cwd/path).resolve()
    require(resolved(command[2]) == checked_path(planned['checker']), 'Wrong native checker invoked')
    options = {}
    index = 3
    while index < len(command):
        key = command[index]
        require(key in {'--output','--per-mode','--per-source','--batch-size','--keep-circuits'} and key not in options,
                'Unsupported or duplicate component option: '+str(key))
        if key == '--keep-circuits':
            options[key] = True
            index += 1
        else:
            require(index+1 < len(command), 'Component option is missing a value')
            options[key] = command[index+1]
            index += 2
    require('--output' in options and resolved(options['--output']) == checked_path(planned['report']).parent,
            'Guard output does not bind the actual report')
    if '--per-mode' in options:
        require(planned['name'] in {'retained_norm195_isolated','matched_norm_debts_isolated','quotient62_isolated'}
                and options['--per-mode'] == '4096',
                'Only the complete selected isolated fixture range is allowed')
    if '--per-source' in options:
        require(planned['name'] == 'cubic20_isolated' and options['--per-source'] == '64',
                'The cubic phase must cover all64 denominators and numerators')
    if '--batch-size' in options:
        require(planned['name'] in {'first_two_retained_norm_production_key','first_two_matched_norm_production_key'}
                and int(options['--batch-size']) > 0, 'Unexpected component batch option')


def cover(rows, seeds, total, start_key, count_key):
    require(sorted({row['seed'] for row in rows}) == seeds, 'Native HMR seed coverage differs')
    for seed in seeds:
        selected = sorted((row for row in rows if row['seed'] == seed), key=lambda row:row[start_key])
        cursor = 0
        for row in selected:
            require(type(row[start_key]) is int and type(row[count_key]) is int
                    and row[start_key] == cursor and row[count_key] > 0, 'Noncontiguous native fixture coverage')
            cursor += row[count_key]
        require(cursor == total, 'Native fixture set is incomplete or repeated')


def check_norm195(report):
    require(report['per_mode'] == 4096 and report['cases'] == 20480
            and report['modes'] == ['base_axis','extension_axis','equal_halves','arbitrary_K24','zero_source']
            and report['seeds'] == [59191,60191,61191]
            and report['full_subfield_axes'] is True and report['full_norm_range_on_base_axis'] is True,
            'Retained inverse did not complete the full required fixtures')
    require(report['accepted_and_frozen_v4_sources_unchanged'] is True
            and report['caller_owned_clean_bank_bits'] == 24
            and report['arbitrary_dirty_bank_supported'] is False
            and report['production_or_official_checked'] is False,
            'Retained inverse scope changed')
    require(set(report['rejected_contracts']) == {'source_length','bank_length','bank_alias','classical_bank','wrong_extension'},
            'Retained inverse contract-rejection coverage changed')
    rows = report['rows']
    require(len(rows) == 3 and {row['panel'] for row in rows} == {'closed_prefix','closed_pair','deferred_pair'},
            'Retained inverse panels incomplete')
    for row in rows:
        metrics = row['metrics']
        actions = 2 if row['panel'] == 'closed_pair' else 1
        static = 195*actions + (192 if row['panel'] == 'deferred_pair' else 0)
        require(row['two_identical_builds'] is True and metrics['component_static_T'] == static
                and metrics['probe_T'] == 3 and metrics['circuit_static_T'] == static+3
                and metrics['Q'] == 889 and metrics['retained_Q'] == 865
                and metrics['additional_helpers'] == metrics['separately_owned_clean_bits'] == 24
                and metrics['child_norm_masks'] == actions,
                'Retained inverse value/width/count contract differs')
        require(len(row['runs']) == 3 and [r['seed'] for r in row['runs']] == report['seeds'],
                'Retained inverse seed set differs')
        for run in row['runs']:
            zeros = run['observed_zero_cleanup_masks_by_call']
            require(run['cases'] == 20480 and not run['value_error_case_ids']
                    and run['scratch_errors'] is False and not run['phase_error_case_ids']
                    and len(zeros) == actions and all(type(x) is int and 0 <= x <= 20480 for x in zeros)
                    and run['total_T'] == run['independent_mask_exact_total_T'] == 20480*(static+3)-4*sum(zeros),
                    'Retained inverse simulation/count check failed')


def check_first_two(report):
    require(report['selected_cases'] == report['full_available_cases'] == report['total_key_domain_cases'] == 782
            and report['key_domain_exclusions'] == 76 and report['complete_key_domain'] is True
            and report['partition_start'] == 0 and report['partition_stop'] == 782
            and report['gauges'] == {'0':781,'1':1}
            and report['two_identical_builds'] is True,
            'Complete original key plus physical gauge-one fixture is required')
    require(report['production_initial_carry'] == 1
            and report['arbitrary_initial_carry_extension_tested'] is False
            and report['old_arbitrary_initial_carry_component_unchanged'] is True
            and report['accepted_and_frozen_v4_sources_unchanged'] is True,
            'Production carry or preservation scope changed')
    metrics = report['metrics']
    require(metrics['key_pair_static_T'] == 216986 and metrics['prefix_static_T'] == 101058
            and metrics['full_pair_static_T'] == 216989 and metrics['probe_static_T'] == 3
            and metrics['Q'] == 889 and metrics['closed_inverse_calls'] == 3
            and metrics['retained_carry_storage_bits'] == 24
            and metrics['static_T_model_delta_from_v4'] == -243
            and Fraction(metrics['exact_mean_delta_from_v4']) == -Fraction(1020002241,4194304),
            'New key ledger differs')
    expectation = metrics['exact_source_expectation']
    require(Fraction(expectation['expected_T_exact']) == Fraction(909157644619,4194304)
            and expectation['measured_mean_T'] is None, 'Key expectation is wrong or mislabelled')
    actual = {(e['name'],e['conditional_T'],e['mask_bits']):e['occurrences'] for e in expectation['events']}
    wanted = {('direct_carry84_selected_target_parities',84,24):33,
              ('inverse_phase27_12_helpers',27,12):67,
              ('last_return_child_norm_guard',15,6):1,
              ('scalar_inverse_six',4,6):4,
              ('tail_or_gauge_fresh_zero_phase',10,1):1,
              ('tail_or_gauge_fresh_zero_phase',22,1):20}
    require(actual == wanted and len(actual) == len(expectation['events']), 'Key event ownership differs')
    expected_borrow = dict(inverse_static_T=195,retained_storage_bits=24,original_norm_bits=12,
        child_norm_bits=6,child_inverse_bits=6,scalar_inverse_phase_static_T=4,
        maximum_additional_helpers=24,all_owned_storage_bits_reset=True)
    require(metrics['borrow_receipts'] == [expected_borrow]*3, 'All three clean-bank lifecycles are required')
    require(metrics['seam']['retained_Q'] == 864 and len(set(metrics['seam']['carry_indices'])) == 24,
            'Actual public-carry seam is absent')
    require({row['panel'] for row in report['runs']} == {'prefix','pair'}, 'Unknown or missing key panel')
    for panel in ('prefix','pair'):
        rows = [row for row in report['runs'] if row['panel'] == panel]
        cover(rows,SEEDS_KEY,782,'offset','count')
        fields = ['value_error_case_ids','probe_error_case_ids','scratch_error_case_ids']
        if panel == 'prefix':
            fields += ['numerator_error_case_ids','denominator_error_case_ids','gauge_data_error_case_ids']
        for row in rows:
            require(all(row[field] == [] for field in fields)
                    and row['phase_error_case_ids'] == (None if panel == 'prefix' else []),
                    'Key phase/value/restoration gate failed')
    cover(report['seam_runs'],SEEDS_KEY,782,'start','shots')
    for row in report['seam_runs']:
        require(row['panel'] == 'public_carry_seam' and row['constant_carry_error_case_ids'] == []
                and row['probe_error_case_ids'] == [] and row['scratch_errors'] is False
                and row['phase_checked'] is False,
                'Public-carry seam failed or its open phase was mislabelled')


def check_transpose11(report):
    require(report['sizes'] == [11] and report['cases_per_size'] == 256
            and report['seeds'] == [22901,22902,22903] and len(report['panels']) == 2,
            'Full isolated size11 handoff gate is required')
    gate = report['new_public_size_gate']
    require(gate['status'] == 'PASS_M11_ISOLATED_HANDOFF_GATE' and gate['smoke'] is False
            and gate['m'] == 11 and gate['complete_preimage_or_official_checked'] is False,
            'Isolated handoff scope changed')
    require(sorted(row['pair'] for row in report['panels']) == [False,True], 'Handoff prefix/pair missing')
    for row in report['panels']:
        metrics = row['metrics']
        require(row['m'] == 11 and row['two_identical_builds'] is True and metrics['Q'] == 889
                and metrics['core_T_per_call'] == 2724
                and metrics['static_T'] == (5561 if row['pair'] else 2768), 'Isolated handoff counts changed')
        require(len(row['simulations']) == 3 and [r['seed'] for r in row['simulations']] == report['seeds'],
                'Isolated handoff HMR seeds changed')
        for run in row['simulations']:
            require(run['cases'] == 256 and not run['errors'] and not run['phase_error_case_ids']
                    and run['returned_flag_observed'] is (not row['pair']), 'Isolated handoff gate failed')


def check_preimage(report, inputs):
    require(report['fixtures'] == 266 and report['gauge_charts'] == [0,1]
            and report['fixture_groups'] == dict(original_component=256, existing_profile_supplement=10)
            and report['two_identical_builds'] is True and report['prefix_two_identical_builds'] is True,
            'Complete original preimage fixtures plus fixed supplements are required')
    source = report['fixture_source']
    require(Path(source['path']).resolve() == checked_path(PREIMAGE_FIXTURES)
            and source['sha256'] == PREIMAGE_FIXTURES_SHA
            and source['original_cases'] == source['original_used_cases'] == 256
            and source['used_cases'] == 266 and source['supplement_cases'] == 10
            and source['selected_indices'] == list(range(256))
            and source['smoke'] is False and source['omissions'] == []
            and source['original_window14_modes'] == {'000':256}
            and source['new_population_draws'] == source['new_physical_inputs'] == 0
            and source['preimage_component_domain_only_supplement'] is True,
            'Original preimage fixtures were omitted, replaced or relabelled')
    extra = source['supplement']
    require(extra['path'] == SUPPLEMENT and extra['sha256'] == SUPPLEMENT_SHA
            and extra['source_path'] == SAVED_PHYSICAL and extra['source_sha256'] == SAVED_PHYSICAL_SHA
            and extra['classical_reference_path'] == REFERENCE
            and extra['classical_reference_sha256'] == REFERENCE_SHA
            and extra['original_indices'] == [3205,3320,3605,5894,6385]
            and extra['original_physical_records'] == 5 and extra['component_cases'] == 10
            and extra['gauges'] == [0,1] and extra['modes'] == {'100':2,'010':4,'001':4}
            and extra['whole_decoder_admitted_cases'] == 4
            and extra['cutoff_only_excluded_cases'] == 6
            and extra['all_preimage_component_admitted'] is True
            and extra['new_population_draws'] == extra['new_physical_inputs'] == 0,
            'Fixed supplement identities, domain labels or all-mode coverage changed')
    for path,sha in ((PREIMAGE_FIXTURES,PREIMAGE_FIXTURES_SHA),(SUPPLEMENT,SUPPLEMENT_SHA),
                     (SAVED_PHYSICAL,SAVED_PHYSICAL_SHA),(REFERENCE,REFERENCE_SHA)):
        inputs.add(path,sha)
    metrics = report['metrics']
    require(metrics['static_T'] == 115043 and metrics['prefix_static_T'] == 57034
            and metrics['circuit_static_T'] == 115046 and metrics['probe_T'] == 3
            and metrics['retained_data'] == 865
            and metrics['Q'] == 889 and metrics['delta_static_T'] == -38
            and metrics['prefix_delta_static_T'] == -19
            and metrics['lower_windows'] == metrics['transpose_windows'] == [14,17]
            and metrics['HMR_event_multiset_unchanged'] is True
            and metrics['additional_excluded_gap_pairs'] == []
            and Fraction(metrics['delta_uniform_fresh_mask_mean_T_exact']) == -38,
            'Transpose14 full caller ledger differs')
    baseline = inputs.read(BASE_PREIMAGE,BASE_PREIMAGE_SHA)['metrics']
    require(metrics['expectation']['events'] == baseline['expectation']['events']
            and metrics['prefix_expectation']['events'] == baseline['prefix_expectation']['events']
            and Fraction(metrics['expectation']['expected_T_exact']) ==
                Fraction(baseline['expectation']['expected_T_exact'])-38,
            'Transpose14 changed a conditional event or double-counted a discount')
    require(len(metrics['paired_phase_calls']) == 18
            and Counter(row['m'] for row in metrics['all_forward_calls']) == {11:2,14:2}
            and Counter(row['m'] for row in metrics['all_transpose_calls']) == {11:2,14:2}
            and len(metrics['all_transpose_handoffs']) == 4
            and sorted((row['n'],row['closing'],row['pay_existing_masks'])
                       for row in metrics['all_transpose_handoffs']) ==
                [(12,False,True),(12,True,False),(15,False,True),(15,True,False)]
            and all(row['new_quantum_allocations'] == 0 and row['exact_witness_owned'] is True
                    for row in metrics['all_transpose_handoffs'])
            and Counter(row['m'] for row in metrics['prefix_forward_calls']) == {11:1,14:1}
            and Counter(row['m'] for row in metrics['prefix_transpose_calls']) == {11:1,14:1}
            and sorted((row['n'],row['closing'],row['pay_existing_masks'])
                       for row in metrics['prefix_transpose_handoffs']) == [(12,False,True),(15,False,True)],
            'Actual public window call/handoff counts differ')
    local_debts = sorted([[closing,n] for closing in (False,True) for n in range(2,18)])
    require(metrics['gauge_parks'] == metrics['gauge_unparks'] == 14
            and metrics['parked_phase_payments'] == 2
            and sorted(metrics['created_local_debts']) == sorted(metrics['retired_local_debts']) == local_debts
            and metrics['pending_local_masks_after_pair'] == 0
            and metrics['top16_gauge_requeries'] == 1,
            'A source/local/gauge lifecycle remains unpaid')
    for field,prefix in (('roundtrip',False),('prefix_values',True)):
        rows = report[field]
        require(len(rows) == 3 and [row['seed'] for row in rows] == SEEDS_PREIMAGE,
                'Full preimage HMR seed coverage changed')
        for row in rows:
            require(row['shots'] == 266 and row['value_restoration_scratch_errors'] == 0
                    and row['prefix_values_only'] is prefix
                    and row['phase_errors'] == (None if prefix else 0)
                    and row['bad_value_indices'] == row['bad_phase_indices'] == [],
                    'Preimage native gate failed')


def check_matched_norm(report):
    require(report['per_mode'] == 4096 and report['cases'] == 20480
            and report['modes'] == ['base_axis','extension_axis','equal_halves','arbitrary_K24','zero_source']
            and report['seeds'] == [59191,60191,61191]
            and report['full_subfield_axes'] is True and report['full_norm_range_on_base_axis'] is True,
            'Matched inverse requires the complete isolated fixture range')
    require(report['accepted_and_frozen_v4_sources_unchanged'] is True
            and report['caller_owned_clean_bank_bits'] == 24
            and report['arbitrary_dirty_bank_supported'] is False
            and report['production_or_official_checked'] is False
            and report['prefix_value_only_with_open_six_bit_phase'] is True
            and report['production_carry_storage_seam_requires_separate_physical_key_gate'] is True,
            'Matched inverse storage, source preservation or phase scope changed')
    wanted_rejections = {'source_length','bank_length','bank_alias','classical_bank','wrong_extension',
                        'return_closed_record','return_wrong_builder','return_wrong_source','return_wrong_extension'}
    require(set(report['rejected_contracts']) == wanted_rejections
            and len(report['rejected_contracts']) == 9, 'Matched-record rejection gates incomplete')
    rows = report['rows']
    require(len(rows) == 2 and {row['panel'] for row in rows} == {'matched_prefix','matched_pair'},
            'Matched prefix/pair gates incomplete')
    expected_receipt = dict(inverse_static_T=195,retained_storage_bits=24,original_norm_bits=12,
        child_norm_bits=6,child_inverse_bits=6,scalar_inverse_phase_static_T=4,
        maximum_additional_helpers=24,all_owned_storage_bits_reset=True,deferred_prefix_mask_paid=True)
    for row in rows:
        paired = row['panel'] == 'matched_pair'
        static = 386 if paired else 191
        metrics = row['metrics']
        require(row['two_identical_builds'] is True and metrics['component_static_T'] == static
                and metrics['probe_T'] == 3 and metrics['circuit_static_T'] == static+3
                and metrics['Q'] == 889 and metrics['retained_Q'] == 865
                and metrics['separately_owned_clean_bits'] == metrics['additional_helpers'] == 24
                and metrics['child_norm_masks'] == (2 if paired else 1)
                and metrics['return_mask_positions'] == ([1] if paired else [])
                and metrics['prefix_mask_paid_at_matching_return'] is paired
                and metrics['phase_checked'] is paired
                and metrics['pending_prefix_phase_mask_bits'] == (0 if paired else 6)
                and metrics['stack_receipts'] == ([expected_receipt] if paired else []),
                'Matched inverse count, width, debt lifecycle or prefix scope differs')
        require(len(row['runs']) == 3 and [run['seed'] for run in row['runs']] == report['seeds'],
                'Matched inverse HMR seeds incomplete')
        for run in row['runs']:
            zeros = run['observed_zero_cleanup_masks_by_call']
            require(len(zeros) == (2 if paired else 1)
                    and all(type(x) is int and 0 <= x <= 20480 for x in zeros), 'Invalid observed HMR counts')
            require(run['cases'] == 20480 and not run['value_error_case_ids']
                    and run['scratch_errors'] is False and run['phase_checked'] is paired
                    and run['phase_error_case_ids'] == ([] if paired else None)
                    and run['total_T'] == run['independent_mask_exact_total_T'] ==
                        20480*(static+3)-(4*zeros[1] if paired else 0),
                    'Matched inverse native value, restoration, phase or exact count failed')


def check_cubic20(report):
    require(report['cases'] == 4096 and report['denominators'] == 64
            and report['all_64_numerators'] is True and report['exhaustive_all_field_pairs'] is True
            and report['seeds'] == [63191,64191,65191]
            and report['full_preimage_or_official_checked'] is False
            and report['whole_decoder_gain_banked'] is False,
            'Cubic20 must cover every small-field pair with isolated scope')
    require(set(report['rejected_contracts']) == {'wrong_length','same_word','duplicate_wire','classical_numerator'}
            and len(report['rejected_contracts']) == 4, 'Cubic20 malformed-source gates incomplete')
    require(len(report['rows']) == 2 and {row['panel'] for row in report['rows']} == {'phase','pair'},
            'Cubic20 phase/cancelling-pair panels incomplete')
    for row in report['rows']:
        static = 40 if row['panel'] == 'pair' else 20
        require(row['static_T'] == static and row['Q'] == 889 and row['retained_Q'] == 879
                and row['helpers'] == 10 and row['two_identical_builds'] is True,
                'Cubic20 width, count or reproducibility gate failed')
        require(len(row['runs']) == 3 and [run['seed'] for run in row['runs']] == report['seeds'],
                'Cubic20 native seeds incomplete')
        for run in row['runs']:
            require(set(run['value_error_case_ids']) == {'denominator','numerator','mask','dirty'}
                    and all(value == [] for value in run['value_error_case_ids'].values())
                    and run['phase_error_case_ids'] == [] and run['scratch_errors'] is False
                    and run['total_T'] == 4096*(static+3),
                    'Cubic20 phase, values, restoration or exact count failed')


def check_quotient62(report):
    require(report['cases'] == 20480 and report['per_mode'] == 4096
            and report['fixture_modes'] == ['zero_numerator','unit_numerator','basis_numerator',
                                           'arbitrary_numerator','zero_denominator']
            and report['seeds'] == [49191,50191,51191]
            and report['full_denominator_range_per_mode'] is True
            and report['full_numerator_range_at_zero_denominator'] is True
            and report['full_preimage_checked'] is False and report['full_DQI_or_official_checked'] is False,
            'Phase62 isolated fixture range or scope is incomplete')
    require(report['measured_single_phase_delta_T'] == -1 and report['measured_helper_delta'] == 4
            and report['full_preimage_static_delta_model'] == -18
            and Fraction(report['full_preimage_mean_delta_model_exact']) == -Fraction(150994935,8388608)
            and report['full_preimage_delta_is_conditional_on_18_paid_nonzero_mask_branches'] is True,
            'Phase62 body and caller models were conflated')
    require(set(report['rejected_contracts']) == {'same_word','one_wire_overlap','duplicate_wire','classical_word'}
            and len(report['rejected_contracts']) == 4, 'Phase62 invalid-input gates incomplete')
    rows = report['rows']
    require(len(rows) == 6 and {(row['implementation'],row['panel']) for row in rows} ==
            {(kind,panel) for kind in ('tensor','reference','candidate') for panel in ('prefix','pair')},
            'All six original tensor/reference/candidate panels are required')
    for row in rows:
        base,helpers = {'tensor':(42,0),'reference':(63,18),'candidate':(62,22)}[row['implementation']]
        actions = 2 if row['panel'] == 'pair' else 1
        metrics = row['metrics']
        require(row['two_identical_builds'] is True and metrics['action_count'] == actions
                and metrics['static_T'] == base*actions and metrics['probe_T'] == 3
                and metrics['circuit_static_T'] == base*actions+3 and metrics['retained_Q'] == 867
                and metrics['helpers'] == helpers and metrics['Q'] == 867+helpers,
                'Phase62 actual helper count or count/reproducibility gate failed')
        require(len(row['simulations']) == 3 and [run['seed'] for run in row['simulations']] == report['seeds'],
                'Phase62 native seed coverage incomplete')
        for run in row['simulations']:
            require(run['cases'] == 20480 and not run['value_error_case_ids']
                    and run['scratch_errors'] is False and run['phase_error_case_ids'] == []
                    and run['total_T'] == run['independent_expected_total_T'] == 20480*(base*actions+3),
                    'Phase62 native phase/value/restoration/count gate failed')


def check_matched_key(report):
    require(report['selected_cases'] == report['full_available_cases'] == report['total_key_domain_cases'] == 782
            and report['key_domain_exclusions'] == 76 and report['complete_key_domain'] is True
            and report['partition_start'] == 0 and report['partition_stop'] == 782
            and report['gauges'] == {'0':781,'1':1}
            and report['two_identical_builds'] is True,
            'Complete original key plus physical gauge-one fixture is required')
    require(report['production_initial_carry'] == 1
            and report['arbitrary_initial_carry_extension_tested'] is False
            and report['old_arbitrary_initial_carry_component_unchanged'] is True
            and report['accepted_and_frozen_v4_sources_unchanged'] is True,
            'Production carry or preservation scope changed')
    metrics = report['metrics']
    require(metrics['key_pair_static_T'] == 216983 and metrics['prefix_static_T'] == 101055
            and metrics['full_pair_static_T'] == 216986 and metrics['probe_static_T'] == 3
            and metrics['Q'] == 889 and metrics['closed_inverse_calls'] == 3
            and metrics['retained_carry_storage_bits'] == 24
            and metrics['static_T_model_delta_from_v4'] == -246
            and Fraction(metrics['exact_mean_delta_from_v4']) == -Fraction(1032585153,4194304),
            'New key ledger differs')
    expectation = metrics['exact_source_expectation']
    require(Fraction(expectation['expected_T_exact']) == Fraction(909145061707,4194304)
            and expectation['measured_mean_T'] is None, 'Key expectation is wrong or mislabelled')
    actual = {(e['name'],e['conditional_T'],e['mask_bits']):e['occurrences'] for e in expectation['events']}
    wanted = {('direct_carry84_selected_target_parities',84,24):33,
              ('inverse_phase27_12_helpers',27,12):67,
              ('last_return_child_norm_guard',15,6):1,
              ('scalar_inverse_six',4,6):4,
              ('tail_or_gauge_fresh_zero_phase',10,1):1,
              ('tail_or_gauge_fresh_zero_phase',22,1):20}
    require(actual == wanted and len(actual) == len(expectation['events']), 'Key event ownership differs')
    expected_borrow = dict(inverse_static_T=195,retained_storage_bits=24,original_norm_bits=12,
        child_norm_bits=6,child_inverse_bits=6,scalar_inverse_phase_static_T=4,
        maximum_additional_helpers=24,all_owned_storage_bits_reset=True,deferred_prefix_mask_paid=True)
    require(metrics['borrow_receipts'] == [expected_borrow]*3, 'All three clean-bank lifecycles are required')
    require(metrics['seam']['retained_Q'] == 864 and len(set(metrics['seam']['carry_indices'])) == 24,
            'Actual public-carry seam is absent')
    require(metrics['prefix_phase_debts_retired'] == 3
            and metrics['prefix_seam']['retained_Q'] == 865
            and metrics['prefix_seam']['initially_zero_tail_flag_index'] == 864
            and metrics['prefix_seam']['carry_indices'] == metrics['seam']['carry_indices'] == list(range(840,864)),
            'Both public carry lifetimes and all matched debts are required')
    require({row['panel'] for row in report['runs']} == {'prefix','pair'}, 'Unknown or missing key panel')
    for panel in ('prefix','pair'):
        rows = [row for row in report['runs'] if row['panel'] == panel]
        cover(rows,SEEDS_KEY,782,'offset','count')
        fields = ['value_error_case_ids','probe_error_case_ids','scratch_error_case_ids']
        if panel == 'prefix':
            fields += ['numerator_error_case_ids','denominator_error_case_ids','gauge_data_error_case_ids']
        for row in rows:
            require(all(row[field] == [] for field in fields)
                    and row['phase_error_case_ids'] == (None if panel == 'prefix' else []),
                    'Key phase/value/restoration gate failed')
    require({row['panel'] for row in report['seam_runs']} ==
            {'prefix_public_carry_seam','return_public_carry_seam'}, 'Both public-carry seams are required')
    for panel in ('prefix_public_carry_seam','return_public_carry_seam'):
        rows = [row for row in report['seam_runs'] if row['panel'] == panel]
        cover(rows,SEEDS_KEY,782,'start','shots')
        for row in rows:
            require(row['constant_carry_error_case_ids'] == [] and row['probe_error_case_ids'] == []
                    and row['scratch_errors'] is False and row['initial_tail_flag_error'] is False
                    and row['phase_checked'] is False,
                    'Matched public-carry seam failed or its open phase was mislabelled')


def check_preimage62(report, inputs):
    require(report['fixtures'] == 266 and report['gauge_charts'] == [0,1]
            and report['fixture_groups'] == dict(original_component=256, existing_profile_supplement=10)
            and report['two_identical_builds'] is True and report['prefix_two_identical_builds'] is True,
            'Complete original preimage fixtures plus fixed supplements are required')
    source = report['fixture_source']
    require(Path(source['path']).resolve() == checked_path(PREIMAGE_FIXTURES)
            and source['sha256'] == PREIMAGE_FIXTURES_SHA
            and source['original_cases'] == source['original_used_cases'] == 256
            and source['used_cases'] == 266 and source['supplement_cases'] == 10
            and source['selected_indices'] == list(range(256))
            and source['smoke'] is False and source['omissions'] == []
            and source['original_window14_modes'] == {'000':256}
            and source['new_population_draws'] == source['new_physical_inputs'] == 0
            and source['preimage_component_domain_only_supplement'] is True,
            'Original preimage fixtures were omitted, replaced or relabelled')
    extra = source['supplement']
    require(extra['path'] == SUPPLEMENT and extra['sha256'] == SUPPLEMENT_SHA
            and extra['source_path'] == SAVED_PHYSICAL and extra['source_sha256'] == SAVED_PHYSICAL_SHA
            and extra['classical_reference_path'] == REFERENCE
            and extra['classical_reference_sha256'] == REFERENCE_SHA
            and extra['original_indices'] == [3205,3320,3605,5894,6385]
            and extra['original_physical_records'] == 5 and extra['component_cases'] == 10
            and extra['gauges'] == [0,1] and extra['modes'] == {'100':2,'010':4,'001':4}
            and extra['whole_decoder_admitted_cases'] == 4
            and extra['cutoff_only_excluded_cases'] == 6
            and extra['all_preimage_component_admitted'] is True
            and extra['new_population_draws'] == extra['new_physical_inputs'] == 0,
            'Fixed supplement identities, domain labels or all-mode coverage changed')
    for path,sha in ((PREIMAGE_FIXTURES,PREIMAGE_FIXTURES_SHA),(SUPPLEMENT,SUPPLEMENT_SHA),
                     (SAVED_PHYSICAL,SAVED_PHYSICAL_SHA),(REFERENCE,REFERENCE_SHA)):
        inputs.add(path,sha)
    metrics = report['metrics']
    require(metrics['static_T'] == 115025 and metrics['prefix_static_T'] == 57034
            and metrics['circuit_static_T'] == 115028 and metrics['probe_T'] == 3
            and metrics['retained_data'] == 865
            and metrics['Q'] == 889 and metrics['delta_static_T'] == -56
            and metrics['prefix_delta_static_T'] == -19
            and metrics['lower_windows'] == metrics['transpose_windows'] == [14,17]
            and metrics['HMR_event_multiset_unchanged'] is False
            and metrics['exact_event_changes_only_paired62_names_and_rhs35'] is True
            and metrics['incremental_static_delta_vs_transpose14'] == -18
            and Fraction(metrics['incremental_mean_delta_vs_transpose14_exact']) == -Fraction(150994935,8388608)
            and metrics['additional_excluded_gap_pairs'] == []
            and Fraction(metrics['delta_uniform_fresh_mask_mean_T_exact']) == -56+Fraction(18,1 << 24),
            'Transpose14 full caller ledger differs')
    baseline = inputs.read(BASE_PREIMAGE,BASE_PREIMAGE_SHA)['metrics']
    expected_events = []
    for old_event in baseline['expectation']['events']:
        event = dict(old_event)
        if event['name'].startswith('paired_dual63_'):
            event['name'] = event['name'].replace('paired_dual63_', 'paired_dual62_')
            if event['name'] == 'paired_dual62_rhs_zero':
                require(event['conditional_T'] == 36 and event['mask_bits'] == 24
                        and event['occurrences'] == 18, 'Unexpected original paired-mask event')
                event['conditional_T'] = 35
                event['total_discount_exact'] = str(Fraction(18*35,1 << 24))
        expected_events.append(event)
    require(metrics['expectation']['events'] == expected_events
            and metrics['prefix_expectation']['events'] == baseline['prefix_expectation']['events']
            and Fraction(metrics['expectation']['expected_T_exact']) ==
                Fraction(baseline['expectation']['expected_T_exact'])-56+Fraction(18,1 << 24),
            'Transpose14 changed a conditional event or double-counted a discount')
    require(len(metrics['paired_phase_calls']) == 18
            and all(row['targets'] == 2 and row['static_T'] == 89 and row['peak_owned_helpers'] == 22
                    for row in metrics['paired_phase_calls'])
            and Counter(row['m'] for row in metrics['all_forward_calls']) == {11:2,14:2}
            and Counter(row['m'] for row in metrics['all_transpose_calls']) == {11:2,14:2}
            and len(metrics['all_transpose_handoffs']) == 4
            and sorted((row['n'],row['closing'],row['pay_existing_masks'])
                       for row in metrics['all_transpose_handoffs']) ==
                [(12,False,True),(12,True,False),(15,False,True),(15,True,False)]
            and all(row['new_quantum_allocations'] == 0 and row['exact_witness_owned'] is True
                    for row in metrics['all_transpose_handoffs'])
            and Counter(row['m'] for row in metrics['prefix_forward_calls']) == {11:1,14:1}
            and Counter(row['m'] for row in metrics['prefix_transpose_calls']) == {11:1,14:1}
            and sorted((row['n'],row['closing'],row['pay_existing_masks'])
                       for row in metrics['prefix_transpose_handoffs']) == [(12,False,True),(15,False,True)],
            'Actual public window call/handoff counts differ')
    local_debts = sorted([[closing,n] for closing in (False,True) for n in range(2,18)])
    require(metrics['gauge_parks'] == metrics['gauge_unparks'] == 14
            and metrics['parked_phase_payments'] == 2
            and sorted(metrics['created_local_debts']) == sorted(metrics['retired_local_debts']) == local_debts
            and metrics['pending_local_masks_after_pair'] == 0
            and metrics['top16_gauge_requeries'] == 1,
            'A source/local/gauge lifecycle remains unpaid')
    for field,prefix in (('roundtrip',False),('prefix_values',True)):
        rows = report[field]
        require(len(rows) == 3 and [row['seed'] for row in rows] == SEEDS_PREIMAGE,
                'Full preimage HMR seed coverage changed')
        for row in rows:
            require(row['shots'] == 266 and row['value_restoration_scratch_errors'] == 0
                    and row['prefix_values_only'] is prefix
                    and row['phase_errors'] == (None if prefix else 0)
                    and row['bad_value_indices'] == row['bad_phase_indices'] == [],
                    'Preimage native gate failed')


def main():
    require(__debug__ and sys.version_info[:2] == (3,13) and sys.executable == PY,
            'Use ordinary /usr/bin/python3.13 -B')
    temporary = DEST.with_name(DEST.name+'.tmp')
    require(not DEST.exists() and not temporary.exists(), 'Refuse to overwrite a native manifest')
    inputs = Inputs()
    plan = inputs.read(PLAN)
    require(plan['format'] == 'DQI_V5B_COMPONENT_GATE_PLAN_V1'
            and plan['status'] == 'SOURCE_PLAN_NOT_NATIVE_EVIDENCE'
            and plan['new_population_event'] is False
            and {row['name'] for row in plan['components']} == ADDITIONAL_COMPONENTS
            and len(plan['components']) == len(ADDITIONAL_COMPONENTS), 'Unreviewed component plan')
    for name,row in plan['source_files'].items():
        require(inputs.add(name,row['sha256']) == name and inputs.files[name]['bytes'] == row['bytes'],
                'Source-plan identity changed')
    inputs.add(Path(__file__))
    frozen = verify_frozen_v4()
    initial = verify_frozen_initial_v5()
    validators = dict(retained_norm195_isolated=check_norm195,
                      first_two_retained_norm_production_key=check_first_two,
                      transpose14_isolated=check_transpose11,
                      matched_norm_debts_isolated=check_matched_norm,
                      first_two_matched_norm_production_key=check_matched_key,
                      cubic20_isolated=check_cubic20,
                      quotient62_isolated=check_quotient62)
    components = []
    for planned in plan['components']:
        require(planned['checker'] in plan['source_files'], 'Native checker is not pinned by the plan')
        for name in (planned['report'],planned['guard']):
            if not (ROOT/name).is_file():
                raise FileNotFoundError(name)
        report = inputs.read(checked_path(planned['report']))
        guard = inputs.read(checked_path(planned['guard']))
        require(report['status'] == planned['passed_status'] and report['status'].startswith('PASS_'),
                'A selected full component has not passed: '+planned['name'])
        check_guard(guard,planned)
        inputs.report_sources(report)
        if planned['name'] == 'transpose14_preimage':
            check_preimage(report,inputs)
        elif planned['name'] == 'quotient62_transpose14_preimage':
            check_preimage62(report,inputs)
        else:
            validators[planned['name']](report)
        components.append(dict(name=planned['name'],report=planned['report'],guard=planned['guard'],
                               passed_status=planned['passed_status'],full_gate=True))
    require(frozen == verify_frozen_v4(), 'Frozen v4 changed during gate inspection')
    require(initial == verify_frozen_initial_v5(), 'Initial v5 source preparation changed')
    inputs.recheck()
    result = dict(format='DQI_V5B_COMPONENT_NATIVE_GATES_V1',
        status='ALL_SELECTED_COMPONENT_GATES_PASSED',new_population_event=False,
        plan_sha256=digest(PLAN),producer_sha256=digest(__file__),frozen_v4=frozen,
        frozen_initial_v5=initial,
        components=components,files={name:inputs.files[name] for name in sorted(inputs.files)},
        native_jobs_launched=0,sampler_or_population_draws=0,
        scope='Only actual full additional component gates. The complete new tape, joined panels, reproducibility and four fresh original official runs remain required.')
    with temporary.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    require(not DEST.exists(), 'Manifest appeared during qualification')
    os.replace(temporary,DEST)
    print(json.dumps(dict(status=result['status'],components=len(components),pinned_files=len(inputs.files),
                          manifest_sha256=digest(DEST))))


if __name__ == '__main__':
    try:
        main()
    except FileNotFoundError as error:
        print(json.dumps(dict(status='INCOMPLETE_NO_V5B_NATIVE_COMPONENT_MANIFEST',error=str(error))),file=sys.stderr)
        raise SystemExit(75)
    except (ValueError,KeyError,TypeError,AssertionError) as error:
        print(json.dumps(dict(status='INVALID_NO_V5B_NATIVE_COMPONENT_MANIFEST',error=str(error))),file=sys.stderr)
        raise SystemExit(1)
