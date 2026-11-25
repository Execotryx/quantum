# SPDX-License-Identifier: Apache-2.0
"""Independent merged two-slot extraction from Ahmed/Phuc's published identities.

SomeJoint: arithmetic/gap chart. Ahmed Berat Ozer and Phuc Thai: published
merged identities. Gluzdov: this source implementation. No missing archive or
public binary is used. Degenerate zero-pivot extensions remain approximate;
the unchanged official full verifier, not the algebra fixture, decides score.
"""
from contextlib import contextmanager
from pathlib import Path
import json

def square(b,word,field,*,reverse=False):
    n=len(word);rows=[[field.pow(1<<c,2)>>r&1 for c in range(n)] for r in range(n)];ops=[]
    for k in range(n):
        p=next(i for i in range(k,n) if rows[i][k])
        if p!=k:rows[k],rows[p]=rows[p],rows[k];ops.append(('swap',k,p))
        for r in range(n):
            if r!=k and rows[r][k]:rows[r]=[x^y for x,y in zip(rows[r],rows[k])];ops.append(('cx',k,r))
    assert rows==[[int(r==c) for c in range(n)] for r in range(n)]
    for op,a,c in ops if reverse else reversed(ops):getattr(b,op)(word[a],word[c])

@contextmanager
def masked_a(b,word,previous):
    if previous is False:
        yield word;return
    reg=b.alloc_qubits(12);b.x(previous);b.init_and(previous,word,reg);b.x(previous)
    yield reg
    b.x(previous);b.del_and(previous,word,reg);b.x(previous);b.free(reg)

@contextmanager
def post_a(b,word,pivot,previous):
    # When the next chart terminates (c'=0), its implicit unit-series
    # extension must not acquire the geometric1/(1+a*x) tail.
    zero=b.alloc_qubits(1)[0];b.flip_if_equal(pivot,0,target=zero);reg=b.alloc_qubits(12)
    def init_control():
        if previous is False:b.x(zero);return zero,None
        enabled=b.alloc_qubits(1)[0];b.x(previous);b.x(zero);b.init_and(previous,zero,enabled);b.x(zero);b.x(previous)
        return enabled,enabled
    def clear_control(enabled,allocated):
        if allocated is None:b.x(zero);return
        b.x(previous);b.x(zero);b.del_and(previous,zero,enabled);b.x(zero);b.x(previous);b.free(enabled)
    enabled,allocated=init_control();b.init_and(enabled,word,reg);clear_control(enabled,allocated)
    yield reg
    enabled,allocated=init_control();b.del_and(enabled,word,reg);clear_control(enabled,allocated);b.free(reg)
    b.flip_if_equal(pivot,0,target=zero);b.free(zero)

def scale_one(b,pivot,word,previous,field,*,divide):
    from jfraction_decoder import scale_words
    if previous is False:return scale_words(b,pivot,[word],divide=divide)
    if getattr(b,'compact_first_division',False):return scale_one_compact(b,pivot,word,previous,field,divide=divide)
    zero=b.alloc_qubits(1)[0];b.flip_if_equal(pivot,0,target=zero);b.cx(zero,pivot[0])
    reg=b.alloc_qubits(12)
    def init(inverse):
        b.x(previous)
        if inverse:_,scaf=b.init_controlled_inverse(pivot,previous,target=reg)
        else:b.init_and(previous,pivot,reg);scaf=None
        b.x(previous);b.cx(previous,reg[0]);return scaf
    def delete(inverse,scaf):
        b.cx(previous,reg[0]);b.x(previous)
        if inverse:b.del_controlled_inverse(pivot,previous,target=reg,scaffold=scaf);b.free(scaf)
        else:b.del_and(previous,pivot,reg)
        b.x(previous)
    scaf=init(divide);temp=b.alloc_qubits(12);b.ixor_gf2_mul(word,reg,target=temp,field=field);b.swap(word,temp);delete(divide,scaf)
    scaf=init(not divide);b.del_gf2_mul(word,reg,target=temp,field=field);delete(not divide,scaf)
    b.free(temp);b.free(reg);b.cx(zero,pivot[0]);b.flip_if_equal(pivot,0,target=zero);b.free(zero)

def discard_controlled_scaffold(b,pivot,control,scaffold):
    basis=b.bases[12];native=b.native;basis.change_basis(native,pivot,to_tower=True)
    a,c=pivot[:6],pivot[6:];norm,recip,chain=scaffold[:6],scaffold[6:12],scaffold[12:]
    b.del_controlled_inverse(norm,control,target=recip,scaffold=chain);b.free(recip+chain)
    basis.add_linear(native,a,norm,basis.square_columns);basis.add_linear(native,c,norm,basis.delta_square_columns)
    native.del_gf2_mul(a,c,target=norm,field=basis.inner);b.free(norm);basis.change_basis(native,pivot,to_tower=False)

