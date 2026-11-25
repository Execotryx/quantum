#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Native value/phase/restoration proof for the complete arithmetic lifecycle.

Run only in the serial guarded native slot. It uses a diagnostic divider
which relocates all fifteen product owners by exact affine HMR and applies
an optional Z parity. Full actual-divider/official proofs belong to parent.
"""
from common import *
import argparse,math,time
import numpy as np
import lifecycle,tables,root_decode
from branch_prover import generated_text
from fourier_resource_expectation import exact_expectation


class ProbeDivider:
    def __init__(self,mask,relocate=True):self.mask=mask;self.relocate=relocate
    def compute_phase_cleanup(self,b,v,P,flags):
        P=list(P)
        for i,old in enumerate(P):
            if self.relocate:
                new=b.alloc_qubits(1)[0];b.cx(old,new)
                m=b.alloc_bits(1)[0];b.hmr(old,m)
                b.push_condition(m);b.z(new);b.pop_condition();b.free(m);b.free(old)
                P[i]=new
            if self.mask>>i&1:b.z(P[i])
        return P


def build(mask,relocate=True):
    b=km.CircuitBuilder();b.set_max_qubits(49)
    v=list(b.alloc_qubits(12));h=list(b.alloc_qubits(10));flags=list(b.alloc_qubits(4))
    original=(v[:],h[:],flags[:]);cuts={};trace=[]
    def hook(label,builder,owners):
        if label in('first_table','first_coefficient','seed_ready','signed_product15','second_coefficient','seed_cleared','A_restored','raw_root_restored'):
            cuts[label]=(builder.finish_circuit(),owners)
    lifecycle.CUT_HOOK=hook
    try:v,h=lifecycle.emit_body(b,v,h,flags,tables,ProbeDivider(mask,relocate),root_decode.decode_root,trace=trace)
    finally:lifecycle.CUT_HOOK=None
    circuit=with_registers(b.finish_circuit(),dict(v=original[0],h=original[1],flags=original[2]))
    return circuit,original,(v,h,flags),cuts,trace


def bits(values,n):
    return((np.asarray(values,dtype=np.uint64)[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)


def read(sim,wires):
    return(sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def values(xs):
    v=np.array([math.isqrt(16*int(n))-4096 for n in xs],dtype=np.uint64)
    d=8193+2*v.astype(np.int64);h=(64*xs.astype(np.int64)-d*d)//64
    D=np.array([MODEL['D'][int(x)]for x in v],dtype=np.int64);C=2*D
    r=(v*(v+1)//2)&7
    seed=-np.ones(len(xs),dtype=np.int64)
    for i in range(3):seed+=(2*((r>>i)&1).astype(np.int64)-1)*((C+(1<<(11-i)))>>(12-i))
    q=(h&1023)^512;F=np.zeros(len(xs),dtype=np.int64)
    for i in range(10):
        shift=8-i;t=((C+(1<<(shift-1)))>>shift)if shift>0 else C if shift==0 else 2*C+1
        F+=(2*((q>>i)&1)-1)*t
    U=seed-F//2
    assert np.all((-16384<=U)&(U<16384))
    return dict(v=v,h=h,D=D,seed=seed,U=U)


def write_inputs(sim,original,wanted,flags):
    sim.clear_for_shot();sim.write_across_shots(array(original[0]),bits(wanted['v'],12))
    sim.write_across_shots(array(original[1]),bits(wanted['h']&1023,10))
    sim.write_across_shots(array(original[2]),bits(flags,4))


def check_final(sim,circuit,current,wanted,flags,mask):
    assert np.array_equal(read(sim,current[0]),wanted['v']),'root restore'
    assert np.array_equal(read(sim,current[1]),wanted['h']&1023),'residual restore'
    assert np.array_equal(read(sim,current[2]),flags),'flags restore'
    keep=set(current[0]+current[1]+current[2]);outside=[km.q(i)for i in range(circuit.num_qubits)if km.q(i)not in keep]
    assert not sim.read_across_shots(array(outside)).any(),'dirty scratch'
    expected=[(int(u)&mask).bit_count()&1 for u in wanted['U']]
    for i,w in enumerate(expected):assert sim.read_shot_phase(i)%2==w,('phase',i,sim.read_shot_phase(i),w)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--shots',type=int,default=8192)
    parser.add_argument('--seeds',default='0,1,2,3');parser.add_argument('--mask',type=lambda s:int(s,0),default=0x5a6d)
    parser.add_argument('--no-relocate',action='store_true')
    parser.add_argument('--output',default='lifecycle_native_proof.json');args=parser.parse_args()
    assert args.shots%256==0;verify_gate_sources();start=time.monotonic()
    c,original,current,cuts,trace=build(args.mask,not args.no_relocate);c.to_file(str(HERE/'lifecycle_probe.kmb'),format='kmb')
    text=generated_text(c);expected_resources=exact_expectation(text)
    assert expected_resources['mean_numeric']==dict(toffoli_like=543.5,T=0.0,generic_rotations=0.0),expected_resources
    prefix,owners=cuts['signed_product15'];prefix.to_file(str(HERE/'lifecycle_product_prefix.kmb'),format='kmb')
    checks=[]
    for seed in map(int,args.seeds.split(',')):
        rng=np.random.default_rng(83000+seed);sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed)
        forward=km.Simulator(batch_size=256,counting_operations=True,seed=seed+101)
        for first in range(0,args.shots,256):
            xs=rng.integers(1<<20,1<<22,256,dtype=np.uint64)
            if first==0:xs[:16]=[v for i in range(8)for v in((1<<20)+i,(1<<22)-1-i)]
            wanted=values(xs);flags=rng.integers(0,11,256,dtype=np.uint64)
            write_inputs(forward,original,wanted,flags);forward.do(prefix)
            assert np.array_equal(read(forward,owners['P']),wanted['U']&32767),'native product value'
            assert np.array_equal(read(forward,owners['D']),wanted['D']),'native coefficient value'
            assert np.array_equal(read(forward,owners['v']),wanted['v']),'prefix root'
            write_inputs(sim,original,wanted,flags);sim.do(c);check_final(sim,c,current,wanted,flags,args.mask)
        stats=sim.operation_statistics()
        checks.append(dict(seed=seed,shots=args.shots,status='PASS',sampled_mean_Toffolis=stats.num_toffoli_like/args.shots))
    result=dict(status='PASS_NATIVE_LIFECYCLE_COMPONENT_NOT_OFFICIAL',mask=args.mask,Q=c.num_qubits,
        exact_resources=expected_resources,checks=checks,cuts=trace,seconds=time.monotonic()-start,
        logical_owner_relocation='Noop divider'if args.no_relocate else'All15 product owners deliberately replaced by exact affine HMR; five roots also retired/recreated by the actual lifecycle.',
        source_sha256=hashlib.sha256((HERE/'lifecycle.py').read_bytes()).hexdigest(),
        kmb_sha256=hashlib.sha256((HERE/'lifecycle_probe.kmb').read_bytes()).hexdigest(),
        unchanged_model_sha256=MODEL_SHA,official_verifier=False)
    (HERE/args.output).write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':main()
