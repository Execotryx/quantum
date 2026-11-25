# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Final polish of a candidate: restricted one-body re-rounding <-> SQP, then official check."""
import sys, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from sqp import SQP, restore
from onebody import reround, coded_columns
from pipeline import h1prime, show, V18
from m15_keep import make_keep, make_keep_codes


def main(src, tag, rounds=4, iters=800):
    z = np.load(V18)
    words0 = z['angle_words'].astype(np.int64); edges = z['tree_edges']
    c = np.load(ROOT / src)
    W = c['words'].astype(np.int64); w = c['w']; H2 = c['H2']
    coded = coded_columns(words0)
    keep = make_keep_codes()
    ref = Ref()
    m = Model(ref); m.set_vectors(decode(W, edges))
    show('start', m.metrics(w, H2))
    sq = None
    for r in range(rounds):
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=40, verbose=False, cols=list(range(45, 75)), keep=keep)
        m = Model(ref); m.set_vectors(decode(W, edges))
        show(f'r{r} one-body', m.metrics(w, H2))
        sq = SQP(m, w, H2, G2=0.0199986 ** 2, G1=0.0199986 ** 2, F=3.914898 + 2e-7)   # fresh each round
        restore(sq)
        w, H2 = sq.run(iters=iters, verbose=False)
        w, H2 = restore(sq)
        ex = m.metrics(w, H2)
        show(f'r{r} sqp', ex)
        np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
        if ex['error_1'] <= 0.0199988 and ex['error_2'] <= 0.0199988 and ex['E_gap'] > 3.914898 + 5e-8:
            break
    return W, w, H2


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
