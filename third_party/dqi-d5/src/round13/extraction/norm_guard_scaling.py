"""Zero-safe scalar caches guarded on the existing six-bit norm.

Derived from the retrieved Apache-2.0 Round12 norm_recycle_inverse.py,
smallspace_inverse.py, and compact_lifetime_kernels.py. Their arithmetic
and HMR corrections are preserved; the two zero tests use the live norm.
"""


def _unwrap(b):
    while hasattr(b,"builder"):b=b.builder
    return b


def init_guarded_inverse(b,source,*,field):
    """Return (reciprocal, zero_flag), with source/reciprocal zero mapped to1.

    The source is temporarily toggled at zero and must be restored through
    clear_guarded_inverse. Source and reciprocal otherwise retain the
    standard polynomial basis throughout the caller's cache body.
    """
    from norm_recycle_inverse import inplace_inverse6
    b=_unwrap(b)
    basis=b.bases[12];native=b.native
    assert len(source)==12 and field.modulus==basis.outer.modulus
    zero=b.alloc_qubits(1)[0]
    basis.change_basis(native,source,to_tower=True)
    a,c=source[:6],source[6:]
    norm=b.init_gf2_mul(a,c,field=basis.inner)
    basis.add_linear(native,a,norm,basis.square_columns)
    basis.add_linear(native,c,norm,basis.delta_square_columns)
    b.flip_if_equal(norm,0,target=zero)
    inplace_inverse6(b,norm)
    out=b.alloc_qubits(12)
    b.init_gf2_mul(a,norm,target=out[:6],field=basis.inner)
    b.init_gf2_mul(c,norm,target=out[6:],field=basis.inner)
    native.cx(out[6:],out[:6])
    basis.add_linear(native,out[:6],norm,basis.square_columns)
    basis.add_linear(native,out[6:],norm,basis.delta_square_columns)
    b.del_gf2_mul(out[:6],out[6:],target=norm,field=basis.inner)
    native.free(norm)
    basis.change_basis(native,out,to_tower=False)
    basis.change_basis(native,source,to_tower=False)
    b.cx(zero,source[0]);b.cx(zero,out[0])
    return out,zero


def clear_guarded_inverse(b,source,target,zero,*,field):
    """Erase reciprocal and zero flag, restoring the source's original value.

    target is zero on return but remains allocated, matching the incumbent
    clear_inverse_hmr API; zero_flag is freed here.
    """
    b=_unwrap(b)
    n=len(source);h=n//2;basis=b.bases[n]
    assert n==12 and field.modulus==basis.outer.modulus
    b.cx(zero,target[0]);b.cx(zero,source[0])
    measured=b.alloc_bits(n)
    b.hmr(target,measured)
    low,high=b.alloc_bits(h),b.alloc_bits(h)
    b.bit_store(low,False);b.bit_store(high,False)
    for i in range(h):
        for j in range(n):
            if basis.columns[i]>>j&1:b.cx(measured[j],low[i])
            if basis.columns[h+i]>>j&1:b.cx(measured[j],high[i])
    basis.change_basis(b,source,to_tower=True)
    a,c=source[:h],source[h:]
    norm,reciprocal=target[:h],target[h:]
    b.init_gf2_mul(a,c,target=norm,field=basis.inner)
    basis.add_linear(b,a,norm,basis.square_columns)
    basis.add_linear(b,c,norm,basis.delta_square_columns)
    b.flip_if_equal(norm,0,target=zero);b.free(zero)
    _,chain=b.init_gf2_inverse_with_scaffold(norm,target=reciprocal,field=basis.inner)
    b.gf2_phase_by_product(a,reciprocal,mask=low,field=basis.inner)
    b.cx(high,low)
    b.gf2_phase_by_product(c,reciprocal,mask=low,field=basis.inner)
    b.del_gf2_inverse_with_scaffold(norm,target=reciprocal,scaffold=chain,field=basis.inner)
    b.free(chain)
    basis.add_linear(b,c,norm,basis.delta_square_columns)
    basis.add_linear(b,a,norm,basis.square_columns)
    b.del_gf2_mul(a,c,target=norm,field=basis.inner)
    basis.change_basis(b,source,to_tower=False)
    b.free(measured+low+high)


