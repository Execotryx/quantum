# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Minimum-cost bit-1 parity coset decoding.

For batch b we need F_b (addresses where one word of batch b gets bit 1 flipped)
with  P_b + F_b + P_ref  in  S = {A(h) + sum_i l_i B_i(h) + C(l)}  on real addresses.
Exact under an additive per-address cost: enumerate the 2^11 nonlinear low parts C
and choose the best affine function per high block.
"""
import numpy as np

NONLIN = [l for l in range(1, 16) if bin(l).count('1') >= 2]
LOWS = np.arange(16)


def monomial_table(m):
    return ((LOWS & m) == m).astype(np.uint8)


def affine_tables():
    """32 affine functions of 4 low bits as (32,16) uint8."""
    out = []
    for s in range(32):
        f = np.full(16, s & 1, dtype=np.uint8)
        for i in range(4):
            if s >> (i + 1) & 1:
                f ^= ((LOWS >> i) & 1).astype(np.uint8)
        out.append(f)
    return np.array(out)


AFF = affine_tables()
MONO = np.array([monomial_table(m) for m in NONLIN])     # (11,16)


def c_tables():
    tabs = np.zeros((2048, 16), dtype=np.uint8)
    for s in range(2048):
        for i in range(11):
            if s >> i & 1:
                tabs[s] ^= MONO[i]
    return tabs


CTAB = c_tables()


def parity_bit1(words, b):
    w = np.asarray(words, dtype=np.int64)[:, 5 * b:5 * b + 5]
    return (np.bitwise_xor.reduce((w >> 1) & 1, axis=1)).astype(np.uint8)


def decode_coset(D, cost):
    """D: (1220,) mismatch bits; cost: (1220,) flip cost (inf = not allowed).
    Returns (best_total, flips mask (1220,), C index)."""
    Dp = np.zeros(1232, dtype=np.uint8); Dp[:1220] = D
    cp = np.zeros(1232); cp[:1220] = cost; cp[1220:] = 0.0
    Dh = Dp.reshape(77, 16); ch = cp.reshape(77, 16)
    real = np.ones((77, 16), dtype=bool); real[76, 4:] = False
    best = (np.inf, None, None)
    # residual for each C: r = D ^ C ; per block choose affine a minimizing sum cost[(r^a)==1]
    # cost of choosing affine a for block h given C: sum_l ch[h,l] * (Dh[h,l]^C[l]^AFF[a,l])
    for s in range(2048):
        r = Dh ^ CTAB[s][None, :]                          # (77,16)
        x = r[:, None, :] ^ AFF[None, :, :]                 # (77,32,16)
        tot = np.where(real[:, None, :], x * ch[:, None, :], 0.0).sum(2)   # (77,32)
        tot = np.where(np.isnan(tot), np.inf, tot)
        a = tot.argmin(1)
        val = tot[np.arange(77), a].sum()
        if val < best[0]:
            best = (val, a.copy(), s)
    val, a, s = best
    r = Dh ^ CTAB[s][None, :]
    F = (r ^ AFF[a]).reshape(-1)[:1220].astype(bool)
    return val, F, s


def in_S(f):
    """check f (1220,) is in S via exact ANF test."""
    import sys
    from relations import anf, positions
    c = anf(np.asarray(f, dtype=np.uint8)[:, None])[:, :, 0]
    return int(c[positions('nonlinear')].sum()) == 0


# ---- degree-2 (quadratic in low bits) code for the bit-2 parity -------------------------
CUBIC = [l for l in range(1, 16) if bin(l).count('1') >= 3]


def quad_tables():
    mons = [0] + [1, 2, 4, 8] + [l for l in range(1, 16) if bin(l).count('1') == 2]
    tabs = []
    for s in range(1 << 11):
        f = np.zeros(16, dtype=np.uint8)
        for i, m in enumerate(mons):
            if s >> i & 1:
                f ^= ((LOWS & m) == m).astype(np.uint8)
        tabs.append(f)
    return np.array(tabs)


QUAD = quad_tables()                                       # (2048,16)
CUBTAB = np.array([[(bin(s).count('1') and 0) or 0 for _ in range(16)] for s in range(32)], dtype=np.uint8)
for _s in range(32):
    _f = np.zeros(16, dtype=np.uint8)
    for _i, _m in enumerate(CUBIC):
        if _s >> _i & 1:
            _f ^= ((LOWS & _m) == _m).astype(np.uint8)
    CUBTAB[_s] = _f


def parity_bit(words, b, bit):
    w = np.asarray(words, dtype=np.int64)[:, 5 * b:5 * b + 5]
    return (np.bitwise_xor.reduce((w >> bit) & 1, axis=1)).astype(np.uint8)


def decode_coset_quad(D, cost):
    """min-cost F with D^F in S2 = {quadratic-in-low per block + shared cubic pure-low}."""
    Dp = np.zeros(1232, dtype=np.uint8); Dp[:1220] = D
    cp = np.zeros(1232); cp[:1220] = cost
    Dh = Dp.reshape(77, 16); ch = cp.reshape(77, 16)
    real = np.ones((77, 16), dtype=bool); real[76, 4:] = False
    best = (np.inf, None, None)
    for s in range(32):
        r = Dh ^ CUBTAB[s][None, :]
        tot = np.empty((77, 2048))
        for h in range(77):
            x = r[h][None, :] ^ QUAD                          # (2048,16)
            tot[h] = np.where(real[h][None, :], x * ch[h][None, :], 0.0).sum(1)
        tot = np.where(np.isnan(tot), np.inf, tot)
        a = tot.argmin(1)
        val = tot[np.arange(77), a].sum()
        if val < best[0]:
            best = (val, a.copy(), s)
    val, a, s = best
    F = ((Dh ^ CUBTAB[s][None, :]) ^ QUAD[a]).reshape(-1)[:1220].astype(bool)
    return val, F, s


def in_S2(f):
    from relations import anf
    c = anf(np.asarray(f, dtype=np.uint8)[:, None])[:, :, 0]
    from relations import FREE
    return int(sum(c[1:, l][~FREE[1:, l]].sum() for l in CUBIC)) == 0
