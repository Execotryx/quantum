# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Direct refit for coded words: one-body re-rounding -> E2 restoration on w (Gauss-Newton)
-> exact H2-only solve (E_gap, lambda_0, err1; E2 untouched) -> optional SQP polish."""
import sys, time, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from repair import E2Repair, HRepair
from sqp import SQP, restore
from onebody import reround, coded_columns
from pipeline import h1prime, show, V18
from m15_keep import make_keep, make_keep_codes


def e2_restore(m, w, H2, target_err, tiny=1e-6, iters=12):
    rep = E2Repair(m, w, H2, tiny=tiny)
    G = target_err ** 2
    w = w.copy()
    free = np.abs(w) > tiny
    for it in range(iters):
        e2, g = rep.E2(w)
        if e2 <= G:
            break
        g = g * free
        t = (e2 - G) / float(np.sum(g * g))
        wn = w - 1.02 * t * g
        cross = free & (np.sign(wn) != np.sign(w))
        wn[cross] = 0.0; free = free & ~cross
        w = wn
    return w


def main(words_path, tag, t_err=0.0199986, polish_iters=600, rounds=2):
    z = np.load(V18)
    words0 = z['angle_words'].astype(np.int64); edges = z['tree_edges']
    w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    W = np.load(ROOT / words_path).astype(np.int64)
    coded = coded_columns(words0)
    keep = make_keep_codes()
    ref = Ref()
    m = Model(ref); m.set_vectors(decode(W, edges))
    show('start', m.metrics(w, H2))
    t0 = time.time()
    for r in range(rounds):
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=40, verbose=False, cols=list(range(45, 75)), keep=keep)
        m = Model(ref); m.set_vectors(decode(W, edges))
        show(f'r{r} one-body', m.metrics(w, H2))
        w = e2_restore(m, w, H2, t_err)
        show(f'r{r} E2 restore', m.metrics(w, H2))
        sqh = SQP(m, w, H2, G2=t_err ** 2, G1=t_err ** 2, F=3.914898 + 2e-7)
        w, H2 = restore(sqh, maxit=200, h2_only=True)
        ex = m.metrics(w, H2)
        show(f'r{r} H2 restore ({time.time()-t0:.0f}s)', ex)
        np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
        if polish_iters:
            sq = SQP(m, w, H2, G2=t_err ** 2, G1=t_err ** 2, F=3.914898 + 2e-7)
            restore(sq)
            w2, H22 = sq.run(iters=polish_iters, verbose=False)
            w2, H22 = restore(sq)
            ex2 = m.metrics(w2, H22)
            show(f'r{r} SQP polish ({time.time()-t0:.0f}s)', ex2)
            ok = ex2['error_1'] <= 0.0199989 and ex2['error_2'] <= 0.0199989 and ex2['E_gap'] > 3.914898 + 5e-8
            if ok and ex2['lambda_eff'] < ex['lambda_eff']:
                w, H2 = w2, H22
                np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
    show('final', m.metrics(w, H2))
    return W, w, H2


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
