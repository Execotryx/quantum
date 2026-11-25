#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Run our native prefix low-basis constructor on a hash-bound word table.

This constructs a basis only. A matching, original emitted circuit, all-branch
proof, and full-package qualification are separate mandatory steps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from planner import cross_tensor,complete_words,BlockPlan
from minrank import slices
from prefix_basis_descent import setup


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--words',type=Path,required=True)
    ap.add_argument('--k',type=int,required=True)
    ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seconds',type=float,default=120)
    ap.add_argument('--min-planes',type=int,default=1)
    ap.add_argument('--engine',type=Path,default=ROOT/'work/prefix_minrank/search_planes')
    ap.add_argument('--engine-source',type=Path,default=ROOT/'scripts/prefix_minrank.cpp')
    ap.add_argument('--resume-rows',type=Path)
    args=ap.parse_args()
    assert 1<=args.k<=3 and 0<=args.min_planes<=7
    args.out.mkdir(parents=True,exist_ok=True)
    with np.load(args.words,allow_pickle=False) as z:
        W=z['words' if 'words' in z.files else 'angle_words'].astype(np.uint8)
    prefix=hashlib.sha256(W.tobytes()).hexdigest()
    target=cross_tensor(complete_words(W),args.k)
    packed=np.asarray(slices(target),dtype='<u8')
    assert packed.shape==(75,15)
    target_file=args.out/f'k{args.k}_target.bin';packed.tofile(target_file)
    command=[str(args.engine.resolve()),str(target_file.resolve()),str(args.seed),
             str(args.seconds),'32767',str(args.min_planes)]
    resume_rows=[]
    if args.resume_rows:
        resume_rows=list(map(int,args.resume_rows.read_text().split()))
        assert len(resume_rows)%3==0 and len(resume_rows)<=12
        from planner import basis
        assert len(basis(resume_rows))==len(resume_rows)
        command.append(str(args.resume_rows.resolve()))
    start=time.time()
    result=subprocess.run(command,text=True,capture_output=True,timeout=args.seconds+30)
    (args.out/'construction.jsonl').write_text(result.stdout)
    if result.stderr:(args.out/'construction.stderr').write_text(result.stderr)
    records=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    if not records or records[-1].get('status')!='FOUND':
        print(json.dumps({'status':'BOUNDED_NO_BASIS','records':records,'returncode':result.returncode}),flush=True)
        raise SystemExit(3)
    state=records[-1]
    assert state['rows'][:len(resume_rows)]==resume_rows
    bp,_,rows,B,info=setup(W,state,args.k,True)
    assert all(i['rank']<=74 for i in info),info
    state.update(k=args.k,B=B,block_info=info,min_planes=args.min_planes,
                 target_prefix_sha256=prefix,word_file_sha256=sha(args.words),
                 target_sha256=sha(target_file),source_sha256=sha(args.engine_source),
                 engine_sha256=sha(args.engine),seconds=time.time()-start,
                 resumed_blocks=len(resume_rows)//3,
                 scope='OWN_BASIS_ONLY; no circuit or package qualification')
    dest=args.out/f'k{args.k}_basis.json';dest.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'status':'BASIS_CONSTRUCTED_AND_CHECKED','path':str(dest),
                      'seconds':state['seconds'],'block_info':info}),flush=True)


if __name__=='__main__':main()
