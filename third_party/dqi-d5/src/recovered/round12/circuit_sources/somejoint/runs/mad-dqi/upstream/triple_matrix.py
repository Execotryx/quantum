"""All-chart triple prototype with explicit polynomial coefficients.

Research path; high-Q scratch is deliberately measured before integration.
No native resource estimate is presented as a full official verification.
"""
from contextlib import contextmanager
from paired_kernels import short,single_step,scale_unit_active

def prefix(b,h,bank,j,*,reverse=False):
    for k in reversed(range(3)) if reverse else range(3):single_step(b,h[2*k:6],bank,j+k,reverse=reverse)

def pivot_zeros(b,h,shorts):
    zeros=b.alloc_qubits(3)
    for i,s in enumerate(shorts):
        b.cswap(s,h[2*i],h[2*i+1]);b.flip_if_equal(h[2*i],0,target=zeros[i]);b.cswap(s,h[2*i],h[2*i+1])
    return zeros

def clear_zeros(b,h,shorts,zeros):
    for i,s in enumerate(shorts):
        b.cswap(s,h[2*i],h[2*i+1]);b.flip_if_equal(h[2*i],0,target=zeros[i]);b.cswap(s,h[2*i],h[2*i+1])
    b.free(zeros)

@contextmanager
def conjunction(b,base,bits):
    current=base;chain=[]
    for bit in bits:
        q=b.alloc_qubits(1)[0];b.init_and(current,bit,q);chain.append((current,bit,q));current=q
    try:yield current
    finally:
        for a,c,q in reversed(chain):b.del_and(a,c,q);b.free(q)

def emit(b,target,control,*,source=None,pair=None,bits=()):
    from jfraction_decoder import GF
    with conjunction(b,control,bits) as flag:
        if pair is not None:b.ixor_gf2_mul(pair[0],pair[1],target=target,field=GF,control=flag)
        elif source is not None:b.gf2_iadd(source,target=target,field=GF,control=flag)
        elif len(target)==1:b.cx(flag,target[0])
        else:b.cx(flag,target[0])

@contextmanager
def chart(b,shorts,code):
    from common import km
    flag=b.alloc_qubits(1)[0];b.flip_if_equal(km.array(shorts),code,target=flag)
    try:yield flag
    finally:b.flip_if_equal(km.array(shorts),code,target=flag);b.free(flag)

def coefficients(b,h,shorts,zeros,C,C4):
    """XOR the exact coefficient table; may be called again to uncompute."""
    # short ordering is little endian for the 3-bit comparison.
    z2,z3=zeros[1],zeros[2]
    for pattern in (0,1,3,4,5,6,7):
        s,t,u=(pattern>>2)&1,(pattern>>1)&1,pattern&1
        code=s|(t<<1)|(u<<2)
        with chart(b,shorts,code) as flag:
            E=lambda k,**kw:emit(b,C[k-1],flag,**kw)
            if pattern in (0,1):
                E(1,source=h[1]);E(1,source=h[3]);E(2,pair=(h[1],h[3]));E(2,source=h[2])
                if pattern==0:
                    E(2,bits=(z3,));E(3,source=h[1],bits=(z3,));emit(b,C4,flag,bits=(z2,z3))
            elif pattern==3:
                E(1,source=h[1]);E(1,source=h[4]);E(2,pair=(h[1],h[4]));E(2,bits=(z3,))
                E(3,source=h[3]);E(3,source=h[1],bits=(z3,))
            elif pattern in (4,5):
                E(1,source=h[2]);E(1,source=h[3])
                if pattern==4:E(2,bits=(z3,));E(3,bits=(z2,z3))
            elif pattern==6:
                E(1,source=h[2]);E(1,bits=(z3,));E(2,source=h[3]);E(2,source=h[2],bits=(z3,));E(3,bits=(z2,z3))
            else:
                E(1,source=h[2]);E(1,source=h[4]);E(2,source=h[3]);E(2,bits=(z3,))

def pre_body(b,h,C,C4,*,reverse=False):
    from jfraction_decoder import GF
    for i in range(6,len(h)) if reverse else reversed(range(6,len(h))):
        for k in (1,2,3):b.ixor_gf2_mul(C[k-1],h[i-k],target=h[i],field=GF)
        b.gf2_iadd(h[i-4],target=h[i],field=GF,control=C4[0])

def H1_mix(b,h,shorts,zeros,C):
    from jfraction_decoder import GF
    s,t,u=shorts;z3=zeros[2]
    b.x(u);b.gf2_iadd(C[0],target=h[5],field=GF,control=u)
    with conjunction(b,t,(u,)) as flag:
        b.gf2_iadd(h[4],target=h[5],field=GF,control=flag);b.ccx(flag,z3,h[5][0])
    b.x(u)

