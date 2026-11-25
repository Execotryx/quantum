#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Original early-loader basis search using dependent two-low-function slices.

For a generic35-output early loader, choose independent low duals x,y,z with
rank([T_x,T_y])<=69, rank([T_x,T_z])<=69, rank([T_y,T_z])<=69.
These expose cut vectors whose projection onto a low form is zero. Keeping
those vectors reduces projected constraint ranks before the pairing search.
All data come from our reordered C table; no public basis is a build input.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time
import sys
import numpy as np
from planner import (BlockPlan, complete_words, cross_tensor, basis, reduce, proj,
                     candidates, physical_cuts, solve_padding, padded_words, NDIM)
from minrank import slices, rslice, dependencies
from lowbasis import inverse15, transform_target, to_physical
from transport_cuts import complete_forced
from compile_reordered_prefix import ROOT, rank_pairs
from extract_matching import matching
from emit_plan import emit
from prove_loader_branches import prove_one

PARTS=[[3*i+j for j in range(3)]for i in range(5)]


def generate(T,rng,seconds=60,planes=3):
    cache={}
    def values(v):
        if v not in cache:cache[v]=rslice(T,v)
        return cache[v]
    def pairdim(x,y):
        return len(dependencies([a|(b<<35)for a,b in zip(values(x),values(y))]))
    start=time.time();rows=[];details=[]
    for block in range(5):
        found=False
        while time.time()-start<seconds and not found:
            x=rng.randrange(1,32768)
            if len(basis(rows+[x]))!=len(rows)+1:continue
            for _ in range(600):
                y=rng.randrange(1,32768)
                if len(basis(rows+[x,y]))!=len(rows)+2:continue
                if pairdim(x,y)>=6:break
            else:continue
            for it in range(6000):
                if it%128==0 and time.time()-start>seconds:break
                z=rng.randrange(1,32768)
                if len(basis(rows+[x,y,z]))!=len(rows)+3:continue
                if pairdim(x,z)<6:continue
                if planes>=3 and pairdim(y,z)<6:continue
                rows += [x,y,z]
                details.append({'block':block,'triple':[x,y,z],
                                'pair_high_kernel_dimensions':[pairdim(x,y),pairdim(x,z),pairdim(y,z)]})
                found=True;break
        if not found:return None
    return {'rows':rows,'details':details,'seconds':time.time()-start,'kind':'own two-plane dependency search'}


def setup(target,rows):
    B=inverse15(rows);tt=transform_target(target,B)
    bp=BlockPlan(tt,PARTS,[],per_coord=False,hmax=76)
    for b,full in enumerate(bp.full):
        forced=[]
        for l in range(1,8):
            for dep in dependencies([proj(x,l)for x in full]):
                v=0
                for i,x in enumerate(full):
                    if dep>>i&1:v^=x
                forced.append(v)
        bp.F[b]=list(basis(forced).values())
        bp.Q[b]=complete_forced(full,bp.F[b])
    return bp,B


def random_rows(vectors,n,rng):
    out=[];bb={}
    while len(out)<n:
        v=0
        for x in vectors:
            if rng.getrandbits(1):v^=x
        if reduce(v,bb):out.append(v);bb=basis(out)
    return out


