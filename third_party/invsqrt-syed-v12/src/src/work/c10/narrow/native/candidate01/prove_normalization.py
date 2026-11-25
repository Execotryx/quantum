#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Native pair-normalizer emission, symbolic proof and seeded simulator checks."""
from common import *
import importlib.util,time
import numpy as np
from branch_prover import Program,generated_text
from fourier_resource_expectation import exact_expectation
from stage94_normalization_proof import execute,leading_support,ZERO,ONE

PATH=NARROW/'research/quantized_producer/pair_normalization.py'
assert hashlib.sha256(PATH.read_bytes()).hexdigest()=='6af7fc14bc3c904efe480e2e23aee2fcbd97ad23f0a7ba324d8c05e1c8ec17fe'
spec=importlib.util.spec_from_file_location('native_pair_normalization_source',PATH)
normalization=importlib.util.module_from_spec(spec);sys.modules[spec.name]=normalization;spec.loader.exec_module(normalization)


def build(roundtrip):
    b=km.CircuitBuilder();b.set_max_qubits(49);x=list(b.create_quantum_register(22,'x'));flags=list(b.create_quantum_register(4,'flags'))
    normalization.forward(b,x,flags)
    if roundtrip:normalization.inverse(b,x,flags)
    c=b.finish_circuit();return c,x,flags


def native_symbolic(c,roundtrip):
    text=generated_text(c);p=Program(text);rows=[]
    for leading in range(22):
        inputs,nvars=leading_support(leading);initial=dict(zip(p.registers['x'],inputs))
        states,stats=execute(p,initial,{'end':len(p.operations)})
        state,phase=states['end'];assert phase==ZERO,('native_phase',roundtrip,leading)
        k=(21-leading)//2
        expected=inputs if roundtrip else [ZERO]*(2*k)+inputs[:22-2*k]
        for q,wanted in zip(p.registers['x'],expected):assert state[q]==wanted,('native_data',roundtrip,leading,q)
        for bit,q in enumerate(p.registers['flags']):assert state[q]==(ZERO if roundtrip or not(k>>bit&1) else ONE),('native_flags',leading,q)
        keep=set(p.registers['x']+p.registers['flags'])
        for q in p.quantum_wires:
            if q not in keep:assert state[q]==ZERO,('native_scratch',roundtrip,leading,q)
        rows.append(dict(leading=leading,independent_input_variables=nvars,**stats))
    return dict(status='PASS_EXACT_NATIVE_TEXT_ALL_INPUTS_ALL_HMR_OUTCOMES',support_classes=22,
        measurements=p.measurements,domain='Everypositive x<3*2^20, a strictsuperset of officialdomain',
        expected_resources=exact_expectation(text),rows=rows)


def bits(values,n):return ((values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)
def read(sim,wires):return (sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def simulator(c,x,flags):
    checks=[];count=32768
    for seed in (0,1,2,3):
        sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed);rng=np.random.default_rng(77100+seed)
        for first in range(0,count,256):
            xs=rng.integers(1,normalization.MAX_X+1,256,dtype=np.uint64)
            if first==0:xs[:44]=[v for i in range(22)for v in (1<<i,min(normalization.MAX_X,(1<<i)+1))]
            sim.clear_for_shot();sim.write_across_shots(array(x),bits(xs,22));sim.do(c)
            assert np.array_equal(read(sim,x),xs)
            assert not sim.read_across_shots(array(flags)).any()
            outside=[km.q(i)for i in range(c.num_qubits)if km.q(i)not in x]
            assert not sim.read_across_shots(array(outside)).any()
            assert all(sim.read_shot_phase(i)%2==0 for i in range(256))
        s=sim.operation_statistics();checks.append(dict(seed=seed,shots=count,status='PASS',sampled_mean_Toffolis=s.num_toffoli_like/count))
    return checks


def main():
    verify_gate_sources();started=time.monotonic();c,x,flags=build(False);c.to_file(str(HERE/'normalization_forward.kmb'),format='kmb')
    f=native_symbolic(c,False);rt,xx,ff=build(True);rt.to_file(str(HERE/'normalization_roundtrip.kmb'),format='kmb');inv=native_symbolic(rt,True)
    assert c.num_qubits==rt.num_qubits==46
    assert f['expected_resources']['mean_numeric']==dict(toffoli_like=53.0,T=0.0,generic_rotations=0.0)
    assert inv['expected_resources']['mean_numeric']==dict(toffoli_like=97.5,T=0.0,generic_rotations=0.0)
    checks=simulator(rt,xx,ff)
    result=dict(status='PASS_NATIVE_COMPONENT_NOT_OFFICIAL',component='direct pair normalization',Q=c.num_qubits,
        forward_symbolic=f,roundtrip_symbolic=inv,simulator=checks,seconds=time.monotonic()-started,
        source_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),
        roundtrip_kmb_sha256=hashlib.sha256((HERE/'normalization_roundtrip.kmb').read_bytes()).hexdigest())
    (HERE/'normalization_native_proof.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('forward_symbolic','roundtrip_symbolic')},indent=2))

if __name__=='__main__':main()
