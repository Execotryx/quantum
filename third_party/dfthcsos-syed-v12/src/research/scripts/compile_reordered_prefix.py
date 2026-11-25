#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Original bounded sparse-drop planner for the reordered early loaders.

No dense 2**30 arrays: enumerate small projected rowspaces, switch to a bounded
dense counter only below 2**20. Large rowspaces are sampled and rescored exactly.
All plans are proved by the existing independent original compiler and prover.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import numpy as np
from planner import (BlockPlan, complete_words, cross_tensor, basis, reduce, proj,
                     candidates, physical_cuts, solve_padding, padded_words, NDIM, NOUT)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agents/planner189'))
sys.path.insert(0, str(ROOT / 'inputs/chem_goal_v18/refit'))
from packed_rank import rank_pairs
from extract_matching import matching
from emit_plan import emit
from prove_loader_branches import prove_one

PARTS = [[0,4,8],[1,5,9],[2,3,11],[6,7,13],[10,12,14]]


def span_array(vs):
    out = np.zeros(1, dtype=np.uint32)
    for v in vs:
        out = np.concatenate((out, out ^ np.uint32(v)))
    return out


def top_sparse_drops(bp, R, b, count, rng):
    n = len(R[b])
    if n == 0:
        return []
    cuts = [bp.F[i] + R[i] for i in range(5)]
    spaces = []
    for l in range(1,8):
        p = [proj(r,l) for r in R[b]]
        forced = [proj(f,l) for f in bp.F[b]]
        for b2 in range(5):
            if b2 == b:
                continue
            for l2 in range(1,8):
                base = basis(forced + [proj(c,l2) for c in cuts[b2]])
                pb = [reduce(v,base) for v in p]
                rb = basis(sum(1 << i for i,v in enumerate(pb) if v >> j & 1) for j in range(NOUT))
                if rb:
                    spaces.append(rb)
    if n <= 20:
        scores = np.zeros(1 << n, dtype=np.uint16)
        for rb in spaces:
            scores[span_array(rb.values())] += 1
        scores[0] = 0
        pool = np.argpartition(scores, -min(count * 8, len(scores)))[-min(count * 8, len(scores)):]
        pool = list(map(int, pool))
        rng.shuffle(pool)
        pool.sort(key=lambda y: -int(scores[y]))
        return [(int(scores[y]), y) for y in pool[:count] if y]
    counts = Counter()
    for rb in spaces:
        vals = list(rb.values())
        if len(vals) <= 13:
            counts.update(map(int, span_array(vals)[1:]))
        else:
            # Bounded approximate candidate generation; exact membership below.
            for _ in range(256):
                y = 0
                for v in vals:
                    if rng.getrandbits(1):
                        y ^= v
                if y:
                    counts[y] += 1
    shortlist = counts.most_common(max(count * 24, 128))
    rng.shuffle(shortlist)
    exact = [(sum(reduce(y,rb) == 0 for rb in spaces), y) for y,_ in shortlist]
    exact.sort(reverse=True, key=lambda x:x[0])
    return exact[:count]


def drop(row, y):
    p = (y & -y).bit_length()-1
    return [row[i] ^ (row[p] if y >> i & 1 else 0) for i in range(len(row)) if i != p]


