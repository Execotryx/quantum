# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Decoupled weight repair (our own method).

Stage E2: change w only in directions that keep every coef_b = sum_c Woff_c w_bc and
every W_off = H2 - sum_b w fixed (H2 follows), so h1' and hence error_1, E_gap and
Lambda_1 are unchanged; minimize Lambda_2 + mu * E2 and bisect mu to the E2 target.
Stage H: change H2 only (E2 does not depend on H2): SLSQP on lambda_eff with
E_gap >= floor + margin, lambda_0 >= 0 (fixed branch) and error_1 <= target.
"""
import numpy as np
from scipy.optimize import minimize, linear_sum_assignment
from fastchem import N


class E2Repair:
    def __init__(self, model, w, H2, R=8, B=143, C=44, tiny=1e-6):
        self.m = model; self.R, self.B, self.C = R, B, C
        self.w0 = w.copy(); self.H20 = H2.copy()
        self.Woff = H2 - w.sum(axis=1)
        self.free = np.abs(w) > tiny
        self.sig = np.sign(w)
        a = np.where(self.free, self.Woff[:, None, :], 0.0)            # (R,B,C)
        self.a = a; self.an2 = np.maximum((a * a).sum(axis=2), 1e-300)
        self.Kb = [model.K[:, s * B:(s + 1) * B] for s in range(R)]
        self.Ab = [model.A[r * B:(r + 1) * B, r * B:(r + 1) * B] for r in range(R)]

    def dw(self, z):
        z = z.reshape(self.R, self.B, self.C) * self.free
        return z - self.a * ((self.a * z).sum(axis=2) / self.an2)[:, :, None]

    def E2(self, w):
        R, B, C = self.R, self.B, self.C
        m = self.m
        KW = [self.Kb[s] @ w[s] for s in range(R)]
        g = np.empty((R, R, C, C))
        for r in range(R):
            for s in range(R):
                g[r, s] = w[r].T @ KW[s][r * B:(r + 1) * B]
        tg = 0.0; gE2 = np.empty_like(w)
        for r in range(R):
            Aw = self.Ab[r] @ w[r]
            tg += float(np.sum(w[r] * Aw))
            acc = np.zeros((B, C))
            for s in range(R):
                acc += KW[s][r * B:(r + 1) * B] @ g[s, r]
            gE2[r] = 4 * acc - 4 * Aw
        return float(np.sum(g * g) - 2 * tg + m.ref.Tnorm2), gE2

    def lam2(self, w, H2):
        s = (np.abs(w)).sum(axis=1) + np.abs(H2)
        gw = 0.5 * s[:, None, :] * np.sign(w) + 0.5 * (s * np.sign(H2))[:, None, :]
        return float(0.25 * np.sum(s * s)), gw

    def phi(self, z, mu):
        d = self.dw(z)
        w = self.w0 + d; H2 = self.H20 + d.sum(axis=1)
        e2, ge = self.E2(w)
        l2, gl = self.lam2(w, H2)
        gz = self.dw((gl + mu * ge).ravel())          # projection is symmetric
        return l2 + mu * e2, gz.ravel()

    def solve(self, mu, z0=None, maxiter=400):
        z0 = np.zeros(self.w0.size) if z0 is None else z0
        r = minimize(self.phi, z0, args=(mu,), jac=True, method='L-BFGS-B',
                     options={'maxiter': maxiter, 'maxcor': 30, 'ftol': 1e-16, 'gtol': 1e-14})
        d = self.dw(r.x)
        w = self.w0 + d; H2 = self.H20 + d.sum(axis=1)
        return w, H2, r

    def to_target(self, target_err, mu0=1e5, iters=12, verbose=True):
        G = target_err ** 2
        lo, hi = None, None; mu = mu0; best = None; z = None
        for it in range(iters):
            w, H2, r = self.solve(mu, z0=z)
            z = r.x
            e2, _ = self.E2(w)
            l2, _ = self.lam2(w, H2)
            if verbose:
                print(f'   mu {mu:.4g}: err2 {np.sqrt(e2)*1e3:.6f} mHa, Lambda2 {l2:.6f}, nit {r.nit}', flush=True)
            if e2 <= G:
                hi = mu; best = (w, H2, e2, l2, mu)
            else:
                lo = mu
            if hi is None:
                mu *= 2
            elif lo is None:
                mu /= 2
            else:
                mu = np.sqrt(lo * hi)
            if best is not None and lo is not None and hi / lo < 1.02:
                break
        return best


class HRepair:
    """SLSQP over H2 only."""
    def __init__(self, model, w, H2, t_err=0.0199986, floor=3.914898, margin=2e-7, R=8, B=143, C=44):
        self.m = model; self.w = w; self.H20 = H2.copy(); self.R, self.B, self.C = R, B, C
        self.G = t_err ** 2; self.F = floor + margin
        self.Ur = model.U.reshape(R, B, N)
        # X_k = sum_b w_bk u_b u_b^T as (R*C, N, N); h1' = h1_base - sum_k Woff_k X_k
        self.X = np.einsum('rbp,rbc,rbq->rcpq', self.Ur, w, self.Ur).reshape(R * C, N, N)
        self.wsum = w.sum(axis=1)
        self.absw = np.abs(w).sum(axis=1)
        lam, phi = np.linalg.eigh(self.h1(H2))
        self.i0 = int(np.argmin(np.abs(lam)))
        ov = np.abs(model.V1 @ phi); qi, ii = linear_sum_assignment(-ov)
        self.perm = np.empty(N, dtype=int); self.perm[qi] = ii
        self.cache = {}

    def h1(self, H2):
        Woff = (H2 - self.wsum).ravel()
        return self.m.ref.h1_base - np.tensordot(Woff, self.X, axes=1)

    def all(self, h):
        key = h.tobytes()
        if key in self.cache:
            return self.cache[key]
        R, C = self.R, self.C
        H2 = h.reshape(R, C)
        Woff = H2 - self.wsum
        h1p = self.h1(H2)
        lam, phi = np.linalg.eigh(h1p)
        ref = self.m.ref
        absl = np.abs(lam); sg = np.sign(lam); absl[self.i0] = lam[self.i0]; sg[self.i0] = 1.0
        lam1 = absl.sum()
        s = self.absw + np.abs(H2)
        Lam = lam1 + 0.25 * np.sum(s * s)
        Egap = ref.E_upper - (ref.ecore - ref.eta * ref.beta_1 - (lam1 - lam.sum()) - 0.5 * np.sum(Woff ** 2))
        ml = lam[self.perm]
        V1 = self.m.V1
        R1 = (V1.T * ml) @ V1 - h1p
        e1sq = np.sum(R1 * R1)
        rr = np.einsum('jp,pq,jq->j', V1, R1, V1)
        Pp = phi[:, self.perm]
        G1 = 2 * ((Pp * rr) @ Pp.T - R1)
        # d h1'/d H2_k = -X_k
        def grad_h1(Gam):
            return -np.tensordot(self.X, Gam, axes=([1, 2], [0, 1]))
        gl1 = grad_h1((phi * sg) @ phi.T)
        gg = grad_h1((phi * (sg - 1)) @ phi.T) + Woff.ravel()
        g0 = grad_h1(np.outer(phi[:, self.i0], phi[:, self.i0]))
        ge1 = grad_h1(G1)
        gLam = gl1 + 0.5 * (s * np.sign(H2)).ravel()
        lev = np.sqrt(Egap * (2 * Lam - Egap))
        glev = (Egap / lev) * gLam + ((Lam - Egap) / lev) * gg
        out = dict(lev=lev, glev=glev, Egap=Egap, gg=gg, lam0=lam[self.i0], g0=g0, e1sq=e1sq, ge1=ge1, Lam=Lam)
        self.cache = {key: out}
        return out

    def solve(self, maxiter=600):
        h0 = self.H20.ravel().copy()
        cons = [{'type': 'ineq', 'fun': lambda h: (self.all(h)['Egap'] - self.F) * 1e4, 'jac': lambda h: self.all(h)['gg'] * 1e4},
                {'type': 'ineq', 'fun': lambda h: self.all(h)['lam0'] * 1e6, 'jac': lambda h: self.all(h)['g0'] * 1e6},
                {'type': 'ineq', 'fun': lambda h: (self.G - self.all(h)['e1sq']) / self.G, 'jac': lambda h: -self.all(h)['ge1'] / self.G}]
        r = minimize(lambda h: self.all(h)['lev'], h0, jac=lambda h: self.all(h)['glev'], method='SLSQP',
                     constraints=cons, options={'maxiter': maxiter, 'ftol': 1e-14})
        return r.x.reshape(self.R, self.C), r
