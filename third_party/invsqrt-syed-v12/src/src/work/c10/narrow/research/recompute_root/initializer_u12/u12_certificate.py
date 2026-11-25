#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Complete abstract gate/width/measurement-phase proof for direct u12.

This builder is a Boolean truth/phase counter. It has no native emitter,
CircuitBuilder, KMB serialization, or official verifier invocation.
"""
import time
from collections import Counter
from dataclasses import asdict
from local_algebra import *

LOCAL_PIN='978c2adafd8d3355558a5e672982623372d459dec610273e1e43847681cc4c14'
raw=(HERE/'local_algebra.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==LOCAL_PIN
LOCAL=json.loads(raw)
CASES=32768;FULL=(1<<CASES)-1

def getplan(data):
    return cb.QuadraticCodePlan(**{k:tuple(tuple(x)for x in v)if k in ('edges','products')else v for k,v in data.items()})

def compose(plan,mapping,width):
    constant=int(plan.constant);linear=0;edges=set()
    for i in cb.bits(plan.linear):constant^=mapping[i][0];linear^=mapping[i][1]
    for i,j in plan.edges:
        ca,ma=mapping[i];cb_,mb=mapping[j];constant^=ca*cb_
        if ca:linear^=mb
        if cb_:linear^=ma
        for a in cb.bits(ma):
            for b in cb.bits(mb):
                if a==b:linear^=1<<a
                else:
                    edge=tuple(sorted((a,b)))
                    if edge in edges:edges.remove(edge)
                    else:edges.add(edge)
    return cb.factor_polynomial(width,constant,linear,edges)

P13=cb.factor_polynomial(5,False,13,set())
P14=cb.factor_polynomial(5,True,23,{(0,2),(0,3),(2,3)})
OLDQ0=cb.factor_polynomial(4,True,7,set())
OLDQ1=cb.factor_polynomial(4,True,12,{(0,1),(0,2),(1,2)})
HIGH=cb.factor_polynomial(6,False,39,{(3,4),(3,5),(4,5)})

class TruthCounter:
    def __init__(self,cap):
        self.cap=cap;self.live=set();self.pool=[];self.nextq=0;self.nextb=0
        self.values={};self.phases={};self.conditions=[];self.peak=0;self.counts=Counter();self.phase_checks=[]
    def alloc_qubits(self,n):
        if len(self.live)+n>self.cap:raise ValueError(f'ownership {len(self.live)}+{n}>{self.cap}')
        out=[]
        for _ in range(n):
            q=self.pool.pop()if self.pool else('q',self.nextq)
            if q[1]==self.nextq:self.nextq+=1
            self.live.add(q);self.values[q]=0;out.append(q)
        self.peak=max(self.peak,len(self.live));return out
    def alloc_bits(self,n):
        out=[]
        for _ in range(n):
            b=('b',self.nextb);self.nextb+=1;self.phases[b]=0;out.append(b)
        return out
    def free(self,x):
        if isinstance(x,list):
            for q in x:self.free(q)
        elif x[0]=='q':
            assert x in self.live and self.values[x]==0,('nonzero free',x)
            self.live.remove(x);self.pool.append(x)
        else:
            assert self.phases[x]==0,('unpaid HMR phase',x)
            self.phase_checks.append(x[1]);del self.phases[x]
    def x(self,q):self.values[q]^=FULL;self.counts['X']+=1
    def cx(self,c,t):self.values[t]^=self.values[c];self.counts['CX']+=1
    def ccx(self,a,b,t):
        assert not self.conditions
        self.values[t]^=self.values[a]&self.values[b];self.counts['CCX']+=1
    def hmr(self,q,m):
        assert m in self.phases
        self.phases[m]^=self.values[q];self.values[q]=0;self.counts['HMR']+=1
    def push_condition(self,m):self.conditions.append(m)
    def pop_condition(self):self.conditions.pop()
    def z(self,q):
        if q[0]=='b':
            assert not self.conditions;self.phases[q]^=FULL;self.counts['classical_branch_Z']+=1
        else:
            assert len(self.conditions)==1;self.phases[self.conditions[0]]^=self.values[q];self.counts['conditional_Z']+=1
    def cz(self,a,b):
        assert len(self.conditions)==1;self.phases[self.conditions[0]]^=self.values[a]&self.values[b];self.counts['conditional_CZ']+=1

def erase(b,target,variables,plan):
    assert target not in variables
    m=b.alloc_bits(1)[0];b.hmr(target,m);cb.emit_phase(b,variables,m,plan);b.free(m);b.free(target)

def emit_forward(b,v,P,flags,u):
    start=b.counts['CCX'];carry=b.alloc_qubits(2)
    for q in (v[0],P[13],P[12]):b.cx(q,u[0])
    env={'v0':v[0],'v1':v[1],'p12':P[12],'p13':P[13],'p14':P[14],
         'u0':u[0],'u1':u[1],'q0':carry[0],'q1':carry[1]}
    for item in LOCAL['best_low']['plans']:
        cb.emit_xor(b,[env[name]for name in item['inputs']],env[item['output']],getplan(item['plan']))
    varsP=[v[0],v[1],P[12],u[0],u[1]]
    erase(b,P[13],varsP,P13);erase(b,P[14],varsP,P14)
    P=list(P);P[13]=None;P[14]=None
    low_cost=b.counts['CCX']-start;rows=[]
    for i in range(2,13):
        before=b.counts['CCX'];nextcarry=b.alloc_qubits(2 if i<12 else 1)
        if i<12:
            aq=v[i];bq=v[i-1];b.x(aq);b.x(bq)
        else:
            aq=u[13];bq=v[11];assert b.values[aq]==0;b.x(bq)
        q0,q1=carry
        # Restricted local carry invariant, checked on every abstract root/P case.
        assert ((FULL^b.values[q0])&(FULL^b.values[q1])&b.values[bq])==0
        assert (b.values[q0]&b.values[q1]&(FULL^b.values[bq]))==0
        b.x(u[i])
        for q in (aq,bq,q0):b.cx(q,u[i])
        for which,target in enumerate(nextcarry):
            cb.emit_xor(b,[aq,bq,q0,q1],target,getplan(LOCAL['high_forward'][f'next{which}']['plan']))
        variables=[aq,bq,u[i],nextcarry[0]]
        erase(b,q0,variables,OLDQ0);erase(b,q1,variables,OLDQ1)
        if i<12:b.x(aq)
        b.x(bq);carry=nextcarry
        rows.append(dict(bit=i,Toffolis=b.counts['CCX']-before,new_carry_wires=len(carry),owners=len(b.live)))
    # Only the next carry's low bit enters bit13. Its high bit was never loaded.
    b.cx(carry[0],u[13]);b.cx(u[13],carry[0]);b.free(carry[0])
    assert len(b.live)==43 and not b.phases
    return P,dict(low_Toffolis=low_cost,high_rows=rows,total_Toffolis=b.counts['CCX']-start,
                  data_after=len(b.live),pending_phase_debts=0)

def emit_cleanup(b,v,P,flags,u):
    start=b.counts['CCX'];P=list(P);P[13],P[14]=b.alloc_qubits(2)
    variables=[v[0],v[1],P[12],u[0],u[1]]
    cb.emit_xor(b,variables,P[13],P13);cb.emit_xor(b,variables,P[14],P14)
    restored_ids=[P[13][1],P[14][1]]
    def aa(i):return(1,1<<i)if 0<=i<12 else(0,0)
    def bb(i):
        if i==0 or i==13:return(1,0)
        return(1,1<<(i-1))
    for i in reversed(range(4,14)):
        mappings=[aa(i),bb(i),aa(i-2),aa(i-3),aa(i-1),(0,1<<12)]
        phase=compose(HIGH,mappings,13)
        erase(b,u[i],list(v)+[u[i-1]],phase)
    for i in reversed(range(4)):
        item=LOCAL['low_cleanup'][i]
        env={f'v{j}':v[j]for j in range(i+1)}
        env.update(p12=P[12],p13=P[13],p14=P[14])
        env.update({f'u{j}':u[j]for j in range(i)})
        erase(b,u[i],[env[name]for name in item['inputs']],getplan(item['plan']))
    assert len(b.live)==31 and not b.phases
    return P,dict(Toffolis=b.counts['CCX']-start,restored_product_owner_ids=restored_ids,
                  final_data=len(b.live),pending_phase_debts=0)

def certify(cap):
    b=TruthCounter(cap);v=b.alloc_qubits(12);P=b.alloc_qubits(15);flags=b.alloc_qubits(4);u=b.alloc_qubits(14)
    for i,q in enumerate(v):b.values[q]=cb.pack_bits((case>>3)>>i for case in range(CASES))
    for i,q in enumerate(P):
        b.values[q]=cb.pack_bits(case>>(i-12) for case in range(CASES))if i>=12 else b.values[v[i]]
    for i,q in enumerate(flags):b.values[q]=b.values[v[i]]
    initial_v=[b.values[q]for q in v];initial_P=[b.values[q]for q in P];initial_flags=[b.values[q]for q in flags]
    original_P_ids=[q[1]for q in P]
    P,forward=emit_forward(b,v,P,flags,u)
    expected=[(4094-3*(case>>3)+((case>>1)&1)-2*((case>>2)&1)+(case&1))&16383 for case in range(CASES)]
    for i,q in enumerate(u):assert b.values[q]==cb.pack_bits(x>>i for x in expected),('u12 bit',i)
    assert [b.values[q]for q in v]==initial_v
    assert [b.values[q]for q in P[:13]]==initial_P[:13]
    assert [b.values[q]for q in flags]==initial_flags
    P,cleanup=emit_cleanup(b,v,P,flags,u)
    assert [b.values[q]for q in v]==initial_v
    assert [b.values[q]for q in P]==initial_P
    assert [b.values[q]for q in flags]==initial_flags
    assert b.counts['CCX']==25 and b.peak==47
    return dict(status='EXACT_ALL_ABSTRACT_BOOLEAN_PHASE_AND_OWNERSHIP_PASS_NOT_NATIVE',Q_cap=cap,
                abstract_cases=CASES,root_bits=12,product_bits_checked=[12,13,14],
                lower_product_and_flags='Untouched spectators; original values are retained.',
                forward=forward,cleanup=cleanup,Toffolis=b.counts['CCX'],T=0,R=0,peak=b.peak,
                source_counts=dict(b.counts),HMR_sign_functions_proved=len(b.phase_checks),
                outcome_scope='Every HMR sign is checked against its complete correction on all32768 cases; linearity proves every joint outcome assignment.',
                original_product_owner_ids=original_P_ids,returned_product_owner_ids=[q[1]for q in P],
                physical_binding='Returned logical P owners are explicit. No claim that reconstructed product bits occupy their original freed physical IDs.',
                all_ancillas_zero=True,all_phase_debts_paid=True)

def main():
    start=time.monotonic();rows=[certify(cap)for cap in [48,49]]
    out=dict(status='COMPLETE_COMPONENT_MATHEMATICAL_AND_SOURCE_GATE_CERTIFICATE_NOT_NATIVE',
             input_local_plans_sha256=LOCAL_PIN,formula='u12=4094−3v+b13−2b14+b12 mod2^14',
             unchanged_phase=True,rows=rows,baseline_Q49_u11_plus_j11=42,component_saving_Q49=17,
             full_candidate_gate='Not established here; normalization and actual loaders remain parent integration obligations.',
             seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    target=HERE/'u12_certificate.json';tmp=target.with_suffix('.json.tmp');tmp.write_text(json.dumps(out,indent=2)+'\n');tmp.replace(target)
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
