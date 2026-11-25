#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Own cut swaps chosen to admit a missing two-low-function product.

The target, cut spaces, and all build inputs are our reordered C table. A move
keeps one block's cut dimension fixed, opens a selected output direction, and
retains its projection-kernel cuts. Full matching and endpoint proof are still
required; a span score alone is never a component result.
"""
import argparse
import json
import math
from pathlib import Path
import random
import time
import numpy as np
from compile_reordered_prefix import ROOT, compile_state, rank_pairs, drop
from planner import (BlockPlan, complete_words, cross_tensor, candidates, basis,
                     reduce, proj, nullspace, physical_cuts, solve_padding, NDIM)
from parity_recover import outer
from lowbasis import inverse15, transform_target
from prefix_pairplanes import setup, compile_plan


def rand_comb(vs,rng):
    out=0
    for v in vs:
        if rng.getrandbits(1):out^=v
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=404)
    ap.add_argument('--seconds',type=int,default=240)
    ap.add_argument('--products',type=int)
    ap.add_argument('--words',type=Path,default=ROOT/'agents/loaders48/reordered_uncoded15.npz')
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    s=json.loads(args.state.read_text());k=s['k'];parts=s['parts']
    with np.load(args.words,allow_pickle=False) as z:
        W=z['words' if 'words' in z.files else 'angle_words'].astype(np.int64)
    target=cross_tensor(complete_words(W.astype(np.uint8)),k)
    rows=s.get('rows');rng=random.Random(args.seed)
    bp,_=setup(target,rows) if rows else (BlockPlan(target,parts,[],per_coord=True,hmax=76),None)
    R=[list(c)for c in s['cuts']]
    for i,cs in enumerate(R):
        assert all(reduce(c,basis(bp.full[i]))==0 for c in cs), ('Input cuts are not annihilators',i)
    if args.products:
        need=NDIM-2*args.products
        assert sum(map(len,R)) >= need, '--products can relax a cut space, not add new cuts'
        while sum(map(len,R))>need:
            b=max(range(5),key=lambda j:len(R[j]))
            # Keep every forced vector during a dimension reduction.
            y=rng.getrandbits(len(R[b]))or 1
            trial=drop(R[b],y)
            if any(reduce(f,basis(trial))for f in bp.F[b]):continue
            R[b]=trial
    d=NDIM-sum(map(len,R));assert d%2==0
    if args.products:assert d==2*args.products
    def evaluate(cs):
        pairs,_=candidates({'parts':parts,'cuts':cs},cs)
        sb=basis(x for p in pairs for x in p[:2])
        return len(sb),pairs,sb
    sp,ps,sb=evaluate(R);bestsp=sp;best=[x[:]for x in R]
    start=time.time();stale=0
    part_of={m:i for i,part in enumerate(parts) for m in part}
    print('START',k,sp,d,'dims',list(map(len,R)),'forced',list(map(len,bp.F)),flush=True)
    for it in range(1000000):
        if sp==d and rank_pairs(ps,rng)==d:
            F=solve_padding(physical_cuts(parts,R,Binv=rows)if rows else physical_cuts(parts,R),target[76])
            if F is not None:
                state={'k':k,'parts':parts,'cuts':R,'padding_F':F,'products':d//2,
                       'search':{'method':'own output-directed cut swaps','seed':args.seed,'iteration':it}}
                if rows:state['rows']=rows
                (args.out/f'k{k}_perfect.json').write_text(json.dumps(state,indent=1)+'\n')
                if rows:compile_plan(W,state,args.out,{'seed':args.seed,'source_state':str(args.state)})
                else:compile_state(W,state,args.out)
                return
        if time.time()-start>args.seconds:break
        local_spans=[0]*5
        for pivot in sb:local_spans[part_of[pivot//35]]+=1
        deficient=[j for j in range(5) if local_spans[j]<105-len(R[j])]
        focus=bool(deficient) and rng.random()<0.8
        b2=rng.choice(deficient) if focus else rng.randrange(5)
        b=rng.randrange(4);b+=b>=b2
        l=rng.randrange(1,8);l2=rng.randrange(1,8)
        low1=sum(1<<parts[b][j]for j in range(3)if l>>j&1)
        low2=sum(1<<parts[b2][j]for j in range(3)if l2>>j&1)
        outspace=nullspace([proj(c,l2)for c in R[b2]]+[proj(f,l)for f in bp.F[b]],35)
        if not outspace:continue
        for _ in range(8):
            v=rand_comb(outspace,rng)
            if v and (reduce(outer(low2,v),sb) if focus else
                      (reduce(outer(low1,v),sb) or reduce(outer(low2,v),sb))):break
        else:continue
        y=sum((((proj(c,l)&v).bit_count()&1)<<i)for i,c in enumerate(R[b]))
        if not y:continue
        trial=drop(R[b],y);tb=basis(trial)
        full=bp.full[b]
        pivot=next((q for q in full if (proj(q,l)&v).bit_count()&1),None)
        for _ in range(8):
            q=rand_comb(full,rng)
            if (proj(q,l)&v).bit_count()&1:
                if pivot is None:continue
                q^=pivot
            if reduce(q,tb):break
        else:continue
        trial.append(q);Rn=[c[:]for c in R];Rn[b]=trial
        sn,pn,bn=evaluate(Rn)
        if sn>=sp or stale>300 and rng.random()<math.exp((sn-sp)/0.8):R,sp,ps,sb=Rn,sn,pn,bn
        stale+=1
        if sp>bestsp:
            bestsp=sp;best=[c[:]for c in R];stale=0
            state={'k':k,'parts':parts,'cuts':best,'span':sp,'dimension':d,'iteration':it}
            if rows:state['rows']=rows
            (args.out/f'k{k}_best.json').write_text(json.dumps(state,indent=1)+'\n')
            print('BEST',k,it,sp,d,'seconds',time.time()-start,flush=True)
        if stale>1400:R=[c[:]for c in best];sp,ps,sb=evaluate(R);stale=150
    print('EXHAUSTED',k,bestsp,d,'seconds',time.time()-start,flush=True)
    raise SystemExit(2)


if __name__=='__main__':main()
