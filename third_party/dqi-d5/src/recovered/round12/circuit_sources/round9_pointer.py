# SPDX-License-Identifier: Apache-2.0
"""Independent two-event gap stack from Phuc Thai's published pointer idea.

Push: controlled swap(A,B), then XOR index+1 into A, then erase the event
flag by A==index+1. Pop is its reverse. Valid for up to two distinct events.
Three or more gaps are outside this approximation, which is measured by the
unchanged statistical DQI verifier. No worst-case decoder claim is made.
SomeJoint/Agniv Banerjee: extraction/conversion arithmetic. Manwithacat:
mask projection. Nazemtsev: extraction mask reuse. Gluzdov: stack source.
"""
from contextlib import contextmanager

def install_compact_scaling():
    """Discard inversion scaffold before multiplication; rebuild for deletion."""
    import inspect
    import compact_lifetime_kernels as K
    import jfraction_decoder as J
    if getattr(K,'_round9_compact_scaling',False):return
    code=inspect.getsource(K.scale_active_reused_mask)
    code=code.replace('inverse, scaffold = b.init_gf2_inverse_with_scaffold(pivot, field=GF)',
                      'inverse = init_compact_inverse(b, pivot, field=GF)')
    code=code.replace('b.del_gf2_inverse_with_scaffold(pivot, target=inverse,\n                                   scaffold=scaffold, field=GF)\n    b.free(inverse + scaffold)',
                      'delete_compact_inverse(b, pivot, inverse, field=GF)\n    b.free(inverse)')
    assert 'scaffold =' not in code and 'scaffold=scaffold' not in code
    exec(compile(code,'<round9-compact-scale-active>','exec'),K.__dict__)
    code=inspect.getsource(J.scale_words)
    code=code.replace('inverse, scaffold = builder.init_gf2_inverse_with_scaffold(pivot, field=GF)',
                      'inverse = init_compact_inverse(builder, pivot, field=GF)')
    code=code.replace('builder.del_gf2_inverse_with_scaffold(pivot, target=inverse,\n                                          scaffold=scaffold, field=GF)\n    builder.free(inverse + scaffold)',
                      'delete_compact_inverse(builder, pivot, inverse, field=GF)\n    builder.free(inverse)')
    assert 'scaffold =' not in code and 'scaffold=scaffold' not in code
    J.init_compact_inverse=K.init_compact_inverse;J.delete_compact_inverse=K.delete_compact_inverse
    exec(compile(code,'<round9-compact-scale-words>','exec'),J.__dict__)
    K._round9_compact_scaling=True

class GapStack:
    def __init__(self,b,*,older_width=6):
        self.b=b;self.a=b.alloc_qubits(6);self.old=b.alloc_qubits(older_width)
    def equal(self,word,index,target):
        if index+1 < (1<<len(word)):self.b.flip_if_equal(word,index+1,target=target)
        if len(self.old)==5 and word is self.a:
            for code,events in [(36,(31,33)),(37,(31,34)),(38,(32,34))]:
                if index in events:self.b.flip_if_equal(word,code,target=target)
    def _escape(self,index,flag,*,reverse=False):
        if len(self.old)!=5 or index not in (33,34):return
        b=self.b
        def mask():
            for k in (1,2,5):b.cx(flag,self.a[k])
        def equals(code,target):b.flip_if_equal(self.a,code,target=target)
        if index==33:
            if reverse:equals(36,flag)
            mask()
            if not reverse:equals(36,flag)
        elif reverse:
            equals(37,flag);equals(38,flag);equals(38,self.old[0]);mask()
            b.ccx(flag,self.old[0],self.a[1]);b.ccx(flag,self.old[0],self.a[0])
        else:
            b.ccx(flag,self.old[0],self.a[0]);b.ccx(flag,self.old[0],self.a[1]);mask()
            equals(38,self.old[0]);equals(37,flag);equals(38,flag)
    def push(self,index,flag):
        b=self.b;b.cswap(flag,self.a[:len(self.old)],self.old)
        for k in range(6):
            if (index+1)>>k&1:b.cx(flag,self.a[k])
        self.equal(self.a,index,flag)
        self._escape(index,flag)
    def pop(self,index,flag):
        b=self.b;self._escape(index,flag,reverse=True);self.equal(self.a,index,flag)
        for k in range(6):
            if (index+1)>>k&1:b.cx(flag,self.a[k])
        b.cswap(flag,self.a[:len(self.old)],self.old)
    @contextmanager
    def access(self,indices):
        b=self.b;indices=sorted(set(indices));flags=b.alloc_qubits(len(indices))
        for index,t in zip(indices,flags):
            self.equal(self.a,index,t);self.equal(self.old,index,t)
        try:yield dict(zip(indices,flags))
        finally:
            for index,t in reversed(list(zip(indices,flags))):
                self.equal(self.old,index,t);self.equal(self.a,index,t)
            b.free(flags)
    def release(self):self.b.free(self.a+self.old)

