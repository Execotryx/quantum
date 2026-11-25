#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Exhaust the small quotient of additional cuts near our reordered k4 plan.

The first layer is exhaustive; a bounded beam keeps promising first additions.
Only a full constructive pairing and exact endpoint proof qualify a new plan.
"""
from pathlib import Path
import json,random,time
import numpy as np
from compile_reordered_prefix import ROOT,compile_state,rank_pairs
from planner import BlockPlan,complete_words,cross_tensor,basis,candidates,physical_cuts,solve_padding
from transport_cuts import complete_forced

out=ROOT/'work/reordered_k4_194';out.mkdir(parents=True,exist_ok=True)
W=np.load(ROOT/'agents/loaders48/reordered_uncoded15.npz')['words'].astype(np.int64)
s=json.loads((ROOT/'agents/loaders48/climb_shape_k4/angle_k_4.plan_state.json').read_text())
parts=s['parts'];target=cross_tensor(complete_words(W.astype(np.uint8)),4)
bp=BlockPlan(target,parts,[],True,76);rng=random.Random(44194);start=time.time()
beam=[(390,s['cuts'])]
for step in range(1,3):
    options=[];d=390-step
    for oldsp,cuts in beam:
        for b in range(5):
            ext=complete_forced(bp.full[b],cuts[b]);vs=[0]
            assert len(ext)<=5
            for x in ext:vs += [v^x for v in vs]
            for v in vs[1:]:
                cs=[c[:]for c in cuts];cs[b].append(v)
                ps,_=candidates({'parts':parts,'cuts':cs},cs)
                sp=len(basis(x for p in ps for x in p[:2]));options.append((sp,cs))
                if step==2 and sp==d and rank_pairs(ps,rng)==d:
                    F=solve_padding(physical_cuts(parts,cs),target[76])
                    if F is not None:
                        state={'k':4,'parts':parts,'cuts':cs,'padding_F':F,
                               'search':{'method':'own exhaustive quotient additions with bounded first-layer beam','seed':44194}}
                        (out/'k4_perfect.json').write_text(json.dumps(state,indent=1)+'\n')
                        compile_state(W,state,out);raise SystemExit(0)
    options.sort(key=lambda x:-x[0]);beam=options[:8]
    state={'k':4,'parts':parts,'cuts':beam[0][1],'span':beam[0][0],'dimension':d,'step':step}
    (out/'k4_best.json').write_text(json.dumps(state,indent=1)+'\n')
    print('STEP',step,'count',len(options),'best_span',beam[0][0],'dimension',d,'seconds',time.time()-start,flush=True)
raise SystemExit(2)
