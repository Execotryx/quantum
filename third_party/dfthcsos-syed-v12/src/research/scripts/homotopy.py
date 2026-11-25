# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Staged (homotopy) code imposition: flips in K random stages, SQP refit after each."""
import sys, time, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from sqp import SQP, restore
from repair import HRepair
from onebody import reround, coded_columns
from pipeline import h1prime, show
from m15_keep import make_keep, make_keep_codes

V18 = ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/submission.npz'
MU1 = 100.0
SURROGATE = False
END_ROUNDS = 4
EPS_STAGE = 2e-3
ANNEAL = (1e-3, 4e-4, 1.5e-4, 5e-5, 1.5e-5, 0.0)
G1_STAGE = 0.0205   # relaxed error_1 target during the stages; final polish restores 19.9986


def run(target_path, tag, stages=10, iters=150, seed=0, w=None, H2=None, start_words=None, final_iters=1500, resume=None, mu1=None):
    z = np.load(V18)
    words0 = z['angle_words'].astype(np.int64); edges = z['tree_edges']
    if w is None:
        w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    target = np.load(target_path).astype(np.int64)
    mu = MU1 if mu1 is None else mu1
    if resume is not None:
        c = np.load(resume); start_words = c['words'].astype(np.int64); w = c['w']; H2 = c['H2']
    W = (words0 if start_words is None else start_words).copy()
    cells = np.argwhere(target != W)
    rng = np.random.default_rng(seed); rng.shuffle(cells)
    ob = cells[cells[:, 0] < N]; tb = cells[cells[:, 0] >= N]
    groups = np.array_split(tb, stages)
    if resume is None:
        groups[0] = np.concatenate([ob, groups[0]])   # all one-body code flips first (before any re-rounding)
    coded = coded_columns(words0)
    keep = make_keep_codes()
    ref = Ref()
    t0 = time.time()
    for s, grp in enumerate(groups):
        for a, t in grp:
            W[a, t] = target[a, t]
        m = Model(ref); m.set_vectors(decode(W, edges))
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=20, verbose=False, cols=list(range(45, 75)), keep=keep)
        m = Model(ref); m.set_vectors(decode(W, edges))
        sq = SQP(m, w, H2, G2=0.0199986 ** 2, G1=0.01995 ** 2, F=3.914898 + 2e-7)   # fresh every stage
        sq.e1_hard = False; sq.mu1 = mu                                                 # exact err1 priced softly
        sq.e1_hard = True; restore(sq); sq.e1_hard = False
        w, H2 = sq.run(iters=iters, verbose=False)
        sq.e1_hard = True; w, H2 = restore(sq); sq.e1_hard = False
        exs = m.metrics(w, H2)
        if exs['error_1'] > 0.0199986:
            hr = HRepair(m, w, H2, t_err=0.0199986)       # H2 only: err1 back to the gate, E2 untouched
            for _ in range(3):
                H2, res = hr.solve(maxiter=1500)
                if res.success:
                    break
                hr = HRepair(m, w, H2, t_err=0.0199986)
        ex = m.metrics(w, H2)
        print(f'   after SQP: err1 {exs["error_1"]*1e3:.4f} err2 {exs["error_2"]*1e3:.6f} gap-floor {exs["E_gap"]-3.914898:.2e} Lam {exs["Lambda"]:.5f}', flush=True)
        show(f'stage {s} ({len(grp)} cells, mu1 {mu:.0f}, {time.time()-t0:.0f}s)', ex)
        pass
        np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
        np.savez(ROOT / f'work/stage_{tag}_{s}.npz', words=W, w=w, H2=H2)
    # end game: alternate [re-round, soft-err1 SQP, H2 solve]; keep the best feasible point
    best = None
    def feasible(e):
        return e['error_1'] <= 0.0199988 and e['error_2'] <= 0.0199988 and e['E_gap'] > 3.914898 + 5e-8
    if feasible(ex):
        best = (ex['lambda_eff'], W.copy(), w.copy(), H2.copy())
        np.savez(ROOT / f'work/best_{tag}.npz', words=W, w=w, H2=H2)
    for rd in range(END_ROUNDS):
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(range(9, 15)), sweeps=40, verbose=False, cols=list(range(45, 75)), keep=keep)
        m = Model(ref); m.set_vectors(decode(W, edges))
        sq = SQP(m, w, H2, G2=0.0199986 ** 2, G1=0.0199986 ** 2, F=3.914898 + 2e-7)
        sq.e1_hard = False; sq.mu1 = mu * (2 ** (rd + 1))
        w, H2 = sq.run(iters=400, verbose=False)
        sq.e1_hard = True; w, H2 = restore(sq); sq.e1_hard = False
        exs = m.metrics(w, H2)
        hr = HRepair(m, w, H2, t_err=0.0199986)
        for _ in range(3):
            H2, res = hr.solve(maxiter=1500)
            if res.success:
                break
            hr = HRepair(m, w, H2, t_err=0.0199986)
        ex = m.metrics(w, H2)
        show(f'end {rd} (mu1 {sq.mu1:.0f}; SQP err1 {exs["error_1"]*1e3:.3f}; {time.time()-t0:.0f}s)', ex)
        if feasible(ex) and (best is None or ex['lambda_eff'] < best[0]):
            best = (ex['lambda_eff'], W.copy(), w.copy(), H2.copy())
            np.savez(ROOT / f'work/best_{tag}.npz', words=W, w=w, H2=H2)
    if best is not None:
        _, W, w, H2 = best
        np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
    return W, w, H2, ex


if __name__ == '__main__':
    run(ROOT / sys.argv[1], sys.argv[2], stages=int(sys.argv[3]), iters=int(sys.argv[4]),
        resume=(ROOT / sys.argv[5]) if len(sys.argv) > 5 else None, mu1=float(sys.argv[6]) if len(sys.argv) > 6 else None)
