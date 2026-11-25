#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Find exact local CCX-to-affine rewrites on both legal loader endpoints.

Each truth table packs all 1220 addresses in both input directions. Before a
CCX, ask whether the product of its control values belongs to the affine span
of other live qubit values. A witness gives an X/CX replacement valid on the
entire legal input subspace. This is only an audit until the rewritten circuit
passes the separate symbolic phase proof and complete-package verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def packed(values):
    return sum(int(x) << i for i,x in enumerate(values))


def affine_witness(value, qubits, excluded, constant):
    pivots = {}
    for i,x in [(len(qubits),constant)] + [(i,x) for i,x in enumerate(qubits) if i != excluded and x]:
        combination=1<<i
        while x:
            b=x.bit_length()-1
            if b not in pivots:
                pivots[b]=(x,combination);break
            v,c=pivots[b];x^=v;combination^=c
    combination=0
    while value:
        b=value.bit_length()-1
        if b not in pivots:return None,len(pivots)
        v,c=pivots[b];value^=v;combination^=c
    return combination,len(pivots)


def audit(source,words,k,rewrite=None):
    original=source.read_text();lines=original.splitlines();registers={};names={}
    for line in lines:
        a=line.split()
        if not a:continue
        if a[0]=='APPEND_TO_REGISTER':registers.setdefault(a[2],[]).append(int(a[1][1:]))
        elif a[0]=='REGISTER':names[a[1]]=a[2].strip('"')
    reg={names[r]:qs for r,qs in registers.items()}
    A=len(words);mask=(1<<(2*A))-1;q=[0]*128
    for j,qi in enumerate(reg['selection']):
        value=packed(((np.arange(A)>>j)&1).tolist());q[qi]=value|(value<<A)
    for j in range(5):
        prev=words[:,5*(k-1)+j] if k else np.zeros(A,dtype=int)
        curr=words[:,5*k+j]
        for b,qi in enumerate(reg[f'word_{j}']):
            q[qi]=packed(((prev>>b)&1).tolist())|(packed(((curr>>b)&1).tolist())<<A)
    initial_selection=[q[x] for x in reg['selection']]
    newlines=[];witnesses=[];ccx=0;start=time.time();span_ranks=[]
    for index,line in enumerate(lines):
        a=line.split()
        if not a or a[0] in ('REGISTER','APPEND_TO_REGISTER'):
            newlines.append(line);continue
        op=a[0];idx=[int(x[1:]) for x in a[1:] if x.startswith('q')]
        replacement=None
        if op=='X':q[idx[0]]^=mask
        elif op=='CX':q[idx[1]]^=q[idx[0]]
        elif op=='CCX':
            ccx+=1;v=q[idx[0]]&q[idx[1]]
            witness,rank=affine_witness(v,q,idx[2],mask);span_ranks.append(rank)
            if witness is not None:
                controls=[i for i in range(128) if witness>>i&1]
                assert idx[2] not in controls
                actual=mask if witness>>128&1 else 0
                for i in controls:actual^=q[i]
                assert actual==v
                replacement=([f'X q{idx[2]}'] if witness>>128&1 else [])
                replacement += [f'CX q{i} q{idx[2]}' for i in controls]
                witnesses.append({'line_index':index,'original':line,'span_rank':rank,
                                  'constant':bool(witness>>128&1),'controls':controls,
                                  'replacement':replacement})
            q[idx[2]]^=v
        elif op=='HMR':q[idx[0]]=0
        elif op=='R':assert q[idx[0]]==0,('nonzero reset',k,index)
        elif op=='CZ':assert a[3]=='if'
        else:raise ValueError(('unsupported instruction',op))
        newlines.extend([line] if replacement is None else replacement)
    assert initial_selection==[q[x] for x in reg['selection']]
    for j in range(5):
        prev=words[:,5*(k-1)+j] if k else np.zeros(A,dtype=int)
        curr=words[:,5*k+j]
        for b,qi in enumerate(reg[f'word_{j}']):
            target=packed(((curr>>b)&1).tolist())|(packed(((prev>>b)&1).tolist())<<A)
            assert q[qi]==target,('endpoint mismatch',k,j,b)
    owned={qi for qs in reg.values() for qi in qs}
    assert all(x==0 for qi,x in enumerate(q) if qi not in owned)
    if rewrite is not None and witnesses:
        rewrite.parent.mkdir(parents=True,exist_ok=True)
        rewrite.write_text('\n'.join(newlines)+'\n')
    return {'k':k,'ccx':ccx,'exact_local_rewrite_count':len(witnesses),
            'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
            'legal_truth_table_cases':2*A,'endpoint_values_checked':True,
            'span_rank_range':[min(span_ranks),max(span_ranks)],
            'witnesses':witnesses,'seconds':time.time()-start,
            'scope':'LOCAL_AFFINE_IDENTITY_AUDIT; full gates still required for a rewritten package'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('package',type=Path)
    ap.add_argument('--k',nargs='+',type=int,default=[4,5,6,7]);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rewrite-dir',type=Path);args=ap.parse_args()
    with np.load(args.package/'submission.npz',allow_pickle=False) as z:words=z['angle_words'].astype(np.int64)
    results=[]
    for k in args.k:
        row=audit(args.package/f'sources/angle_k_{k}.kmx',words,k,
                  args.rewrite_dir/f'angle_k_{k}.kmx' if args.rewrite_dir else None)
        results.append(row);print(json.dumps({a:b for a,b in row.items() if a!='witnesses'}),flush=True)
    report={'package':str(args.package),'word_prefix_sha256':hashlib.sha256(words.astype(np.uint8).tobytes()).hexdigest(),
            'results':results,'total_exact_local_rewrites':sum(r['exact_local_rewrite_count'] for r in results)}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
