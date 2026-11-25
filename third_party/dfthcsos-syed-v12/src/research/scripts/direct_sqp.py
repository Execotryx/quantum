# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""One fresh SQP on fully coded, one-body re-rounded words, then re-round/SQP rounds."""
import sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from sqp import SQP, restore
from onebody import reround, coded_columns
from pipeline import h1prime, show, V18
from m15_keep import make_keep_codes


MU1 = 100.0


def main(words_path, tag, rounds=3, iters=1200, start=None):
    z = np.load(V18)
    words0 = z['angle_words'].astype(np.int64); edges = z['tree_edges']
    if start:
        c = np.load(ROOT / start); w, H2 = c['w'], c['H2']
    else:
        w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    W = np.load(ROOT / words_path).astype(np.int64)
    coded = coded_columns(words0); keep = make_keep_codes(); ref = Ref()
    m = Model(ref); m.set_vectors(decode(W, edges))
    show('start', m.metrics(w, H2))
    t0 = time.time()
    for r in range(rounds):
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=40, verbose=False, cols=list(range(45, 75)), keep=keep)
        m = Model(ref); m.set_vectors(decode(W, edges))
        show(f'r{r} one-body', m.metrics(w, H2))
        sq = SQP(m, w, H2, G2=0.0199986 ** 2, G1=0.0199986 ** 2, F=3.914898 + 2e-7)
        sq.e1_hard = False; sq.mu1 = MU1 * (3 ** r)
        for chunk in range(iters // 100):
            w, H2 = sq.run(iters=100, verbose=False)
            ex = m.metrics(w, H2)
            show(f'r{r} sqp {100 * (chunk + 1)} ({time.time()-t0:.0f}s)', ex)
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            if abs(ex['error_2'] - 0.0199986) < 2e-9 and abs(ex['E_gap'] - 3.9148982) < 3e-8 and chunk >= 3:
                break
        w, H2 = restore(sq)
        ex = m.metrics(w, H2); show(f'r{r} restore (mu1 {sq.mu1:.0f})', ex)
        np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
        if ex['error_1'] <= 0.0199987 and ex['error_2'] <= 0.0199988 and ex['E_gap'] > 3.914898 + 5e-8:
            # final one-body touch-up cannot hurt E2 or the gap
            W2, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=40, verbose=False, cols=list(range(45, 75)), keep=keep)
            m2 = Model(ref); m2.set_vectors(decode(W2, edges)); ex2 = m2.metrics(w, H2)
            if ex2['error_1'] <= ex['error_1']:
                W, m, ex = W2, m2, ex2
                np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            show('FEASIBLE', ex)
            break
    return W, w, H2


if __name__ == '__main__':
    if len(sys.argv) > 4:
        MU1 = float(sys.argv[4])
    main(sys.argv[1], sys.argv[2], start=sys.argv[3] if len(sys.argv) > 3 else None,
         rounds=int(sys.argv[5]) if len(sys.argv) > 5 else 3, iters=int(sys.argv[6]) if len(sys.argv) > 6 else 1200)
