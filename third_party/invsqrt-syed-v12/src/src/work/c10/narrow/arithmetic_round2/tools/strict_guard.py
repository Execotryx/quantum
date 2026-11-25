#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Small-job guard for the sandbox where cgroup counters are not exposed.

This does not impersonate a cgroup-aware preflight. It explicitly records that
limitation and uses an independently enforced, smaller execution envelope:
512MiB hard address space per process;768MiB aggregate RSS; at least4GiB current
host headroom; at most8 live processes; one shared serialized job. Descendant
identity tracking/cleanup and the shared lock come from the pinned original
guard. The original guard and the official verifier are never modified.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,os,resource,selectors,signal,subprocess,sys,time
from collections import deque

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'checkpoint002/cleanroom/baseline_stage97/tooling/resource_guard.py'
SHA='6795b9ac76c889da1aa311ae59da5d1f1a6000a5c0cfbeec142185091943b202'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
spec=importlib.util.spec_from_file_location('_pinned_guard_helpers',SOURCE)
guard=importlib.util.module_from_spec(spec);sys.modules[spec.name]=guard;spec.loader.exec_module(guard)
WINDOW=Path(__file__).resolve().parents[1]/'WORK_WINDOW.json'
WINDOW_SHA='18a44534df9aaa46f4ab3bcaeb452e46cad3a7bd317a0edf798ee37ecde622fe'
assert hashlib.sha256(WINDOW.read_bytes()).hexdigest()==WINDOW_SHA
MiB=1024**2
ADDRESS=512*MiB;RSS_STOP=768*MiB;HEADROOM=4096*MiB;PROCESS_CAP=8
LAUNCH_CUTOFF=datetime.datetime(2026,11,12,9,50,tzinfo=datetime.timezone.utc).timestamp()
HARD_STOP=datetime.datetime(2026,11,12,9,55,tzinfo=datetime.timezone.utc).timestamp()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--timeout',type=float,required=True)
    ap.add_argument('--queue-seconds',type=float,default=900);ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--log',type=Path,required=True);ap.add_argument('--cwd',type=Path);ap.add_argument('--preflight',action='store_true')
    ap.add_argument('command',nargs=argparse.REMAINDER);args=ap.parse_args()
    if args.command and args.command[0]=='--':args.command=args.command[1:]
    assert 0<args.timeout<=3600 and 0<=args.queue_seconds<=1800
    assert args.preflight or args.command
    assert args.report.resolve()!=args.log.resolve()
    report=dict(status='QUEUED',work_window_sha256=WINDOW_SHA,work_window_path=str(WINDOW),source_helpers_sha256=SHA,cgroup_counters='UNAVAILABLE_IN_EXEC_SANDBOX_NOT_CLAIMED_CHECKED',
                substitute_envelope='Hard RLIMIT_AS plus lower aggregate RSS cap, current host headroom, bounded descendants and shared lock',
                limits=dict(per_process_hard_address_bytes=ADDRESS,aggregate_RSS_stop_bytes=RSS_STOP,
                            minimum_host_available_bytes=HEADROOM,live_process_cap=PROCESS_CAP),
                command=args.command,timeout_seconds=args.timeout,automatic_workload_retries=0,
                peak_aggregate_rss_bytes=0,peak_process_count=0,minimum_host_available_bytes=None,
                started_unix=time.time(),samples=[],child_cleanup=dict(complete=True,remaining_pids=[]))
    fd=None;child=None;tree=None;log=None;selector=None;old_signals={};interrupted=[]
    samples=deque(maxlen=1024);began=time.monotonic();last_save=0
    def save():
        report['elapsed_seconds']=time.monotonic()-began;report['samples']=list(samples)
        guard.atomic_json(args.report,report)
    def emit(event,**extra):
        line=json.dumps(dict(event=event,elapsed_seconds=time.monotonic()-began,**extra),allow_nan=False)
        print(line,flush=True)
        if log:log.write(('\n[strict_guard] '+line+'\n').encode());log.flush()
    def limit_child():
        resource.setrlimit(resource.RLIMIT_AS,(ADDRESS,ADDRESS))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        queued=False
        while fd is None:
            if time.time()>=LAUNCH_CUTOFF:raise RuntimeError('Launch cutoff reached before final checkpoint.')
            try:fd=guard.acquire_lock()
            except guard.GuardError as error:
                if str(error)!='another heavy operation holds the resource guard lock':raise
                if not queued:emit('queued_for_original_shared_lock');queued=True
                if time.monotonic()-began>=args.queue_seconds:raise RuntimeError('Bounded queue expired; no workload launched.')
                time.sleep(.5)
        args.log.parent.mkdir(parents=True,exist_ok=True);log=args.log.open('wb',buffering=0)
        report['queue_wait_seconds']=time.monotonic()-began
        host=guard.host_memory();guard.proc_snapshot()
        assert host['available_bytes']>HEADROOM,'Insufficient host memory headroom.'
        assert host['total_bytes']>=HEADROOM+RSS_STOP,'Host too small for the bounded envelope.'
        report['preflight_host']=host;report['status']='PREFLIGHT_PASS';save();emit('preflight_passed',limits=report['limits'])
        if args.preflight:return 0
        report['subreaper_enabled']=guard.become_subreaper()
        assert report['subreaper_enabled'],'Unable to track adopted descendants.'
        for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):
            old_signals[sig]=signal.getsignal(sig);signal.signal(sig,lambda number,frame:interrupted.append(number))
        child=subprocess.Popen(args.command,cwd=args.cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,bufsize=0,preexec_fn=limit_child)
        tree=guard.Tree(child.pid);selector=selectors.DefaultSelector();selector.register(child.stdout,selectors.EVENT_READ)
        report.update(status='RUNNING',child_pid=child.pid,child_cleanup=dict(complete=False,remaining_pids=[child.pid]));save()
        started=time.monotonic();reason='completed';output_bytes=0
        while True:
            for key,_ in selector.select(timeout=.2):
                data=os.read(key.fileobj.fileno(),65536)
                if data:
                    output_bytes+=len(data);log.write(data);sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
                else:selector.unregister(key.fileobj)
            members=tree.refresh();live=[p for p in members.values()if p.state not in guard.DEAD_STATES]
            rss=sum(p.rss for p in live);host=guard.host_memory();available=host['available_bytes']
            report['peak_aggregate_rss_bytes']=max(report['peak_aggregate_rss_bytes'],rss)
            report['peak_process_count']=max(report['peak_process_count'],len(live))
            report['minimum_host_available_bytes']=min(available,report['minimum_host_available_bytes']or available)
            sample=dict(elapsed_seconds=time.monotonic()-started,aggregate_rss_bytes=rss,live_processes=len(live),host_available_bytes=available)
            samples.append(sample)
            if interrupted:reason='interrupted'
            elif time.time()>=HARD_STOP:reason='absolute_final_saving_cutoff'
            elif time.monotonic()-started>=args.timeout:reason='wall_timeout'
            elif rss>=RSS_STOP:reason='aggregate_RSS_limit'
            elif available<=HEADROOM:reason='host_headroom_limit'
            elif len(live)>PROCESS_CAP:reason='process_count_limit'
            elif output_bytes>32*MiB:reason='log_limit'
            if reason!='completed':emit('stopping',reason=reason);break
            if child.poll()is not None and not selector.get_map():break
            if time.monotonic()-last_save>=2:save();last_save=time.monotonic()
        report['child_cleanup']=guard.cleanup(child,tree,1.0)
        report.update(status='COMPLETED'if reason=='completed'else'STOPPED',stop_reason=reason,returncode=child.poll(),output_bytes=output_bytes)
        if not report['child_cleanup']['complete']:report['status']='CLEANUP_FAILED'
        save();emit('finished',status=report['status'],returncode=report['returncode'],peak_rss=report['peak_aggregate_rss_bytes'])
        if not report['child_cleanup']['complete']:return 125
        return child.returncode if reason=='completed'and 0<=child.returncode<=255 else 124
    except BaseException as error:
        report.update(status='REFUSED'if child is None else'ERROR',error=f'{type(error).__name__}: {error}')
        if child is not None and tree is not None:report['child_cleanup']=guard.cleanup(child,tree,1.0)
        if fd is not None:save()
        emit('error',detail=report['error']);return 125
    finally:
        if child is not None and tree is not None and not report['child_cleanup'].get('complete',False):
            guard.cleanup(child,tree,1.0)
        if selector:selector.close()
        if child and child.stdout:child.stdout.close()
        for sig,handler in old_signals.items():signal.signal(sig,handler)
        if log:log.close()
        if fd is not None:os.close(fd)


if __name__=='__main__':raise SystemExit(main())
