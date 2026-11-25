#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Bounded exact-feature angle fitting; mathematical evidence only."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import hashlib,importlib.util,json,math,resource,sys,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
sys.path.insert(0,str(NARROW/'native/candidate01'))
import numpy as np
from scipy.optimize import linprog
import whole_model
PINS={
 'native/candidate01/whole_model.py':'740b3530990003de29fc3a29726c1ac7f97aa29467fc14fd7608f5c5f58bfca4',
 'base/official/verifier_invsqrt/verify_submission_invsqrt.py':'ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a',
 'research/recompute_root/models/phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json':'24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219',
}
for path,sha in PINS.items():assert hashlib.sha256((NARROW/path).read_bytes()).hexdigest()==sha,path
sp=importlib.util.spec_from_file_location('angle_refit_original_verifier',NARROW/'base/official/verifier_invsqrt/verify_submission_invsqrt.py')
verifier=importlib.util.module_from_spec(sp);sys.modules[sp.name]=verifier;sp.loader.exec_module(verifier)
SPEC=verifier.ProblemSpecInvSqrt.for_n_p(10);N=SPEC.max_x;UNIT=1<<27;CHUNK=32768
COEFF=np.array([(1<<i)+(1<<27 if i==0 else 0)for i in range(27)]+[-(1<<27)]+[1<<(27+j)for j in range(1,7)],dtype=np.int64)
assert len(COEFF)==34


def features(mask):
    return ((mask[:,None]>>np.arange(34,dtype=np.uint64)[None,:])&np.uint64(1)).astype(np.float64)


def generate():
    masks=np.empty(N,dtype=np.uint64);errors=np.empty(N,dtype=np.int64);tols=np.empty(N,dtype=np.int64)
    for first in range(1,N+1,CHUNK):
        stop=min(first+CHUNK,N+1);xs=np.arange(first,stop,dtype=np.int64)
        word,chart=whole_model.phase_units(xs,return_chart=True);k=chart['flags'];z=word&((1<<27)-1)
        packed=z.astype(np.uint64);packed|=(k==0).astype(np.uint64)<<np.uint64(27)
        for j in range(1,7):packed|=(((z>>j)&1)*(k>j)).astype(np.uint64)<<np.uint64(27+j)
        # Independent existing-angle feature identity, including all T/Clifford terms.
        baseline=features(packed).astype(np.int64)@COEFF
        for j in (7,8,9):baseline+=((z>>j)&1)*(k>j)*(1<<(27+j))
        assert np.array_equal(baseline&((1<<37)-1),word)
        target,tol=verifier.reference_values(SPEC,xs.astype(np.uint64))
        signed=((word.astype(np.uint64)<<np.uint64(27))-target).view(np.int64)
        masks[first-1:stop-1]=packed;errors[first-1:stop-1]=signed;tols[first-1:stop-1]=tol.astype(np.int64)
    margin=tols-np.abs(errors);assert int(margin.min())==31966138
    return masks,errors,tols


def screen_float(masks,errors,tols,delta):
    margin=np.empty(N,dtype=np.float64)
    for start in range(0,N,CHUNK):
        stop=min(start+CHUNK,N);pred=features(masks[start:stop])@delta
        margin[start:stop]=tols[start:stop]/UNIT-np.abs(errors[start:stop]/UNIT+pred)
    return margin


def exact_screen(masks,errors,tols,delta_units):
    minimum=(1<<63)-1;worst_x=None;ratio=0;bad=0
    for start in range(0,N,CHUNK):
        stop=min(start+CHUNK,N);F=features(masks[start:stop]).astype(np.int64)
        newerr=errors[start:stop]+F@delta_units
        margin=tols[start:stop]-np.abs(newerr)
        ix=int(margin.argmin());value=int(margin[ix])
        if value<minimum:minimum=value;worst_x=start+ix+1
        ratio=max(ratio,float((np.abs(newerr)/tols[start:stop]).max()))
        bad+=int((margin<0).sum())
    return dict(inputs=N,failures=bad,minimum_margin_units=minimum,minimum_margin_x=worst_x,worst_error_over_tolerance=ratio)


def main():
    start=time.monotonic();masks,errors,tols=generate()
    original_margin=(tols-np.abs(errors)).astype(np.float64)/UNIT
    active=set(np.argpartition(original_margin,256)[:256].tolist())
    active.update(np.linspace(0,N-1,256,dtype=np.int64).tolist())
    rounds=[];best=np.zeros(34);screen=original_margin
    for iteration in range(16):
        ix=np.array(sorted(active),dtype=np.int64);F=features(masks[ix]);ones=np.ones((len(ix),1))
        A=np.concatenate((np.concatenate((F,ones),axis=1),np.concatenate((-F,ones),axis=1)),axis=0)
        b=np.concatenate(((tols[ix]-errors[ix])/UNIT,(tols[ix]+errors[ix])/UNIT))
        objective=np.zeros(35);objective[-1]=-1
        result=linprog(objective,A_ub=A,b_ub=b,bounds=[(-1.0,1.0)]*34+[(0,None)],method='highs',options={'time_limit':20.0,'threads':1})
        assert result.success,(result.status,result.message)
        delta=result.x[:34];screen=screen_float(masks,errors,tols,delta)
        minimum=float(screen.min());gap=float(result.x[-1]-minimum)
        rounds.append(dict(iteration=iteration,active_cases=len(active),LP_margin_units37=float(result.x[-1]),full_margin_units37=minimum,gap=gap))
        print(json.dumps(rounds[-1]),flush=True)
        if minimum>float(screen_float(masks,errors,tols,best).min()):best=delta.copy()
        if gap<=2e-8:break
        bad=np.argpartition(screen,128)[:128]
        before=len(active);active.update(bad.tolist());assert len(active)>before,'No new separating constraints'
    quant=np.rint(best*UNIT).astype(np.int64)
    exact=exact_screen(masks,errors,tols,quant)
    # Every perturbed original generic site must remain generic, using exact dyadic arithmetic.
    new_units=COEFF*UNIT+quant
    assert all(int(u)%(1<<61)!=0 for u in new_units),'A generic angle changed class'
    margin=exact['minimum_margin_units'];eps=math.pi*margin/(1<<64)/34
    rotation=34*verifier.rotation_t_count(eps)/4
    result=dict(status='EXACT_ALL_INPUT_ANGLE_REFIT_PAPER_PASS_NATIVE_PENDING'if margin>31966138 and not exact['failures']else'ANGLE_REFIT_PAPER_CLOSED_NO_GAIN',
        source_pins=PINS,baseline_generic_feature_coefficients_units37=COEFF.tolist(),
        delta_turn_units64=quant.tolist(),new_generic_turn_units64=new_units.tolist(),
        fixed_T=4,fixed_R=34,Q=49,expected_Toffolis=1570.5,rotation_charge=rotation,
        predicted_complete_cost=49*(1571.5+rotation),exact_original_tolerance=exact,
        feature_identity_all_inputs=True,rounds=rounds,continuous_global_optimum_claim=False,
        exact_native_proof_required=True,official_four_salts_required=True,no_native_emission=True,
        seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (HERE/'refit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
