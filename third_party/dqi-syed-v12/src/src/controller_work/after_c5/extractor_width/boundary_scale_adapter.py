# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Pure-stdlib boundary oracle adapter for direct/first-two unit carries.

Input is an independently generated C5 physical_boundary_oracle.boundary
dictionary (or its immutable recorded copy).  This does not replace its
polynomial/native-value proof: it independently replays only the changed
homogeneous carry, proves every stored head and flag unchanged, and scales
the already certified physical padded N,D by the resulting F unit.

No production emitter, sampler, native library or census is imported.
"""
from functools import cache
from direct_carry_scalar_screen import (mul, power, kmul, kinverse, kscale,
                                        node_value, DELTA)


@cache
def _geometry():
    kappas = [DELTA ^ mul(2*i, 2*i) ^ 2*i for i in range(35)]
    inverse = {(old, i): power(kappas[old] ^ kappas[i], 4094)
               for i in range(35) for old in range(i)}
    return kappas, inverse


def changed_carry(old, *, variant='direct'):
    assert variant in ('direct', 'first2')
    raw, heads, flags = old['raw_queries'], old['heads'], old['tail_flags']
    assert len(raw) == len(heads) == len(flags) == 35
    kappas, inverse = _geometry()
    start = 0
    if variant == 'first2':
        assert raw[0] and raw[1]
        first = node_value(kinverse(raw[0]), 0)
        middle = kinverse(raw[1]) ^ node_value(first, 1)
        assert middle
        second = node_value(kscale(kinverse(middle), kappas[0] ^ kappas[1]), 1)
        assert [first, second] == heads[:2]
        assert flags[:2] == [0, 0]
        start = 2
    carry = 1
    for i in range(start, 35):
        n, d = kmul(carry, raw[i]), carry
        for old_index in range(i):
            n, d = kscale(d ^ kmul(node_value(heads[old_index], i), n),
                          inverse[old_index, i]), n
        assert n or d
        flag = int(n == 0)
        assert flag == flags[i]
        if flag:
            n, d = d, n
        assert n
        assert node_value(kmul(d, kinverse(n)), i) == heads[i]
        carry = n
    return carry


def rescale_boundary(old, *, variant='direct'):
    """Return a new oracle dictionary; never mutate the C5 record."""
    carry = changed_carry(old, variant=variant)
    low, high = carry & 4095, carry >> 12
    gauge = int(low == 0)
    selected, other = (high, low) if gauge else (low, high)
    assert selected and old['selected_lambda'] and old['terminal_unit']
    ratio = mul(selected, power(old['selected_lambda'], 4094))
    gamma = mul(selected, power(old['terminal_unit'], 4094))
    assert gamma == mul(ratio, old['gamma'])
    n = [mul(ratio, x) for x in old['N']]
    d = [mul(ratio, x) for x in old['D']]
    assert len(n) == 35 and len(d) == 36 and d[-1] == gamma
    result = dict(old)
    result.update(N=n, D=d, raw_carry=carry, gauge=gauge,
                  selected_lambda=selected, other_carry_half=other, gamma=gamma,
                  changed_carry_variant=variant, C5_to_new_scale_ratio=ratio,
                  C5_raw_carry=old['raw_carry'], C5_gamma=old['gamma'],
                  oracle_scope='Existing physical polynomial boundary plus exact changed-carry replay')
    return result
