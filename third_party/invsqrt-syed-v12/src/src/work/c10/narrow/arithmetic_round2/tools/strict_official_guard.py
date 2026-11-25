#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Official-only envelope after the monolithic reference-table AS limit.

Split simulation across two workers. The untouched verifier reference setup
gets640MiB hard AS; the entire child tree is limited to a tighter640MiB RSS
and six processes. The original shared lock,4GiB host headroom, identities,
cleanup, queue bounds and absolute deadline stay enforced. Native/math jobs
continue to use their unchanged512MiB hard-AS guard.
"""
from pathlib import Path
import argparse,fcntl,hashlib,os,signal,time
import strict_guard as strict
SOURCE=Path(__file__).with_name('strict_guard.py')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='bc01e3aa123f56bbf815bf55a0bef93ebc08f7dd0b99e51c0082ea96b3ba45bc'
assert strict.ADDRESS==512*strict.MiB and strict.RSS_STOP==768*strict.MiB and strict.PROCESS_CAP==8
strict.ADDRESS=640*strict.MiB
strict.RSS_STOP=640*strict.MiB
strict.PROCESS_CAP=6
parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--queue-seconds',type=float,default=900)
options,_=parser.parse_known_args();original=strict.guard.acquire_lock


def wait_on_shared_lock():
    try:return original()
    except strict.guard.GuardError as error:
        if str(error)!='another heavy operation holds the resource guard lock':raise
    path=f'/tmp/invsqrt-resource-guard-{os.getuid()}.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    old_handler=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('Bounded kernel wait expired before official workload launch.')
    try:
        if os.fstat(fd).st_uid!=os.getuid():raise strict.guard.GuardError('Shared lock is not owned by this user.')
        duration=min(options.queue_seconds,strict.LAUNCH_CUTOFF-time.time())
        if duration<=0:raise TimeoutError('Launch cutoff reached before workload.')
        print('{"event":"kernel_wait_on_original_shared_lock_official_two_worker_envelope"}',flush=True)
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,duration)
        fcntl.flock(fd,fcntl.LOCK_EX);signal.setitimer(signal.ITIMER_REAL,0)
        os.ftruncate(fd,0);os.write(fd,(str(os.getpid())+'\n').encode());return fd
    except BaseException:
        os.close(fd);raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)


strict.guard.acquire_lock=wait_on_shared_lock
raise SystemExit(strict.main())