def fit(target,bp,rows,rng,out,k,seconds=180,products=215):
    total=NDIM-2*products
    dims=[19]*5
    for i in range(total-95):dims[i%5]+=1
    d=2*products
    def cuts(R):return [bp.F[i]+R[i]for i in range(5)]
    def evaluate(R):
        cs=cuts(R);ps,_=candidates({'parts':PARTS,'cuts':cs},cs)
        return len(basis(x for p in ps for x in p[:2])),ps
    best=None;start=time.time()
    for trial in range(40):
        R=[random_rows(bp.Q[i],dims[i]-len(bp.F[i]),rng)for i in range(5)]
        sp,ps=evaluate(R)
        if best is None or sp>best[0]:best=(sp,[x[:]for x in R],ps)
    sp,R,ps=best;bestsp=sp;bestR=[x[:]for x in R];stale=0
    print('FIT_START',k,products,'span',sp,'F',list(map(len,bp.F)),'full',list(map(len,bp.full)),flush=True)
    for it in range(100000):
        if sp==d and rank_pairs(ps,rng)==d:
            cs=cuts(R);F=solve_padding(physical_cuts(PARTS,cs,Binv=rows),target[76])
            if F is not None:return {'k':k,'parts':PARTS,'cuts':cs,'rows':rows,'padding_F':F,'products':products}
        if time.time()-start>seconds:break
        b=rng.randrange(5);Rn=[x[:]for x in R];Ri=Rn[b]
        y=rng.getrandbits(len(Ri))or 1;p=(y&-y).bit_length()-1
        Rn[b]=[Ri[i]^(Ri[p] if y>>i&1 else 0)for i in range(len(Ri))if i!=p]
        bb=basis(bp.F[b]+Rn[b])
        for _ in range(20):
            v=0
            for x in bp.Q[b]:
                if rng.getrandbits(1):v^=x
            if reduce(v,bb):break
        else:continue
        Rn[b].append(v);sn,pn=evaluate(Rn)
        if sn>=sp or stale>200 and rng.random()<math.exp((sn-sp)/1.5):R,sp,ps=Rn,sn,pn
        stale+=1
        if sp>bestsp:
            bestsp=sp;bestR=[x[:]for x in R];stale=0
            print('FIT_BEST',k,it,sp,'/',d,'seconds',time.time()-start,flush=True)
            (out/f'k{k}_best.json').write_text(json.dumps({'k':k,'parts':PARTS,'cuts':cuts(R),'rows':rows,
                                  'span':sp,'dimension':d},indent=1)+'\n')
        if stale>700:R=[x[:]for x in bestR];sp,ps=evaluate(R);stale=150
    return None


def compile_plan(W,s,out,source):
    pairs,cert=matching(s);B=inverse15(s['rows']);k=s['k']
    plan={'k':k,'explicit_products':[{'l1':int(to_physical(p[2],B)),
           'l2':int(to_physical(p[3],B)),'out':int(p[4])}for p in pairs],
          'explicit_certificate':dict(cert,method='own pair-plane low-basis search and projection-kernel cut constraints',
             low_basis_dual_rows=s['rows'],search_source=source),
          'padding_completion':{'version':1,'first_unused_address':1220,'word_width':75,
             'words':padded_words(W,k,s['padding_F'])[1220:].astype(int).tolist(),
             'real_word_prefix_sha256':hashlib.sha256(np.ascontiguousarray(W.astype(np.uint8)).tobytes()).hexdigest()}}
    f=out/f'angle_k_{k}.kmx';report=emit(plan,complete_words(W.astype(np.uint8)),f)
    proofs=[prove_one(f,W,k,rev)for rev in(False,True)]
    (out/f'angle_k_{k}.plan_state.json').write_text(json.dumps(plan,indent=1)+'\n')
    (out/f'angle_k_{k}.proofs.json').write_text(json.dumps(proofs,indent=1)+'\n')
    (out/f'angle_k_{k}.summary.json').write_text(json.dumps(report,indent=1)+'\n')
    print('COMPILED_PROVED',k,json.dumps(report),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--k',type=int,required=True)
    ap.add_argument('--seed',type=int,default=445);ap.add_argument('--planes',type=int,default=3)
    ap.add_argument('--products',type=int,default=215);ap.add_argument('--seconds',type=int,default=240)
    ap.add_argument('--basis-file',type=Path);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True);rng=random.Random(args.seed)
    W=np.load(ROOT/'agents/loaders48/reordered_uncoded15.npz')['words'].astype(np.int64)
    target=cross_tensor(complete_words(W.astype(np.uint8)),args.k)
    found=json.loads(args.basis_file.read_text()) if args.basis_file else generate(slices(target),rng,seconds=90,planes=args.planes)
    if found is None:raise SystemExit(2)
    (args.out/f'k{args.k}_basis.json').write_text(json.dumps(found,indent=2)+'\n')
    bp,B=setup(target,found['rows'])
    s=fit(target,bp,found['rows'],rng,args.out,args.k,args.seconds,args.products)
    if s is None:raise SystemExit(3)
    (args.out/f'k{args.k}_perfect.json').write_text(json.dumps(s,indent=1)+'\n')
    compile_plan(W,s,args.out,{'seed':args.seed,'planes':args.planes,'basis_file':str(args.basis_file)if args.basis_file else None})
