#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only m11 gate using the unchanged isolated handoff checker.

The fixed new size is11. This wrapper pins and invokes the original native
checker, then adds source-preservation bindings to its new output receipt.
It never edits the old checker, tensor, fixtures, or any existing receipt.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import variant_support as Support

PINS = {
    'check_transpose_handoff.py': '6e5c6264937963bf07fe764a988b6fd2a921f9e9638a20faa24593c8509aeb47',
    'check_transpose_retained.py': 'fa9355de142e7c3b3b2265063e1891167bdec10ef7634b7b9a5adfe60a24803b',
    'window_transpose_handoff.py': 'bb8423494ded91d4b42e83b147de4d45cf5bdb87695788ea66ef73cc3f817b21',
}


def check_pins():
    for name, wanted in PINS.items():
        assert Support.digest(Support.BLOCKS/name) == wanted, name
    return dict(PINS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert __debug__ and sys.version_info[:2] == (3, 13)
    args.output.mkdir(parents=True, exist_ok=True)
    assert not any(args.output.iterdir()), 'Use a fresh empty output directory'
    Support.enable_import_paths()
    pins = check_pins()
    derivation = Support.verify_derivation()
    frozen = Support.verify_frozen_v4()
    sources = Support.source_snapshot()
    path = Support.BLOCKS/'check_transpose_handoff.py'
    spec = importlib.util.spec_from_file_location('unchanged_m11_handoff_checker', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    argv = sys.argv
    per_mode = 8 if args.smoke else 64
    try:
        sys.argv = [str(path), '--output', str(args.output), '--sizes', '11',
                    '--per-mode', str(per_mode)]
        if args.keep_circuits:
            sys.argv.append('--keep-circuits')
        assert module.main() == 0
    finally:
        sys.argv = argv
    report_path = args.output/'report.json'
    report = json.loads(report_path.read_text())
    assert report['status'] == 'PASS_NATIVE_TRANSPOSE_FLAG_HANDOFF_COMPONENT_ONLY'
    assert report['sizes'] == [11] and report['cases_per_size'] == 4*per_mode
    assert report['seeds'] == [22901, 22902, 22903]
    assert len(report['panels']) == 2
    assert sorted(row['pair'] for row in report['panels']) == [False, True]
    for row in report['panels']:
        assert row['m'] == 11 and row['two_identical_builds'] is True
        metrics = row['metrics']
        assert metrics['Q'] == 889 and metrics['core_T_per_call'] == 2724
        assert metrics['static_T'] == (5561 if row['pair'] else 2768)
        assert len(row['simulations']) == 3
        assert [r['seed'] for r in row['simulations']] == [22901, 22902, 22903]
        assert all(not r['errors'] and not r['phase_error_case_ids']
                   and r['cases'] == 4*per_mode for r in row['simulations'])
    assert pins == check_pins()
    assert derivation == Support.verify_derivation()
    assert frozen == Support.verify_frozen_v4()
    assert sources == Support.source_snapshot()
    report['new_public_size_gate'] = dict(
        status='PASS_M11_ISOLATED_HANDOFF_GATE', m=11, smoke=args.smoke,
        unchanged_checker_pins=pins, source_snapshot=sources,
        copied_caller_derivation=derivation, frozen_v4_preservation=frozen,
        complete_preimage_or_official_checked=False,
        paired_caller_delta_T_model=-38,
        paired_caller_model_requires_separate_full_preimage_gate=True)
    temporary = report_path.with_name(report_path.name+'.tmp')
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    temporary.replace(report_path)
    print(json.dumps(dict(status='PASS_M11_ISOLATED_HANDOFF_GATE',
                          smoke=args.smoke, cases=4*per_mode,
                          report_sha256=Support.digest(report_path))), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
