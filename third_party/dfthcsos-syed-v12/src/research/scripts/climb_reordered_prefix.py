#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Bounded fixed-cut search for complete early-loader matchings.

This operates on new reordered words, not the closed late147-cut repair route.
Only exact GF2 span and a constructive matching can qualify a component.
"""
import argparse
import json
import math
from pathlib import Path
import random
import time
import numpy as np
from compile_reordered_prefix import ROOT, compile_state, rank_pairs
from planner import (BlockPlan, complete_words, cross_tensor, candidates,
                     basis, reduce, physical_cuts, solve_padding, NDIM)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--k',type=int,required=True)
    ap.add_argument('--seed',type=int,default=919)
    ap.add_argument('--seconds',type=int,default=240)
    ap.add_argument('--state',type=Path)
    ap.add_argument('--out',type=Path,default=ROOT/'work/reordered_prefix_climb')
    args=ap.parse_args()
    src=args.state or ROOT/f'work/reordered_prefix_balanced/k{args.k}_seed74_latest.json'
    s=json.loads(src.read_text());parts=s['parts']
    W=np.load(ROOT/'agents/loaders48/reordered_uncoded15.npz')['words'].astype(np.int64)
    target=cross_tensor(complete_words(W.astype(np.uint8)),args.k)
    bp=BlockPlan(target,parts,[],per_coord=True,hmax=76)
    assert all(len(x)==0 for x in bp.F)
    R=[list(c) for c in s['cuts']]
    d=NDIM-sum(map(len,R));assert d%2==0
    args.out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(args.seed);start=time.time()
    def evaluate(cs):
        ps,_=candidates({'parts':parts,'cuts':cs},cs)
        return len(basis(x for p in ps for x in p[:2])),ps
    sp,ps=evaluate(R);bestsp=sp;best=[c[:]for c in R];stale=0
    print('INITIAL',args.k,'span',sp,'dimension',d,flush=True)
    for iteration in range(50000):
        if sp==d:
            rk=rank_pairs(ps,rng)
            if rk==d:
                F=solve_padding(physical_cuts(parts,R),target[76])
                if F is not None:
                    state={'k':args.k,'parts':parts,'cuts':R,'padding_F':F,
                           'search':{'method':'own balanced sparse descent plus fixed-cut swaps',
                                     'seed':args.seed,'iteration':iteration,'span':sp,'rank':rk}}
                    (args.out/f'k{args.k}_complete.json').write_text(json.dumps(state,indent=1)+'\n')
                    compile_state(W,state,args.out)
                    return
        if time.time()-start>args.seconds:
            break
        b=rng.randrange(5);Rn=[c[:]for c in R];Ri=Rn[b]
        y=rng.getrandbits(len(Ri)) or 1;p=(y&-y).bit_length()-1
        Rn[b]=[Ri[i]^(Ri[p] if y>>i&1 else 0)for i in range(len(Ri))if i!=p]
        bb=basis(Rn[b])
        for _ in range(20):
            q=0
            for v in bp.Q[b]:
                if rng.getrandbits(1):q^=v
            if q and reduce(q,bb):break
        else:continue
        Rn[b].append(q);ns,npairs=evaluate(Rn)
        if ns>=sp or stale>200 and rng.random()<math.exp((ns-sp)/1.3):
            R,sp,ps=Rn,ns,npairs
        stale+=1
        if sp>bestsp:
            bestsp=sp;best=[c[:]for c in R];stale=0
            print('BEST',args.k,iteration,sp,'/',d,'seconds',time.time()-start,flush=True)
            (args.out/f'k{args.k}_best.json').write_text(json.dumps({'k':args.k,'parts':parts,'cuts':best,
                                     'span':bestsp,'dimension':d,'iteration':iteration},indent=1)+'\n')
        if stale>700:
            R=[c[:]for c in best];sp,ps=evaluate(R);stale=150
    raise SystemExit(2)


if __name__=='__main__':main()