def extract(b,words,stack,*,reverse=False):
    from jfraction_gap_decoder import reciprocal_active,rotate,toggle_gap
    from compact_lifetime_kernels import scale_active_reused_mask
    for j in reversed(range(35)) if reverse else range(35):
        gap=b.alloc_qubits(1)[0]
        if reverse:stack.pop(j,gap)
        with stack.access([j-1] if j else []) as flags:
            previous=flags[j-1] if j else False;active=words[2*j:]
            if not reverse:toggle_gap(b,active,previous,gap)
            short=b.alloc_qubits(1)[0];b.cx(gap,short)
            if j:b.cx(previous,short)
            rotate(b,active,short,left=True)
            if reverse:
                reciprocal_active(b,[1]+active[1:],short,reverse=True)
                scale_active_reused_mask(b,active[0],active[1:],short,divide=False)
            else:
                scale_active_reused_mask(b,active[0],active[1:],short,divide=True)
                reciprocal_active(b,[1]+active[1:],short)
            rotate(b,active,short,left=False)
            if j:b.cx(previous,short)
            b.cx(gap,short);b.free(short)
            if reverse:toggle_gap(b,active,previous,gap)
        if not reverse:stack.push(j,gap)
        b.free(gap)

def short_value(stack,j,target):
    """XOR gap[j] XOR gap[j-1] directly, without persistent decoded flags."""
    for index in ([j-1,j] if j else [j]):
        stack.equal(stack.a,index,target);stack.equal(stack.old,index,target)

def extract_short_lifetime(b,words,stack,*,reverse=False):
    """Keep only the combined shortening predicate live through field kernels."""
    from jfraction_gap_decoder import reciprocal_active,rotate,toggle_gap
    from compact_lifetime_kernels import scale_active_reused_mask
    for j in reversed(range(35)) if reverse else range(35):
        active=words[2*j:];short=b.alloc_qubits(1)[0]
        if reverse:
            short_value(stack,j,short)
        else:
            gap=b.alloc_qubits(1)[0]
            with stack.access([j-1] if j else []) as flags:
                previous=flags[j-1] if j else False
                toggle_gap(b,active,previous,gap);b.cx(gap,short)
                if j:b.cx(previous,short)
            stack.push(j,gap);b.free(gap)
        rotate(b,active,short,left=True)
        if reverse:
            reciprocal_active(b,[1]+active[1:],short,reverse=True)
            scale_active_reused_mask(b,active[0],active[1:],short,divide=False)
        else:
            scale_active_reused_mask(b,active[0],active[1:],short,divide=True)
            reciprocal_active(b,[1]+active[1:],short)
        rotate(b,active,short,left=False)
        if reverse:
            gap=b.alloc_qubits(1)[0];stack.pop(j,gap)
            with stack.access([j-1] if j else []) as flags:
                previous=flags[j-1] if j else False
                b.cx(gap,short)
                if j:b.cx(previous,short)
                toggle_gap(b,active,previous,gap)
            b.free(gap)
        else:short_value(stack,j,short)
        b.free(short)

