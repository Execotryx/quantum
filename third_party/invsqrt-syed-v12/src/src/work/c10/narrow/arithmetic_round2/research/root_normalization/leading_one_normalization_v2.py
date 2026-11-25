#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""RN2-B exact forward-normalization source proof, not native execution."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import hashlib,importlib.util,json,resource,sys,time
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[2]
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
for pin in json.loads((HERE/'normalization_inputs_v2.json').read_text())['files']:
    raw=(NARROW/pin['path']).read_bytes()
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],pin['path']
path=NARROW/'research/quantized_producer/pair_normalization.py'
spec=importlib.util.spec_from_file_location('round2_pinned_pair_normalization',path)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
km,cb=old.km,old.cb
ODD_LAST=old.small_plan(2,lambda previous,H:previous^(previous&H))


def route_lane(builder,lane,T):
    count=0
    for op in old.operations(len(lane)):
        terms=[i for i in op['prefix_terms'] if i<=10]
        assert terms and 0 not in terms
        control=T[terms[0]-1];others=[T[i-1]for i in terms[1:]]
        for q in others:builder.cx(q,control)
        builder.cswap(control,lane[op['first']],lane[op['second']]);count+=1
        for q in reversed(others):builder.cx(q,control)
    assert count=={10:15,11:17}[len(lane)]


def forward(builder,x,flags):
    x=list(x);flags=list(flags)
    assert len(x)==22 and len(flags)==4
    P=[]
    for length in range(1,21):
        q=builder.alloc_qubits(1)[0];data=x[22-length]
        if length==1:builder.x(q);builder.cx(data,q)
        elif length==2:builder.cx(P[-1],q);builder.cx(data,q)
        else:
            builder.x(data);builder.ccx(P[-1],data,q);builder.x(data)
        P.append(q)
    T=P[1::2]
    assert len(T)==10
    for bit,flag in enumerate(flags):
        for j in range(1<<bit,11,1<<bit):builder.cx(T[j-1],flag)
    # Clear the leading-one indicator above the two lowest input positions.
    for position in range(2,22):
        for prefix in (21-position,22-position):
            if prefix==0:builder.x(x[position])
            else:builder.cx(P[prefix-1],x[position])
    # Raw x1 remains available. P21 is folded into the intended H output.
    builder.x(x[21])
    for q in P:builder.cx(q,x[21])
    builder.x(x[1]);builder.ccx(T[-1],x[1],x[21]);builder.x(x[1])
    # P21=H xor1 xor sum(P1..20); P20 xor P21 omits P20.
    for target,prefixes in ((x[0],P),(x[1],P[:-1])):
        builder.x(target);builder.cx(x[21],target)
        for q in prefixes:builder.cx(q,target)
    route_lane(builder,x[0::2],T)
    route_lane(builder,x[1:21:2],T)
    builder.x(x[20]);builder.cx(x[21],x[20])
    for j in range(1,11):
        q=P[2*j-2];m=builder.alloc_bits(1)[0];builder.hmr(q,m)
        if j==1:cb.emit_phase(builder,[T[0],x[21]],m,old.ODD_FIRST)
        else:cb.emit_phase(builder,[T[j-2],T[j-1],x[21]],m,old.ODD_OTHER)
        builder.free(m);builder.free(q)
    g=builder.alloc_qubits(1)[0];builder.ccx(flags[0],flags[1],g)
    for q,p in zip(T,old.THRESHOLD_PLANS):
        m=builder.alloc_bits(1)[0];builder.hmr(q,m);cb.emit_phase(builder,flags+[g],m,p)
        builder.free(m);builder.free(q)
    builder.del_and(flags[0],flags[1],g);builder.free(g)


inverse=old.inverse


def paper(cap=48):
    b=old.Counter(cap);x=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
    forward(b,x,flags);f=float(b.count);fp=b.peak
    assert b.num_allocated_qubits==26
    b.peak=26;inverse(b,x,flags)
    assert b.num_allocated_qubits==26 and f==52 and float(b.count)==96.5 and fp==46
    return dict(forward_E=f,inverse_E=float(b.count)-f,total_E=float(b.count),
                modeled_forward_peak=fp,modeled_inverse_peak=b.peak,Q_cap=cap,
                old_total_E=97.5,saving_E=1,T=0,R=0,accuracy_change=0,
                complete_Q=48,complete_expected_Toffolis=1583,
                complete_expected_cost=48*(1583+1+230.84805946161188))


def certify():
    began=time.monotonic();size=1<<22;full=(1<<size)-1;valid=(1<<(old.MAX_X+1))-2
    src=old.input_truths();b=old.TruthPhaseBuilder(48,full,valid)
    x=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
    for q,v in zip(x,src):b.values[q]=v
    expected=[0]*22;expected_flags=[0]*4
    for k in range(11):
        lo=1<<(20-2*k);hi=min(old.MAX_X+1,1<<(22-2*k));mask=((1<<hi)-(1<<lo))if hi>lo else 0
        for i in range(2*k,22):expected[i]^=mask&src[i-2*k]
        for bit in range(4):
            if k>>bit&1:expected_flags[bit]^=mask
    forward(b,x,flags)
    assert all(not((b.value(q)^v)&valid)for q,v in zip(x,expected)),'normalization_map'
    assert all(not((b.value(q)^v)&valid)for q,v in zip(flags,expected_flags)),'flags'
    assert b.num_allocated_qubits==26;b.check_phase()
    f=float(b.count);fpeak=b.peak;fm=b.measurements
    inverse(b,x,flags)
    assert all(not((b.value(q)^v)&valid)for q,v in zip(x,src)),'input_restoration'
    assert all(not(b.value(q)&valid)for q in flags),'flag_cleanup'
    assert b.num_allocated_qubits==26;b.check_phase()
    assert (f,float(b.count),fpeak)==(52,96.5,46)
    return dict(status='PASS_ALL_ORIGINAL_INPUTS_ALL_SYMBOLIC_HMR_PHASES_NOT_NATIVE',
                original_inputs=old.MAX_X,input_interval=[1,old.MAX_X+1],end_exclusive=True,
                normalized_map='n=x*4**k, k=floor((22-bit_length(x))/2)',
                original_input_owners_restored=True,all_scratch_and_flags_zero=True,
                forward_HMR_symbols=fm,total_independent_HMR_symbols=b.measurements,
                all_phase_coefficients_zero=True,mathematical_phase_error=0,
                forward_E=f,roundtrip_E=float(b.count),modeled_peak=fpeak,
                seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                native_builder_or_simulator=False,official_verifier_run=False)


def main():
    result=dict(paper=paper(),certificate=certify(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                inputs_sha256=hashlib.sha256((HERE/'normalization_inputs_v2.json').read_bytes()).hexdigest())
    with (HERE/'leading_one_normalization_v2.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
