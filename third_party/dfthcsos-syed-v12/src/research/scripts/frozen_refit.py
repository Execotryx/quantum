# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Weights-only refit for FROZEN coded words (so already compiled loaders stay valid).

Homotopy over the changed cells from v18's words to the frozen target (no re-rounding);
per stage a fresh SQP with err1 priced softly (E2, E_gap, lambda_0 exact). End game:
H2-only solve (err1 back to the gate, E2 untouched), then a few alternations; the best
feasible point (lowest lambda_eff) is kept in work/best_<tag>.npz.
"""
import sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from sqp import SQP, restore
from repair import HRepair
from pipeline import show, V18


def feasible(e):
    return e['error_1'] <= 0.0199988 and e['error_2'] <= 0.0199988 and e['E_gap'] > 3.914898 + 5e-8


def h2_solve(m, w, H2):
    hr = HRepair(m, w, H2, t_err=0.0199986)
    for _ in range(4):
        H2, res = hr.solve(maxiter=1500)
        if res.success:
            break
        hr = HRepair(m, w, H2, t_err=0.0199986)
    return H2


def main(target_path, tag, stages=10, iters=400, mu1=100.0, seed=0, resume=None):
    z = np.load(V18)
    W = z['angle_words'].astype(np.int64).copy(); edges = z['tree_edges']
    w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    target = np.load(ROOT / target_path).astype(np.int64)
    if resume:
        c = np.load(ROOT / resume); W = c['words'].astype(np.int64); w = c['w']; H2 = c['H2']
    cells = np.argwhere(target != W)
    rng = np.random.default_rng(seed); rng.shuffle(cells)
    ob = cells[cells[:, 0] < N]; tb = cells[cells[:, 0] >= N]
    groups = np.array_split(tb, stages)
    groups[0] = np.concatenate([ob, groups[0]])
    ref = Ref(); t0 = time.time(); best = None
    def keep(ex, W, w, H2, label):
        nonlocal best
        if feasible(ex) and (best is None or ex['lambda_eff'] < best):
            best = ex['lambda_eff']
            np.savez(ROOT / f'work/best_{tag}.npz', words=W, w=w, H2=H2)
            print(f'   kept feasible ({label}): lambda_eff {best:.7f}', flush=True)
    for s, grp in enumerate(groups):
        for a, t in grp:
            W[a, t] = target[a, t]
        m = Model(ref); m.set_vectors(decode(W, edges))
        sq = SQP(m, w, H2, G2=0.0199986 ** 2, G1=0.0199986 ** 2, F=3.914898 + 2e-7)
        sq.e1_hard = True; restore(sq); sq.e1_hard = False; sq.mu1 = mu1
        w, H2 = sq.run(iters=iters, verbose=False)
        sq.e1_hard = True; w, H2 = restore(sq); sq.e1_hard = False
        ex = m.metrics(w, H2)
        show(f'stage {s} ({len(grp)} cells, {time.time()-t0:.0f}s)', ex)
        np.savez(ROOT / f'work/stage_{tag}_{s}.npz', words=W, w=w, H2=H2)
    assert np.array_equal(W, target)
    H2a = h2_solve(m, w, H2)
    ex = m.metrics(w, H2a); show(f'H2 solve ({time.time()-t0:.0f}s)', ex); keep(ex, W, w, H2a, 'H2 solve')
    wc, H2c = w, H2a
    for rd in range(5):
        sq = SQP(m, wc, H2c, G2=0.0199986 ** 2, G1=0.0199986 ** 2, F=3.914898 + 2e-7)
        sq.e1_hard = False; sq.mu1 = mu1 * (2 ** (rd + 1))
        wc, H2c = sq.run(iters=250, verbose=False)
        sq.e1_hard = True; wc, H2c = restore(sq); sq.e1_hard = False
        exs = m.metrics(wc, H2c)
        H2c = h2_solve(m, wc, H2c)
        ex = m.metrics(wc, H2c)
        show(f'end {rd} (mu1 {sq.mu1:.0f}; after SQP err1 {exs["error_1"]*1e3:.3f} gap {exs["E_gap"]-3.914898:.2e}; {time.time()-t0:.0f}s)', ex)
        keep(ex, W, wc, H2c, f'end {rd}')
    print('BEST', best, flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], stages=int(sys.argv[3]) if len(sys.argv) > 3 else 10,
         resume=sys.argv[4] if len(sys.argv) > 4 else None)
