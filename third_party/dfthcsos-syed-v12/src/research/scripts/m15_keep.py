# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Move filter: a word move is kept only if it leaves every m15 relation of the target words intact."""
import numpy as np
from m15_select import m15_codes, pattern_bits, gvec


def make_keep(W_target, loaders=range(9, 15)):
    codes = {k: m15_codes(W_target, k) for k in loaders}
    def keep(row, move):
        xb = {}
        for t, nv in move:
            b = t // 5
            xb[b] = xb.get(b, 0) ^ pattern_bits(row[t], nv, t % 5)
        for b, x in xb.items():
            for k in (b, b + 1):
                if k in codes and gvec(codes[k], x):
                    return False
        return True
    return keep, codes


def make_keep_codes(batches=range(9, 15), bits=(1, 2)):
    """Keep filter protecting only the batch parities of the given bits (the two word codes)."""
    def keep(row, move):
        par = {}
        for t, nv in move:
            b = t // 5
            if b not in batches:
                continue
            x = int(row[t]) ^ int(nv)
            for bit in bits:
                par[(b, bit)] = par.get((b, bit), 0) ^ ((x >> bit) & 1)
        return not any(par.values())
    return keep
