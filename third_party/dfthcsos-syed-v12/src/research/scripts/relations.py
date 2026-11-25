# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Exact GF(2) relation structure of ANGLE_k loader deltas.

Address a = 16*h + l, h in [0,77) (7 high bits), l in [0,16) (4 low bits).
Real addresses are a < 1220; rows 1220..1231 (h=76, l>=4) are off-domain.
For a Boolean function f on the real addresses, its ANF coefficients
c(h', l') (h' a high monomial < 77, l' a low monomial < 16) are unique except
the twelve coefficients c(76, l' >= 4), which the twelve off-domain values set
freely (the map between them is triangular and invertible).

Delta_k(a) = batch_k(a) XOR batch_{k-1}(a) in F2^40 (bit 8*j+b = bit b of word j).

Definitions (all dimensions over GF(2)):
  live(k)    = rank of the 40 output functions of Delta_k on the real addresses.
  N_k        = matrix of determined ANF coefficients c_j(h', l') with h' != 0 and
               |l'| >= 2 (nonlinear low monomial times nonconstant high monomial).
  nonlinear output relation: g in F2^40 with g . c(h', l') = 0 for every such
               determined coefficient, i.e. g . Delta_k = P(high) + sum_i l_i Q_i(high) + R(low)
               for some off-domain completion.
  rel_nl(k)  = live(k) - rank(N_k)  = number of independent nonlinear output relations
               (relations modulo combinations that vanish identically).
  rel_mix(k) = live(k) - rank(M_k), M_k = all determined c(h' != 0, l' != 0): relations
               that need no mixed product at all.
"""
import numpy as np

NH, NL = 77, 16
FREE = np.zeros((NH, NL), dtype=bool)
FREE[76, 4:] = True
NONLIN_L = [l for l in range(1, 16) if bin(l).count('1') >= 2]
LIN_L = [1, 2, 4, 8]


def deltas(words, k):
    """(1220, 40) uint8 bit matrix of Delta_k."""
    w = np.asarray(words, dtype=np.int64)
    cur = w[:, 5 * k:5 * k + 5]
    d = cur ^ w[:, 5 * k - 5:5 * k] if k else cur.copy()
    bits = ((d[:, :, None] >> np.arange(8)[None, None, :]) & 1).reshape(len(w), 40)
    return bits.astype(np.uint8)


def anf(bits):
    """bits: (1220, n) -> ANF coefficients (77, 16, n) with off-domain values zero."""
    n = bits.shape[1]
    f = np.zeros((1232, n), dtype=np.uint8)
    f[:len(bits)] = bits
    f = f.reshape(NH, NL, n).copy()
    for b in range(4):
        for l in range(NL):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(7):
        for h in range(NH):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    return f


def inverse_anf(c):
    """Inverse Moebius (same transform over GF(2))."""
    f = c.copy()
    for b in range(7):
        for h in range(NH):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(NL):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    return f


def rows_as_ints(mat):
    """mat (n_out, n_pos) uint8 -> list of python ints (one per output)."""
    mat = np.asarray(mat, dtype=np.uint8)
    packed = np.packbits(mat, axis=1, bitorder='little')
    return [int.from_bytes(r.tobytes(), 'little') for r in packed]


def basis(xs):
    d = {}
    for x in xs:
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p]
            else:
                d[p] = x
                break
    return d


def rank(xs):
    return len(basis(xs))


def left_null(rows):
    """Basis of {g : XOR_j g_j rows[j] = 0} as int masks over the row index."""
    d = {}
    null = []
    for i, x in enumerate(rows):
        co = 1 << i
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p][0]
                co ^= d[p][1]
            else:
                d[p] = (x, co)
                break
        if not x:
            null.append(co)
    return null


def positions(kind):
    """Boolean mask (77,16) of determined ANF positions of a kind."""
    m = np.zeros((NH, NL), dtype=bool)
    if kind == 'nonlinear':
        for l in NONLIN_L:
            m[1:, l] = True
    elif kind == 'mixed':
        m[1:, 1:] = True
    elif kind == 'linear':
        for l in LIN_L:
            m[1:, l] = True
    else:
        raise ValueError(kind)
    return m & ~FREE


def structure(words, k):
    bits = deltas(words, k)
    c = anf(bits)                      # (77,16,40)
    live_rows = rows_as_ints(bits.T)
    live = rank(live_rows)
    zero_rel = left_null(live_rows)    # identically-zero combinations
    out = {'k': k, 'live': live, 'zero_relations': len(zero_rel)}
    rel = {}
    for kind in ('nonlinear', 'mixed', 'linear'):
        m = positions(kind)
        sub = c[m]                     # (npos, 40)
        rows = rows_as_ints(sub.T)
        r = rank(rows)
        out[f'rank_{kind}'] = r
        out[f'rel_{kind}'] = live - r
        rel[kind] = left_null(rows)
    # per nonlinear coordinate: rank of the (high x out) slice
    out['rank_per_low'] = {int(l): rank(rows_as_ints(c[1:, l][~FREE[1:, l]].T)) for l in range(1, 16)}
    # payload-only variant (bits 0..6 of each word; bit 7 is our helper gauge bit)
    pay = [8 * j + b for j in range(5) for b in range(7)]
    live_p = rank(rows_as_ints(bits[:, pay].T))
    rank_p = rank(rows_as_ints(c[positions('nonlinear')][:, pay].T))
    out['live_payload'] = live_p
    out['rank_nonlinear_payload'] = rank_p
    out['rel_nonlinear_payload'] = live_p - rank_p
    return out, rel, zero_rel


def describe_relations(rel, zero_rel, nbits=40):
    """Reduce relation vectors modulo identically-zero ones; return readable masks."""
    zb = basis(zero_rel)
    reps = []
    b = dict(zb)
    for g in rel:
        x = g
        for p in sorted(b, reverse=True):
            if x >> p & 1:
                x ^= b[p]
        if x:
            reps.append(g)
            b = basis(list(b.values()) + [g])
    def name(g):
        return '+'.join(f'w{i // 8}b{i % 8}' for i in range(nbits) if g >> i & 1)
    return [name(g) for g in reps], [name(g) for g in zero_rel]
