"""Independent scalar P1 checks. No competition input or downloaded code used.

Known identities: Bezoutian Euclid congruence and Barnett multiplication
relation. The reversible integration is a proposal, not an official circuit.
Field modulus 0x1053 matches the published repository benchmark arithmetic.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import time

MODULUS = 0x1053
ORDER = 4095
EXP = [1]
for _ in range(ORDER - 1):
    value = EXP[-1] << 1
    EXP.append(value ^ (MODULUS if value & 4096 else 0))
assert len(set(EXP)) == ORDER
LOG = [0] * 4096
for i, value in enumerate(EXP):
    LOG[value] = i
EXP += EXP


def mul(a, b):
    return EXP[LOG[a] + LOG[b]] if a and b else 0


def inv(a):
    if not a:
        raise ZeroDivisionError
    return EXP[ORDER - LOG[a]]


def div(a, b):
    return mul(a, inv(b))


def sqrt(a):
    return EXP[(LOG[a] * 2048) % ORDER] if a else 0


def trim(a):
    a = list(a)
    while a and not a[-1]:
        a.pop()
    return a


def padd(a, b):
    out = [0] * max(len(a), len(b))
    for i, v in enumerate(a):
        out[i] ^= v
    for i, v in enumerate(b):
        out[i] ^= v
    return trim(out)


def pmul(a, b):
    out = [0] * max(0, len(a) + len(b) - 1)
    for i, v in enumerate(a):
        for j, w in enumerate(b):
            out[i+j] ^= mul(v, w)
    return trim(out)


def pdiv(a, b):
    a, b = trim(a), trim(b)
    assert b
    q = [0] * max(0, len(a)-len(b)+1)
    reciprocal = inv(b[-1])
    while len(a) >= len(b):
        shift = len(a)-len(b)
        factor = mul(a[-1], reciprocal)
        q[shift] = factor
        for i, v in enumerate(b):
            a[i+shift] ^= mul(factor, v)
        a = trim(a)
    return trim(q), a


def pinv(a, p):
    r0, r1, u0, u1 = trim(p), trim(a), [], [1]
    while r1:
        q, r = pdiv(r0, r1)
        r0, r1 = r1, r
        u0, u1 = u1, padd(u0, pmul(q, u1))
    assert len(r0) == 1
    return pdiv([div(v, r0[0]) for v in u0], p)[1]


def peval(a, x):
    v = 0
    for c in reversed(a):
        v = mul(v, x) ^ c
    return v


def matvec(matrix, vector):
    return [xor(mul(a, b) for a, b in zip(row, vector)) for row in matrix]


def xor(values):
    value = 0
    for v in values:
        value ^= v
    return value


def bezout(p, d):
    n = max(len(p), len(d))-1
    pp, dd = list(p)+[0]*(n+1-len(p)), list(d)+[0]*(n+1-len(d))
    out = [[0]*n for _ in range(n)]
    for i in range(n+1):
        for j in range(i):
            v = mul(pp[i], dd[j]) ^ mul(pp[j], dd[i])
            for k in range(i-j):
                out[i-1-k][j+k] ^= v
    return out


def linear_solve(matrix, rhs):
    n = len(rhs)
    a = [list(row)+[value] for row, value in zip(matrix, rhs)]
    for col in range(n):
        pivot = next(i for i in range(col, n) if a[i][col])
        a[col], a[pivot] = a[pivot], a[col]
        iv = inv(a[col][col])
        a[col] = [mul(v, iv) for v in a[col]]
        for i in range(n):
            if i == col:
                continue
            factor = a[i][col]
            a[i] = [v ^ mul(factor, w) for v, w in zip(a[i], a[col])]
    return [row[-1] for row in a]


def bezout_solve(p, d, rhs, gaps=None):
    """Block congruence; matrices here expose algebra, not circuit resources.

    L consists of the first m coordinate vectors and k shifts of D.
    Bez(P,D) = L diag(Bez(D,r), Bez(q,1)) L^T.
    k=1 is the proposed O(n) border circuit.
    """
    p, d = trim(p), trim(d)
    n, m = len(p)-1, len(d)-1
    assert n > m >= 0 and len(rhs) == n
    q, r = pdiv(p, d)
    k = n-m
    if gaps is not None:
        gaps[k] += 1
    # L has identity in the first m columns and convolution by D after it.
    lower = [[d[m+i-j] if 0 <= m+i-j <= m else 0
              for j in range(k)] for i in range(k)]
    upper = [[d[i-j] if 0 <= i-j <= m else 0
              for j in range(k)] for i in range(m)]
    high = linear_solve(lower, rhs[m:])
    low = [v ^ w for v, w in zip(rhs[:m], matvec(upper, high))]
    if m:
        assert r
        low = bezout_solve(d, r, low, gaps)
    high = linear_solve(bezout(q, [1]), high)
    upper_t = list(map(list, zip(*upper))) if m else [[] for _ in range(k)]
    high = [v ^ w for v, w in zip(high, matvec(upper_t, low))]
    high = linear_solve(list(map(list, zip(*lower))), high)
    return low+high


def generic_border_solve(p, d, rhs):
    """Explicit ordinary-step schedule, including its scalar rescalings."""
    p, d = trim(p), trim(d)
    n = len(p)-1
    assert len(d) == n and len(rhs) == n
    if n == 1:
        return [div(rhs[0], mul(p[1], d[0]))]
    q, r = pdiv(p, d)
    assert len(q) == 2 and len(r) == n-1
    lo, hi = list(rhs[:-1]), div(rhs[-1], d[-1])
    for i, v in enumerate(d[:-1]):
        lo[i] ^= mul(v, hi)
    hi = div(hi, q[1])
    lo = generic_border_solve(d, r, lo)
    hi ^= xor(mul(v, w) for v, w in zip(d[:-1], lo))
    hi = div(hi, d[-1])
    return lo+[hi]


def modular_divide(p, d, rhs, gaps=None):
    n = len(p)-1
    rhs = list(rhs)+[0]*(n-len(rhs))
    d = pdiv(d, p)[1]
    z = bezout_solve(p, d, rhs, gaps)
    return trim(matvec(bezout(p, [1]), z))


def forney_map(sigma, omega, gaps=None):
    """R42 half-degree identity; odd degree only, own scalar implementation."""
    sigma, omega = trim(sigma), trim(omega)
    n = len(sigma)-1
    assert n % 2 == 1 and len(omega) <= n
    d = n//2
    a = trim([sqrt(v) for v in sigma[::2]])
    b = trim([sqrt(v) for v in sigma[1::2]])
    c = trim([sqrt(v) for v in omega[::2]])
    dd = trim([sqrt(v) for v in omega[1::2]])
    if d == 0:
        return [div(omega[0] if omega else 0, sigma[1])]
    quotient, rem = pdiv(c, b)
    assert len(quotient) <= 1
    scalar = quotient[0] if quotient else 0
    h0 = modular_divide(b, a, rem, gaps)
    h1 = modular_divide(b, a, dd)
    q0 = pdiv(pmul(a, h0), b)[0]
    q1 = pdiv(pmul(a, h1), b)[0]
    even = padd(padd(q0, [scalar]), [0]+h1)
    odd = padd(h0, q1)
    out = [0]*n
    for i, v in enumerate(even):
        out[2*i] = mul(v, v)
    for i, v in enumerate(odd):
        out[2*i+1] = mul(v, v)
    return trim(out)


def triangular(n):
    return 0 if n <= 1 else triangular(n//2)+triangular(n-n//2)+n-1


def projected_cost(d=17, monic=False):
    # Initial A reduction and C division, including A restoration.
    initial = 3*d + (0 if monic else 3)
    # Each ordinary recursive step: 4(n-1) RHS vector products,
    # 4(n-1) locator products, 4 locator scales and 6 RHS scales.
    recursive = sum(8*n+2 for n in range(2, d+1)) + 3
    groups = 3*(d-1)+1
    if monic:
        recursive -= 2  # P leading=1: first quotient recovered, not stored.
        groups -= 1     # Its inverse q1^-1 equals D's leading coefficient.
    else:
        groups += 2     # Shared B^-1 setup and restoration/final transform.
    barnett = 2*triangular(d)+(0 if monic else 2*d)
    final = 2*triangular(d)+(0 if monic else 2*d)+2*(2*d-1)+triangular(d+1)
    products = initial+recursive+barnett+final
    forward = products*42+groups*90
    replacement = 2*forward+4025*11
    old_scan = 4025*80
    old_t = 1116994.35
    return dict(kind="optimistic generic-degree, no degree-control cost",
                monic_reversed_locator=monic, half_degree=d,
                initial_products=initial, recursive_products=recursive,
                barnett_products=barnett, final_products=final,
                total_products_scales=products, shared_inverse_groups=groups,
                forward_toffolis=forward, phase_toffolis=replacement,
                fraction_at_q881=(old_t-old_scan+replacement)/old_t,
                max_q_for_ten_percent=881*(0.9/((old_t-old_scan+replacement)/old_t))**0.5)


def run(cases, seed):
    start = time.monotonic()
    rng = random.Random(seed)
    gaps = Counter()
    general_cases = generic_cases = forney_cases = 0
    for n in range(1, 18):
        for _ in range(cases):
            p = [rng.randrange(4096) for _ in range(n)]+[rng.randrange(1, 4096)]
            degree = rng.randrange(n)
            d = [rng.randrange(4096) for _ in range(degree)]+[rng.randrange(1, 4096)]
            rhs = [rng.randrange(4096) for _ in range(n)]
            try:
                reference = pinv(d, p)
            except AssertionError:
                continue
            got = modular_divide(p, d, rhs, gaps)
            expected = pdiv(pmul(reference, rhs), p)[1]
            assert got == expected, (n, p, d, rhs, got, expected)
            general_cases += 1
            if len(d) == n:
                try:
                    border = generic_border_solve(p, d, rhs)
                except AssertionError:
                    pass
                else:
                    assert matvec(bezout(p, d), border) == rhs
                    generic_cases += 1
    for weight in range(1, 36):
        for _ in range(cases):
            roots = rng.sample(range(1, 4096), weight)
            sigma = [1]
            for root in roots:
                sigma = pmul(sigma, [root, 1])
            omega = [rng.randrange(4096) for _ in range(weight)]
            original_sigma, original_omega = list(sigma), list(omega)
            if weight % 2 == 0:
                sigma, omega = [0]+sigma, [0]+omega
            got = forney_map(sigma, omega, gaps)
            derivative = [v if i % 2 else 0 for i, v in enumerate(sigma)][1:]
            assert not pdiv(padd(pmul(got, derivative), omega), sigma)[1]
            for root in roots:
                original_derivative = [v if i % 2 else 0 for i, v in enumerate(original_sigma)][1:]
                assert peval(got, root) == div(peval(original_omega, root), peval(original_derivative, root))
            forney_cases += 1
    return dict(status="PASS", scope="classical identities, not quantum or official verification",
                seed=seed, cases_per_degree=cases, modular_division_cases=general_cases,
                ordinary_border_cases=generic_cases, forney_cases=forney_cases,
                quotient_degrees=dict(sorted(gaps.items())),
                scalar_seconds=time.monotonic()-start,
                optimistic_costs=[projected_cost(monic=False), projected_cost(monic=True)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=16)
    parser.add_argument("--seed", type=int, default=2026102519)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.cases, args.seed)
    serialized = json.dumps(result, indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")
