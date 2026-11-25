"""Exact truth-domain specialization; all 3,133,452 promised fusion inputs.
Each bitset is the exact quantum wire's basis value on the complete domain.
HMR affects phase and resets its operand; its record never enters value logic
outside closed diagonal classical-condition blocks, checked at every join.
SPDX-License-Identifier: Apache-2.0
"""
import re,heapq,collections,time,json
import numpy as np
Q=re.compile(r'(?<!\w)q(\d+)(?!\w)')

def compile(source,destination,max_x=3133452,linear=False):
    lines=open(source).readlines();protected=set()
    for line in lines:
        if line.startswith('APPEND_TO_REGISTER'):protected.update(map(int,Q.findall(line)))
    assert protected==set(range(22))
    full=(1<<max_x)-1
    x=np.arange(1,max_x+1,dtype=np.uint32)
    values={q:int.from_bytes(np.packbits((x>>q)&1,bitorder='little').tobytes(),'little') for q in protected}
    initial=values.copy();mapping={q:q for q in protected};free=[];slots=22;peak=22;stack=[];changes=collections.Counter();ops=collections.Counter()
    def val(q):return values.get(q,0)
    def materialize(q):
        nonlocal slots,peak
        if q not in mapping:
            if free:mapping[q]=heapq.heappop(free)
            else:mapping[q]=slots;slots+=1;peak=max(peak,slots)
        return mapping[q]
    def release():
        for q in list(mapping):
            if q not in protected and val(q)==0 and not stack:heapq.heappush(free,mapping.pop(q))
    def solve(product,exclude):
        basis={};wires=[q for q in values if q not in exclude and val(q) not in (0,full)]
        for k,v in enumerate([full]+[val(q) for q in wires]):
            mask=1<<k
            while v:
                pivot=v.bit_length()-1
                if pivot not in basis:basis[pivot]=(v,mask);break
                a,c=basis[pivot];v^=a;mask^=c
        v=product;result=0
        while v:
            pivot=v.bit_length()-1
            if pivot not in basis:return None
            a,c=basis[pivot];v^=a;result^=c
        return bool(result&1),[q for k,q in enumerate(wires) if result>>(k+1)&1]
    with open(destination,'w') as out:
        for i,line in enumerate(lines):
            ts=line.split()
            if not ts:continue
            op=ts[0]
            if op in ('REGISTER','INFO_TAG'):out.write(line);continue
            if op=='PUSH_CONDITION':stack.append(values.copy());out.write(line);continue
            if op=='POP_CONDITION':
                before=stack.pop()
                assert all(val(q)==before.get(q,0) for q in values.keys()|before.keys()),('non-diagonal condition join',i)
                out.write(line);release();continue
            qs=list(map(int,Q.findall(line)))
            if op=='APPEND_TO_REGISTER':out.write(line);continue
            if not qs:out.write(line);continue
            vs=[val(q) for q in qs];new=op;nqs=qs
            if op=='CCX':
                a,b,t=qs;prod=vs[0]&vs[1]
                if prod==0:new=None
                elif prod==full:new='X';nqs=[t]
                elif prod==vs[0]:new='CX';nqs=[a,t]
                elif prod==vs[1]:new='CX';nqs=[b,t]
                values[t]=vs[2]^prod
            elif op=='CSWAP':
                c,a,b=qs;delta=vs[0]&(vs[1]^vs[2])
                if not delta:new=None
                elif delta==(vs[1]^vs[2]):new='SWAP';nqs=[a,b]
                values[a]=vs[1]^delta;values[b]=vs[2]^delta
            elif op=='CX':
                a,t=qs;values[t]=vs[0]^vs[1]
                if vs[0]==0:new=None
                elif vs[0]==full:new='X';nqs=[t]
            elif op=='X':
                for q in qs:values[q]=val(q)^full
            elif op=='SWAP':values[qs[0]],values[qs[1]]=vs[1],vs[0]
            elif op in ('R','HMR'):
                for q in qs:values[q]=0
            elif op in ('Z','CZ','CCZ'):
                product=full
                for v in vs:product&=v
                if product==0:new=None
                elif op=='CCZ':
                    for j in range(3):
                        for k in range(j):
                            if vs[j]&vs[k]==product:new='CZ';nqs=[qs[j],qs[k]];break
                        if new!='CCZ':break
                if product==full:new='NEG';nqs=[]
            elif op=='Z_POW':
                if vs[0]==0:new=None
            else:raise ValueError(('Unsupported value instruction',line))
            synthesized=None
            if linear and new==op and op in ('CCX','CSWAP'):
                if op=='CCX':product=prod;targets=[qs[-1]]
                else:product=delta;targets=qs[1:]
                sol=solve(product,set(targets))
                if sol is not None:
                    constant,sources=sol;synthesized=[]
                    for t in targets:
                        if constant:synthesized.append('X q'+str(t)+'\n')
                        synthesized.extend('CX q'+str(q)+' q'+str(t)+'\n' for q in sources)
                    for l in synthesized:
                        for q in map(int,Q.findall(l)):materialize(q)
                        out.write(Q.sub(lambda m:'q'+str(mapping[int(m[1])]),l));ops[l.split()[0]]+=1
                    changes[op+'->AFFINE']+=1;release();continue
            if new!=op:changes[op+'->'+str(new)]+=1
            if new is None:release();continue
            for q in nqs:materialize(q)
            if new!=op:
                line=' '.join([new]+['q'+str(q) for q in nqs])+'\n'
            out.write(Q.sub(lambda m:'q'+str(mapping[int(m[1])]),line))
            ops[new]+=1;release()
            if i%6000==0:print('compiled',i,'qubits',peak,dict(changes),flush=True)
    assert not stack
    assert all(val(q)==initial.get(q,0) for q in values)
    return {'qubits':peak,'rewrites':dict(changes),'operations':dict(ops),'exhaustive_domain':max_x,'value_restoration':'PASS'}

