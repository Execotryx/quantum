"""Reduced-shot diagnostics for an unmodified official DQI circuit contract.

No confidence bound or competition score is reported. The official verifier
remains authoritative for final acceptance. All-weights mode deliberately
covers every weight instead of drawing the official nonuniform distribution.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'lab/official/kickmix'),str(ROOT/'lab/official/dqi')]
import numpy as np
import kickmix as km
import verify_submission_dqi as v

def all_weights(spec,tables,rng,n,*,zero_sigma1=False):
    weights=np.arange(n)%(spec.max_errors+1)
    mbuc=rng.integers(0,spec.q,size=(n,spec.m),dtype=np.int64)
    syndromes=np.zeros((n,spec.n),dtype=np.int64)
    phases=np.zeros(n,dtype=bool)
    rows=np.arange(1,spec.n+1,dtype=np.int64)[:,None]
    for shot,k in enumerate(weights):
        k=int(k)
        if not k:continue
        if zero_sigma1 and k>=3:
            while True:
                pos=rng.choice(spec.m,size=k-1,replace=False)
                final=int(np.bitwise_xor.reduce(tables.antilog[pos]))
                if final and int(tables.log[final]) not in pos:
                    pos=np.r_[pos,int(tables.log[final])]
                    break
        else:pos=rng.choice(spec.m,size=k,replace=False)
        vals=rng.integers(1,spec.q,size=k,dtype=np.int64)
        exps=(tables.log[vals][None,:]+rows*pos[None,:])%tables.order
        syndromes[shot]=np.bitwise_xor.reduce(tables.antilog[exps],axis=1)
        phases[shot]=sum(int(x).bit_count() for x in vals&mbuc[shot,pos])&1==1
    return (syndromes,mbuc,phases),weights

def max_gap_shots(spec,tables,rng,n):
    """Legal weight-35 errors with locator 1+x^35 and a maximal half-degree drop."""
    assert spec.m==4095 and spec.n==70 and spec.degree==12
    pos=np.arange(35,dtype=np.int64)*(tables.order//35)
    values=rng.integers(1,spec.q,size=(n,35),dtype=np.int64)
    mbuc=rng.integers(0,spec.q,size=(n,spec.m),dtype=np.int64)
    rows=np.arange(1,spec.n+1,dtype=np.int64)[:,None]
    syndromes=np.empty((n,spec.n),dtype=np.int64)
    phases=np.empty(n,dtype=bool)
    for shot,vals in enumerate(values):
        exps=(tables.log[vals][None,:]+rows*pos[None,:])%tables.order
        syndromes[shot]=np.bitwise_xor.reduce(tables.antilog[exps],axis=1)
        phases[shot]=sum(int(x).bit_count() for x in vals&mbuc[shot,pos])&1==1
    return (syndromes,mbuc,phases),np.full(n,35,dtype=np.int64)

def exact_max_gap_shots(spec,tables,n):
    """sigma=1+x^35, Omega=1, M=x; one mask bit at position117.

    e_(117*k)=alpha^(-117*k). The syndromes are exactly S0=S35=1,
    with all others0. e_117=1631 is odd, so the requested phase is -1.
    """
    assert spec.m==4095 and spec.n==70 and spec.degree==12
    assert int(tables.antilog[-117%tables.order])==1631
    syndromes=np.zeros((n,70),dtype=np.int64)
    syndromes[:,0]=1;syndromes[:,35]=1
    mbuc=np.zeros((n,4095),dtype=np.int64);mbuc[:,117]=1
    return (syndromes,mbuc,np.ones(n,dtype=bool)),np.full(n,35,dtype=np.int64)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('circuit',type=Path)
    p.add_argument('--num-shots',type=int,default=256)
    p.add_argument('--batch-size',type=int,default=256)
    p.add_argument('--seed',type=int,default=20261026)
    p.add_argument('--all-weights',action='store_true')
    p.add_argument('--zero-sigma1',action='store_true')
    p.add_argument('--max-gap',action='store_true',
                   help='Use weight35 on positions117*j, whose locator is1+x^35')
    p.add_argument('--exact-max-gap',action='store_true',
                   help='Use S0=S35=1 and only mask117 bit0; expected phase flip is1')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if (a.max_gap or a.exact_max_gap) and (a.all_weights or a.zero_sigma1):
        p.error('Gap fixtures are separate; omit --all-weights and --zero-sigma1')
    if a.max_gap and a.exact_max_gap:
        p.error('Choose --max-gap or --exact-max-gap')
    started=time.monotonic()
    spec=v.ProblemSpecDQI.benchmark_instance(num_shots=a.num_shots)
    c=km.Circuit.from_file(str(a.circuit),format='kmb')
    sq,mb,aq=v.validate_registers(c,spec)
    sq,mb=km.array(sq),km.array(mb)
    rng=np.random.default_rng(a.seed)
    tables=v.FieldTables(km.GF2Field(12))
    if a.exact_max_gap:
        shots,weights=exact_max_gap_shots(spec,tables,a.num_shots)
    elif a.max_gap:
        shots,weights=max_gap_shots(spec,tables,rng,a.num_shots)
    elif a.all_weights:
        shots,weights=all_weights(spec,tables,rng,a.num_shots,zero_sigma1=a.zero_sigma1)
    else:
        assert not a.zero_sigma1,'--zero-sigma1 requires --all-weights'
        shots=v.sample_shots(spec,tables,rng,a.num_shots)
        weights=None
    value_errors=[];phase_errors=[];toffolis=0
    for lo in range(0,a.num_shots,a.batch_size):
        hi=min(a.num_shots,lo+a.batch_size)
        s,m,phase=(x[lo:hi] for x in shots)
        sim=km.Simulator(batch_size=hi-lo,debug_print=False,counting_operations=True,seed=a.seed+lo)
        sim.use_same_registers_as(c)
        before=v.to_bits(s,12)
        sim.write_across_shots(sq,before)
        sim.write_across_shots(mb,v.to_bits(m,12))
        sim.do(c)
        ve=(sim.read_across_shots(sq)^before).any(axis=0)
        if len(aq):ve|=sim.read_across_shots(aq).any(axis=0)
        pe=(sim.read_phase_flipped_across_shots()^phase)&~ve
        value_errors.extend((np.flatnonzero(ve)+lo).tolist())
        phase_errors.extend((np.flatnonzero(pe)+lo).tolist())
        toffolis+=int(sim.operation_statistics().num_toffoli_like)
    out={'scope':'diagnostic only; no confidence bound or official score',
         'distribution':('exact sigma=1+x^35, Omega=1, mask117 bit0' if a.exact_max_gap
                         else 'fixed35-position subgroup, random nonzero error values' if a.max_gap
                         else 'weights 0..35 cyclic' if a.all_weights else 'official DQI weight distribution'),
         'max_gap_locator_1_plus_x35':a.max_gap or a.exact_max_gap,
         'exact_max_gap':a.exact_max_gap,
         'zero_sigma1_for_weights_ge_3':a.zero_sigma1 or a.max_gap or a.exact_max_gap,'num_shots':a.num_shots,
         'num_qubits':c.num_qubits,'value_errors':len(value_errors),'phase_errors':len(phase_errors),
         'value_error_indices':value_errors,'phase_error_indices':phase_errors,
         'toffoli_count_mean':toffolis/a.num_shots,'seconds':time.monotonic()-started}
    if weights is not None:
        out['value_error_weights']=[int(weights[i]) for i in value_errors]
        out['phase_error_weights']=[int(weights[i]) for i in phase_errors]
    text=json.dumps(out,indent=2)+'\n'
    print(text,flush=True)
    if a.output:a.output.write_text(text)

if __name__=='__main__':main()
