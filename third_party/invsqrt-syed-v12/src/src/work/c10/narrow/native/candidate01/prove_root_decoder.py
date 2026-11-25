#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Native five-root decoder proof with all128 charts and all HMR outcomes."""
from common import *
import time
import numpy as np
from root_decode import decode_root
from branch_prover import Program,generated_text
from fourier_resource_expectation import exact_expectation
from stage94_normalization_proof import execute,ZERO,ONE


def r_frame(b,v,inverse=False):
    operations=[('cx',v[7],v[8]),('cx',v[7],v[10]),('ccx',v[6],v[10],v[8]),('cx',v[7],v[10])]
    if inverse:operations.reverse()
    for kind,*args in operations:getattr(b,kind)(*args)


def build():
    b=km.CircuitBuilder();b.set_max_qubits(49)
    v=list(b.alloc_qubits(12));A=list(b.alloc_qubits(13));H=list(b.alloc_qubits(5))
    original=list(v);r_frame(b,v);outcomes={}
    for i in (0,1,2,4,6):
        m=b.alloc_bits(1)[0];b.hmr(v[5+i],m);b.free(v[5+i]);outcomes[i]=m;v[5+i]=None
    v=decode_root(b,v,A,H,outcomes);r_frame(b,v,inverse=True)
    assert b.num_allocated_qubits==30
    return with_registers(b.finish_circuit(),dict(v=original,A=A,H=H)),original,v,A,H


def bits(values,n):return ((values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)
def read(sim,w):return (sim.read_across_shots(array(w)).astype(np.uint64)<<np.arange(len(w),dtype=np.uint64)[:,None]).sum(axis=0)


def main():
    started=time.monotonic();verify_gate_sources();c,original,v,A,H=build();text=generated_text(c);p=Program(text)
    stats=[]
    for address in range(128):
        expected=[frozenset((1<<i,))for i in range(5)]+[ONE if address>>i&1 else ZERO for i in range(7)]
        initial=dict(zip(map(str,original),expected))
        for wires,value in ((A,MODEL['A'][address]),(H,MODEL['stored_slope'][address])):
            initial.update({str(q):ONE if value>>i&1 else ZERO for i,q in enumerate(wires)})
        result,details=execute(p,initial,{'end':len(p.operations)});state,phase=result['end']
        assert phase==ZERO,('all_outcome_phase',address)
        assert all(state[str(q)]==wanted for q,wanted in zip(v,expected)),('restored_root',address)
        for q in A+H:assert state[str(q)]==initial[str(q)],('chart_preserved',address,str(q))
        keep=set(map(str,v+A+H))
        for q in p.quantum_wires:
            if q not in keep:assert state[q]==ZERO,('scratch',address,q)
        stats.append(details)
    counts=exact_expectation(text);assert counts['mean_numeric']['toffoli_like']==23
    simulations=[]
    for seed in (0,1,2,3):
        sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed)
        for first in range(0,4096,256):
            values=np.arange(first,first+256,dtype=np.uint64);address=values>>5
            aa=np.asarray(MODEL['A'],dtype=np.uint64)[address];hh=np.asarray(MODEL['stored_slope'],dtype=np.uint64)[address]
            sim.clear_for_shot();sim.write_across_shots(array(original),bits(values,12));sim.write_across_shots(array(A),bits(aa,13));sim.write_across_shots(array(H),bits(hh,5));sim.do(c)
            assert np.array_equal(read(sim,v),values) and np.array_equal(read(sim,A),aa) and np.array_equal(read(sim,H),hh)
            assert all(sim.read_shot_phase(i)%2==0 for i in range(256))
            spare=[km.q(i)for i in range(c.num_qubits)if km.q(i)not in set(v+A+H)]
            if spare:assert not sim.read_across_shots(array(spare)).any()
        simulations.append(dict(seed=seed,all_root_values=4096,status='PASS',native_measured_Toffolis=sim.operation_statistics().num_toffoli_like/4096))
    out=HERE/'root_decoder_roundtrip.kmb';c.to_file(str(out),format='kmb')
    report=dict(status='PASS_EXACT_NATIVE_COMPONENT_NOT_OFFICIAL',native_Q=c.num_qubits,
                decoder_Toffolis=21,frame_and_unframe_Toffolis=2,exact_native_expectation=counts,
                symbolic_chart_cases=128,arbitrary_low_root_bits=5,all_HMR_outcomes_proved=True,
                exact_phase_zero=True,scratch_zero=True,root_and_chart_restored=True,
                maximum_data_monomials=max(x['maximum_data_monomials']for x in stats),
                maximum_phase_monomials=max(x['maximum_phase_monomials']for x in stats),
                simulator=simulations,kmb_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),seconds=time.monotonic()-started)
    (HERE/'root_decoder_native_proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
