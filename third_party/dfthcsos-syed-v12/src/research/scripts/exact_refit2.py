# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""h1'-preserving weight refit for FROZEN words, with a free sign/zero pattern (our own).

Same construction as exact_refit.py (coef_rb = w_rb . Woff_r held at its start value, so h1',
error_1, lambda_1 and the eigenvalue part of E_gap are exactly those of the start weights on the
new words; step A puts E_gap on floor + margin by the exact scaling Woff -> a Woff, w -> w / a).
Step B here writes every non-pivot weight as w = P - N with P, N >= 0 and |w| = P + N, so weights
that sit at zero in v18 can switch on and signs can change (the fixed pattern of exact_refit.py
bottoms out at error_2 20.037 mHa, measured). Augmented Lagrangian on E2(w) = G2, L-BFGS-B.
"""
import sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18
from exact_refit import e2_and_grad, feasible, FLOOR


class Valley2:
    def __init__(self, m, w0, H20, t_err2=0.0199986, margin=2e-7, scale_gap=True):
        self.m = m
        R, B, C = w0.shape
        self.shape = (R, B, C)
        e0 = m.metrics(w0, H20)
        Woff0 = H20 - w0.sum(1)
        self.coef0 = np.einsum('rbc,rc->rb', w0, Woff0)
        q = 0.5 * float(np.sum(Woff0 ** 2))
        self.a = float(np.sqrt(1.0 - (e0['E_gap'] - (FLOOR + margin)) / q)) if scale_gap else 1.0
        self.Woff = self.a * Woff0
        w = w0 / self.a
        self.G2 = t_err2 ** 2
        score = np.abs(w * self.Woff[:, None, :])
        self.piv = score.argmax(axis=2)
        rr, bb = np.indices((R, B))
        self.pmask = np.zeros(w.shape, dtype=bool); self.pmask[rr, bb, self.piv] = True
        self.Wp = self.Woff[rr, self.piv]
        P = np.maximum(w, 0.0); Nn = np.maximum(-w, 0.0)
        P[self.pmask] = 0.0; Nn[self.pmask] = 0.0
        self.x0 = np.concatenate([P.ravel(), Nn.ravel()])
        pm = self.pmask.ravel()
        b1 = [(0.0, 0.0) if p else (0.0, None) for p in pm]
        self.bounds = b1 + b1
        self.nfun = 0

    def build(self, x):
        R, B, C = self.shape
        n = R * B * C
        P = x[:n].reshape(R, B, C); Nn = x[n:].reshape(R, B, C)
        w = P - Nn
        rest = np.einsum('rbc,rc->rb', w, self.Woff)
        wp = (self.coef0 - rest) / self.Wp
        w[self.pmask] = wp.ravel()
        absw = P + Nn
        absw[self.pmask] = np.abs(wp).ravel()
        return w, self.Woff + w.sum(1), absw

    def fun(self, x, nu, rho):
        w, H2, absw = self.build(x)
        s = absw.sum(1) + np.abs(H2)
        lam2 = 0.25 * float(np.sum(s * s))
        E2, gE2 = e2_and_grad(self.m, w)
        c = (E2 - self.G2) / self.G2
        f = lam2 + nu * c + 0.5 * rho * c * c
        ga = 0.5 * np.broadcast_to(s[:, None, :], w.shape)
        gw = 0.5 * (s * np.sign(H2))[:, None, :] + ((nu + rho * c) / self.G2) * gE2
        gp = np.take_along_axis(gw + ga * np.sign(w), self.piv[..., None], axis=2)[..., 0]
        gred = gw - (gp / self.Wp)[:, :, None] * self.Woff[:, None, :]
        self.last = (lam2, E2, c)
        self.nfun += 1
        return f, np.concatenate([(gred + ga).ravel(), (-gred + ga).ravel()])


def main(target_path, tag, outer=6, inner=3000, nu=39.3, rho=1e4, start=None):
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
    vy = Valley2(m, w, H2)
    x = vy.x0
    wA, H2A, _ = vy.build(x)
    show(f'step A (gap scaling a = 1 - {1 - vy.a:.3e})', m.metrics(wA, H2A))
    rng = np.random.default_rng(1)
    dchk = np.abs(rng.standard_normal(len(x))) * x * 1e-5
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
        wB, H2B, absw = vy.build(x)
        ex = m.metrics(wB, H2B)
        show(f'outer {k} (nu {nu:.3f} rho {rho:.3g} c {c:+.3e} its {res.nit} nfun {vy.nfun} nonzero {int((np.abs(wB) > 1e-9).sum())} {time.time()-t0:.0f}s)', ex)
        if feasible(ex) and (best is None or ex['lambda_eff'] < best - 1e-9):
            best = ex['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=wB, H2=H2B)
            print(f'   kept feasible (outer {k}): lambda_eff {best:.7f}', flush=True)
        np.savez(ROOT / f'work/last_{tag}.npz', words=W, w=wB, H2=H2B)
        nu = nu + rho * c
        rho = min(rho * 4, 1e8)
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], outer=int(a[3]) if len(a) > 3 else 6, inner=int(a[4]) if len(a) > 4 else 3000,
         start=a[5] if len(a) > 5 else None)
