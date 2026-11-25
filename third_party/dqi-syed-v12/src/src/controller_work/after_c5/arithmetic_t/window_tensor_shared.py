# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Same raw three-border map, sharing its two RHS source/phase preparations.

Source-matched variant of the supplied raw_window_tensor.emit. This file is
not integrated into C5. Domain: flags f,m,t = zero(q1,F[-1],G[-1]) are one
of 000,100,010,001. It preserves every source/head and XORs the same lower
map into two RHS vectors. Source-only zero-predicate masks use the original
record_flag API. No target-dependent phase leaves this call.

Paper delta per two-RHS call: -24 source-mask T, -12 A-debt source-mask T,
-11 third-predicate T = -47 T. Peak scratch remains25; extra retained records
are classical. Counts and implementation remain pending native testing.
"""
import kickmix as km
from monic_forney import add_scaled
from coherent_border import toggle_zero
from tower_inverse import xor_product, phase_product, kernel
from raw_window_tensor import evaluate


def emit(builder, F, G, q0, q1, rhss, record_flag):
    m = len(G)-1
    assert len(F) == m+2 and len(rhss) == 2 and all(len(r) == m+3 for r in rhss)
    witnesses = (q1, F[-1], G[-1])

    def query(slot):
        flag = builder.alloc_qubits(1)
        toggle_zero(builder, witnesses[slot], flag[0])
        return flag

    def release(slot, flag):
        mask = builder.alloc_bits(1)
        builder.hmr(flag, mask)
        builder.free(flag)
        record_flag(slot, mask)

    def shared_source_form(f):
        # h2 += (1+f)*q0*h1 on both disjoint RHSs, using one masked source.
        masked = builder.alloc_qubits(12)
        builder.init_and(f[0], q0, masked)
        builder.cx(masked, q0)
        for rhs in rhss:
            xor_product(builder, q0, rhs[-1], rhs[-2])
        builder.cx(masked, q0)
        builder.del_and(f[0], q0, masked)
        builder.free(masked)

    evaluate(builder, F, m)
    evaluate(builder, G, m)
    f, middle = query(0), query(1)
    shared_source_form(f)
    a_debts, b_debts = [], []
    for rhs in rhss:
        low = rhs[:m]
        h3, h2, h1 = rhs[m:]
        product = builder.alloc_qubits(12)
        xor_product(builder, q1, h1, product)
        builder.ccx(f[0], h1, product)
        upper = builder.alloc_qubits(11)
        builder.init_and(middle[0], product[1:], upper)
        builder.ccx(middle[0], product[0], f[0])
        builder.cx(upper, product[1:])
        builder.ccx(middle[0], f[0], product[0])
        builder.cswap(middle[0], h1, h2)
        for point, (coefficient, target) in enumerate(zip(F[:m], low)):
            add_scaled(builder, product, h2, point)
            xor_product(builder, coefficient, h2, target)
            add_scaled(builder, product, h2, point)
        builder.cswap(middle[0], h1, h2)
        product_mask = builder.alloc_bits(12)
        builder.hmr(product, product_mask)
        builder.free(product)
        first = builder.alloc_qubits(1)
        builder.init_and(middle[0], f[0], first[0])
        builder.cx(first, f)
        A = km.array([*first, *upper])
        phase_product(builder, q1, h1, product_mask, kernel(12))
        builder.cz(product_mask, A)
        for bit in range(12):
            builder.ccz(product_mask[bit], f[0], h1[bit])
        builder.free(product_mask)

        builder.cx(h1, h3)
        builder.ccx(f[0], h1, h3)
        builder.ccx(middle[0], h1, h3)
        release(0, f)
        third = query(2)
        linear_upper = builder.alloc_qubits(11)
        builder.init_and(middle[0], h2[1:], linear_upper)
        builder.cx(h1, h3)
        builder.ccx(third[0], h3[1:], linear_upper)
        builder.cx(h1, h3)
        builder.cx(h1[0], h3[0])
        builder.ccx(third[0], h3[0], A[0])
        builder.cx(h1[0], h3[0])
        release(2, third)
        linear_first = builder.alloc_qubits(1)
        builder.init_and(middle[0], A[0], linear_first[0])
        builder.cx(linear_first[0], A[0])
        builder.swap(linear_first[0], A[0])
        builder.ccx(middle[0], h2[0], linear_first[0])
        B = km.array([*linear_first, *linear_upper])
        builder.cx(B, h3)
        builder.ccx(middle[0], h2, h3)
        for point, (coefficient, target) in enumerate(zip(G[:m], low)):
            square = km.GF2Field(12).mul(point, point)
            add_scaled(builder, B, h3, point)
            add_scaled(builder, A, h3, square)
            xor_product(builder, coefficient, h3, target)
            add_scaled(builder, A, h3, square)
            add_scaled(builder, B, h3, point)
        builder.ccx(middle[0], h2, h3)
        builder.cx(B, h3)

        bmask = builder.alloc_bits(12)
        builder.hmr(B, bmask)
        builder.free(linear_upper)
        builder.free(linear_first)
        b_debts.append((h2, h3, bmask))
        amask = builder.alloc_bits(12)
        builder.hmr(A, amask)
        builder.free(upper)
        builder.free(first)
        a_debts.append((h1, amask))
        f = query(0)
        builder.ccx(middle[0], h1, h3)
        builder.ccx(f[0], h1, h3)
        builder.cx(h1, h3)

    # h3 is now original; h2 still includes its shared source-form shear.
    # Original B=m*h2+t*(h3_temporary+h1)=m*h2+t*h3_original because
    # f*t=m*t=0 on this unchanged domain. Pay both masks before undoing h2.
    third = query(2)
    for h2, h3, mask in b_debts:
        for bit in range(12):
            builder.ccz(mask[bit], middle[0], h2[bit])
            builder.ccz(mask[bit], third[0], h3[bit])
        builder.free(mask)
    release(2, third)

    # A=m*q1*h1; every h1 and q1 is restored and unchanged across both RHSs.
    masked = builder.alloc_qubits(12)
    builder.init_and(middle[0], q1, masked)
    for h1, mask in a_debts:
        phase_product(builder, masked, h1, mask, kernel(12))
        builder.free(mask)
    builder.del_and(middle[0], q1, masked)
    builder.free(masked)
    shared_source_form(f)
    release(0, f)
    release(1, middle)
    evaluate(builder, G, m, True)
    evaluate(builder, F, m, True)
