#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Independent classical C2.7 failure classifier. No kickmix and no sampling.

Inputs are physical nonzero roots and nonzero magnitudes, not a supplied
decoder profile. All field and polynomial operations are exact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MODULUS = 0x1053
KAPPA = 2048
CUTOFFS = (15, 16, 17)
FINITE_N = 1
FINITE_D = 2
DROP = 4
WINDOW17 = 8
WINDOW14 = 16
GCD = 32


def manual_mul(a: int, b: int) -> int:
    answer = 0
    while b:
        if b & 1:
            answer ^= a
        b >>= 1
        a <<= 1
        if a & 4096:
            a ^= MODULUS
    return answer


EXP = [0] * 8190
LOG = [-1] * 4096
_x = 1
for _i in range(4095):
    assert LOG[_x] == -1
    EXP[_i] = _x
    LOG[_x] = _i
    _x = manual_mul(_x, 2)
assert _x == 1
EXP[4095:] = EXP[:4095]
INV = [0] + [EXP[4095 - LOG[x]] for x in range(1, 4096)]
SQRT = [0] + [EXP[(2048 * LOG[x]) % 4095] for x in range(1, 4096)]


def mul(a, b):
    return EXP[LOG[a] + LOG[b]] if a and b else 0


def divide(a, b):
    if not b:
        raise ZeroDivisionError("GF4096 divisor")
    return mul(a, INV[b])


def trace(a):
    value = 0
    for _ in range(12):
        value ^= a
        a = mul(a, a)
    return value


KAPPAS = tuple(KAPPA ^ mul(2*i, 2*i) ^ (2*i) for i in range(35))
QUADRATICS = tuple((c, 1, 1) for c in KAPPAS)
assert len(set(KAPPAS)) == 35 and all(trace(c) == 1 for c in KAPPAS)


def trim(p):
    p = list(p)
    while p and p[-1] == 0:
        p.pop()
    return p


def add(a, b):
    out = [0] * max(len(a), len(b))
    for i, x in enumerate(a):
        out[i] ^= x
    for i, x in enumerate(b):
        out[i] ^= x
    return trim(out)


def product(a, b):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i+j] ^= mul(x, y)
    return trim(out)


def scale(a, factor):
    return trim([mul(x, factor) for x in a])


def divrem(a, b):
    a, b = trim(a), trim(b)
    if not b:
        raise ZeroDivisionError("polynomial divisor")
    out = [0] * max(0, len(a) - len(b) + 1)
    while len(a) >= len(b):
        shift = len(a) - len(b)
        factor = divide(a[-1], b[-1])
        out[shift] = factor
        for i, x in enumerate(b):
            a[i+shift] ^= mul(factor, x)
        a = trim(a)
    return trim(out), a


def evaluate(p, x):
    out = 0
    for a in reversed(p):
        out = mul(out, x) ^ a
    return out


def quadratic_remainder(p, c):
    a = b = 0
    for x in reversed(p):
        a, b = x ^ mul(c, b), a ^ b
    return a, b


def quadratic_mul(x, y, c):
    a, b = x
    d, e = y
    z = mul(b, e)
    return mul(a, d) ^ mul(c, z), mul(a, e) ^ mul(b, d) ^ z


def quadratic_div(x, y, c):
    a, b = y
    norm = mul(a, a) ^ mul(a, b) ^ mul(c, mul(b, b))
    if not norm:
        raise ZeroDivisionError("quadratic divisor")
    conjugate = (divide(a ^ b, norm), divide(b, norm))
    return quadratic_mul(x, conjugate, c)


PADDING = []
for _j in range(36):
    _pad = [0, 1] if _j % 2 == 0 else [1]
    for _i in range(_j, 34 - (_j % 2 == 0), 2):
        _pad = product(_pad, QUADRATICS[_i])
    assert len(_pad) == 36 - _j
    PADDING.append(tuple(_pad))