def convert_short_lifetime(b,words,stack,*,reverse=False):
    """Release decoded flags during the independent scale_words kernel."""
    from jfraction_decoder import conversion_layout,scale_words
    from jfraction_gap_decoder import conversion_core,rotate,toggle_header
    p,q,stages=conversion_layout(words)
    stages=[(34-i,*stage) for i,stage in enumerate(stages)]
    for j,x,y,oldp,oldq in reversed(stages) if reverse else stages:
        newp=[x]+oldq[1:];rotations=[x,y]+oldq[1:]
        if reverse:
            with stack.access([j]) as flag:rotate(b,newp,flag[j],left=True)
            scale_words(b,x,oldq[1:],divide=True)
            with stack.access([j-1,j] if j else [j]) as flag:
                pending=flag[j-1] if j else False;gap=flag[j]
                toggle_header(b,y,oldq,pending);conversion_core(b,y,oldp,oldq,pending)
                rotate(b,rotations,gap,left=False)
                if j:b.cswap(pending,x,y)
        else:
            with stack.access([j-1,j] if j else [j]) as flag:
                pending=flag[j-1] if j else False;gap=flag[j]
                if j:b.cswap(pending,x,y)
                rotate(b,rotations,gap,left=True);conversion_core(b,y,oldp,oldq,pending)
                toggle_header(b,y,oldq,pending)
            scale_words(b,x,oldq[1:],divide=False)
            with stack.access([j]) as flag:rotate(b,newp,flag[j],left=False)
    return p,q

def build_circuit(*,short_lifetime=False,older_width=6):
    from common import build
    from static_divisions import StaticArithmeticBuilder
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from compact_gap_variant import convert_compact
    from round6_dqi import lean_forney
    extract_impl=extract_short_lifetime if short_lifetime else extract
    convert_impl=convert_short_lifetime if short_lifetime else convert_compact
    class Decoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
            b=builder;b.stage_records=[];words=list(syndromes)
            outcomes=projected_record(b,syndromes,error_mbuc);stack=GapStack(b,older_width=older_width)
            self._record(b,'initialization')
            extract_impl(b,words,stack);self._record(b,'moment_to_fraction')
            # Existing conversion only accesses flags; count names its levels.
            stack.count=35
            numerator,denominator=convert_impl(b,words,stack)
            self._record(b,'fraction_to_polynomials')
            lean_forney(b,numerator,denominator,outcomes,self.field)
            self._record(b,'phase_correction')
            convert_impl(b,words,stack,reverse=True)
            self._record(b,'polynomials_to_fraction')
            extract_impl(b,words,stack,reverse=True);stack.release()
            self._record(b,'fraction_to_moments')
    b=StaticArithmeticBuilder();c=build(b,iterations=35,decoder_type=Decoder)
    return c,dict(stages=b.stage_records,algorithm=f'two-event6+{older_width}bit reversible gap stack; lean Forney; three escape codes if width5',approximation='at most two gaps; full statistical verifier required')

def classical_certificate(*,older_width=6):
    """Exhaust all legal zero/one/two-event stack patterns, independent of shots."""
    from itertools import combinations
    count=0;mask=(1<<older_width)-1
    def equal(a,j):return (a==j+1)^((older_width==5) and ((a==36 and j in (31,33)) or (a==37 and j in (31,34)) or (a==38 and j in (32,34))))
    def escape(a,old,g,j,reverse=False):
        if older_width!=5 or j not in (33,34):return a,old,g
        if j==33:
            if reverse:g^=int(a==36)
            if g:a^=38
            if not reverse:g^=int(a==36)
        elif reverse:
            g^=int(a==37)^int(a==38);old^=int(a==38)
            if g:a^=38
            if g and old&1:a^=3
        else:
            if g and old&1:a^=3
            if g:a^=38
            old^=int(a==38);g^=int(a==37)^int(a==38)
        return a,old,g
    for size in range(3):
        for events in combinations(range(35),size):
            if any(b==a+1 for a,b in zip(events,events[1:])):continue
            a=old=0
            for j in range(35):
                flag=int(j in events)
                if flag:a,old=((a&~mask)|old),a&mask;a^=j+1
                flag^=equal(a,j);a,old,flag=escape(a,old,flag,j)
                assert flag==0
            for j in range(35):assert (equal(a,j)^(old==j+1))==(j in events)
            for j in reversed(range(35)):
                a,old,flag=escape(a,old,0,j,reverse=True);flag^=equal(a,j)
                if flag:a^=j+1;a,old=((a&~mask)|old),a&mask
                assert flag==(j in events)
            assert a==old==0;count+=1
    return dict(patterns=count,excluded_patterns=[],escape_codes=[36,37,38] if older_width==5 else [],older_width=older_width,levels=35,event_cap=2,nonadjacent=True,all_pass=True)
