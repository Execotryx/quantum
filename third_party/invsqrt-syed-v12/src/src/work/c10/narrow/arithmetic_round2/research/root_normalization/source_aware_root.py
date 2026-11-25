#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""RN3-A exact source proof; no native builder or simulator is instantiated."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,importlib.util,json,resource,sys,time

HERE=Path(__file__).resolve().parent
NARROW=HERE.parents[2]
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
for pin in json.loads((HERE/'INPUTS.json').read_text())['files']:
    path=NARROW/pin['path'];raw=path.read_bytes()
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],pin['path']
sys.path[:0]=[str(NARROW/'research/stream_phase'),
             str(NARROW/'checkpoint002/cleanroom/odd_sqrt')]
from drive_paper_ledger import PaperCounter,km
import consuming_odd_sqrt as original
import numpy as np


def arr(wires):return km.array(list(wires))


def last_step(builder,remainder,older,b,*,initial=False,inverse=False):
    """The inherited j11 zero-pair rule plus the new j12 carry alias."""
    remainder=list(remainder);older=list(older)
    j=len(remainder)-3
    if j<11:
        return original._root_step(builder,remainder,older,b,initial=initial,inverse=inverse)
    assert j in (11,12) and not initial and isinstance(b,km.q)
    assert len(set(remainder+older+[b]))==len(remainder)+len(older)+1
    low=remainder[:3];high=remainder[3:]
    if hasattr(builder,'values'):
        pair=builder.full if inverse else 0
        assert builder.value(low[0])==builder.value(low[1])==pair
        if j==12:
            expected=(builder.full ^ builder.value(b) ^ builder.value(older[0])) if inverse else builder.full
            assert builder.value(high[0])==expected,('j12_first_high',inverse)
    if not inverse:builder.x(low[0]);builder.x(low[1])
    builder.cx(b,arr(high))
    if inverse:original._add_leading_one(builder,high,inverse=True)
    if j==12:
        builder.cx(b,high[0]);builder.cx(older[0],high[0])
        original.add(builder,older[1:],high[1:],carry_in=older[0],subtract=inverse)
    else:
        original.add(builder,older,high,carry_in=b,subtract=inverse)
    if not inverse:original._add_leading_one(builder,high)
    builder.cx(b,arr(high))
    if inverse:builder.x(low[0]);builder.x(low[1])


def initial_low_xor(builder,Q,low):
    """The preconversion low word is (1,1,1,1 xor Q1 xor Q2)."""
    builder.x(arr(low));builder.cx(Q[1],low[3]);builder.cx(Q[2],low[3])


def _p_frame(builder,Q):
    builder.cx(Q[2],Q[0]);builder.cx(Q[2],Q[1])


def _carry_frame(builder,Q,p):
    # Q3 becomes Q3 xor a2; p becomes c2 xor a2.
    builder.x(Q[3])
    for q in Q[:3]:builder.cx(q,Q[3])
    builder.x(p);builder.cx(Q[0],p);builder.cx(Q[2],p)


def _a2_xor(builder,Q,target):
    builder.x(target)
    for q in Q[:3]:builder.cx(q,target)


def carry_prepare(builder,Q):
    p,c=builder.alloc_qubits(2)
    _p_frame(builder,Q);builder.ccx(Q[0],Q[1],p);_p_frame(builder,Q)
    _a2_xor(builder,Q,c)
    _carry_frame(builder,Q,p);builder.ccx(Q[3],p,c);_carry_frame(builder,Q,p)
    return p,c


def carry_clear(builder,Q,p,c):
    _a2_xor(builder,Q,c)
    _carry_frame(builder,Q,p);builder.del_and(Q[3],p,c);_carry_frame(builder,Q,p)
    builder.free(c)
    _p_frame(builder,Q);builder.del_and(Q[0],Q[1],p);_p_frame(builder,Q)
    builder.free(p)


def convert_high(builder,Q,high,*,inverse=False):
    p,c=carry_prepare(builder,Q)
    builder.cx(Q[0],arr(high))
    if inverse:original._add_leading_one(builder,high,inverse=True)
    original.add(builder,Q[4:],high,carry_in=c,subtract=inverse)
    if not inverse:original._add_leading_one(builder,high)
    builder.cx(Q[0],arr(high))
    carry_clear(builder,Q,p,c)


