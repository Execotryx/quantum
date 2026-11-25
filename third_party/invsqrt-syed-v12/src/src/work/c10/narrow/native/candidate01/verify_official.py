#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Run one untouched official full-domain verifier, with its original64 shots.

This wrapper has no tolerance, domain, or shot-count override. It records the
official result verbatim and only accepts the narrow task's Q<=52 limit.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
VERIFIER=NARROW/'base/official/verifier_invsqrt/verify_submission_invsqrt.py'
VERIFIER_SHA='ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('circuit',type=Path)
    ap.add_argument('--salt',choices=('default','1','2','3'),required=True)
    ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--max-workers',type=int,default=4);args=ap.parse_args()
    assert hashlib.sha256(VERIFIER.read_bytes()).hexdigest()==VERIFIER_SHA
    assert hashlib.sha256((NARROW/'base/official/kickmix/kickmix.so').read_bytes()).hexdigest()=='c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e'
    args.output_dir.mkdir(parents=True,exist_ok=True);circuit=args.circuit.resolve()
    files={name:args.output_dir/(args.salt+suffix)for name,suffix in (('stdout','.json'),('stderr','.stderr.txt'),('record','.record.json'))}
    assert not any(p.exists()for p in files.values()),'Use fresh official evidence paths.'
    digest=hashlib.sha256(circuit.read_bytes()).hexdigest()
    cmd=[sys.executable,str(VERIFIER),str(circuit),'--max-workers',str(args.max_workers)]
    if args.salt!='default':cmd+=['--salt',args.salt]
    env=os.environ.copy();env['PYTHONPATH']=str(NARROW/'base/official/kickmix')
    env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1'
    record=dict(status='RUNNING',circuit_sha256=digest,verifier_sha256=VERIFIER_SHA,
                salt=args.salt,required_inputs=3133452,required_shots_per_input=64,
                original_tolerance_unchanged=True,command=cmd,no_submission=True)
    files['record'].write_text(json.dumps(record,indent=2)+'\n');began=time.monotonic()
    print(json.dumps(record),flush=True)
    with files['stdout'].open('x')as out,files['stderr'].open('x')as err:
        result=subprocess.run(cmd,stdout=out,stderr=err,env=env,check=False)
    try:official=json.loads(files['stdout'].read_text())
    except (ValueError,OSError)as error:official=dict(status='ERROR',detail=str(error))
    passed=(result.returncode==0 and official.get('status')=='PASS'
            and official.get('verified_shots')==3133452*64
            and official.get('circuit_sha256')==digest and official.get('num_qubits',100)>0
            and official.get('num_qubits',100)<=52)
    record.update(status='PASS'if passed else'FAIL',exit_code=result.returncode,elapsed_seconds=time.monotonic()-began,
                  official_result=official,beats_stage97=passed and official['score']<92278.95,
                  target_met=passed and official['score']<=89987,stretch_met=passed and official['score']<=82740)
    files['record'].write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True)
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
