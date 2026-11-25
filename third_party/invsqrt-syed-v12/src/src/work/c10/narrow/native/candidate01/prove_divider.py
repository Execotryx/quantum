#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Guarded native proofs for the direct u12 and consuming endpoint divider.

Run only after obtaining the team's serial native execution slot. Exact native
text is checked independently for u12 on every abstract case and every HMR
outcome; seeded native simulation checks the full divider's integer phase.
"""
from common import *
import argparse,time
from fractions import Fraction
import numpy as np
from branch_prover import Program,generated_text
from fourier_resource_expectation import exact_expectation
import divider


def atomic(name,value):
    p=HERE/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(value,indent=2,default=str)+'\n');t.replace(p)


def build(initializer=False,phase=True):
    b=km.CircuitBuilder();b.set_max_qubits(49)
    v=list(b.alloc_qubits(12))
    P=list(b.alloc_qubits(15))
    flags=list(b.alloc_qubits(4))
    if initializer:
        u=list(b.alloc_qubits(14));current=divider.initialize_u12(b,v,P,u)
        current=divider.cleanup_u12(b,v,current,u)
    else:
        token=divider.compute_divider(b,v,P,flags)
        if phase:divider.phase_endpoint(b,token)
        current=divider.cleanup_divider(b,token)
    c=with_registers(b.finish_circuit(),{'v':v,'P':P,'flags':flags})
    return c,v,P,flags,current


def exact_initializer(c,v,P,flags,current,forward_u=None):
    """Every abstract root/top-product input and every native HMR outcome."""
    p=Program(generated_text(c));cases=32768;full=(1<<cases)-1
    vals=np.arange(cases,dtype=np.uint64)
    def pack(a):return int.from_bytes(np.packbits(np.asarray(a,dtype=np.uint8),bitorder='little').tobytes(),'little')
    state={wire:0 for wire in p.wires};classical={};phase={};stack=[{0:full}]
    state.update({'0':0,'False':0,'1':full,'True':full})
    for i,q in enumerate(v):state[str(q)]=pack(((vals>>3)>>i)&1)
    for i,q in enumerate(P):state[str(q)]=pack((vals>>(i-12))&1)if i>=12 else state[str(v[i])]
    for i,q in enumerate(flags):state[str(q)]=state[str(v[i])]
    inputs=dict(state)
    def add(a,b):
        out=dict(a)
        for k,x in b.items():
            out[k]=out.get(k,0)^x
            if not out[k]:out.pop(k)
        return out
    def mul(a,b):
        out={}
        for ka,va in a.items():
            for kb,vb in b.items():
                key=ka|kb;out[key]=out.get(key,0)^(va&vb)
        return {k:x for k,x in out.items()if x}
    def value(q):return classical.get(q,{0:state.get(q,0)}if state.get(q,0)else{})
    for index,op in enumerate(p.operations):
        kind,args=op.kind,op.arguments;active=stack[-1]
        if op.condition is not None:active=mul(active,value(op.condition))
        if kind=='PUSH_CONDITION':stack.append(active);continue
        if kind=='POP_CONDITION':stack.pop();continue
        if not active:continue
        if kind in ('Z','CZ','CCZ','NEG','Z_POW'):
            if kind=='Z_POW':
                assert op.half_turns.denominator==1
                if not int(op.half_turns)%2:continue
            term=active
            for q in args:term=mul(term,value(q))
            phase=add(phase,term);continue
        if kind in ('BIT_STORE0','BIT_STORE1','BIT_INVERT'):
            old=value(args[0]);new={}if kind=='BIT_STORE0'else{0:full}
            classical[args[0]]=add(old,active)if kind=='BIT_INVERT'else add(old,mul(active,add(old,new)))
            continue
        assert active=={0:full},('unexpected measurement-controlled data',index,kind)
        if kind=='X':state[args[0]]^=full
        elif kind=='CX':state[args[1]]^=state[args[0]]
        elif kind=='CCX':state[args[2]]^=state[args[0]]&state[args[1]]
        elif kind=='SWAP':state[args[0]],state[args[1]]=state[args[1]],state[args[0]]
        elif kind=='CSWAP':
            diff=state[args[0]]&(state[args[1]]^state[args[2]])
            state[args[1]]^=diff;state[args[2]]^=diff
        elif kind=='HMR':
            outcome={1<<op.event:full};phase=add(phase,mul(outcome,{0:state[args[0]]}))
            state[args[0]]=0;classical[args[1]]=outcome
        elif kind=='R':assert state[args[0]]==0,('dirty reset',index,args[0])
        else:raise AssertionError((index,kind))
    assert len(stack)==1 and not phase,('unpaid phase',list(phase)[:10])
    for old,new in zip(P,current):
        if new is not None:assert state[str(new)]==inputs[str(old)]
    for q in v+flags:assert state[str(q)]==inputs[str(q)]
    if forward_u is not None:
        values=(4094-3*(vals>>3).astype(np.int64)+((vals>>1)&1).astype(np.int64)
                -2*((vals>>2)&1).astype(np.int64)+(vals&1).astype(np.int64))&16383
        for i,q in enumerate(forward_u):assert state[str(q)]==pack((values>>i)&1),('native u12 value',i)
    keep=set(map(str,v+[q for q in current if q is not None]+flags+(forward_u or [])))
    for q in p.quantum_wires:
        if q not in keep:assert not state[q],('dirty output',q)
    expected=exact_expectation(generated_text(c))
    assert expected['mean_numeric']=={'toffoli_like':24.0 if forward_u is not None else 25.0,'T':0.0,'generic_rotations':0.0},expected
    assert c.num_qubits==47
    return dict(status='PASS_NATIVE_TEXT_ALL_ABSTRACT_INPUTS_ALL_HMR_OUTCOMES',
                abstract_inputs=cases,independent_HMR_outcomes=p.measurements,Q=c.num_qubits,
                resources=expected,mode='forward'if forward_u is not None else'roundtrip',
                exact_forward_value=forward_u is not None,all_data_restored=forward_u is None,all_scratch_zero=True,
                original_P=list(map(str,P)),returned_P=[None if q is None else str(q)for q in current],
                forward_u=None if forward_u is None else list(map(str,forward_u)))


def product(C,U0,h):
    q=h+512;F=np.zeros_like(h)
    for i in range(10):
        sh=8-i;t=(C+(1<<(sh-1)))>>sh if sh>0 else C if sh==0 else 2*C+1
        F+=(2*((q>>i)&1)-1)*t
    return U0-F//2


def model_cases(count,seed):
    """Include both normalized residual edges for all4096 roots, then official x."""
    assert count>=8192 and count%256==0
    records=MODEL['records'];vv=np.repeat(np.arange(4096,dtype=np.int64),2)
    d=8193+2*vv;nlo=((d-1)**2+63)//64
    nhi=np.minimum(1<<22,((d+1)**2+63)//64)-1
    n=np.where(np.arange(8192)%2,nhi,nlo)
    # The divider contract permits every exponent0..10 for these root/U
    # values, even when a particular normalized pair is not an original-x
    # image. Exercise that stronger component domain uniformly at the edges.
    s=(np.arange(8192,dtype=np.int64)+seed)%11
    rng=np.random.default_rng(41491+seed)
    xs=rng.integers(1,3133453,count-8192,dtype=np.int64)
    if len(xs)>=44:xs[:44]=[min(3133452,x)for i in range(22)for x in (1<<i,(1<<i)+1)]
    leading=np.searchsorted(np.left_shift(np.ones(22,dtype=np.int64),np.arange(22)),xs,side='right')-1
    ss=(21-leading)//2;nn=xs<<2*ss
    import math
    extra_v=np.array([math.isqrt(16*int(x))-4096 for x in nn],dtype=np.int64)
    vv=np.concatenate([vv,extra_v]);n=np.concatenate([n,nn]);s=np.concatenate([s,ss]);d=8193+2*vv
    C=np.array([r['C']for r in records],dtype=np.int64)[vv]
    U0=np.array([r['U0']for r in records],dtype=np.int64)[vv]
    U=product(C,U0,n-(d*d+63)//64)
    assert np.all((U>=-16384)&(U<16384))
    return vv,U,s


def expected_phase(v,U,s):
    """Independent integer recurrence with explicit physical signed wrapping."""
    word=U&32767
    u=4094-3*v+((word>>13)&1)-2*((word>>14)&1)+((word>>12)&1)
    u=((u+8192)&16383)-8192;signs={}
    V=4096+v
    for j in range(12,36):
        sign=(u<0).astype(np.int64);signs[j]=sign
        if j<=24:
            prev=(word>>(24-j))&1;cur=(word>>(23-j))&1 if j<24 else np.zeros_like(word)
            nextu=2*u+(2*sign-1)*V+sign+cur-prev
        else:
            k=j-26 if j>=28 else 0
            A=(((V>>(k+1))+((V>>k)&1))<<(k+1))-(V&1)if k else V
            nextu=2*u+sign+(2*sign-1)*A
        u=((nextu+8192)&16383)-8192
    signs[36]=(u<0).astype(np.int64)
    P=np.full_like(U,1|(1<<26))
    for j in range(12,37):P|=(1-signs[j])<<(37-j)
    result=(P<<s)+(P>>(27-s))
    return result&((1<<37)-1)


def bits(values,n):
    values=values.astype(np.uint64)
    return ((values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1).astype(bool)


def read(sim,wires):
    return (sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def simulate(c,v,P,flags,current,count,seeds,phase):
    checks=[];kept=set(v+current+flags)
    scratch=[km.q(i)for i in range(c.num_qubits)if km.q(i)not in kept]
    for seed in seeds:
        started=time.monotonic();vv,U,s=model_cases(count,seed);wanted=expected_phase(vv,U,s)if phase else np.zeros(count,dtype=np.int64)
        sim=km.Simulator(batch_size=256,seed=seed,counting_operations=True)
        for first in range(0,count,256):
            stop=first+256;sim.clear_for_shot()
            for wires,data in [(v,vv[first:stop]),(P,U[first:stop]&32767),(flags,s[first:stop])]:
                sim.write_across_shots(array(wires),bits(data,len(wires)))
            sim.do(c)
            for wires,data in [(v,vv[first:stop]),(current,U[first:stop]&32767),(flags,s[first:stop])]:
                observed=read(sim,wires)
                assert np.array_equal(observed,data.astype(np.uint64)),('data',seed,first,list(map(str,wires)),observed.tolist(),data.tolist())
            assert not sim.read_across_shots(array(scratch)).any(),('scratch',seed,first)
            for i in range(256):
                target=Fraction(2*int(wanted[first+i]),1<<37)
                actual=sim.read_shot_phase(i)
                assert (actual-target)%2==0,('phase',seed,first+i,int(vv[first+i]),int(U[first+i]),int(s[first+i]),str(actual),str(target))
            if first%32768==0:print(json.dumps(dict(progress='native_divider',seed=seed,first=first,phase=phase)),flush=True)
        stats=sim.operation_statistics()
        row=dict(seed=seed,shots=count,status='PASS_NATIVE_EXACT_PHASE_RESTORATION_AND_SCRATCH',
                 all_root_edge_pairs=8192,sampled_mean_Toffolis=stats.num_toffoli_like/count,
                 seconds=time.monotonic()-started)
        checks.append(row);print(json.dumps(row),flush=True)
    return checks


def native_text_checks(c,v,P,flags,current,count=8192):
    """Independent actual-instruction replay; checks every reset before it acts.

    The initializer has a separate all-outcome proof. Here the full recurrence
    uses three explicit complete transcripts (all0, all1, and per-input random)
    alongside the native simulator's independent measurement seeds.
    """
    program=Program(generated_text(c));vv,U,s=model_cases(count,771)
    wanted=expected_phase(vv,U,s).astype(np.uint64)
    checks=[]
    assert program.modulus==(1<<37)
    for mode in ('all0','all1','independent_random'):
        rng=np.random.default_rng(20261112)
        state={wire:np.zeros(count,dtype=bool)for wire in program.wires}
        state.update({'0':np.zeros(count,dtype=bool),'False':np.zeros(count,dtype=bool),
                      '1':np.ones(count,dtype=bool),'True':np.ones(count,dtype=bool)})
        for wires,data in [(v,vv),(P,U&32767),(flags,s)]:
            for q,column in zip(wires,bits(data,len(wires))):state[str(q)]=column.copy()
        phase=np.zeros(count,dtype=np.uint64);stack=[np.ones(count,dtype=bool)];resets=0
        for index,op in enumerate(program.operations):
            kind,args=op.kind,op.arguments;active=stack[-1]
            if op.condition is not None:active=active&state[op.condition]
            if kind=='PUSH_CONDITION':stack.append(active);continue
            if kind=='POP_CONDITION':stack.pop();continue
            if not active.any():continue
            if kind=='X':state[args[0]]^=active
            elif kind=='CX':state[args[1]]^=active&state[args[0]]
            elif kind=='CCX':state[args[2]]^=active&state[args[0]]&state[args[1]]
            elif kind in ('SWAP','CSWAP'):
                if kind=='SWAP':a,b=args;enable=active
                else:ctrl,a,b=args;enable=active&state[ctrl]
                diff=enable&(state[a]^state[b]);state[a]^=diff;state[b]^=diff
            elif kind in ('Z','CZ','CCZ','NEG','Z_POW'):
                enabled=active.copy()
                for q in args:enabled&=state[q]
                coefficient=program.phase_steps[index]if kind=='Z_POW'else program.denominator
                phase+=enabled.astype(np.uint64)*np.uint64(coefficient%program.modulus)
            elif kind=='HMR':
                outcome=(rng.integers(0,2,count,dtype=np.uint8).astype(bool)if mode=='independent_random'
                         else np.full(count,mode=='all1',dtype=bool))
                phase+=(active&outcome&state[args[0]]).astype(np.uint64)*np.uint64(program.denominator)
                state[args[0]]&=~active
                state[args[1]]^=active&(state[args[1]]^outcome)
            elif kind=='R':
                assert not (active&state[args[0]]).any(),('nonzero native reset',mode,index,args[0])
                resets+=1
            elif kind in ('BIT_STORE0','BIT_STORE1'):
                target=np.full(count,kind=='BIT_STORE1',dtype=bool)
                state[args[0]]^=active&(state[args[0]]^target)
            elif kind=='BIT_INVERT':state[args[0]]^=active
            else:raise AssertionError((index,kind))
        assert len(stack)==1
        for wires,data in [(v,vv),(current,U&32767),(flags,s)]:
            for q,column in zip(wires,bits(data,len(wires))):assert np.array_equal(state[str(q)],column),('native text data',mode,str(q))
        keep=set(map(str,v+current+flags))
        for q in program.quantum_wires:
            if q not in keep:assert not state[q].any(),('native text scratch',mode,q)
        observed=phase&np.uint64(program.modulus-1)
        assert np.array_equal(observed,wanted),('native text phase',mode,int(np.flatnonzero(observed!=wanted)[0]))
        checks.append(dict(transcript=mode,inputs=count,status='PASS',checked_reset_instructions=resets,
                           syntactic_measurements=program.measurements))
        print(json.dumps(dict(native_text=checks[-1])),flush=True)
    return dict(status='PASS_INDEPENDENT_NATIVE_TEXT_FINITE_TRANSCRIPTS',checks=checks,
                qualification='Full reset/phase semantics on the stated cases and transcripts, separate from exact all-outcome u12 and seeded native simulation.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['initializer','counts','full','all'],default='all')
    ap.add_argument('--cases',type=int,default=32768);ap.add_argument('--seeds',default='0,1,2,3')
    args=ap.parse_args();verify_gate_sources();started=time.monotonic();result={}
    if args.stage in ('initializer','all'):
        b=km.CircuitBuilder();b.set_max_qubits(49)
        fv=list(b.alloc_qubits(12));fP=list(b.alloc_qubits(15))
        ff=list(b.alloc_qubits(4));fu=list(b.alloc_qubits(14))
        fcurrent=divider.initialize_u12(b,fv,fP,fu)
        fc=with_registers(b.finish_circuit(),{'v':fv,'P':fP,'flags':ff})
        fout=HERE/'u12_forward.kmb';fc.to_file(fout,format='kmb')
        result['initializer_forward']=exact_initializer(fc,fv,fP,ff,fcurrent,fu)
        result['initializer_forward']['kmb_sha256']=hashlib.sha256(fout.read_bytes()).hexdigest()
        atomic('u12_forward_native_proof.json',result['initializer_forward'])
        c,v,P,f,current=build(initializer=True)
        out=HERE/'u12_roundtrip.kmb';c.to_file(out,format='kmb')
        result['initializer']=exact_initializer(c,v,P,f,current)
        result['initializer']['kmb_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
        atomic('u12_native_proof.json',result['initializer']);print(json.dumps(result['initializer'],default=str),flush=True)
    if args.stage in ('counts','full','all'):
        c,v,P,f,current=build();out=HERE/'divider_phase_roundtrip.kmb';c.to_file(out,format='kmb')
        text=generated_text(c);(HERE/'divider_phase_roundtrip.kmx').write_text(text)
        counts=exact_expectation(text)
        result['resources']=dict(Q=c.num_qubits,counts=counts,kmb_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                                 original_P=list(map(str,P)),returned_P=list(map(str,current)))
        assert c.num_qubits==49,result['resources']
        assert counts['mean_numeric']=={'toffoli_like':734.5,'T':4.0,'generic_rotations':34.0},result['resources']
        atomic('divider_native_counts.json',result['resources']);print(json.dumps(result['resources'],default=str),flush=True)
        if args.stage in ('full','all'):
            result['native_text']=native_text_checks(c,v,P,f,current)
            result['simulator']=simulate(c,v,P,f,current,args.cases,[int(x)for x in args.seeds.split(',')],True)
    result.update(status='PASS_NATIVE_COMPONENT_NOT_OFFICIAL',stage=args.stage,source_sha256=hashlib.sha256((HERE/'divider.py').read_bytes()).hexdigest(),
                  model_sha256=MODEL_SHA,seconds=time.monotonic()-started)
    atomic('divider_native_proof_'+args.stage+'.json',result)
    print(json.dumps({k:v for k,v in result.items()if k not in ('initializer','resources')},indent=2),flush=True)


if __name__=='__main__':main()