def kernel(b,h,shorts,zeros,C,*,reverse=False):
    from jfraction_gap_decoder import rotate
    from merge_kernels import reciprocal_early
    H1_mix(b,h,shorts,zeros,C)
    for i,s in enumerate(shorts):b.cswap(s,h[2*i],h[2*i+1]);b.cx(zeros[i],h[2*i][0])
    scale_unit_active(b,h[0],[h[4]],False,divide=False)
    scale_unit_active(b,h[2],[h[4]],False,divide=False)
    if not reverse:scale_unit_active(b,h[4],h[6:],False,divide=True)
    rotate(b,h[5:],shorts[2],left=True)
    reciprocal_early(b,[1]+h[5:],shorts[2],reverse=reverse)
    rotate(b,h[5:],shorts[2],left=False)
    if reverse:scale_unit_active(b,h[4],h[6:],False,divide=False)
    scale_unit_active(b,h[2],[h[4]],False,divide=True)
    scale_unit_active(b,h[0],[h[4]],False,divide=True)
    for i in reversed(range(3)):
        s=shorts[i];b.cx(zeros[i],h[2*i][0]);b.cswap(s,h[2*i],h[2*i+1])
    H1_mix(b,h,shorts,zeros,C)

def correction(b,h,shorts,zeros,C,C4):
    from jfraction_decoder import GF
    u=shorts[2];body=h[6:]
    # Cbar and (1+a3*x)*Cbar contributions after deflation.
    for last_short in (0,1):
        if not last_short:b.x(u)
        d=2-last_short
        for k in (1,2,3,4):
            i=k-d
            if not 0<=i<len(body):continue
            if k<4:b.gf2_iadd(C[k-1],target=body[i],field=GF,control=u)
            else:b.ccx(u,C4[0],body[i][0])
        if not last_short:
            for k in (1,2,3,4):
                i=k-1
                if i>=len(body):continue
                if k<4:b.ixor_gf2_mul(h[5],C[k-1],target=body[i],field=GF,control=u)
                else:
                    with conjunction(b,u,(C4[0],)) as flag:b.gf2_iadd(h[5],target=body[i],field=GF,control=flag)
            b.x(u)
    # cs3*C21 / x^(2-2*s2), emitted directly, no second polynomial bank.
    for pattern in (0,1,3,4,5,6,7):
        s,t,last=(pattern>>2)&1,(pattern>>1)&1,pattern&1
        with chart(b,shorts,s|(t<<1)|(last<<2)) as flag:
            pivot=h[4+last];b.cx(zeros[2],pivot[0])
            terms=[(2-t,None,())]
            if not s:terms.append((3-t,h[1],()))
            if t and s:terms.append((3-s,h[2],())) # h2=0 on the s=0,t=1 chart
            terms.append((4-s,None,(zeros[1],)))
            for power,source,bits in terms:
                i=power-(2-2*last)
                if not 0<=i<len(body):continue
                if source is None:emit(b,body[i],flag,source=pivot,bits=bits)
                else:emit(b,body[i],flag,pair=(pivot,source),bits=bits)
            b.cx(zeros[2],pivot[0])

def post_body(b,h,shorts,zeros,C,C4,*,reverse=False):
    from jfraction_decoder import GF
    if not reverse:correction(b,h,shorts,zeros,C,C4)
    for i in reversed(range(7,len(h))) if reverse else range(7,len(h)):
        for k in (1,2,3):
            if i-k>=6:b.ixor_gf2_mul(C[k-1],h[i-k],target=h[i],field=GF)
        if i>=10:b.gf2_iadd(h[i-4],target=h[i],field=GF,control=C4[0])
    if reverse:correction(b,h,shorts,zeros,C,C4)

def triple_matrix(b,h,bank,j,*,reverse=False):
    assert len(h)>=8 and len(h)%2==0
    if not reverse:prefix(b,h,bank,j)
    with short(b,bank,j) as s,short(b,bank,j+1) as t,short(b,bank,j+2) as u:
        shorts=(s,t,u);zeros=pivot_zeros(b,h,shorts)
        C=[b.alloc_qubits(12) for _ in range(3)];C4=b.alloc_qubits(1)
        coefficients(b,h,shorts,zeros,C,C4)
        if reverse:
            post_body(b,h,shorts,zeros,C,C4,reverse=True);kernel(b,h,shorts,zeros,C,reverse=True)
            prefix(b,h,bank,j,reverse=True);pre_body(b,h,C,C4,reverse=True);prefix(b,h,bank,j)
        else:
            prefix(b,h,bank,j,reverse=True);pre_body(b,h,C,C4);prefix(b,h,bank,j)
            kernel(b,h,shorts,zeros,C);post_body(b,h,shorts,zeros,C,C4)
        coefficients(b,h,shorts,zeros,C,C4)
        for word in C:b.free(word)
        b.free(C4);clear_zeros(b,h,shorts,zeros)
    if reverse:prefix(b,h,bank,j,reverse=True)


def extract_mixed(b,words,bank,*,reverse=False,triple_threshold=34):
    from matrix_pair_kernels import fused_matrix_pair_step
    from paired_kernels import pair_step
    stages=[];j=0
    while j<bank.count:
        n=len(words)-2*j
        kind='triple' if n>=triple_threshold else 'matrix' if n>=18 else 'pair' if n>=14 else 'single'
        stages.append((j,kind));j+=3 if kind=='triple' else 1 if kind=='single' else 2
    for j,kind in reversed(stages) if reverse else stages:
        fn=triple_matrix if kind=='triple' else fused_matrix_pair_step if kind=='matrix' else pair_step if kind=='pair' else single_step
        fn(b,words[2*j:],bank,j,reverse=reverse)
