#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Bounded native and all-transcript text proofs of the complete own circuit.

Native sampled diagnostics are explicitly labelled. An exhaustive text mode
covers every supplied original input and every possible HMR transcript, while
all four unchanged official64-shot runs remain a separate qualification gate.
"""
from common import *
import argparse,resource,time
from fractions import Fraction
import numpy as np
from branch_prover import Program,generated_text
from whole_model import phase_units,MAX_X


def atomic(path,value):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,default=str)+'\n');temporary.replace(path)


def bits(values,n):return((values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)
def read(sim,w):return(sim.read_across_shots(array(w)).astype(np.uint64)<<np.arange(len(w),dtype=np.uint64)[:,None]).sum(axis=0)


def native_sample(circuit,count,seeds):
    assert count>=1024 and count%256==0
    original=list(circuit.register_data['x']);scratch=[km.q(i)for i in range(circuit.num_qubits)if km.q(i)not in original]
    boundaries=sorted(set([1,MAX_X]+[min(MAX_X,v)for i in range(22)for v in((1<<i)-1,1<<i,(1<<i)+1)if v>0]))
    records=[]
    for seed in seeds:
        began=time.monotonic();sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed)
        rng=np.random.default_rng(171711+seed)
        for first in range(0,count,256):
            xs=rng.integers(1,MAX_X+1,256,dtype=np.uint64)
            if first==0:xs[:len(boundaries)]=boundaries
            wanted=phase_units(xs)
            sim.clear_for_shot();sim.write_across_shots(array(original),bits(xs,22));sim.do(circuit)
            observed=read(sim,original)
            assert np.array_equal(observed,xs),('native_input_restoration',seed,first,int(xs[np.flatnonzero(observed!=xs)[0]]))
            assert not sim.read_across_shots(array(scratch)).any(),('native_scratch',seed,first)
            for i,target in enumerate(wanted):
                actual=sim.read_shot_phase(i);expected=Fraction(2*int(target),1<<37)
                assert(actual-expected)%2==0,('native_exact_phase',seed,int(xs[i]),str(actual),str(expected))
        statistics=sim.operation_statistics()
        record=dict(seed=seed,shots=count,status='PASS_SAMPLED_NATIVE_EXACT_PHASE_INPUT_AND_SCRATCH',
                    sampled_mean_Toffolis=statistics.num_toffoli_like/count,seconds=time.monotonic()-began)
        records.append(record);print(json.dumps(record),flush=True)
    return dict(status='PASS_NATIVE_SAMPLED_COMPLETE_CIRCUIT_NOT_OFFICIAL',checks=records,
                original_input_register_restored=True,scratch_zero=True,phase_exactly_matches_frozen_integer_model=True)


def exhaustive_text(circuit,first,last,chunk_size,out):
    from whole_text_symbolic import prove_native_chunk
    assert 1<=first<last<=MAX_X+1 and 1<=chunk_size<=65536
    text=generated_text(circuit);program=Program(text);assert program.modulus==1<<37
    rows=[];began=time.monotonic()
    for start in range(first,last,chunk_size):
        xs=np.arange(start,min(last,start+chunk_size),dtype=np.uint64)
        receipt=prove_native_chunk(program,xs,phase_units(xs));rows.append(dict(first=start,stop=int(xs[-1])+1,**receipt))
        status=dict(status='PARTIAL_EXACT_NATIVE_TEXT',requested_interval=[first,last],proved_inputs=sum(r['inputs']for r in rows),
                    chunks=rows,seconds=time.monotonic()-began)
        atomic(out.with_suffix('.partial.json'),status)
        print(json.dumps(dict(progress='exact_native_text',first=start,stop=int(xs[-1])+1,proved_inputs=status['proved_inputs'],seconds=status['seconds'])),flush=True)
    return dict(status='PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS',
                input_interval=[first,last],input_interval_end_exclusive=True,proved_inputs=last-first,
                whole_official_domain=(first==1 and last==MAX_X+1),
                original_input_register_restored=True,scratch_zero=True,all_resets_provably_zero=True,
                every_HMR_transcript_proved=True,phase_exactly_matches_frozen_integer_model=True,
                native_operations=len(program.operations),independent_HMR_variables=program.measurements,
                native_text_sha256=hashlib.sha256(text.encode()).hexdigest(),chunks=rows,seconds=time.monotonic()-began)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--circuit',type=Path,default=HERE/'candidate01.kmb')
    ap.add_argument('--mode',choices=('sample','text'),required=True);ap.add_argument('--shots',type=int,default=8192)
    ap.add_argument('--seeds',default='0,1,2,3');ap.add_argument('--first',type=int,default=1)
    ap.add_argument('--last',type=int,default=MAX_X+1);ap.add_argument('--chunk',type=int,default=65536)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    verify_gate_sources();began=time.monotonic();raw=args.circuit.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    circuit=km.Circuit.from_file(str(args.circuit));assert circuit.num_qubits==49
    assert list(circuit.register_data)==['x'] and len(circuit.register_data['x'])==22
    result=native_sample(circuit,args.shots,list(map(int,args.seeds.split(','))))if args.mode=='sample'else exhaustive_text(circuit,args.first,args.last,args.chunk,args.output)
    result.update(circuit_sha256=digest,Q=circuit.num_qubits,model_sha256=MODEL_SHA,
                  unchanged_original_tolerance=True,official_verifier=False,no_submission=True,
                  elapsed_seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    atomic(args.output,result);print(json.dumps({k:v for k,v in result.items()if k!='chunks'},indent=2),flush=True)


if __name__=='__main__':main()
