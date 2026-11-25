"""Exact merged-extraction tail update without a second field-word temporary."""

def h_filter(b,words,previous,short,field,*,reverse=False):
    n=len(words)
    zero=b.alloc_qubits(1)[0];b.flip_if_equal(words[2],0,target=zero)
    if previous is False:
        b.x(zero);enabled=zero
    else:
        enabled=b.alloc_qubits(1)[0]
        b.x(previous);b.x(zero);b.init_and(previous,zero,enabled);b.x(zero);b.x(previous)
    a=b.alloc_qubits(12)
    def ordinary():
        if n==4:return
        b.init_and(enabled,words[1],a)
        if not reverse:b.cx(a,words[3])
        for j in reversed(range(4,n-1)) if reverse else range(4,n-1):
            b.ixor_gf2_mul(a,words[j-1],target=words[j],field=field)
        if reverse:b.cx(a,words[3])
        b.del_and(enabled,words[1],a)
    def tail():
        control=b.alloc_qubits(1)[0]
        b.x(short);b.init_and(enabled,short,control);b.x(short)
        b.init_and(control,words[1],a)
        if n==4:b.cx(a,words[3])
        else:b.ixor_gf2_mul(a,words[-2],target=words[-1],field=field)
        b.del_and(control,words[1],a)
        b.x(short);b.del_and(enabled,short,control);b.x(short);b.free(control)
    for fn in (tail,ordinary)if reverse else(ordinary,tail):fn()
    b.free(a)
    if previous is False:b.x(zero)
    else:
        b.x(previous);b.x(zero);b.del_and(previous,zero,enabled);b.x(zero);b.x(previous);b.free(enabled)
    b.flip_if_equal(words[2],0,target=zero);b.free(zero)

def install():
    import merged_own as M
    M.h_filter=h_filter
