# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Parity-code (sixth relation) imposition on batches 9-14 that preserves the m15 codes.

m15 code of loader k: payload functional g whose block parity (XOR of g.Delta_k over the 16
addresses of a block) is the same on every real block 0..75. A flip of word j in batch b changes
Delta_b and Delta_{b+1} by the same 8-bit pattern x in slot j. Batches are processed 9 -> 14; for
batch b a per-block dynamic program picks, for every code flip, the word/direction such that the
block parity changes of all m15 functionals of loader b cancel the changes already made by batch
b-1, at minimum cost. Parity-neutral double flips are available as repair items.
"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from relations import deltas, anf, rows_as_ints, left_null, basis
from parity_code import decode_coset, parity_bit1, in_S

PAY = [8 * j + b for j in range(5) for b in range(7)]


def m15_codes(W, k):
    d = deltas(W, k)[:, PAY]
    c = anf(d)
    rows = c[1:76, 15]
    return left_null(rows_as_ints(rows.T))          # payload functionals (35-bit ints)


def pattern_bits(old, new, j):
    """35-bit payload change vector for slot j."""
    x = int(old) ^ int(new)
    return sum(((x >> b) & 1) << (7 * j + b) for b in range(7))


def gvec(G, xv):
    v = 0
    for i, g in enumerate(G):
        if bin(g & xv).count('1') & 1:
            v |= 1 << i
    return v


def helper_ok(o, n):
    return (((o >> 7) ^ (o >> 6)) & 1) == (((n >> 7) ^ (n >> 6)) & 1)


def block_dp(items, target, nbits):
    """items: list of option lists [(cost, vec, payload)], choose one option per item
    (an option may be 'none' only if present) with XOR of vecs == target, min cost."""
    INF = float('inf')
    S = 1 << nbits
    best = np.full(S, INF); best[0] = 0.0
    back = []
    for opts in items:
        nb = np.full(S, INF); arg = np.full((S, 2), -1, dtype=np.int64)
        for oi, (c, v, _) in enumerate(opts):
            src = np.arange(S)
            dst = src ^ v
            val = best + c
            upd = val < nb[dst]
            nb[dst[upd]] = val[upd]; arg[dst[upd], 0] = src[upd]; arg[dst[upd], 1] = oi
        back.append(arg); best = nb
    if not np.isfinite(best[target]):
        return None
    choice = []; s = target
    for arg in reversed(back):
        prev, oi = arg[s]; choice.append(oi); s = prev
    return best[target], list(reversed(choice))


BIT1 = sum(1 << (7 * j + 1) for j in range(5))


def bit1_free(G):
    """basis of the subspace of span(G) with zero coefficients on every bit-1 position."""
    # eliminate bit-1 coordinates: track combinations
    rows = [(g & BIT1, g) for g in G]
    d = {}
    out = []
    for r, g in rows:
        x, y = r, g
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p][0]; y ^= d[p][1]
            else:
                d[p] = (x, y); break
        if not x and y:
            out.append(y)
    return list(basis(out).values())


def impose(W18, cost_fn, batches=range(9, 15), ref_batch=8, max_double=3, verbose=True, mode='all'):
    W = W18.copy()
    P = parity_bit1(W18, ref_batch)
    codes = {k: m15_codes(W18, k) for k in range(9, 15)}
    if mode == 'bit1free':
        codes = {k: bit1_free(G) for k, G in codes.items()}
    prev_contrib = np.zeros(77, dtype=np.int64)     # per-block vec contribution of batch b-1 to loader b codes
    total = 0.0; nfl = 0; ndouble = 0; fails = 0
    for b in batches:
        G = codes[b]; Gn = codes.get(b + 1, [])
        nb = len(G)
        # per-address single-flip options and costs
        opt = {}
        cvec = np.full(1220, np.inf)
        for a in range(1220):
            lst = []
            for j in range(5):
                t = 5 * b + j
                for st in (2, -2):
                    nv = (W[a, t] + st) % 256
                    if not helper_ok(W[a, t], nv):
                        continue
                    c = cost_fn(a, t, nv)
                    xv = pattern_bits(W[a, t], nv, j)
                    lst.append((c, xv, (t, nv)))
            opt[a] = lst
            if lst:
                cvec[a] = min(o[0] for o in lst)
        D = parity_bit1(W, b) ^ P
        val, F, s = decode_coset(D, cvec)
        new_contrib = np.zeros(77, dtype=np.int64)
        for h in range(77):
            addrs = [a for a in range(16 * h, min(16 * h + 16, 1220)) if F[a]]
            items = [[(c, gvec(G, xv) if h < 76 else 0, (a, pl, xv)) for (c, xv, pl) in opt[a]] for a in addrs]
            target = int(prev_contrib[h]) if h < 76 else 0
            res = block_dp(items, target, nb) if items or target else (0.0, [])
            if res is None and h < 76:
                # repair with up to max_double parity-neutral double flips at addresses of this block
                extra = []
                for a in range(16 * h, min(16 * h + 16, 1220)):
                    if a in addrs:
                        continue
                    dl = [(0.0, 0, None)]
                    singles = opt[a]
                    for i1 in range(len(singles)):
                        for i2 in range(i1 + 1, len(singles)):
                            c1, x1, p1 = singles[i1]; c2, x2, p2 = singles[i2]
                            if p1[0] == p2[0]:
                                continue
                            dl.append((c1 + c2, gvec(G, x1 ^ x2), (a, (p1, p2), x1 ^ x2)))
                    dl.sort(key=lambda o: o[0]); extra.append(dl[:12])
                res = block_dp(items + extra, target, nb)
                if res is not None:
                    items = items + extra
            if res is None:
                fails += 1
                continue
            cost, choice = res
            total += cost
            for it, oi in zip(items, choice):
                c, vec, pl = it[oi]
                if pl is None:
                    continue
                a, payload, xv = pl
                if isinstance(payload[0], tuple):
                    for (t, nv) in payload:
                        W[a, t] = nv
                    ndouble += 1
                else:
                    t, nv = payload; W[a, t] = nv; nfl += 1
                if h < 76:
                    new_contrib[h] ^= gvec(Gn, xv) if Gn else 0
        prev_contrib = new_contrib
        if verbose:
            print(f'  batch {b}: code flips {int(F.sum())} m15 functionals {nb} fails {fails}', flush=True)
    return W, total, nfl, ndouble, fails