def recreate_controlled_scaffold(b,pivot,control):
    basis=b.bases[12];native=b.native;basis.change_basis(native,pivot,to_tower=True);a,c=pivot[:6],pivot[6:]
    norm=b.init_gf2_mul(a,c,field=basis.inner);basis.add_linear(native,a,norm,basis.square_columns);basis.add_linear(native,c,norm,basis.delta_square_columns)
    recip,chain=b.init_controlled_inverse(norm,control);basis.change_basis(native,pivot,to_tower=False)
    return norm+recip+chain

def scale_one_compact(b,pivot,word,previous,field,*,divide):
    zero=b.alloc_qubits(1)[0];b.flip_if_equal(pivot,0,target=zero);b.cx(zero,pivot[0])
    inv=b.alloc_qubits(12);b.x(previous);_,scaf=b.init_controlled_inverse(pivot,previous,target=inv)
    discard_controlled_scaffold(b,pivot,previous,scaf);b.x(previous);b.cx(previous,inv[0])
    ordinary=b.alloc_qubits(12);b.x(previous);b.init_and(previous,pivot,ordinary);b.x(previous);b.cx(previous,ordinary[0])
    factor,undo=(inv,ordinary) if divide else (ordinary,inv)
    temporary=b.alloc_qubits(12);b.ixor_gf2_mul(word,factor,target=temporary,field=field);b.swap(word,temporary)
    b.del_gf2_mul(word,undo,target=temporary,field=field);b.free(temporary)
    b.cx(previous,ordinary[0]);b.x(previous);b.del_and(previous,pivot,ordinary);b.x(previous);b.free(ordinary)
    b.cx(previous,inv[0]);b.x(previous);scaf=recreate_controlled_scaffold(b,pivot,previous)
    b.del_controlled_inverse(pivot,previous,target=inv,scaffold=scaf);b.free(scaf);b.x(previous);b.free(inv)
    b.cx(zero,pivot[0]);b.flip_if_equal(pivot,0,target=zero);b.free(zero)

def product_update(b,a,c,target,protected,field):
    if protected is False:b.ixor_gf2_mul(a,c,target=target,field=field);return
    temp=b.init_gf2_mul(a,c,field=field);b.x(protected);b.gf2_iadd(temp,target=target,control=protected,field=field);b.x(protected)
    b.del_gf2_mul(a,c,target=temp,field=field);b.free(temp)

def e_filter(b,words,previous,first,field,*,reverse=False):
    n=len(words)
    with masked_a(b,words[1],previous) as a:
        def quadratic():
            square(b,a,field);b.ixor_gf2_mul(words[0],a,target=words[2],field=field);square(b,a,field,reverse=True)
        if reverse:quadratic()
        for j in range(3,n) if reverse else reversed(range(3,n)):
            product_update(b,a,words[j-1],words[j],first if j==n-1 else False,field)
        if not reverse:quadratic()

def inject(b,words,previous,second,field):
    n=len(words);c=words[2]
    def add(index,control=True):
        if index>=n or(index==5 and n==6):return
        if control is True:b.cx(c,words[index])
        else:b.gf2_iadd(c,target=words[index],control=control,field=field)
    add(4)
    if previous is not False:add(3,previous);add(4,previous)
    add(4,second);add(5,second)
    if previous is not False:
        both=b.alloc_qubits(1)[0];b.init_and(previous,second,both);add(3,both);add(5,both);b.del_and(previous,second,both);b.free(both)

def h_filter(b,words,previous,short,field,*,reverse=False):
    n=len(words)
    with post_a(b,words[1],words[2],previous) as a:
        def first():
            if n==4:b.x(short);b.gf2_iadd(a,target=words[3],control=short,field=field);b.x(short)
            else:b.cx(a,words[3])
        if not reverse:first()
        for j in reversed(range(4,n)) if reverse else range(4,n):
            product_update(b,a,words[j-1],words[j],short if j==n-1 else False,field)
        if reverse:first()

