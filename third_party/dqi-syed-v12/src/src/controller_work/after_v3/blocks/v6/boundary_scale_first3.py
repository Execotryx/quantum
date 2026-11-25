# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Independent scalar boundary replay for the repaired third public chart.

This pure-stdlib oracle consumes an existing C5 physical boundary dictionary.
It checks all heads and tail flags against that dictionary and changes only
the common nonzero scale and its explicitly selected gauge coordinates.
It imports no production emitter, sampler, native library or census runner.
"""
from pathlib import Path
from functools import cache
import sys

WORK = Path(__file__).resolve().parents[3]
SCALAR = WORK/'after_c5/extractor_width'
if str(SCALAR) not in sys.path:
    sys.path.insert(0, str(SCALAR))
from direct_carry_scalar_screen import mul, power, kmul, kinverse, kscale, node_value, DELTA


def inv0(value):
    return kinverse(value) if value else 0


@cache
def _public_inverse_differences():
    kappas = [DELTA ^ mul(2*i, 2*i) ^ 2*i for i in range(35)]
    return {(earlier, i): power(kappas[earlier] ^ kappas[i], 4094)
            for i in range(3, 35) for earlier in range(i)}


def third_head(raw, first_head, second_head):
    first, second = node_value(first_head, 2), node_value(second_head, 2)
    assert first and second
    a, b = 20, 18
    denominator = 1 ^ kmul(first, raw)
    assert denominator, 'existing active denominator at third pivot'
    first_n = kscale(denominator, power(a, 4094))
    second_n = kscale(raw ^ kmul(second, first_n), power(b, 4094))
    assert second_n, 'existing active numerator at third pivot'
    middle = inv0(inv0(raw) ^ (first if raw else 0))
    assert middle == kmul(raw, kinverse(denominator))
    final_argument = kscale(middle, a) ^ second
    assert final_argument
    actual = kscale(kinverse(final_argument), b)
    assert actual == kmul(first_n, kinverse(second_n))
    return actual, dict(raw_zero=raw == 0, middle=middle,
                       queried_numerator=second_n, queried_denominator=first_n)


def changed_carry(old):
    raw, heads, flags = old['raw_queries'], old['heads'], old['tail_flags']
    assert len(raw) == len(heads) == len(flags) == 35
    assert raw[0] and raw[1] and flags[:3] == [0, 0, 0]
    first = node_value(kinverse(raw[0]), 0)
    inner = kinverse(raw[1]) ^ node_value(first, 1)
    assert inner
    second = node_value(kscale(kinverse(inner), 6), 1)
    assert [first, second] == heads[:2]
    third, seam = third_head(raw[2], first, second)
    assert node_value(third, 2) == heads[2]
    inverse_differences = _public_inverse_differences()
    carry = 1
    for i in range(3, 35):
        numerator, denominator = kmul(carry, raw[i]), carry
        for earlier in range(i):
            numerator, denominator = kscale(
                denominator ^ kmul(node_value(heads[earlier], i), numerator),
                inverse_differences[earlier, i]), numerator
        assert numerator or denominator
        flag = int(numerator == 0)
        assert flag == flags[i]
        if flag:
            numerator, denominator = denominator, numerator
        assert numerator
        assert node_value(kmul(denominator, kinverse(numerator)), i) == heads[i]
        carry = numerator
    return carry, seam


def rescale_boundary(old):
    carry, seam = changed_carry(old)
    low, high = carry & 4095, carry >> 12
    gauge = int(low == 0)
    selected, other = (high, low) if gauge else (low, high)
    assert selected and old['selected_lambda'] and old['terminal_unit']
    ratio = mul(selected, power(old['selected_lambda'], 4094))
    gamma = mul(selected, power(old['terminal_unit'], 4094))
    assert gamma == mul(ratio, old['gamma'])
    numerator = [mul(ratio, value) for value in old['N']]
    denominator = [mul(ratio, value) for value in old['D']]
    assert len(numerator) == 35 and len(denominator) == 36 and denominator[-1] == gamma
    result = dict(old)
    result.update(N=numerator, D=denominator, raw_carry=carry, gauge=gauge,
                  selected_lambda=selected, other_carry_half=other, gamma=gamma,
                  changed_carry_variant='first3_zero_repaired', third_chart=seam,
                  C5_to_new_scale_ratio=ratio, C5_raw_carry=old['raw_carry'],
                  C5_gamma=old['gamma'],
                  oracle_scope='Unchanged physical polynomial boundary plus exact third-chart and carry replay')
    return result
