# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Direct RN2-B forward52 + original inverse44.5; no inherited patching."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[3]
for pin in json.loads((HERE/'INPUTS.json').read_text())['files']:
    path=NARROW/pin['path'];raw=path.read_bytes()
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],pin['path']
path=NARROW/'research/quantized_producer/pair_normalization.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='6af7fc14bc3c904efe480e2e23aee2fcbd97ad23f0a7ba324d8c05e1c8ec17fe'
spec=importlib.util.spec_from_file_location('_round2_rn2b_private_pair_normalizer',path)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
km,cb=old.km,old.cb
MAX_X=old.MAX_X


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

