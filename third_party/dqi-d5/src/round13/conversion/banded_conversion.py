"""Exact interpolation of the controlled one-step conversion band.

Only jfraction_gap_decoder.conversion_core is patched. Coherent pending
flags stay quantum. The original allocation/normalization contract is kept.
No downloaded source is edited; call install() after the source imports.
"""
from contextlib import contextmanager
from functools import cache

from poly_arithmetic import GF, add_scaled, product_vector
from jfraction_gap_decoder import conversion_core as ORIGINAL


def _mul_poly(a,b):
    out=[0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):out[i+j]^=GF.mul(x,y)
    return out


@cache
def plan(k):
    """k finite Lagrange columns and the monic infinity column."""
    product=[1]
    for point in range(k):product=_mul_poly(product,[point,1])
    finite=[]
    for point in range(k):
        quotient=[0]*k;quotient[-1]=product[-1]
        for i in reversed(range(1,k)):quotient[i-1]=product[i]^GF.mul(point,quotient[i])
        assert product[0]==GF.mul(point,quotient[0])
        denominator=0
        for value in reversed(quotient):denominator=GF.mul(denominator,point)^value
        inverse=GF.div(1,denominator)
        finite.append(tuple(GF.mul(inverse,x) for x in quotient))
    return tuple(finite),tuple(product[:-1])


@contextmanager
def evaluate_reverse(b,words,point):
    pivot=words[-1]
    powers=[];power=point
    for word in reversed(words[:-1]):
        powers.append((word,power))
        add_scaled(b,word,pivot,power)
        power=GF.mul(power,point)
    try:yield pivot
    finally:
        for word,coefficient in reversed(powers):add_scaled(b,word,pivot,coefficient)


def controlled_vector(b,control,source,outputs,coefficients):
    active=[i for i,c in enumerate(coefficients) if c]
    if not active:return
    pivot=active[0];weight=coefficients[pivot];out=outputs[pivot]
    for j in active[1:]:add_scaled(b,out,outputs[j],GF.div(coefficients[j],weight))
    b.gf2_idiv(weight,target=out,field=GF)
    b.gf2_iadd(source,target=out,control=control,field=GF)
    b.gf2_imul(weight,target=out,field=GF)
    for j in reversed(active[1:]):add_scaled(b,out,outputs[j],GF.div(coefficients[j],weight))


def conversion_core(b,y,old_p,old_q,pending):
    k=len(old_p)
    if pending is False or k<=2:return ORIGINAL(b,y,old_p,old_q,pending)
    assert len(old_q)==k+1 and old_q[0]==1
    mu=b.alloc_qubits(12)
    b.x(pending);b.init_and(pending,y,mu);b.x(pending);b.cx(pending,mu[0])
    # pending now temporarily holds b=1-original_pending.
    b.x(pending)
    outputs=list(reversed(old_p));qtail=old_q[1:]
    finite,infinity=plan(k)
    for point,weights in enumerate(finite):
        if point:b.gf2_iadd(point,target=mu,control=pending,field=GF)
        with evaluate_reverse(b,qtail,point) as value:
            product_vector(b,mu,value,outputs,weights)
        if point:b.gf2_iadd(point,target=mu,control=pending,field=GF)
    controlled_vector(b,pending,qtail[0],outputs,infinity)
    b.x(pending)
    b.cx(pending,mu[0]);b.x(pending);b.del_and(pending,y,mu);b.x(pending);b.free(mu)


def install():
    import jfraction_gap_decoder
    jfraction_gap_decoder.conversion_core=conversion_core


def uninstall():
    import jfraction_gap_decoder
    jfraction_gap_decoder.conversion_core=ORIGINAL
