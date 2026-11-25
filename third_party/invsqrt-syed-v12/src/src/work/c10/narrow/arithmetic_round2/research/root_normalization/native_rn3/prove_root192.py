#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Native192 root component, exact all-normalized/all-HMR proof and hybrid."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import argparse,hashlib,importlib.util,json,sys,time
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[3]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


for pin in json.loads((HERE/'SOURCE_READY.json').read_text())['files']:
    path=HERE/pin['path'];assert path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],pin['path']
gate=NARROW/'arithmetic_round2/receipts/ROOT_RN3_PAPER_ACCEPTED.json'
assert sha(gate)=='04a2f62efca37e06c484a8cd3ba5c43ace9cda133ea9a23ae7ec8fa405d03b27'
assert json.loads(gate.read_text())['native_build_authorized'] is True
import root192
sys.path.insert(0,str(NARROW/'native/candidate01'))
from common import km,array,with_registers
from branch_prover import Program,generated_text
from fourier_resource_expectation import exact_expectation
import numpy as np


def atomic(name,value):
    p=HERE/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(value,indent=2,default=str)+'\n');t.replace(p)


def checker_module():
    path=NARROW/'native/candidate01/whole_text_symbolic.py'
    spec=importlib.util.spec_from_file_location('_round2_rn3_native_checker',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    # This component contains only integral half-turn phases; retain the
    # checker's exact original checks with the actual native phase modulus.
    module.CANDIDATE_MODULUS=2
    return module


def build(hybrid=False):
    b=km.CircuitBuilder();b.set_max_qubits(48)
    x=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
    values=root192.forward(b,x)
    forward=with_registers(b.finish_circuit(),{'x':x})
    if hybrid:root192.ORIGINAL_INVERSE(b,x)
    else:root192.inverse(b,x)
    complete=with_registers(b.finish_circuit(),{'x':x})
    assert b.num_allocated_qubits==26
    return forward,complete,x,flags,values


def prove_all(circuit,chunk,label):
    checker=checker_module();program=Program(generated_text(circuit));assert program.modulus==2
    rows=[];began=time.monotonic()
    for first in range(1<<20,1<<22,chunk):
        xs=np.arange(first,min(1<<22,first+chunk),dtype=np.uint64)
        receipt=checker.prove_native_chunk(program,xs,np.zeros(len(xs),dtype=np.uint64))
        rows.append(dict(first=first,stop=int(xs[-1])+1,**receipt))
        atomic(label+'.partial.json',dict(status='PARTIAL_NOT_COMPLETE',inputs=sum(r['inputs']for r in rows),chunks=rows))
        if len(rows)%12==0:print(json.dumps(dict(root_native_progress=label,inputs=sum(r['inputs']for r in rows),seconds=time.monotonic()-began)),flush=True)
    assert sum(r['inputs']for r in rows)==3145728
    return dict(status='PASS_EXACT_NATIVE_TEXT_ALL_NORMALIZED_INPUTS_ALL_HMR_TRANSCRIPTS',
                inputs=3145728,interval=[1<<20,1<<22],end_exclusive=True,phase_modulus=2,
                independent_HMR_variables=program.measurements,all_input_and_scratch_values_correct=True,
                every_HMR_transcript_proved=True,checker_sha256=sha(NARROW/'native/candidate01/whole_text_symbolic.py'),
                chunks=rows,seconds=time.monotonic()-began)


def bits(values,n):return ((values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)
def read(sim,wires):return (sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def forward_native(circuit,x,flags,count=32768):
    records=[];keep=set(x+flags);scratch=[km.q(i)for i in range(circuit.num_qubits)if km.q(i)not in keep]
    program=Program(generated_text(circuit))
    assert not set(map(str,flags))&set(program.quantum_wires),'Exponent spectators must be untouched.'
    vv=np.repeat(np.arange(4096,dtype=np.uint64),2);d=8193+2*vv
    low=((d-1)**2+63)//64;high=np.minimum(np.uint64(1<<22),((d+1)**2+63)//64)-1
    edges=np.where(np.arange(8192)%2,high,low)
    for seed in (0,1,2,3):
        rng=np.random.default_rng(192000+seed);xs=rng.integers(1<<20,1<<22,count,dtype=np.uint64);xs[:8192]=edges
        ss=rng.integers(0,16,count,dtype=np.uint64)
        Q=np.sqrt(xs<<np.uint64(4)).astype(np.uint64)
        assert np.all(Q*Q<=xs<<np.uint64(4)) and np.all((Q+1)*(Q+1)>xs<<np.uint64(4))
        v=Q-4096;h=((xs.astype(np.int64)<<6)-(2*Q.astype(np.int64)+1)**2)//64
        wanted=(v<<np.uint64(10))|(h.astype(np.uint64)&1023)
        sim=km.Simulator(batch_size=256,seed=seed,counting_operations=True)
        for first in range(0,count,256):
            sim.clear_for_shot();sim.write_across_shots(array(x),bits(xs[first:first+256],22))
            sim.write_across_shots(array(flags),bits(ss[first:first+256],4));sim.do(circuit)
            assert np.array_equal(read(sim,x),wanted[first:first+256])
            assert np.array_equal(read(sim,flags),ss[first:first+256])
            assert not sim.read_across_shots(array(scratch)).any()
            assert all(sim.read_shot_phase(i)%2==0 for i in range(256))
        stats=sim.operation_statistics()
        records.append(dict(seed=seed,inputs=count,all_root_edges=8192,
                            status='PASS_NATIVE_FORWARD_VALUE_PHASE_SCRATCH_AND_FLAGS',
                            sampled_mean_Toffolis=stats.num_toffoli_like/count))
    return records


def save_resource(name,circuit,cost,peak):
    binary=HERE/(name+'.kmb');text=HERE/(name+'.kmx')
    assert not binary.exists() and not text.exists()
    circuit.to_file(binary,format='kmb');text.write_text(generated_text(circuit))
    counts=exact_expectation(text.read_text())
    assert counts['mean_numeric']=={'toffoli_like':float(cost),'T':0.0,'generic_rotations':0.0}
    assert circuit.num_qubits==peak
    return dict(native_Q=peak,exact_native_expectation=counts,kmb_sha256=sha(binary),kmx_sha256=sha(text))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--chunk',type=int,default=65536);args=ap.parse_args()
    assert 1<=args.chunk<=65536;began=time.monotonic()
    assert not (HERE/'root192_native_proof.json').exists()
    forward,roundtrip,x,flags,_=build()
    resources={'forward':save_resource('root192_forward',forward,96,39),
               'roundtrip':save_resource('root192_roundtrip',roundtrip,192,39)}
    samples=forward_native(forward,x,flags)
    exact=prove_all(roundtrip,args.chunk,'root192_roundtrip_exact')
    _,hybrid,_,_,_=build(hybrid=True)
    resources['hybrid']=save_resource('root192_new_forward_original_inverse',hybrid,199,42)
    hybrid_exact=prove_all(hybrid,args.chunk,'root192_hybrid_exact')
    result=dict(status='PASS_NATIVE_ROOT192_COMPONENT_NOT_OFFICIAL',resources=resources,
                forward_simulator=samples,exact_roundtrip=exact,exact_equivalence_to_original=hybrid_exact,
                normalized_inputs=3145728,every_HMR_transcript_proved=True,all_scratch_zero=True,
                root_source_sha256=sha(HERE/'root192.py'),proof_source_sha256=sha(Path(__file__)),
                inputs_sha256=sha(HERE/'INPUTS.json'),source_ready_sha256=sha(HERE/'SOURCE_READY.json'),
                paper_acceptance_sha256=sha(gate),source_math_certificate_sha256=sha(HERE.parent/'source_aware_root.json'),
                inherited_sources_and_modules_unchanged=True,complete_fusion_qualification=False,
                official_verifier_run=False,seconds=time.monotonic()-began)
    atomic('root192_native_proof.json',result)
    print(json.dumps({k:v for k,v in result.items()if k not in('exact_roundtrip','exact_equivalence_to_original')},indent=2),flush=True)


if __name__=='__main__':main()