def forward(builder,norm):
    norm=list(norm)
    assert len(norm)==22 and len(set(norm))==22
    builder.x(norm[20]);builder.cx(norm[20],norm[21])
    remainder=norm[20:22];roots=[]
    for j in range(1,13):
        pair=norm[20-2*j:22-2*j] if j<=10 else list(builder.alloc_qubits(2))
        if j==1:b=True;older=[];remainder=pair+remainder
        else:
            b=remainder[-1];builder.x(b);older=roots
            roots=[b]+roots;remainder=pair+remainder[:-1]
        last_step(builder,remainder,older,b,initial=j==1)
    b=remainder[-1];builder.x(b);Q=[b]+roots;W=remainder[:-1]
    initial_low_xor(builder,Q,W[:4]);builder.free(arr(W[:4]))
    convert_high(builder,Q,W[4:])
    assert Q==norm[10:] and W[4:]==norm[:10]
    return dict(root=Q,residual=W[4:])


def inverse(builder,norm):
    norm=list(norm);Q=norm[10:];high=norm[:10]
    convert_high(builder,Q,high,inverse=True)
    low=list(builder.alloc_qubits(4));initial_low_xor(builder,Q,low)
    W=low+high;b=Q[0];roots=Q[1:]
    builder.x(b);remainder=W+[b]
    for j in reversed(range(1,13)):
        pair=remainder[:2]
        if j==1:b=True;older=[]
        else:b=roots[0];older=roots[1:]
        last_step(builder,remainder,older,b,initial=j==1,inverse=True)
        if j==1:remainder=remainder[2:]
        else:
            remainder=remainder[2:]+[b];builder.x(b);roots=older
        if j>=11:builder.free(arr(pair))
        else:assert pair==norm[20-2*j:22-2*j]
    assert remainder==norm[20:] and not roots
    builder.cx(norm[20],norm[21]);builder.x(norm[20])
    return norm


class BooleanBuilder:
    """Bitset basis values; each local del_and proves its own HMR phase."""
    def __init__(self,count,cap=48):
        self.max_qubits=cap;self.full=(1<<count)-1;self.live=set();self.pool=[]
        self.nextq=0;self.values={};self.peak=0;self.Toffolis=0;self.HMR=0
    @property
    def num_allocated_qubits(self):return len(self.live)
    def alloc_qubits(self,n):
        assert len(self.live)+n<=self.max_qubits
        out=[]
        for _ in range(n):
            if self.pool:q=self.pool.pop()
            else:q=km.q(self.nextq);self.nextq+=1
            self.live.add(q);self.values[q]=0;out.append(q)
        self.peak=max(self.peak,len(self.live));return arr(out)
    def free(self,wires):
        if isinstance(wires,km.q):
            assert wires in self.live and self.values[wires]==0,('nonzero_release',str(wires))
            self.live.remove(wires);self.pool.append(wires)
        else:
            for q in wires:self.free(q)
    def value(self,q):return self.full if q is True else 0 if q is False else self.values[q]
    def x(self,wires):
        if isinstance(wires,km.q):self.values[wires]^=self.full
        else:
            for q in wires:self.x(q)
    def cx(self,control,target):
        if isinstance(target,km.q):self.values[target]^=self.value(control)
        else:
            for q in target:self.cx(control,q)
    def ccx(self,a,b,t):
        assert len({a,b,t})==3
        self.values[t]^=self.value(a)&self.value(b);self.Toffolis+=1
    def del_and(self,a,b,t):
        assert self.values[t]==(self.value(a)&self.value(b)),('unpaid_HMR',str(a),str(b),str(t))
        self.values[t]=0;self.HMR+=1
    def alloc_bits(self,n):raise AssertionError('Unexpected segmented source arithmetic.')


def pack(values):
    return int.from_bytes(np.packbits(np.asarray(values,dtype=np.uint8),bitorder='little').tobytes(),'little')


def local_carry():
    rows=[]
    for word in range(16):
        q=[(word>>i)&1 for i in range(4)]
        target=(1^q[0]) | ((1^q[0])<<1) | ((1^q[0]^q[1]^q[2])<<2)
        source=q[1] | (q[2]<<1) | (q[3]<<2)
        expected=(target+source+q[0])>>3
        p=(q[0]^q[2])&(q[1]^q[2]);a2=1^q[0]^q[1]^q[2];c2=q[1]^p
        c3=a2 ^ ((q[3]^a2)&(c2^a2))
        assert c3==expected
        rows.append(dict(Q_low4=word,carry=c3,original_carry=expected))
    b=BooleanBuilder(16);Q=list(b.alloc_qubits(12))
    for i in range(4):b.values[Q[i]]=sum(((x>>i)&1)<<x for x in range(16))
    original_values=[b.value(q)for q in Q]
    p,c=carry_prepare(b,Q)
    assert b.value(c)==sum(row['carry']<<i for i,row in enumerate(rows))
    carry_clear(b,Q,p,c)
    assert [b.value(q)for q in Q]==original_values and b.num_allocated_qubits==12
    assert b.Toffolis==2 and b.HMR==2
    return dict(cases=16,AND_preparation=2,AND_cleanup=0,independent_HMR_functions=2,
                all_root_controls_restored=True,all_scratch_zero=True,rows=rows)