def dead_cells(W, edges, cols):
    """(a, t) where rotation t acts on two exact zeros in the official float decoding."""
    import numpy as np
    ang = np.asarray(W, dtype=np.float64) / 128.0
    n = ang.shape[0]
    v = np.zeros((n, 76)); v[:, 0] = 1.0
    dead = np.zeros((n, 75), dtype=bool)
    for t, (p, c) in enumerate(edges):
        dead[:, t] = (v[:, p] == 0.0) & (v[:, c] == 0.0)
        pv = v[:, p].copy(); cv = v[:, c].copy()
        th = np.pi * ang[:, t]; co = np.cos(th); si = np.sin(th)
        v[:, p] = co * pv - si * cv; v[:, c] = si * pv + co * cv
    out = set()
    for t in cols:
        for a in np.nonzero(dead[:, t])[0]:
            out.add((int(a), int(t)))
    return out


def impose_dead(W18, edges, cost_fn, batches=range(9, 15), ref_batch=8, verbose=True, max_dead_opts=24):
    """Like impose(), with free dead-cell changes (bits 0,1 and helper kept) as repair items."""
    W = W18.copy()
    P = parity_bit1(W18, ref_batch)
    codes = {k: m15_codes(W18, k) for k in range(9, 15)}
    prev_contrib = np.zeros(77, dtype=np.int64)
    total = 0.0; nfl = 0; ndead = 0; fails = 0
    for b in batches:
        G = codes[b]; Gn = codes.get(b + 1, [])
        nb = len(G)
        dead = dead_cells(W, edges, range(5 * b, 5 * b + 5))
        opt = {}
        cvec = np.full(1220, np.inf)
        for a in range(1220):
            lst = []
            for j in range(5):
                t = 5 * b + j
                for st in (2, -2):
                    nv = (W[a, t] + st) % 256
                    if not helper_ok(W[a, t], nv):
                        continue
                    c = 0.0 if (a, t) in dead else cost_fn(a, t, nv)
                    lst.append((c, pattern_bits(W[a, t], nv, j), (t, nv)))
            opt[a] = lst
            if lst:
                cvec[a] = min(o[0] for o in lst)
        D = parity_bit1(W, b) ^ P
        val, F, s = decode_coset(D, cvec)
        new_contrib = np.zeros(77, dtype=np.int64)
        for h in range(77):
            lo, hi = 16 * h, min(16 * h + 16, 1220)
            addrs = [a for a in range(lo, hi) if F[a]]
            items = [[(c, gvec(G, xv) if h < 76 else 0, (a, pl, xv)) for (c, xv, pl) in opt[a]] for a in addrs]
            if h < 76:
                for a in range(lo, hi):
                    if a in addrs:
                        continue
                    for j in range(5):
                        t = 5 * b + j
                        if (a, t) not in dead:
                            continue
                        o = int(W[a, t]); dl = [(0.0, 0, None)]; seen = set()
                        for nv in range(256):
                            if nv == o or (nv & 3) != (o & 3) or not helper_ok(o, nv):
                                continue
                            xv = pattern_bits(o, nv, j); gv = gvec(G, xv)
                            if gv in seen:
                                continue
                            seen.add(gv); dl.append((1e-12, gv, (a, (t, nv), xv)))
                        items.append(dl[:max_dead_opts])
            target = int(prev_contrib[h]) if h < 76 else 0
            res = block_dp(items, target, nb) if (items or target) else (0.0, [])
            if res is None:
                fails += 1
                continue
            cost, choice = res
            total += cost
            for it, oi in zip(items, choice):
                c, vec, pl = it[oi]
                if pl is None:
                    continue
                a, (t, nv), xv = pl
                W[a, t] = nv
                if (a, t) in dead and not F[a]:
                    ndead += 1
                else:
                    nfl += 1
                if h < 76 and Gn:
                    new_contrib[h] ^= gvec(Gn, xv)
        prev_contrib = new_contrib
        if verbose:
            print(f'  batch {b}: code flips {int(F.sum())} dead cells {len(dead)} m15 functionals {nb} fails so far {fails}', flush=True)
    return W, total, nfl, ndead, fails
