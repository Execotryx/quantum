#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Compare two new candidate builds and actual loaded sources, without Kickmix."""
from pathlib import Path
import argparse
import hashlib
import json
from source_binding import (atomic_json, canonical_digest, checked_path, digest,
                            verify_accepted_sources, ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first-build', type=Path, required=True)
    parser.add_argument('--second-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    reports = [json.loads(path.read_text()) for path in (args.first_build, args.second_build)]
    inventories = []
    for report in reports:
        assert report['status'] == 'BUILT_UNVERIFIED_POST_C5_FIXED_CANDIDATE'
        assert report['Q'] == 889 and report['measured_mean_T'] is None
        assert report['contract']['fixed_schedule'] and not report['contract']['compiler_profile']
        assert report['contract']['j_min'] == 15
        inventory_path = Path(report['source_inventory']['path']).resolve()
        assert inventory_path.is_file()
        assert digest(inventory_path) == report['source_inventory']['sha256']
        inv = json.loads(inventory_path.read_text())
        assert inv['status'] == 'CAPTURED_NEW_CANDIDATE_SOURCE_BINDING'
        assert inv['file_count'] == len(inv['files'])
        mapping = {row['path']: row for row in inv['files']}
        assert len(mapping) == len(inv['files'])
        assert canonical_digest(mapping) == inv['source_map_sha256']
        for name, row in mapping.items():
            path = checked_path(name)
            assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
        inventories.append(inv)
    assert inventories[0] == inventories[1], 'Runtime sources, bindings, or environment differ'
    for key in ('Q','static_T','instructions','classical_bits','full_DQI_scan',
                'contract','uniform_mask_source_expectation'):
        assert reports[0][key] == reports[1][key], key
    stages = [[{k:v for k,v in row.items() if k != 'elapsed_seconds'}
               for row in r['stages']] for r in reports]
    assert stages[0] == stages[1]
    hashes = [hashlib.sha256(), hashlib.sha256()]
    total = 0
    with Path(reports[0]['circuit']).open('rb') as left, Path(reports[1]['circuit']).open('rb') as right:
        while True:
            a, b = left.read(1 << 20), right.read(1 << 20)
            assert a == b, ('Circuit bytes differ', total)
            if not a:
                break
            hashes[0].update(a)
            hashes[1].update(b)
            total += len(a)
    sha = hashes[0].hexdigest()
    assert hashes[1].hexdigest() == sha
    assert all(r['sha256'] == sha and r['bytes'] == total for r in reports)
    baseline = verify_accepted_sources()
    assert baseline == inventories[0]['accepted_C5_and_frozen_sources']
    output = dict(status='PASS_NEW_CANDIDATE_BYTE_SOURCE_STAGE_EQUALITY',
                  circuit_sha256=sha, bytes_each=total,
                  source_map_sha256=inventories[0]['source_map_sha256'],
                  source_file_count=inventories[0]['file_count'],
                  source_and_runtime_bindings_identical=True, byte_identical=True,
                  stage_sequence_sha256=canonical_digest(stages[0]),
                  full_DQI_scan=reports[0]['full_DQI_scan'],
                  Q=reports[0]['Q'], static_T=reports[0]['static_T'],
                  contract=reports[0]['contract'],
                  measured_mean_T=None, official_cost=None,
                  first_build=dict(path=str(args.first_build.resolve()), sha256=digest(args.first_build)),
                  second_build=dict(path=str(args.second_build.resolve()), sha256=digest(args.second_build)),
                  scopes=['No circuit load, simulation, depth computation, sampler or official scoring call.',
                          'Memory-guard completion receipts remain separate from byte equality.',
                          'No new correctness, failure-budget, or goal-price PASS is inferred.'])
    atomic_json(args.output, output)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