def scale_words(builder,pivot,words,*,divide):
    from jfraction_decoder import GF
    if not words:return
    inverse,zero=init_guarded_inverse(builder,pivot,field=GF)
    temporary=builder.alloc_qubits(12)
    factor,undo_factor=(inverse,pivot) if divide else (pivot,inverse)
    for word in words:
        builder.ixor_gf2_mul(word,factor,target=temporary,field=GF)
        builder.swap(word,temporary)
        builder.del_gf2_mul(word,undo_factor,target=temporary,field=GF)
    builder.free(temporary)
    clear_guarded_inverse(builder,pivot,inverse,zero,field=GF)
    builder.free(inverse)


def scale_active_reused_mask(builder,pivot,words,shortened,*,divide):
    from jfraction_decoder import GF
    assert words
    b=builder
    inverse,zero=init_guarded_inverse(b,pivot,field=GF)
    temporary=b.alloc_qubits(12)
    factor,undo_factor=(inverse,pivot) if divide else (pivot,inverse)
    for word in words[:-1]:
        b.ixor_gf2_mul(word,factor,target=temporary,field=GF)
        b.swap(word,temporary)
        b.del_gf2_mul(word,undo_factor,target=temporary,field=GF)
    word=words[-1]
    b.ixor_gf2_mul(word,factor,target=temporary,field=GF)
    b.x(shortened);b.cswap(shortened,word,temporary)
    mask=b.alloc_bits(12);b.hmr(temporary,mask)
    b.gf2_phase_by_product(word,factor,mask=mask,field=GF)
    b.init_and(shortened,word,temporary)
    b.cx(undo_factor,factor)
    b.gf2_phase_by_product(temporary,factor,mask=mask,field=GF)
    b.cx(undo_factor,factor)
    b.del_and(shortened,word,temporary)
    b.free(mask);b.x(shortened);b.free(temporary)
    clear_guarded_inverse(b,pivot,inverse,zero,field=GF)
    b.free(inverse)


def install_phase_scaling():
    import border_circuit as B
    import central_circuit as C
    import retry_circuit as R
    original=B.Scaling
    class NormGuardScaling(original):
        def __init__(self,b,pivot,counts):
            self.b,self.pivot,self.counts=b,pivot,counts
            self.inverse,self.zero=init_guarded_inverse(b,pivot,field=B.GF)
            self.tmp=b.alloc_qubits(12)
            counts["inverse_groups"]+=1
        def close(self):
            b=self.b
            b.free(self.tmp)
            clear_guarded_inverse(b,self.pivot,self.inverse,self.zero,field=B.GF)
            b.free(self.inverse)
    B.Scaling=C.Scaling=R.Scaling=NormGuardScaling
    return NormGuardScaling


def install(*,phase=True):
    """Install after round12/runtime imports, before build_circuit(recipe).

    The incumbent compact-patch initialization is completed first so its
    source rewriting does not overwrite these new scalar functions.
    """
    import sys
    import round11_dqi
    round11_dqi.install_inverses()
    import compact_lifetime_kernels as K
    import jfraction_decoder as J
    old_words=J.scale_words
    K.scale_active_reused_mask=scale_active_reused_mask
    J.scale_words=scale_words
    for name in ('jfraction_gap_decoder','merge_kernels','matrix_pair_kernels',
                 'round9_pointer','compact_gap_variant','paired_kernels'):
        module=sys.modules.get(name)
        if module is not None and getattr(module,'scale_words',None) is old_words:
            module.scale_words=scale_words
    if phase:install_phase_scaling()
    return {'scalar_zero_test_width':6,'expected_saving_per_cache':12,'phase_scaling_patched':phase}
