"""Native research prototype: three levels, nonzero ordinary chart ONLY.

Never selected by the production builder. Gap/zero inputs are unsupported;
no approximation-rate or full-decoder gain is claimed for this prototype.
"""
from matrix_pair_kernels import raw_moment,reciprocal_four
from paired_kernels import scale_unit_active

def coefficient_map(b,h,*,reverse=False):
    from jfraction_decoder import GF,add_scaled
    if reverse:
        add_scaled(b,h[1],h[2],frobenius=2)
        b.ixor_gf2_mul(h[1],h[3],target=h[2],field=GF)
        b.cx(h[1],h[3])
    else:
        b.cx(h[1],h[3]);b.ixor_gf2_mul(h[1],h[3],target=h[2],field=GF)
        add_scaled(b,h[1],h[2],frobenius=2)

def prefix_four(b,h,s,*,reverse=False):
    if reverse:
        scale_unit_active(b,h[2],[h[3]],False,divide=False)
        reciprocal_four(b,h,s)
        scale_unit_active(b,h[0],h[1:4],False,divide=False)
    else:
        scale_unit_active(b,h[0],h[1:4],False,divide=True)
        reciprocal_four(b,h,s)
        scale_unit_active(b,h[2],[h[3]],False,divide=True)

def pre(b,h,flags,*,reverse=False):
    from jfraction_decoder import GF
    def bulk():
        coefficient_map(b,h)
        for i in range(6,len(h)) if reverse else reversed(range(6,len(h))):
            b.ixor_gf2_mul(h[3],h[i-1],target=h[i],field=GF)
            b.ixor_gf2_mul(h[2],h[i-2],target=h[i],field=GF)
        coefficient_map(b,h,reverse=True)
    def fifth():
        coefficient_map(b,h);b.ixor_gf2_mul(h[3],h[4],target=h[5],field=GF);coefficient_map(b,h,reverse=True)
    def third():
        with raw_moment(b,h,*flags,3) as raw:
            coefficient_map(b,h)
            b.ixor_gf2_mul(h[2],raw,target=h[5],field=GF)
            b.ixor_gf2_mul(h[3],raw,target=h[4],field=GF)
            coefficient_map(b,h,reverse=True)
    def second():
        with raw_moment(b,h,*flags,2) as raw:
            coefficient_map(b,h);b.ixor_gf2_mul(h[2],raw,target=h[4],field=GF);coefficient_map(b,h,reverse=True)
    if reverse:second();third();fifth();bulk()
    else:bulk();fifth();third();second()

def post(b,h,*,reverse=False):
    from jfraction_decoder import GF
    coefficient_map(b,h)
    def a3():b.cx(h[3],h[5])
    def correction():
        if len(h)>6:
            b.cx(h[4],h[6]);b.cx(h[2],h[6]);b.ixor_gf2_mul(h[3],h[5],target=h[6],field=GF)
        if len(h)>7:
            b.ixor_gf2_mul(h[4],h[1],target=h[7],field=GF)
            b.ixor_gf2_mul(h[2],h[5],target=h[7],field=GF)
    if not reverse:a3();correction()
    for i in reversed(range(7,len(h))) if reverse else range(7,len(h)):
        b.ixor_gf2_mul(h[3],h[i-1],target=h[i],field=GF)
        if i>=8:b.ixor_gf2_mul(h[2],h[i-2],target=h[i],field=GF)
    if reverse:correction();a3()
    coefficient_map(b,h,reverse=True)

def triple(b,h,*,reverse=False):
    from jfraction_decoder import reciprocal
    assert len(h)>=6 and len(h)%2==0
    flags=list(b.alloc_qubits(4))
    if reverse:
        post(b,h,reverse=True)
        scale_unit_active(b,h[2],[h[4]],False,divide=False)
        scale_unit_active(b,h[0],[h[4]],False,divide=False)
        reciprocal(b,[1]+h[5:],reverse=True)
        scale_unit_active(b,h[4],h[5:],False,divide=False)
        pre(b,h,flags,reverse=True)
        prefix_four(b,h,flags[0],reverse=True)
    else:
        prefix_four(b,h,flags[0]);pre(b,h,flags)
        scale_unit_active(b,h[4],h[5:],False,divide=True)
        reciprocal(b,[1]+h[5:])
        scale_unit_active(b,h[0],[h[4]],False,divide=True)
        scale_unit_active(b,h[2],[h[4]],False,divide=True)
        post(b,h)
    for q in flags:b.free(q)
