# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Paper phase emitter and exact Boolean/basis certificates; no KMB/native build."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys,json,math,resource
from pathlib import Path
from fractions import Fraction
from contextlib import contextmanager
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from drive_paper_ledger import PaperCounter,km
from quadratic_terms import xor_polynomial
from cyclic_phase import _erase_polynomial

CENTRES=(0,-2,-6,0,-1)
ACTIVE=(30,6,27,3,17,9,18,10,23,15,20)
# Variables are f0,f1,f2,f3,p,c, where p=f1*(f2 XOR f3), c=f1*f3.
CONTROLS=((2,4,8),(0,4,16),(0,2,4,16),(0,1,4,8),(0,1))
THRESHOLDS={
    1:(1,2,4,8,16,3,5,9,17),
    2:(2,4,8,16),
    3:(4,8,3,17),
    4:(4,8),
    5:(8,16,32,5,17),
    6:(8,16,32),
    7:(8,17),
    8:(8,),
    9:(9,10),
    10:(32,),
}


class PhaseCounter(PaperCounter):
    def __init__(self,cap):
        super().__init__(cap);self.R=0;self.T=0;self.calls=[]
    def z_pow(self,wire,halfturn):
        a=Fraction(halfturn)%2
        if not a:return
        if (a*2).denominator==1:kind='Clifford'
        elif (a*4).denominator==1:self.T+=1;kind='T'
        else:self.R+=1;kind='R'
        self.calls.append(dict(half_turns=str(a),kind=kind))


def truth(terms,value):
    return sum(int(value&t==t) for t in terms)&1


def certificates(N,m,approximate):
    checks=0
    for s in range(11):
        f=[(s>>i)&1 for i in range(4)]
        p=f[1]&(f[2]^f[3]);c=f[1]&f[3]
        a=s|(p<<4)|(c<<5)
        assert all(truth(THRESHOLDS[t],a)==int(s>=t) for t in range(1,11))
        assert all(truth(CONTROLS[j],a)==((ACTIVE[s]>>j)&1) for j in range(5))
        checks+=15
    words=[]
    for s in range(11):
        word=list(range(N))
        for stage,centre in enumerate(CENTRES):
            if ACTIVE[s]>>stage&1:
                word=[word[(centre-i)%N] for i in range(N)]
        words.append(word)
    inv0={v:i for i,v in enumerate(words[0])}
    slots=[inv0[i] for i in range(N)]
    for s in range(11):
        assert [words[s][i] for i in slots]==[(i-s)%N for i in range(N)]
    W=m-10;J=m-N-1;basischecks=0
    # Coefficient identity for each independent input bit, plus the two fixed
    # endpoints. The represented diagonal is affine in those bit indicators.
    samples=[(1<<(W-1))|1]+[(1<<(W-1))|1|(1<<i) for i in range(1,W-1)]
    for s in range(11):
        for P in samples:
            r=((P<<s)|(P>>(N-s if s else N)))&((1<<N)-1)
            actual=r
            factor=(1<<N) if approximate else (1<<N)-1
            actual+=factor*sum(((r>>j)&1)*(1<<j)*int(s>=j+1) for j in range(J+1))
            wanted=(P<<s)+(P>>(N-s if s else N)) if approximate else P<<s
            assert actual==wanted
            # First feature complement and last feature constant are exact.
            assert ((1-int(s>=1))*(r&1))==int(s==0)
            assert int(s>=J+1)*((r>>J)&1)==int(s==10)
            basischecks+=1
    return dict(boolean_checks=checks,phase_basis_checks=basischecks,
                route_classes=11,slots=slots,identity='P*2^s + floor(P/2^(N-s))' if approximate else 'P*2^s')


@contextmanager
def affine_control(b,variables,terms):
    linear=[t.bit_length()-1 for t in terms if t]
    assert linear and all(t==0 or t.bit_count()==1 for t in terms)
    pivot=variables[linear[0]]
    for i in linear[1:]:b.cx(variables[i],pivot)
    if 0 in terms:b.x(pivot)
    try:yield pivot
    finally:
        if 0 in terms:b.x(pivot)
        for i in reversed(linear[1:]):b.cx(variables[i],pivot)


@contextmanager
def threshold(b,variables,t):
    terms=THRESHOLDS[t]
    if len(variables)==5:
        terms=tuple(10 if x==32 else x for x in terms)
    if max(x.bit_count() for x in terms)<=1:
        with affine_control(b,variables,terms) as q:yield q
    else:
        q=b.alloc_qubits(1)[0]
        xor_polynomial(b,variables,q,terms)
        try:yield q
        finally:_erase_polynomial(b,q,variables,terms)


