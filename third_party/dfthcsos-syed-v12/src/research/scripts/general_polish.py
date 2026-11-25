# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""General polish from a feasible point: alfit.ALFit (all weights and H2 free, w = p - n, objective
lambda_eff, augmented Lagrangian on error_1, error_2, E_gap) warm-started with the multipliers of the
h1'-preserving solution, then exact_refit2.Valley2 to land exactly on the gates again
(h1' of the polished point is kept, so error_1 is whatever the polish left).
"""
import sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode
from pipeline import show, V18
from alfit import ALFit
from exact_refit import feasible
from exact_refit2 import Valley2


def land(m, w, H2, nu=121.0, rho=1e5, outer=3, inner=2000):
    vy = Valley2(m, w, H2)
    x = vy.x0
    for k in range(outer):
        res = minimize(vy.fun, x, args=(nu, rho), jac=True, method='L-BFGS-B', bounds=vy.bounds,
                       options={'maxiter': inner, 'maxfun': 3 * inner, 'maxcor': 20, 'ftol': 1e-15, 'gtol': 1e-10})
        x = res.x
        vy.fun(x, nu, rho)
        c = vy.last[2]
        nu = nu + rho * c; rho = min(rho * 4, 1e8)
    wB, H2B, _ = vy.build(x)
    return wB, H2B, c


def main(start, tag, outer=4, inner=1000, mu_e2=10.11, rho_e2=1e4, t_err=0.019998):
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    m = Model(Ref()); m.set_vectors(decode(W, edges))
    e0 = m.metrics(w, H2); show('start', e0)
    best = e0['lambda_eff'] if feasible(e0) else None
    t0 = time.time()
    al = ALFit(m, t_err=t_err, gap_margin=2e-7)
    mu = (0.0, mu_e2, 6.3e-4, 0.0); rho = (1000.0, rho_e2, 1.0, 1.0)
    for rd in range(outer):
        w, H2, hist = al.run(w, H2, mu=mu, rho=rho, outer=1, inner=inner, verbose=True)
        mu = tuple(al.mu); rho = tuple(al.rho)
        wL, H2L, cl = land(m, w, H2, nu=mu[1] / 0.08343)
        ex = m.metrics(wL, H2L)
        show(f'round {rd} landed (c {cl:+.2e}, {time.time()-t0:.0f}s)', ex)
        if feasible(ex) and (best is None or ex['lambda_eff'] < best - 1e-9):
            best = ex['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=wL, H2=H2L)
            print(f'   kept feasible (round {rd}): lambda_eff {best:.7f}', flush=True)
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], outer=int(a[3]) if len(a) > 3 else 4, inner=int(a[4]) if len(a) > 4 else 1000)
