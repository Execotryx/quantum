# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Scalar physical-input oracle for the new key boundary; no circuit engine.

The complete numerator/denominator oracle comes from the physical rational
pair and squarefree padding, not from simulating coefficient synthesis. A
separate exact raw-query replay determines the retained carry/gauge chart.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
C27 = HERE.parents[1]
sys.path.insert(0, str(C27/'census'))
import reference as R


def pack(pair):
    return pair[0] | (pair[1] << 12)


def unpack(word):
    return word & 4095, word >> 12


def multiply(a, b):
    return pack(R.quadratic_mul(unpack(a), unpack(b), R.KAPPA))


def inverse(word):
    return pack(R.quadratic_div((1, 0), unpack(word), R.KAPPA))


def node_view(word, index):
    low, high = unpack(word)
    return (low ^ R.mul(2*index, high)) | (high << 12)


def scalar_scale(word, scalar):
    low, high = unpack(word)
    return R.mul(low, scalar) | (R.mul(high, scalar) << 12)


def raw_queries(numerator, denominator):
    result = []
    for i, kappa in enumerate(R.KAPPAS):
        n = R.quadratic_remainder(numerator, kappa)
        d = R.quadratic_remainder(denominator, kappa)
        result.append(node_view(pack(R.quadratic_div(n, d, kappa)), i))
    return result


def replay_raw_queries(raw, weight, *, j_min=15):
    """Return coefficient heads, reciprocal carry and real zero flags."""
    assert len(raw) == 35 and j_min <= weight <= 35
    heads, flags, carry, previous = [], [], 1, 0
    for i, word in enumerate(raw):
        n, d = multiply(carry, word), carry
        for old, head in enumerate(heads):
            p = node_view(head, i)
            n, d = scalar_scale(d ^ multiply(p, n), R.INV[R.KAPPAS[old] ^ R.KAPPAS[i]]), n
        assert n or d, ('joint_zero_raw_pair', i)
        flag = int(n == 0)
        if i < weight:
            assert not flag, ('active_numerator_zero', i)
        if flag:
            assert i >= j_min
            n, d = d, n
        carry = inverse(n)
        head = multiply(d, carry)
        assert bool(head) == (i < weight), ('active_zero_or_nonzero_tail', i)
        assert int(head == 0) == (previous ^ flag), ('rolling_zero_identity', i)
        heads.append(node_view(head, i))
        flags.append(flag)
        previous = flag
    assert flags[-1] == int(weight % 2 == 0)
    return heads, carry, flags


def terminal_unit(numerator, denominator, weight, heads=None):
    """Independent polynomial recurrence, including every active head."""
    n, d = list(numerator), list(denominator)
    for i in range(weight):
        nr = R.quadratic_remainder(n, R.KAPPAS[i])
        dr = R.quadratic_remainder(d, R.KAPPAS[i])
        assert nr != (0, 0) and dr != (0, 0)
        head = R.quadratic_div(dr, nr, R.KAPPAS[i])
        if heads is not None:
            assert pack(head) == heads[i], ('independent_polynomial_head', i)
        child, remainder = R.divrem(R.add(d, R.product(head, n)), R.QUADRATICS[i])
        assert not remainder
        n, d = child, n
    assert not n and len(d) == 1 and d[0]
    return d[0]


def boundary(roots, values, *, j_min=15):
    weight = len(roots)
    assert j_min <= weight <= 35
    n, d = R.physical_pair(roots, values)
    raw = raw_queries(n, d)
    heads, carry, flags = replay_raw_queries(raw, weight, j_min=j_min)
    nu = terminal_unit(n, d, weight, heads)
    low, high = unpack(carry)
    gauge = int(low == 0)
    selected, other = (high, low) if gauge else (low, high)
    assert selected
    gamma = R.divide(selected, nu)
    padded_n = R.scale(R.product(n, R.PADDING[weight]), gamma)
    padded_d = R.scale(R.product(d, R.PADDING[weight]), gamma)
    assert len(padded_n) <= 35 and len(padded_d) == 36 and padded_d[-1] == gamma
    padded_n += [0] * (35-len(padded_n))
    return dict(N=padded_n, D=padded_d, other_carry_half=other, gauge=gauge,
                gamma=gamma, selected_lambda=selected, terminal_unit=nu,
                raw_carry=carry, raw_queries=raw, heads=heads,
                tail_flags=flags, terminal_seed_flag=flags[-1])