def route(b,word,variables,inverse=False):
    N=len(word)
    stages=list(range(5))
    if inverse:stages.reverse()
    for j in stages:
        with affine_control(b,variables,CONTROLS[j]) as q:
            for i in range(N):
                k=(CENTRES[j]-i)%N
                if i<k:b.cswap(q,word[i],word[k])


def feature(b,control,data,turns):
    turns=Fraction(turns)%1
    if turns==Fraction(1,2):
        b.cz(control,data)
    elif turns in (Fraction(1,4),Fraction(3,4)):
        sign=1 if turns==Fraction(1,4) else -1
        # CS = T(a) T(b) T^-1(a XOR b). No helper or measurement.
        b.z_pow(control,Fraction(sign,4));b.z_pow(data,Fraction(sign,4))
        b.cx(control,data);b.z_pow(data,Fraction(-sign,4));b.cx(control,data)
    else:
        q=b.alloc_qubits(1)[0]
        b.ccx(control,data,q);b.z_pow(q,2*turns)
        b.del_and(control,data,q);b.free(q)


def paper(cap,m,N,approximate):
    W=m-10
    if N<W:raise ValueError('Ring shorter than full endpoint word')
    cert=certificates(N,m,approximate)
    b=PhaseCounter(cap)
    flags=list(b.alloc_qubits(4));word=list(b.alloc_qubits(N))
    # 43 existing owners + two explicit constant1 wires + optional padding.
    base=45+(N-W)
    rest=list(b.alloc_qubits(base-N-4))
    p=b.alloc_qubits(1)[0]
    xor_polynomial(b,flags,p,(6,10))
    compact=cap-base<4
    c=None
    if not compact:
        c=b.alloc_qubits(1)[0]
        xor_polynomial(b,flags,c,(10,))
    variables=flags+[p]+([] if compact else [c])
    route(b,word,variables)
    slots=[word[i] for i in cert['slots']]
    factor=(1<<N) if approximate else (1<<N)-1
    for i,q in enumerate(slots):
        units=(1<<i)
        if i==0:units+=factor  # complementary first overflow feature
        b.z_pow(q,Fraction(2*units,1<<m))
    J=m-N-1
    for j in range(J+1):
        angle=Fraction(factor*(1<<j),1<<m)
        if j==0:
            with threshold(b,variables,1) as q:
                b.x(q);b.z_pow(q,-2*angle);b.x(q)
        elif j==J:
            if c is not None:
                b.z_pow(c,2*angle)  # padded/full-word top endpoint is fixed1
            elif approximate and angle==Fraction(1,2):
                b.cz(flags[1],flags[3])
            else:
                with threshold(b,variables,10) as q:b.z_pow(q,2*angle)
        else:
            with threshold(b,variables,j+1) as q:
                feature(b,q,slots[j],angle)
    route(b,word,variables,inverse=True)
    if c is not None:_erase_polynomial(b,c,flags,(10,))
    _erase_polynomial(b,p,flags,(6,10))
    frame=2  # one exact CCX endpoint frame and its inverse, no new owner
    return dict(status='SOURCE_EXPANDED_PHASE_PAPER_NOT_NATIVE',Q=cap,m=m,N=N,
        approximate_cyclic=approximate,compact_controls=compact,base_owners=base,peak=b.peak,
        routing_and_controls_Toffolis=float(b.count),endpoint_frame_Toffolis=frame,
        Toffolis=float(b.count)+frame,T=b.T,R=b.R,
        direct_E=float(b.count)+frame+b.T/4,
        data_measurements=0,threshold_repayment='All physical degree<=2 functions of flags and retained p,c; Clifford only',
        certificate={k:v for k,v in cert.items() if k!='slots'})


if __name__=='__main__':
    rows=[]
    for cap in range(48,53):
        for m in (37,38):
            for N in range(m-10,min(m-6,35)):
                for approx in (False,True):
                    try:r=paper(cap,m,N,approx)
                    except Exception as e:r=dict(Q=cap,m=m,N=N,approximate_cyclic=approx,status='PAPER_BLOCKED',reason=str(e))
                    rows.append(r)
                    if r['status']!='PAPER_BLOCKED':print(json.dumps(r))
    (HERE/'phase_ledger.json').write_text(json.dumps(dict(rows=rows),indent=2)+'\n')