def pair(b,words,stack,j,field,*,reverse=False):
    from jfraction_gap_decoder import rotate,toggle_gap,reciprocal_active
    from compact_lifetime_kernels import scale_active_reused_mask
    if reverse:
        first,second=b.alloc_qubits(2);short=b.alloc_qubits(1)[0]
        stack.pop(j+1,second);stack.pop(j,first);b.cx(first,short);b.cx(second,short)
        with stack.access([j-1] if j else []) as flag:
            p=flag[j-1] if j else False
            rotate(b,words,first,left=True)
            if p is not False:b.cswap(p,words[0],words[1])
            rotate(b,words[2:],second,left=True)
            h_filter(b,words,p,short,field,reverse=True);inject(b,words,p,second,field)
        scale_one(b,words[0],words[2],False,field,divide=False)
        reciprocal_active(b,[1]+list(words[3:]),short,reverse=True)
        scale_active_reused_mask(b,words[2],words[3:],short,divide=False)
        rotate(b,words[2:],second,left=False)
        b.cx(first,short);b.cx(second,short);b.free(short)
        toggle_gap(b,words[2:],first,second)
        b.free(second);second=None
        with stack.access([j-1] if j else []) as flag:
            p=flag[j-1] if j else False
            e_filter(b,words,p,first,field,reverse=True);scale_one(b,words[0],words[1],p,field,divide=False)
            if p is not False:b.cswap(p,words[0],words[1])
            rotate(b,words,first,left=False);toggle_gap(b,words,p,first)
    else:
        first=b.alloc_qubits(1)[0]
        with stack.access([j-1] if j else []) as flag:
            p=flag[j-1] if j else False;toggle_gap(b,words,p,first);rotate(b,words,first,left=True)
            if p is not False:b.cswap(p,words[0],words[1])
            scale_one(b,words[0],words[1],p,field,divide=True);e_filter(b,words,p,first,field)
        second=b.alloc_qubits(1)[0];short=b.alloc_qubits(1)[0]
        toggle_gap(b,words[2:],first,second);b.cx(first,short);b.cx(second,short);rotate(b,words[2:],second,left=True)
        scale_active_reused_mask(b,words[2],words[3:],short,divide=True)
        reciprocal_active(b,[1]+list(words[3:]),short)
        scale_one(b,words[0],words[2],False,field,divide=True)
        with stack.access([j-1] if j else []) as flag:
            p=flag[j-1] if j else False;inject(b,words,p,second,field);h_filter(b,words,p,short,field)
            rotate(b,words[2:],second,left=False)
            if p is not False:b.cswap(p,words[0],words[1])
            rotate(b,words,first,left=False)
        b.cx(first,short);b.cx(second,short);b.free(short);stack.push(j,first);stack.push(j+1,second)
    b.free(first)
    if second is not None:b.free(second)

def single(b,words,stack,j,field,*,reverse=False):
    from jfraction_gap_decoder import rotate,toggle_gap,reciprocal_active
    from compact_lifetime_kernels import scale_active_reused_mask
    gap=b.alloc_qubits(1)[0]
    if reverse:stack.pop(j,gap)
    with stack.access([j-1]) as flags:
        p=flags[j-1]
        if not reverse:toggle_gap(b,words,p,gap)
        short=b.alloc_qubits(1)[0];b.cx(gap,short);b.cx(p,short);rotate(b,words,short,left=True)
        if reverse:reciprocal_active(b,[1]+list(words[1:]),short,reverse=True);scale_active_reused_mask(b,words[0],words[1:],short,divide=False)
        else:scale_active_reused_mask(b,words[0],words[1:],short,divide=True);reciprocal_active(b,[1]+list(words[1:]),short)
        rotate(b,words,short,left=False);b.cx(p,short);b.cx(gap,short);b.free(short)
        if reverse:toggle_gap(b,words,p,gap)
    if not reverse:stack.push(j,gap)
    b.free(gap)

def extract(b,words,stack,field,*,reverse=False):
    if reverse:single(b,words[68:],stack,34,field,reverse=True)
    for j in reversed(range(0,34,2)) if reverse else range(0,34,2):pair(b,words[2*j:],stack,j,field,reverse=reverse)
    if not reverse:single(b,words[68:],stack,34,field)

def build_circuit(*,compact_division=False):
    from common import build
    from static_divisions import StaticArithmeticBuilder
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from round9_pointer import GapStack,convert_short_lifetime,install_compact_scaling
    from round6_dqi import lean_forney
    install_compact_scaling()
    class Decoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
            b=builder;b.stage_records=[];words=list(syndromes);outcomes=projected_record(b,syndromes,error_mbuc);stack=GapStack(b,older_width=5)
            self._record(b,'initialization');extract(b,words,stack,self.field);self._record(b,'moment_to_fraction')
            numerator,denominator=convert_short_lifetime(b,words,stack);self._record(b,'fraction_to_polynomials')
            lean_forney(b,numerator,denominator,outcomes,self.field);self._record(b,'phase_correction')
            convert_short_lifetime(b,words,stack,reverse=True);self._record(b,'polynomials_to_fraction')
            extract(b,words,stack,self.field,reverse=True);stack.release();self._record(b,'fraction_to_moments')
    b=StaticArithmeticBuilder();b.compact_first_division=compact_division;c=build(b,iterations=35,decoder_type=Decoder)
    return c,dict(stages=b.stage_records,method='own merged identity implementation; zero-pivot branches approximate')

