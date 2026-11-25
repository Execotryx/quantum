#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Serial candidate04 batch, launched only by the parent's bounded guard."""
from pathlib import Path
import argparse,hashlib,json,resource,subprocess,sys,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]


def verify_sources():
    for row in json.loads((HERE/'SOURCE_READY.json').read_text())['files']:
        raw=(HERE/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
    for row in json.loads((HERE/'INPUTS.json').read_text())['files']:
        raw=(NARROW/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-proof',action='store_true');args=ap.parse_args()
    hard=resource.getrlimit(resource.RLIMIT_AS)[1]
    assert 0<hard<=512*1024**2,'Parent strict native guard with a512MiB hard address-space bound is required.'
    verify_sources();py=sys.executable
    jobs=[
        [py,str(NARROW/'research/postgate_angle_refit/quantize50.py')],
        [py,str(HERE/'generate.py')],
        [py,str(HERE/'prove50.py'),'--mode','selftest','--output',str(HERE/'checker50_selftest.json')],
        [py,str(HERE/'prove50.py'),'--mode','sample','--shots','8192','--seeds','0,1,2,3','--output',str(HERE/'whole_native_sample.json')],
        [py,str(HERE/'prove50.py'),'--mode','text','--last','1025','--chunk','1024','--output',str(HERE/'whole_native_text_diagnostic.json')],
    ]
    if args.full_proof:
        jobs.append([py,str(HERE/'prove50.py'),'--mode','text','--output',str(HERE/'whole_native_text_all.json')])
    began=time.monotonic();records=[]
    for command in jobs:
        verify_sources()
        print(json.dumps(dict(candidate04_job_start=command[1],arguments=command[2:])),flush=True)
        started=time.monotonic();completed=subprocess.run(command,check=False,timeout=720 if args.full_proof else 180)
        records.append(dict(command=command,returncode=completed.returncode,seconds=time.monotonic()-started))
        (HERE/'batch_partial.json').write_text(json.dumps(dict(status='PARTIAL',jobs=records),indent=2)+'\n')
        if completed.returncode:raise SystemExit(completed.returncode)
    verify_sources()
    result=dict(status='PASS_CANDIDATE04_NATIVE_BATCH_NOT_OFFICIAL',jobs=records,full_domain_text_proof=args.full_proof,
        serial_subprocesses=True,hard_address_space=hard,seconds=time.monotonic()-began,official_verifier=False,
        original_candidates_preserved=True,phase_grid_turns='1/1125899906842624',no_submission=True)
    (HERE/'batch_complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
