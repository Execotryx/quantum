#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Same DQI memory guard with a blocking shared-lock acquisition.

Only the LOCK_NB flag differs from the accepted runtime guard. A waiting
process has no heavy child. Memory limits and process cleanup are unchanged.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def available():
    fields = dict(x.split(':', 1) for x in Path('/proc/meminfo').read_text().splitlines())
    result = int(fields['MemAvailable'].split()[0]) * 1024
    maximum, current = Path('/sys/fs/cgroup/memory.max'), Path('/sys/fs/cgroup/memory.current')
    if maximum.is_file() and current.is_file():
        limit = maximum.read_text().strip()
        if limit.isdecimal():
            result = min(result, int(limit) - int(current.read_text()))
    return result


def group_rss(pgid):
    total = 0
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():
            continue
        try:
            if os.getpgid(int(p.name)) == pgid:
                fields = dict(x.split(':', 1) for x in (p/'status').read_text().splitlines() if ':' in x)
                total += int(fields.get('VmRSS', '0').split()[0]) * 1024
        except (OSError, ProcessLookupError):
            pass
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--stdout', type=Path)
    p.add_argument('--cwd', type=Path)
    p.add_argument('--rss-soft', type=int, default=4_000_000_000)
    p.add_argument('--reserve', type=int, default=4_000_000_000)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command and a.command[0] == '--' else a.command
    if not command:
        p.error('command required')
    lock = open('/tmp/syed_dqi_heavy_job.lock', 'a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
    except BlockingIOError:
        raise SystemExit('Another DQI heavy job owns the lock; child not started.')
    if available() < a.reserve:
        raise SystemExit('Insufficient free memory; child not started.')
    a.log.parent.mkdir(parents=True, exist_ok=True)
    record = dict(command=command, cwd=str(a.cwd or Path.cwd()), start_unix=time.time(),
                  rss_soft=a.rss_soft, available_reserve=a.reserve, peak_rss=0,
                  status='starting', stopped=False, save_policy='Completed-stage logs remain on disk; split the interrupted stage before retry.')
    def save():
        record['elapsed_seconds'] = time.time()-record['start_unix']
        temp = a.log.with_suffix(a.log.suffix+'.tmp')
        temp.write_text(json.dumps(record, indent=2)+'\n')
        temp.replace(a.log)
    out = None
    if a.stdout:
        a.stdout.parent.mkdir(parents=True, exist_ok=True)
        out = a.stdout.open('wb')
    child = subprocess.Popen(command, cwd=a.cwd, start_new_session=True, stdout=out, stderr=subprocess.STDOUT if out else None)
    record.update(status='running', process_group=child.pid)
    save()
    stopping = False
    def terminate(reason):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        record.update(stopped=True, status='soft_stopping', stop_reason=reason)
        save()  # durable progress/stop record BEFORE terminating any process
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda signum, frame: terminate(f'guard signal {signum}'))
    last = 0.0
    try:
        while child.poll() is None:
            rss, free = group_rss(child.pid), available()
            record.update(current_rss=rss, available_bytes=free, peak_rss=max(rss, record['peak_rss']))
            if rss >= a.rss_soft:
                terminate('group RSS reached soft stop')
            elif free < a.reserve:
                terminate('available memory reached reserve')
            if time.monotonic()-last >= 5:
                save(); last=time.monotonic()
            time.sleep(0.2)
        record['exit_code'] = child.wait()
        record['status'] = 'stopped' if record['stopped'] else 'complete'
        save()
    except BaseException as e:
        terminate(f'guard exception {type(e).__name__}: {e}')
        child.wait()
        raise
    finally:
        # Reap/terminate descendants even when their leader exits normally.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        if out:
            out.close()
    print(json.dumps(record), flush=True)
    return 125 if record['stopped'] else record['exit_code']


if __name__ == '__main__':
    sys.exit(main())
