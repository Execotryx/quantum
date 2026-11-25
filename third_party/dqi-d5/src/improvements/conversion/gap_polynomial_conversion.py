"""Replace long coherent gap rotations with a degree-two interpolation band.

Exact for arbitrary conversion words and all pending/gap bit combinations.
Install after the round13 scalar/quotient/banded patches.
"""
from poly_arithmetic import GF,add_scaled,product_vector
from banded_conversion import plan,evaluate_reverse,controlled_vector


def mask_mu(b,y,q0,pending,gap,gb):
    mu=b.alloc_qubits(12)
    if pending is False:
        b.cx(y,mu)
    else:
        b.x(pending);b.init_and(pending,y,mu);b.x(pending);b.cx(pending,mu[0])
    # mu = pending + (1-pending)*y + (1-pending)*gap*(y+q0)
    b.cx(q0,y);b.gf2_iadd(y,target=mu,control=gb,field=GF);b.cx(q0,y)
    return mu


def clear_mu(b,y,q0,pending,gap,gb,mu):
    measured=b.alloc_bits(12);b.hmr(mu,measured)
    if pending is False:
        b.cz(measured,y)
    else:
        b.x(pending);b.ccz(measured,pending,y);b.x(pending);b.cz(measured[0],pending)
    b.ccz(measured,gb,y);b.ccz(measured,gb,q0)
    b.free(measured);b.free(mu)


def core(b,y,p,q,pending,gap,gb):
    k=len(p);assert k>=2 and len(q)==k
    mu=mask_mu(b,y,q[0],pending,gap,gb)
    gmu=b.alloc_qubits(12);b.init_and(gap,mu,gmu)
    outputs=list(reversed(p));finite,infinity=plan(k+1)
    for point,coefficients in enumerate(finite):
        # A(a)=(mu+b*a)*(1+gap+gap*a), b=1-pending.
        add_scaled(b,gmu,mu,1^point)
        if pending is False:
            b.gf2_iadd(point,target=mu,field=GF)
        else:
            b.x(pending);b.gf2_iadd(point,target=mu,control=pending,field=GF);b.x(pending)
        b.gf2_iadd(point^GF.mul(point,point),target=mu,control=gb,field=GF)
        with evaluate_reverse(b,q,point)as value:
            product_vector(b,mu,value,outputs,coefficients[:k])
        b.gf2_iadd(point^GF.mul(point,point),target=mu,control=gb,field=GF)
        if pending is False:
            b.gf2_iadd(point,target=mu,field=GF)
        else:
            b.x(pending);b.gf2_iadd(point,target=mu,control=pending,field=GF);b.x(pending)
        add_scaled(b,gmu,mu,1^point)
    # Leading coefficient of A*R is gb*q0. Keep only the low k columns.
    controlled_vector(b,gb,q[0],outputs,infinity[:k])
    # The cycled-in tail y contributes gap*y*(mu+b*z).
    b.ixor_gf2_mul(gmu,y,target=outputs[0],field=GF)
    b.gf2_iadd(y,target=outputs[1],control=gb,field=GF)
    b.del_and(gap,mu,gmu);b.free(gmu)
    clear_mu(b,y,q[0],pending,gap,gb,mu)


def header(b,y,q,pending,gap,gb):
    # Ordinary branch: y += b*q0. Gap branch: q0 += b*q1.
    if pending is False:
        b.x(gap);b.gf2_iadd(q[0],target=y,control=gap,field=GF);b.x(gap)
    else:
        b.x(pending);b.cx(gb,pending)
        b.gf2_iadd(q[0],target=y,control=pending,field=GF)
        b.cx(gb,pending);b.x(pending)
    b.gf2_iadd(q[1],target=q[0],control=gb,field=GF)


def direct_stage(b,scaler,x,y,p,q,pending,gap,*,reverse=False):
    from jfraction_decoder import scale_words
    assert len(q)==len(p) and len(p)>=2
    gb=gap
    if pending is not False:
        gb=b.alloc_qubits(1)[0];b.x(pending);b.init_and(pending,gap,gb);b.x(pending)
    if reverse:
        b.cswap(gap,x,q[0])
        scale_words(scaler,x,q,divide=True)
        b.cswap(gap,y,q[0])
        header(b,y,q,pending,gap,gb)
        core(b,y,p,q,pending,gap,gb)
        b.cswap(gap,x,y)
        if pending is not False:b.cswap(pending,x,y)
    else:
        if pending is not False:b.cswap(pending,x,y)
        b.cswap(gap,x,y)
        core(b,y,p,q,pending,gap,gb)
        header(b,y,q,pending,gap,gb)
        b.cswap(gap,y,q[0])
        scale_words(scaler,x,q,divide=False)
        b.cswap(gap,x,q[0])
    if pending is not False:
        b.x(pending);b.del_and(pending,gap,gb);b.x(pending);b.free(gb)


def original_stage(b,scaler,x,y,p,oldq,pending,gap,*,reverse=False):
    from jfraction_decoder import scale_words
    from jfraction_gap_decoder import conversion_core,rotate,toggle_header
    q=oldq[1:];newp=[x]+q;rotations=[x,y]+q
    if reverse:
        rotate(b,newp,gap,left=True);scale_words(scaler,x,q,divide=True);toggle_header(b,y,oldq,pending)
    else:
        if pending is not False:b.cswap(pending,x,y)
        rotate(b,rotations,gap,left=True)
    conversion_core(b,y,p,oldq,pending)
    if reverse:
        rotate(b,rotations,gap,left=False)
        if pending is not False:b.cswap(pending,x,y)
    else:
        toggle_header(b,y,oldq,pending);scale_words(scaler,x,q,divide=False);rotate(b,newp,gap,left=False)


def convert_pointers(builder,words,bank,*,reverse=False,release_inverse=False):
    from jfraction_decoder import conversion_layout
    from merge_kernels import scale_builder
    b=builder;scaler=scale_builder(b,release_inverse)
    p,q,stages=conversion_layout(words);stages=[(bank.count-1-i,*s)for i,s in enumerate(stages)]
    for j,x,y,oldp,oldq in reversed(stages)if reverse else stages:
        pending=bank.read(j-1)if j else False;gap=bank.read(j)
        if len(oldp)>=8:
            direct_stage(b,scaler,x,y,oldp,oldq[1:],pending,gap,reverse=reverse)
        else:
            original_stage(b,scaler,x,y,oldp,oldq,pending,gap,reverse=reverse)
        bank.unread(j,gap)
        if j:bank.unread(j-1,pending)
    return p,q


def install():
    import merge_kernels
    merge_kernels.convert_pointers=convert_pointers
