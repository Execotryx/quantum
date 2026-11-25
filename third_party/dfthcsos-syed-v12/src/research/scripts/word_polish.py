# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Word polish for coded batches (our own): alternate code-safe word moves and the h1'-preserving refit.

Moves: single-word steps of +/-8, +/-16, +/-32 on two-body rows of columns 45-74. They leave bits 0-2
of every word unchanged (so the word LSB codes, the bit-1 parity code and the bit-2 parity code of
batches 9-14 are untouched) and are filtered to keep the bit7^bit6 helper. Batches 0-8 are not touched.
Each move is priced exactly in E2 and to first order in h1' (flipcost.Coster) with the current
multipliers: dLambda = nu dE2 + dLambda_1 + kappa_gap dE_gap + eta d(err1^2). One move per row per
round; a round is accepted only if the exactly evaluated priced objective falls. After the rounds,
exact_refit2.Valley2 re-fits the weights (h1' held, E_gap put back on the floor, E2 on its target).
"""
import sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18
from flipcost import Coster, price, helper_ok
from exact_refit import feasible
from exact_refit2 import Valley2

G2 = 0.0199986 ** 2


def refit(m, w, H2, nu, rho=1e4, outer=5, inner=2000):
    vy = Valley2(m, w, H2)
    x = vy.x0
    c = 0.0
    for k in range(outer + 2):
        res = minimize(vy.fun, x, args=(nu, rho), jac=True, method='L-BFGS-B', bounds=vy.bounds,
                       options={'maxiter': inner, 'maxfun': 3 * inner, 'maxcor': 20, 'ftol': 1e-15, 'gtol': 1e-10})
        x = res.x
        vy.fun(x, nu, rho)
        c = vy.last[2]
        if k >= outer - 1 and -2e-5 < c < 1e-5:
            break
        nu = max(0.0, nu + rho * c); rho = min(rho * 4, 1e8)
    wB, H2B, _ = vy.build(x)
    return wB, H2B, nu, c


def word_round(ref, W, edges, w, H2, nu_abs, kg, eta, cols, steps, per_round, thr=1e-4):
    m = Model(ref); m.set_vectors(decode(W, edges))
    e0 = m.metrics(w, H2)
    co = Coster(m, W, edges, w, H2)
    cands = []
    for t in cols:
        for st in steps:
            new = (W[:, t] + st) % 256
            ok = helper_ok(W[:, t], new); ok[:N] = False
            cands += [(int(a), t, int(new[a])) for a in np.nonzero(ok)[0]]
    a, tt, v, res = price(co, cands)
    dL = nu_abs * res[:, 0] + res[:, 3] + kg * res[:, 2] + eta * res[:, 1]
    used = set(); pick = []
    for i in np.argsort(dL):
        if dL[i] > -thr or len(pick) >= per_round:
            break
        if int(a[i]) in used:
            continue
        used.add(int(a[i])); pick.append(int(i))
    while pick:
        Wn = W.copy()
        for i in pick:
            Wn[a[i], tt[i]] = v[i]
        m2 = Model(ref); m2.set_vectors(decode(Wn, edges))
        e1 = m2.metrics(w, H2)
        dJ = ((e1['Lambda'] - e0['Lambda']) + nu_abs * (e1['E2'] - e0['E2']) + kg * (e1['E_gap'] - e0['E_gap'])
              + eta * (e1['error_1'] ** 2 - e0['error_1'] ** 2))
        if dJ < 0 and e1['error_1'] < 0.01997:
            return Wn, m2, e1, len(pick), dJ, float(dL[pick].sum())
        pick = pick[:len(pick) // 2]
    return W, m, e0, 0, 0.0, 0.0


def main(start, tag, cycles=3, rounds=6, per_round=150, nu_rel=121.2, kg=10.0, eta=2000.0):
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    W0 = W.copy()
    ref = Ref(); t0 = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    e = m.metrics(w, H2); show('start', e)
    best = e['lambda_eff'] if feasible(e) else None
    cols = list(range(45, 75)); steps = (8, -8, 16, -16, 32, -32)
    for cy in range(cycles):
        for rd in range(rounds):
            W, m, e, n, dJ, pred = word_round(ref, W, edges, w, H2, nu_rel / G2, kg, eta, cols, steps, per_round)
            show(f'cycle {cy} round {rd}: {n} moves, priced exact {dJ:+.4f} (predicted {pred:+.4f}), {time.time()-t0:.0f}s', e)
            if n == 0:
                break
        w, H2, nu_rel, cc = refit(m, w, H2, nu_rel)
        e = m.metrics(w, H2)
        show(f'cycle {cy} refit (nu {nu_rel:.2f}, c {cc:+.2e}, cells changed so far {int((W != W0).sum())}, {time.time()-t0:.0f}s)', e)
        np.savez(ROOT / f'work/last_{tag}.npz', words=W, w=w, H2=H2)
        if feasible(e) and (best is None or e['lambda_eff'] < best - 1e-9):
            best = e['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            np.savez(ROOT / f'work/cand_{tag}_words.npz', words=W)
            print(f'   kept feasible (cycle {cy}): lambda_eff {best:.7f}', flush=True)
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], cycles=int(a[3]) if len(a) > 3 else 3, rounds=int(a[4]) if len(a) > 4 else 6,
         per_round=int(a[5]) if len(a) > 5 else 150)