def search(W, k, out, seed=73, seconds=600, per_block=4, floor=19, spread=3):
    target = cross_tensor(complete_words(W.astype(np.uint8)), k)
    bp = BlockPlan(target, PARTS, [], per_coord=True, hmax=76)
    rng = random.Random(seed)
    R = [list(x) for x in bp.Q]
    def evaluate(Rs, need_rank=True):
        cuts = [bp.F[i]+Rs[i] for i in range(5)]
        pairs,_ = candidates({'parts':PARTS, 'cuts':cuts},cuts)
        d = NDIM-sum(map(len,cuts))
        sp = len(basis(v for p in pairs for v in p[:2]))
        rk = rank_pairs(pairs,rng) if need_rank else -1
        return d,sp,rk
    t0 = time.time()
    d,sp,rk = evaluate(R)
    rows = []
    while time.time()-t0 < seconds:
        cuts = [bp.F[i]+R[i] for i in range(5)]
        row = {'k':k, 'seed':seed, 'cuts':NDIM-d, 'dimension':d, 'span':sp,
               'rank':rk, 'product_upper_bound':d-rk//2, 'seconds':time.time()-t0,
               'block_cut_dimensions':list(map(len,cuts))}
        rows.append(row)
        print(json.dumps(row),flush=True)
        state = {'k':k, 'parts':PARTS, 'cuts':cuts, 'search':row}
        (out / f'k{k}_seed{seed}_latest.json').write_text(json.dumps(state,indent=1)+'\n')
        (out / f'k{k}_seed{seed}_progress.json').write_text(json.dumps(rows,indent=1)+'\n')
        if rk == d and d % 2 == 0:
            F = solve_padding(physical_cuts(PARTS,cuts),target[76])
            if F is not None:
                state['padding_F']=F
                return state
        pool=[]
        for b in range(5):
            sizes=[len(bp.F[i])+len(R[i]) for i in range(5)]
            if sizes[b] <= floor or sizes[b] <= max(sizes)-spread:
                continue
            pool += [(score,b,y) for score,y in top_sparse_drops(bp,R,b,per_block,rng)]
        trials=[]
        for sc,b,y in pool:
            Rn=[list(x) for x in R]; Rn[b]=drop(R[b],y)
            d2,sp2,_=evaluate(Rn,False)
            trials.append((sp2,sc,b,y,Rn,d2))
        trials.sort(key=lambda x:(x[0],x[1]),reverse=True)
        best=None
        for sp2,sc,b,y,Rn,d2 in trials[:max(5,per_block*2)]:
            _,_,r2=evaluate(Rn)
            score=(r2,sp2,sc)
            if best is None or score>best[0]:
                best=(score,Rn,d2,sp2,r2)
        if best is None:
            break
        _,R,d,sp,rk=best
    return None


def compile_state(W, state, out):
    k=state['k']
    pairs,cert=matching(state)
    state['explicit_products']=[{'l1':int(p[2]),'l2':int(p[3]),'out':int(p[4])}for p in pairs]
    state['explicit_certificate']=dict(cert,method='own sparse projected-rowspace drop search from saturation; original matching',
                                       sum_cuts=sum(map(len,state['cuts'])))
    Wpad=padded_words(W,k,state['padding_F'])
    state['padding_completion']={'version':1,'first_unused_address':1220,'word_width':75,
        'words':Wpad[1220:].astype(int).tolist(),
        'real_word_prefix_sha256':hashlib.sha256(np.ascontiguousarray(W.astype(np.uint8)).tobytes()).hexdigest()}
    source=out/f'angle_k_{k}.kmx'
    report=emit(state,complete_words(W.astype(np.uint8)),source)
    proofs=[prove_one(source,W,k,rev) for rev in (False,True)]
    (out/f'angle_k_{k}.plan_state.json').write_text(json.dumps(state,indent=1)+'\n')
    (out/f'angle_k_{k}.proofs.json').write_text(json.dumps(proofs,indent=1)+'\n')
    (out/f'angle_k_{k}.summary.json').write_text(json.dumps(report,indent=1)+'\n')
    print('COMPILED_PROVED',json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--k',type=int,required=True)
    ap.add_argument('--words',type=Path,default=ROOT/'agents/loaders48/reordered_uncoded15.npz')
    ap.add_argument('--out',type=Path,default=ROOT/'work/reordered_prefix')
    ap.add_argument('--seed',type=int,default=73)
    ap.add_argument('--seconds',type=float,default=600)
    ap.add_argument('--per-block',type=int,default=4)
    ap.add_argument('--floor',type=int,default=19)
    ap.add_argument('--spread',type=int,default=3)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    W=np.load(args.words)['words'].astype(np.int64)
    state=search(W,args.k,args.out,args.seed,args.seconds,args.per_block,args.floor,args.spread)
    if state is None:
        raise SystemExit(2)
    compile_state(W,state,args.out)
