#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Parent-guarded serial candidate07 native batch with a new phase oracle."""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
NARROW = HERE.parents[1]


def verify_sources():
    for row in json.loads((HERE / 'SOURCE_READY.json').read_text())['files']:
        raw = (HERE / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
    for row in json.loads((HERE / 'INPUTS.json').read_text())['files']:
        raw = (NARROW / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--full-proof', action='store_true')
    args = ap.parse_args()
    hard = resource.getrlimit(resource.RLIMIT_AS)[1]
    assert 0 < hard <= 512 * 1024**2, 'Parent512MiB strict native guard is required.'
    verify_sources()
    py = sys.executable
    jobs = [[py, str(HERE / 'generate.py')],
            [py, str(HERE / 'prove50.py'), '--mode', 'selftest', '--output', str(HERE / 'checker50_selftest.json')],
            [py, str(HERE / 'prove50.py'), '--mode', 'sample', '--shots', '8192', '--seeds', '0,1,2,3', '--output', str(HERE / 'whole_native_sample.json')],
            [py, str(HERE / 'prove50.py'), '--mode', 'text', '--last', '1025', '--chunk', '1024', '--output', str(HERE / 'whole_native_text_diagnostic.json')]]
    if args.full_proof:
        jobs.append([py, str(HERE / 'prove50.py'), '--mode', 'text', '--output', str(HERE / 'whole_native_text_all.json')])
    began = time.monotonic()
    records = []
    for command in jobs:
        verify_sources()
        print(json.dumps(dict(candidate07_job_start=command[1], arguments=command[2:])), flush=True)
        started = time.monotonic()
        result = subprocess.run(command, check=False, timeout=720 if args.full_proof else 180)
        records.append(dict(command=command, returncode=result.returncode, seconds=time.monotonic() - started))
        (HERE / 'batch_partial.json').write_text(json.dumps(dict(status='PARTIAL', jobs=records), indent=2) + '\n')
        if result.returncode:
            raise SystemExit(result.returncode)
    verify_sources()
    out = dict(status='PASS_CANDIDATE07_NATIVE_BATCH_NOT_OFFICIAL', jobs=records,
               full_domain_text_proof=args.full_proof, serial_subprocesses=True,
               hard_address_space=hard, seconds=time.monotonic() - began,
               official_verifier=False, old_candidates_preserved=[1,2,3,4,5,6],
               new_independent_ring26_oracle=True, no_submission=True)
    (HERE / 'batch_complete.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2), flush=True)


if __name__ == '__main__':
    main()
