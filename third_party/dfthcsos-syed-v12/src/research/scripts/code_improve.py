# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Code-preserving improvement of coded words (bit-1 affine code + bit-2 quadratic code).

A set F of addresses that is itself in the code space (affine-low for bit 1, quadratic-low for
bit 2) can be flipped without leaving the code. Bit-1 moves use only the carry-free direction
(+2 if bit 1 is 0, -2 if it is 1), so bit 2 and above never change; bit-2 moves are +/-4 and keep
bits 0-1. Signed exact single-move E2 prices (plus an optional E_gap weight) feed the coset decoders;
an iteration is accepted only if the exact E2 drops.
"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from flipcost import Coster, price
from parity_code import decode_coset, decode_coset_quad, parity_bit1, parity_bit, in_S, in_S2


def helper_ok(o, n):
    return (((o >> 7) ^ (o >> 6)) & 1) == (((n >> 7) ^ (n >> 6)) & 1)


def moves(W, kind, batches=range(9, 15)):
    out = []
    for b in batches:
        for j in range(5):
            t = 5 * b + j
            col = W[:, t]
            if kind == 1:
                new = np.where(((col >> 1) & 1) == 0, col + 2, col - 2) % 256
                steps = [new]
            else:
                steps = [(col + 4) % 256, (col - 4) % 256]
            for new in steps:
                ok = helper_ok(col, new)
                for a in np.nonzero(ok)[0]:
                    out.append((int(a), t, int(new[a])))
    return out


def improve(W, w, H2, edges, ref, rounds=3, kappa_gap=0.0, verbose=True):
    W = W.copy()
    m = Model(ref); m.set_vectors(decode(W, edges)); base = m.metrics(w, H2)
    P1 = {b: parity_bit1(W, b) for b in range(9, 15)}; P2 = {b: parity_bit(W, b, 2) for b in range(9, 15)}
    for r in range(rounds):
        for kind in (1, 2):
            co = Coster(m, W, edges, w, H2)
            cands = moves(W, kind)
            a, t, v, res = price(co, cands)
            cost = 98227.0 * res[:, 0] + kappa_gap * res[:, 2]
            Wn = W.copy()
            for b in range(9, 15):
                sel = np.nonzero((t >= 5 * b) & (t < 5 * b + 5))[0]
                c = np.full(1220, np.inf); arg = np.full(1220, -1)
                for i in sel:
                    if cost[i] < c[a[i]]:
                        c[a[i]] = cost[i]; arg[a[i]] = i
                D = np.zeros(1220, dtype=np.uint8)
                val, F, s = (decode_coset if kind == 1 else decode_coset_quad)(D, c)
                if val >= 0:
                    continue
                for addr in np.nonzero(F)[0]:
                    i = arg[addr]; Wn[a[i], t[i]] = v[i]
            m2 = Model(ref); m2.set_vectors(decode(Wn, edges)); new = m2.metrics(w, H2)
            ok = new['E2'] < base['E2']
            if verbose:
                print(f'  round {r} kind {kind}: cells {int((Wn != W).sum())} err2 {base["error_2"]*1e3:.6f} -> {new["error_2"]*1e3:.6f} {"accept" if ok else "reject"}', flush=True)
            if ok:
                W, m, base = Wn, m2, new
    for b in range(9, 15):
        assert in_S(parity_bit1(W, b) ^ P1[b] ) and in_S2(parity_bit(W, b, 2) ^ P2[b])
    return W, base
