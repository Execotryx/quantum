#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Run the complete native proof once, under the original resource envelope."""
from pathlib import Path
import hashlib, json, subprocess, sys, time

HERE = Path(__file__).resolve().parent


def main():
    start = time.monotonic()
    manifest = json.loads((HERE/'SOURCE_READY.json').read_text())
    for pin in manifest['files']:
        p = HERE/pin['path']
        assert p.stat().st_size == pin['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == pin['sha256']
    jobs = [
        [sys.executable, str(HERE/'generate.py')],
        [sys.executable, str(HERE/'prove50.py'), '--mode', 'sample',
         '--output', str(HERE/'whole_native_sample.json')],
        [sys.executable, str(HERE/'prove50.py'), '--mode', 'text',
         '--output', str(HERE/'whole_native_text_all.json')],
    ]
    for command in jobs:
        print(json.dumps(dict(event='native_job', command=command)), flush=True)
        subprocess.run(command, check=True, timeout=240)
    result = dict(status='COMPLETE_NATIVE_BATCH_NOT_OFFICIAL',
        seconds=time.monotonic()-start, automatic_workload_retries=0,
        original_exact50_checker_and_selftests_unchanged=True)
    out = HERE/'native_batch_complete.json'
    assert not out.exists()
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
