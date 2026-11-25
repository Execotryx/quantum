#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Bind the unchanged original physical-panel checker to the fixed v6 tape.

With --fixtures-file, every selected fixture, including declared exclusions,
is simulated by the original corpus checker. Without it, the original small
all-terminal engineering panel is used. This wrapper does not weaken checks.
"""
from pathlib import Path
import argparse
import json
import runpy
import sys
from v6_paths import WORK
from v6_binding import atomic_json, digest, validate_inventory, verify_receipt_preservation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--circuit', type=Path, required=True)
    parser.add_argument('--build-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixtures-file', type=Path)
    parser.add_argument('--scan-positions', type=int, default=4095)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int)
    parser.add_argument('--weights', type=int, nargs='+', default=list(range(15,36)))
    parser.add_argument('--per-weight', type=int, default=1)
    args = parser.parse_args()
    assert not (args.output/'report.json').exists(), 'Use a new panel directory'
    build = json.loads(args.build_receipt.read_text())
    assert build['status'] == 'BUILT_UNVERIFIED_FIXED_V6_CANDIDATE'
    inventory = validate_inventory(build['source_inventory'])
    before = verify_receipt_preservation(inventory['preservation_and_component_gates'])
    assert build['Q'] == 889
    assert build['contract']['j_min'] == 15 and not build['contract']['compiler_profile']
    assert build['contract']['scan']['physical_positions'] == args.scan_positions
    assert args.circuit.resolve() == Path(build['circuit']).resolve()
    assert digest(args.circuit) == build['sha256']
    common = ['--circuit', str(args.circuit), '--output', str(args.output),
              '--scan-positions', str(args.scan_positions)]
    if args.fixtures_file is not None:
        script = WORK/'night_c27/arithmetic/panel_audit/check_fixture_corpus.py'
        child = [*common, '--fixtures-file', str(args.fixtures_file),
                 '--j-min','15','--batch-size',str(args.batch_size),'--start',str(args.start)]
        if args.count is not None:
            child += ['--count',str(args.count)]
    else:
        assert args.start == 0 and args.count is None
        script = WORK/'night_c27/check_candidate.py'
        child = [*common, '--weights',*[str(j) for j in args.weights],
                 '--per-weight',str(args.per_weight)]
    sys.path.insert(0, str(script.parent))
    old_argv = sys.argv
    try:
        sys.argv = [str(script), *child]
        runpy.run_path(str(script), run_name='__main__')
    finally:
        sys.argv = old_argv
    path = args.output/'report.json'
    report = json.loads(path.read_text())
    assert report['status'].startswith('PASS_')
    assert report.get('circuit_sha256', report.get('sha256')) == build['sha256']
    assert report['Q'] == 889 and report['static_T'] == build['static_T']
    assert before == verify_receipt_preservation(inventory['preservation_and_component_gates'])
    assert validate_inventory(build['source_inventory']) == inventory
    report['new_candidate_binding'] = dict(build_receipt=str(args.build_receipt.resolve()),
        build_receipt_sha256=digest(args.build_receipt), source_inventory=build['source_inventory'],
        runtime_bindings=build['contract']['runtime_bindings'],
        unchanged_checker=dict(path=str(script), sha256=digest(script)),
        accepted_C5_and_frozen_sources_unchanged=True,
        official_verification=False, new_population_draws=False)
    atomic_json(path, report)
    print(json.dumps(dict(status=report['status'], new_candidate_sha256=build['sha256'],
                          report=str(path.resolve()), report_sha256=digest(path))))


if __name__ == '__main__':
    main()