def physical_pair(roots, values):
    roots, values = tuple(roots), tuple(values)
    if not (0 <= len(roots) <= 35 and len(roots) == len(values)):
        raise ValueError("support/value shape")
    if len(set(roots)) != len(roots) or any(not 1 <= x < 4096 for x in roots + values):
        raise ValueError("physical roots and magnitudes must be nonzero, roots distinct")
    locator = [1]
    for a in roots:
        locator = product(locator, [a, 1])
    numerator = []
    for a, e in zip(roots, values):
        weighted = a
        a2a = mul(a, a) ^ a
        for c in KAPPAS:
            weighted = mul(weighted, a2a ^ c)
        quotient, rem = divrem(locator, [a, 1])
        assert not rem
        numerator = add(numerator, scale(quotient, mul(e, weighted)))
    return numerator, locator


def active_profile(numerator, locator, weight):
    n, d = list(numerator), list(locator)
    for i in range(weight):
        nr = quadratic_remainder(n, KAPPAS[i])
        dr = quadratic_remainder(d, KAPPAS[i])
        if nr == (0, 0) or dr == (0, 0):
            assert nr != dr, "coprime active pair cannot vanish together"
            return dict(bad=True, slot=i, kind="N" if nr == (0, 0) else "D",
                        numerator_remainder=list(nr), denominator_remainder=list(dr))
        head = quadratic_div(dr, nr, KAPPAS[i])
        nxt, remainder = divrem(add(d, product(head, n)), QUADRATICS[i])
        assert not remainder
        n, d = nxt, n
        assert len(n) <= weight-i-1 and len(d) <= weight-i
    assert not n and len(d) == 1 and d[0]
    return dict(bad=False, slot=-1, kind=None)


def half_profile(denominator):
    d = trim(denominator)
    if len(d) != 36 or not d[-1]:
        raise ValueError("full-35 denominator required")
    a = [SQRT[x] for x in d[1::2]]
    evens = [SQRT[x] for x in d[::2]]
    quotient = divide(evens[-1], a[-1])
    b = trim([x ^ mul(quotient, y) for x, y in zip(evens[:-1], a[:-1])])
    degrees = [len(a)-1]
    while b:
        degrees.append(len(b)-1)
        a, b = b, divrem(a, b)[1]
    drops = [u-v for u, v in zip(degrees, degrees[1:])]
    padded = {u for u, v in zip(degrees, degrees[1:]) if u-v == 2}
    reason = (GCD if degrees[-1] != 0 else 0)
    reason |= DROP if max(drops, default=1) > 2 else 0
    reason |= WINDOW17 if {17, 15} <= padded else 0
    reason |= WINDOW14 if {14, 12} <= padded else 0
    mask = sum(1 << n for n in degrees) | ((1 << 30) if degrees[-1] != 0 else 0)
    return dict(degrees=degrees, degree_mask=mask, reason_mask=reason, admitted=reason == 0,
                drop2_starts=sorted(padded, reverse=True))


def classify(roots, values, *, include_polynomials=False):
    n, d = physical_pair(roots, values)
    j = len(roots)
    full = product(d, PADDING[j])
    assert len(full) == 36 and full[-1] == 1
    finite = active_profile(n, d, j)
    half = half_profile(full)
    reason = half["reason_mask"]
    if finite["bad"]:
        reason |= FINITE_N if finite["kind"] == "N" else FINITE_D
    out = dict(weight=j, finite=finite, half=half, reason_mask=reason,
               union={str(c): j < c or bool(reason) for c in CUTOFFS})
    if include_polynomials:
        out.update(numerator=n, locator=d, padded_locator=full)
    return out


def read_cases(path):
    with Path(path).open() as stream:
        for line in stream:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            row = list(map(int, line.split()))
            j = row[0]
            if len(row) != 1 + 2*j:
                raise ValueError("case requires weight then root/value pairs")
            yield row[1::2], row[2::2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--polynomials", action="store_true")
    args = parser.parse_args()
    for index, (roots, values) in enumerate(read_cases(args.cases), 1):
        print(json.dumps(dict(case=index, **classify(roots, values,
                                                   include_polynomials=args.polynomials)),
                         sort_keys=True))


if __name__ == "__main__":
    main()
