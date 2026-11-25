# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Borrowed-source forward window, preserving the accepted record API.

This is a new candidate; a native receipt is required before any gain is
credited. Its gate body is the prior scalar-only candidate, SHA-256
bf9f6f424f3ac920aae9115828f9dbe05e61d4daa235eae59338ebdcd4ddd28f.
The added pre-emission checks make the physical alias contract explicit.

All fields are disjoint 12-qubit words. The actual source zero predicates
(f,middle,third) are one of 000,100,010,001. Two arbitrary RHSs each have
m low targets and three head words. Sources and heads are restored; only
the low targets are XOR-updated. Every target-dependent HMR debt is paid
inside this call. Exactly three source-predicate masks are returned through
record_flag, to be paid by the unchanged caller on its restored witnesses.

The conditional-zero borrows use F[-1] only when its actual zero flag is1,
and G[-1] only when its actual zero flag is1. Those physical words are
restored before the public inverse evaluation maps. Model:168*m+645 T,
15 live helper qubits, with no change to the transpose implementation.
"""
import kickmix as km
from raw_window_tensor import evaluate
from monic_forney import F as FIELD, add_scaled
from coherent_border import toggle_zero
from tower_inverse import xor_product, phase_product, kernel


def emit(builder, F, G, q0, q1, rhss, record_flag):
    # Validate the entire physical view before emitting or allocating.
    m = len(G)-1
    assert m >= 1 and len(F) == m+2 and len(rhss) == 2
    assert all(len(rhs) == m+3 for rhs in rhss)
    words = [*F, *G, q0, q1, *rhss[0], *rhss[1]]
    assert all(len(word) == 12 for word in words)
    wires = [wire for word in words for wire in word]
    assert all(isinstance(wire, km.q) for wire in wires)
    assert len(set(wires)) == len(wires), 'source, head, or target views overlap'
    assert callable(record_flag)
    witnesses = (q1, F[-1], G[-1])
    flags = []
    for witness in witnesses:
        flag = builder.alloc_qubits(1)
        toggle_zero(builder, witness, flag[0])
        flags.append(flag)
    f, middle, third = flags

    def source_form():
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
    for point in range(m):
        add_scaled(builder, G[point], F[point], point)
    source_form()
    for rhs in rhss:
        low = rhs[:m]
        k, y, h = rhs[m:]
        product = builder.alloc_qubits(12)
        # The original quotient is restored before either borrowed-source
        # interval and before its measurement mask is repaid.
        builder.cx(f[0], q1[0])
        xor_product(builder, q1, h, product)
        builder.cx(f[0], q1[0])

        # Only F[:m] is read during this interval.  F[-1] is known zero
        # exactly on the branch that moves the product into that field.
        builder.cswap(middle[0], product, F[-1])
        builder.cswap(middle[0], h, y)
        for point, (coefficient, target) in enumerate(zip(F[:m], low)):
            add_scaled(builder, product, y, point)
            xor_product(builder, coefficient, y, target)
            add_scaled(builder, product, y, point)
        builder.cswap(middle[0], h, y)
        builder.cswap(middle[0], product, F[-1])

        # The three G coefficients become k0, y+m*h+t*k, and product.
        # G[-1] is borrowed only under its actual zero predicate.  G[:m]
        # still contains the evaluations of the unmodified source G.
        builder.ccx(middle[0], h, y)
        builder.ccx(third[0], k, y)
        builder.cswap(third[0], k, G[-1])
        builder.cx(h, k)
        builder.ccx(f[0], h, k)
        builder.ccx(middle[0], h, k)
        for point, (coefficient, target) in enumerate(zip(G[:m], low)):
            square = FIELD.mul(point, point)
            add_scaled(builder, y, k, point)
            add_scaled(builder, product, k, square)
            xor_product(builder, coefficient, k, target)
            add_scaled(builder, product, k, square)
            add_scaled(builder, y, k, point)
        builder.ccx(middle[0], h, k)
        builder.ccx(f[0], h, k)
        builder.cx(h, k)
        builder.cswap(third[0], k, G[-1])
        builder.ccx(third[0], k, y)
        builder.ccx(middle[0], h, y)

        mask = builder.alloc_bits(12)
        builder.hmr(product, mask)
        builder.free(product)
        phase_product(builder, q1, h, mask, kernel(12))
        for bit in range(12):
            builder.ccz(mask[bit], f[0], h[bit])
        builder.free(mask)
    source_form()
    for point in range(m):
        add_scaled(builder, G[point], F[point], point)
    evaluate(builder, G, m, True)
    evaluate(builder, F, m, True)
    for slot, flag in enumerate(flags):
        mask = builder.alloc_bits(1)
        builder.hmr(flag, mask)
        builder.free(flag)
        record_flag(slot, mask)