def paper():
    b=PaperCounter(48);norm=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
    result=forward(b,norm);f=float(b.count);live=b.num_allocated_qubits
    assert result==dict(root=norm[10:],residual=norm[:10])
    restored=inverse(b,norm)
    assert restored==norm and b.num_allocated_qubits==26 and live==26
    assert f==96 and float(b.count)==192
    assert b.peak<=39
    return dict(forward_E=f,inverse_E=float(b.count)-f,total_E=float(b.count),
                peak_including_flags4=b.peak,body_live=26,T=0,R=0,
                baseline_root_E=198,saving_E=6,complete_Q=48,complete_expected_Toffolis=1578,
                complete_expected_cost=48*(1578+1+230.84805946161188),
                accuracy_change=0,original_phase_and_loaders_unchanged=True)


def certify():
    began=time.monotonic();checked=0;sign_checks=0;rows=[]
    for first in range(1<<20,1<<22,65536):
        values=np.arange(first,min(1<<22,first+65536),dtype=np.int64)
        b=BooleanBuilder(len(values));norm=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
        for i,q in enumerate(norm):b.values[q]=pack((values>>i)&1)
        for i,q in enumerate(flags):b.values[q]=pack((values>>(i+1))&1)
        saved_norm=[b.value(q)for q in norm];saved_flags=[b.value(q)for q in flags]
        result=forward(b,norm)
        Q=np.sqrt(values<<4).astype(np.int64)
        assert np.all(Q*Q<=values<<4) and np.all((Q+1)*(Q+1)>values<<4)
        expected_v=Q-4096;expected_h=((values<<6)-(2*Q+1)**2)//64
        for i,q in enumerate(result['root']):assert b.value(q)==pack((expected_v>>i)&1),('root',first,i)
        for i,q in enumerate(result['residual']):assert b.value(q)==pack((expected_h>>i)&1),('residual',first,i)
        assert [b.value(q)for q in flags]==saved_flags and b.num_allocated_qubits==26 and b.Toffolis==96
        inverse(b,norm)
        assert [b.value(q)for q in norm]==saved_norm and [b.value(q)for q in flags]==saved_flags
        assert b.num_allocated_qubits==26 and b.Toffolis==192 and b.peak<=39
        checked+=len(values);sign_checks+=len(values)*b.HMR
        rows.append(dict(first=first,stop=int(values[-1])+1,inputs=len(values),HMR_symbols=b.HMR,
                         Toffolis=b.Toffolis,peak=b.peak))
        if len(rows)%12==0:print(json.dumps(dict(progress='root_source_math',inputs=checked,seconds=time.monotonic()-began)),flush=True)
    assert checked==3145728
    return dict(status='PASS_ALL_NORMALIZED_INPUTS_ALL_LOCAL_HMR_PHASES_NOT_NATIVE',
                normalized_inputs=checked,input_interval=[1<<20,1<<22],end_exclusive=True,
                root_formula='v=isqrt(16*n)-4096',residual_formula='h=(64*n-(8193+2*v)^2)//64',
                source_root_owner_interface_preserved=True,all_original_data_and_flags_restored=True,
                all_scratch_releases_zero=True,all_local_HMR_sign_checks=sign_checks,
                HMR_proof='Every measured AND equals its complete local Clifford correction; every independent phase coefficient vanishes.',
                chunks=rows,seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                native_builder_or_simulator=False,official_verifier_run=False)


def main():
    result=dict(local=local_carry(),paper=paper(),certificate=certify())
    result['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['inputs_sha256']=hashlib.sha256((HERE/'INPUTS.json').read_bytes()).hexdigest()
    with (HERE/'source_aware_root.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k!='certificate'}|{'certificate':{k:v for k,v in result['certificate'].items()if k!='chunks'}},indent=2))


if __name__=='__main__':main()
