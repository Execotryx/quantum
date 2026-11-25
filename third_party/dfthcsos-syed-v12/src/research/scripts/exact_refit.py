# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""h1'-preserving weight refit for FROZEN words (our own).

h1' depends on the weights only through coef_rb = sum_c w_rbc Woff_rc (Woff = H2 - sum_b w).
Holding coef at its start value keeps h1' exactly: error_1, lambda_1 and the eigenvalue part of
E_gap stay those of the start weights on the new words. What is left is smooth:
  step A (gap, exact): Woff -> a Woff, w -> w / a. coef is unchanged and
         E_gap = E_gap0 + 0.5 (a^2 - 1) ||Woff||^2, so a puts E_gap on floor + margin exactly.
  step B (error_2): with Woff frozen, each row w_rb moves only inside {w_rb . Woff_r = coef_rb}
         (one pivot entry per row is eliminated), H2 = Woff + sum_b w. Minimise
         lambda_2 = 0.25 sum_rc (sum_b |w| + |H2|)^2 subject to E2(w) = G2 by an augmented
         Lagrangian with L-BFGS-B (signs of the weights kept by bounds; zeros stay zero).
A first Gauss-Newton min-norm restoration on (E2, coef, gap) failed: E2 is a narrow least-squares
valley and its linear model is only valid for very small steps (measured 12 Nov 05:44 PKT).
Exact metrics come from fastchem.Model.metrics; the official verifier decides.
"""
import sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18

FLOOR = 3.914898


def e2_and_grad(m, w):
    R, B, C = w.shape
    KW = [m.K[:, s * B:(s + 1) * B] @ w[s] for s in range(R)]
    g = np.empty((R, R, C, C))
    for r in range(R):
        for s in range(R):
            g[r, s] = w[r].T @ KW[s][r * B:(r + 1) * B]
    tg = 0.0; gE2 = np.empty_like(w)
    for r in range(R):
        Aw = m.A[r * B:(r + 1) * B, r * B:(r + 1) * B] @ w[r]
        tg += float(np.sum(w[r] * Aw))
        acc = np.zeros((B, C))
        for s in range(R):
            acc += KW[s][r * B:(r + 1) * B] @ g[s, r]
        gE2[r] = 4 * acc - 4 * Aw
    return float(np.sum(g * g) - 2 * tg + m.ref.Tnorm2), gE2


class Valley:
    def __init__(self, m, w0, H20, t_err2=0.0199986, margin=2e-7, tiny=1e-6):
        self.m = m
        R, B, C = w0.shape
        e0 = m.metrics(w0, H20)
        Woff0 = H20 - w0.sum(1)
        self.coef0 = np.einsum('rbc,rc->rb', w0, Woff0)
        q = 0.5 * float(np.sum(Woff0 ** 2))
        self.a = float(np.sqrt(1.0 - (e0['E_gap'] - (FLOOR + margin)) / q))
        self.Woff = self.a * Woff0
        w = w0 / self.a
        self.G2 = t_err2 ** 2
        self.fw = np.abs(w) > tiny
        score = np.where(self.fw, np.abs(w * self.Woff[:, None, :]), -1.0)
        self.piv = score.argmax(axis=2)
        assert (score.max(axis=2) > 0).all()
        rr, bb = np.indices((R, B))
        self.pmask = np.zeros_like(self.fw); self.pmask[rr, bb, self.piv] = True
        self.vm = self.fw & ~self.pmask
        self.wfix = np.where(self.fw, 0.0, w)
        self.Wp = self.Woff[rr, self.piv]
        self.z0 = w[self.vm].copy()
        pos = self.z0 > 0
        self.bounds = [(0.0, None) if p else (None, 0.0) for p in pos]
        self.nfun = 0

    def build(self, z):
        w = self.wfix.copy()
        w[self.vm] = z
        rest = np.einsum('rbc,rc->rb', w, self.Woff)
        w[self.pmask] = ((self.coef0 - rest) / self.Wp).ravel()
        return w, self.Woff + w.sum(1)

    def fun(self, z, nu, rho):
        w, H2 = self.build(z)
        s = np.abs(w).sum(1) + np.abs(H2)
        lam2 = 0.25 * float(np.sum(s * s))
        E2, gE2 = e2_and_grad(self.m, w)
        c = (E2 - self.G2) / self.G2
        f = lam2 + nu * c + 0.5 * rho * c * c
        g = 0.5 * s[:, None, :] * (np.sign(w) + np.sign(H2)[:, None, :]) + ((nu + rho * c) / self.G2) * gE2
        gp = np.take_along_axis(g, self.piv[..., None], axis=2)[..., 0]
        gred = g - (gp / self.Wp)[:, :, None] * self.Woff[:, None, :]
        self.last = (lam2, E2, c)
        self.nfun += 1
        return f, gred[self.vm]


def feasible(e):
    return e['error_1'] <= 0.019999 - 2e-7 and e['error_2'] <= 0.019999 - 2e-7 and e['E_gap'] > FLOOR + 5e-8


def main(target_path, tag, outer=6, inner=1500, nu=39.3, rho=1e4, start=None):
    z = np.load(V18)
    edges = z['tree_edges']
    w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    if start:
        c = np.load(ROOT / start); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    W = np.load(ROOT / target_path)
    W = (W['words'] if hasattr(W, 'files') else W).astype(np.int64)
    ref = Ref(); t0 = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    show('start (start weights on the frozen words)', m.metrics(w, H2))
    vy = Valley(m, w, H2)
    x = vy.z0
    wA, H2A = vy.build(x)
    show(f'step A (gap scaling a = 1 - {1 - vy.a:.3e}; {len(x)} variables, {int(vy.pmask.sum())} pivots)', m.metrics(wA, H2A))
    rng = np.random.default_rng(1)
    dchk = rng.standard_normal(len(x)) * np.abs(x) * 1e-3
    f0, g0 = vy.fun(x, nu, rho)
    fp, _ = vy.fun(x + dchk, nu, rho); fm, _ = vy.fun(x - dchk, nu, rho)
    print(f'gradient check: finite difference {(fp - fm) / 2:.6e} vs analytic {g0 @ dchk:.6e}; c0 {vy.last[2]:+.3e}', flush=True)
    best = None
    for k in range(outer):
        res = minimize(vy.fun, x, args=(nu, rho), jac=True, method='L-BFGS-B', bounds=vy.bounds,
                       options={'maxiter': inner, 'maxfun': 3 * inner, 'maxcor': 20, 'ftol': 1e-15, 'gtol': 1e-10})
        x = res.x
        vy.fun(x, nu, rho)
        lam2, E2, c = vy.last
        wB, H2B = vy.build(x)
        ex = m.metrics(wB, H2B)
        show(f'outer {k} (nu {nu:.3f} rho {rho:.3g} c {c:+.3e} its {res.nit} nfun {vy.nfun} {time.time()-t0:.0f}s)', ex)
        if feasible(ex) and (best is None or ex['lambda_eff'] < best - 1e-9):
            best = ex['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=wB, H2=H2B)
            print(f'   kept feasible (outer {k}): lambda_eff {best:.7f}', flush=True)
        nu = nu + rho * c
        rho = min(rho * 4, 1e8)
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], outer=int(a[3]) if len(a) > 3 else 6, inner=int(a[4]) if len(a) > 4 else 1500,
         start=a[5] if len(a) > 5 else None)
