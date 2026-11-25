# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Parent-queued split continuation and finite framed-loader seed study."""
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from atomic_io import atomic_text

HERE = Path(__file__).resolve().parent


def output_text(value):
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')


def main():
    _, inherited = resource.getrlimit(resource.RLIMIT_AS)
    cap = 512*1024**2 if inherited == resource.RLIM_INFINITY else min(512*1024**2, inherited)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    signal.alarm(90)
    began = time.monotonic()
    manifest = json.loads((HERE/'loader_followup003_inputs.json').read_text())
    for item in manifest['files']:
        raw = (HERE/item['path']).read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    assert (HERE/'random_product_subspace.bin').exists(), 'Compilation is excluded from this batch.'
    old_path = HERE/'search/v2_first_q48_cap22_s8.json'
    old = json.loads(old_path.read_text())
    assert old['status'] == 'BOUNDED_PARTIAL' and old['mode'] == 'first_raw'
    assert old['Toffolis'] == 47 and len(old['loaded_output_masks']) == 11 and old['work_cap'] == 22
    old_digest = hashlib.sha256(old_path.read_bytes()).hexdigest()
    assert old_digest == '722578071128eccef2e33f4d99d5e073ea84d260281584f6451c7f73cb68653a'
    jobs = [
        ('v3_first_q48_cap22_s8_resume002', 'first_raw', 22, 8, old_path),
        ('v3_framed_second_q49_cap22_s0', 'second_framed', 22, 0, None),
        ('v3_framed_second_q49_cap22_s8', 'second_framed', 22, 8, None),
    ]
    records = []
    for name, mode, workcap, seed, resume in jobs:
        assert not (HERE/'search'/f'{name}.json').exists(), 'Use a new bounded slice name; do not overwrite prior evidence.'
        remaining = 88 - (time.monotonic()-began)
        if remaining <= 2:
            records.append(dict(name=name, mode=mode, status='NOT_STARTED_BATCH_BUDGET_EXHAUSTED'))
            break
        command = [sys.executable, '-u', str(HERE/'adaptive_loader_v2.py'),
                   '--name', name, '--mode', mode, '--work-cap', str(workcap),
                   '--seed', str(seed), '--seconds', '20', '--rounds', '8',
                   '--factor-seconds', '0.5', '--tail-seconds', '2']
        if resume is not None:
            command += ['--resume', str(resume)]
        started = time.monotonic()
        timeout = min(32, remaining)
        row = dict(name=name, mode=mode, command=command, child_hard_timeout=timeout)
        try:
            child = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            log = child.stdout+child.stderr
            row['returncode'] = child.returncode
        except subprocess.TimeoutExpired as exc:
            # subprocess.run has killed and waited for this worker. The outer
            # shared guard still owns cleanup of any complete process tree.
            log = output_text(exc.stdout)+output_text(exc.stderr)
            row.update(returncode=None, bounded_worker_timeout=True)
        row['seconds'] = time.monotonic()-started
        atomic_text(HERE/'search'/f'{name}.log', log)
        path = HERE/'search'/f'{name}.json'
        if path.exists():
            certificate = json.loads(path.read_text())
            row.update(status=certificate['status'], Toffolis=certificate['Toffolis'],
                loaded_outputs=len(certificate['loaded_output_masks']), complete_peak=certificate['complete_peak'],
                certificate_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            if resume is not None:
                row.update(resume_source=str(resume), resume_sha256=old_digest,
                           inherited_Toffolis=47, inherited_outputs=11)
            if certificate['status'] == 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE':
                remaining = 88-(time.monotonic()-began)
                if remaining > 1:
                    try:
                        check = subprocess.run([sys.executable, str(HERE/'replay_loader_v2.py'), str(path)],
                            capture_output=True, text=True, timeout=min(8, remaining))
                        atomic_text(HERE/'search'/f'{name}.replay.log', check.stdout+check.stderr)
                        row['independent_replay_returncode'] = check.returncode
                        assert check.returncode == 0, check.stdout+check.stderr
                        replay = json.loads(path.with_suffix('.replay.json').read_text())
                        assert replay['certificate_sha256'] == row['certificate_sha256']
                        row['independent_replay_sha256'] = hashlib.sha256(path.with_suffix('.replay.json').read_bytes()).hexdigest()
                    except subprocess.TimeoutExpired as exc:
                        atomic_text(HERE/'search'/f'{name}.replay.log', output_text(exc.stdout)+output_text(exc.stderr))
                        row['independent_replay_status'] = 'BOUNDED_TIMEOUT_NOT_A_CERTIFIED_SURVIVOR'
                else:
                    row['independent_replay_status'] = 'NOT_STARTED_NO_REMAINING_BUDGET_NOT_A_CERTIFIED_SURVIVOR'
        else:
            row['status'] = 'NO_CERTIFICATE_WRITTEN'
        assert hashlib.sha256(old_path.read_bytes()).hexdigest() == old_digest, 'The immutable old partial changed.'
        records.append(row)
        atomic_text(HERE/'loader_followup003.partial.json', json.dumps(dict(jobs=records,
            seconds=time.monotonic()-began), indent=2)+'\n')
        print(json.dumps(row), flush=True)
    result = dict(status='BOUNDED_SOURCE_SEARCH_BATCH_COMPLETE_NOT_NATIVE', jobs=records,
        seconds=time.monotonic()-began, global_hard_seconds=90, search_worker_AS_MiB=128,
        batch_AS_MiB=cap//1024**2, immutable_followup002_partial_sha256=old_digest,
        native_sources_unchanged=True, circuit_builds=0, official_verifier=False)
    atomic_text(HERE/'loader_followup003.json', json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
