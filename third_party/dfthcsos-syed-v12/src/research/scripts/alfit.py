# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Constrained weight refit: minimize lambda_eff s.t. err1, err2 <= target, E_gap >= floor + margin.

Augmented Lagrangian, inner L-BFGS-B. w = p - n (p, n >= 0) makes the L1 part smooth.
The smallest |eigenvalue| kink is smoothed with sqrt(l^2 + eps^2) inside the solver only;
all reported numbers are exact (fastchem.Model.metrics) and the official verifier decides.
"""
import time
import numpy as np
from scipy.optimize import minimize, linear_sum_assignment
from fastchem import N

EPS = 1e-9


class ALFit:
    def __init__(self, model, R=8, B=143, C=44, t_err=0.0199985, gap_floor=3.914898, gap_margin=3e-7):
        self.m = model; self.R, self.B, self.C = R, B, C
        self.G = t_err ** 2
        self.F = gap_floor + gap_margin
        m = model
        self.Kb = [[m.K[r * B:(r + 1) * B, s * B:(s + 1) * B] for s in range(R)] for r in range(R)]
        self.Ab = [m.A[r * B:(r + 1) * B, r * B:(r + 1) * B] for r in range(R)]
        self.Ur = m.U.reshape(R, B, N)
        self.perm = None
        self.i0 = None
        self.nw = R * B * C
        self.nh = R * C

    def unpack(self, x):
        R, B, C = self.R, self.B, self.C
        p = x[:self.nw].reshape(R, B, C); n = x[self.nw:2 * self.nw].reshape(R, B, C)
        hp = x[2 * self.nw:2 * self.nw + self.nh].reshape(R, C); hn = x[2 * self.nw + self.nh:].reshape(R, C)
        return p, n, hp, hn

    def core(self, w, H2, perm=None, smooth=True, absw=None, absh=None):
        """exact-ish metrics and gradients wrt w and H2."""
        R, B, C = self.R, self.B, self.C
        m = self.m; ref = m.ref
        # E2 via blocks
        KW = np.empty((R, R * B, C))       # KW[s] = K[:, s-block] @ w[s]  -> (1144, C)
        for s in range(R):
            KW[s] = m.K[:, s * B:(s + 1) * B] @ w[s]
        # g[r,s] = w[r]^T K[r,s] w[s]  (C x C)
        g = np.empty((R, R, C, C))
        for r in range(R):
            for s in range(R):
                g[r, s] = w[r].T @ KW[s][r * B:(r + 1) * B]
        tg = 0.0; gE2 = np.empty_like(w)
        for r in range(R):
            Aw = self.Ab[r] @ w[r]
            tg += float(np.sum(w[r] * Aw))
            # (K Wm g)[r-block rows, r cols] = sum_s KW[s][r rows] @ g[s, r]
            acc = np.zeros((B, C))
            for s in range(R):
                acc += KW[s][r * B:(r + 1) * B] @ g[s, r]
            gE2[r] = 4 * acc - 4 * Aw
        E2 = float(np.sum(g * g) - 2 * tg + ref.Tnorm2)
        Woff = H2 - w.sum(axis=1)
        coef = np.einsum('rbc,rc->rb', w, Woff)
        h1p = ref.h1_base - np.einsum('rbp,rb,rbq->pq', self.Ur, coef, self.Ur)
        lam, phi = np.linalg.eigh(h1p)
        if perm is None:
            ov = np.abs(m.V1 @ phi); qi, ii = linear_sum_assignment(-ov)
            perm = np.empty(N, dtype=int); perm[qi] = ii
        ml = lam[perm]
        R1 = (m.V1.T * ml) @ m.V1 - h1p
        e1sq = float(np.sum(R1 * R1))
        rr = np.einsum('jp,pq,jq->j', m.V1, R1, m.V1)
        Pp = phi[:, perm]
        G1 = 2 * ((Pp * rr) @ Pp.T - R1)
        if getattr(self, 'eps', 0.0) > 0:
            absl = np.sqrt(lam ** 2 + self.eps ** 2); dabs = lam / absl
        else:
            absl = np.abs(lam); dabs = np.sign(lam)
        if self.i0 is not None:
            absl[self.i0] = lam[self.i0]; dabs[self.i0] = 1.0   # fixed non-negative branch
        Glam1 = (phi * dabs) @ phi.T
        Ggap = (phi * (dabs - 1)) @ phi.T
        lam1 = float(absl.sum())
        s_ = (np.abs(w) if absw is None else absw).sum(axis=1) + (np.abs(H2) if absh is None else absh)
        Lam = lam1 + float(0.25 * np.sum(s_ ** 2))
        Egap = ref.E_upper - (ref.ecore - ref.eta * ref.beta_1 - (lam1 - float(lam.sum())) - 0.5 * float(np.sum(Woff ** 2)))

        def via(Gam):
            gam = np.einsum('rbp,pq,rbq->rb', self.Ur, Gam, self.Ur)
            gw = -gam[:, :, None] * Woff[:, None, :] + np.einsum('rb,rbc->rc', gam, w)[:, None, :]
            gH = -np.einsum('rb,rbc->rc', gam, w)
            return gw, gH
        g1 = via(G1); gl1 = via(Glam1); gg = via(Ggap)
        # smooth surrogate of err1^2: least-squares residual of h1' on span{v_j v_j^T} (a quadratic form
        # in h1'; equals err1^2 with the best coefficients instead of the exact eigenvalues, so S <= err1^2)
        if not hasattr(self, '_Gm_inv'):
            self._Gm_inv = np.linalg.inv((m.V1 @ m.V1.T) ** 2)
        bvec = np.einsum('jp,pq,jq->j', m.V1, h1p, m.V1)
        lam_star = self._Gm_inv @ bvec
        R_alt = (m.V1.T * lam_star) @ m.V1 - h1p
        S_sur = float(np.sum(R_alt * R_alt))
        gS = via(-2 * R_alt)
        g0 = via(np.outer(phi[:, self.i0], phi[:, self.i0])) if self.i0 is not None else None
        lam0 = float(lam[self.i0]) if self.i0 is not None else 0.0
        return dict(S=S_sur, gS=gS, g0=g0, lam0=lam0, E2=E2, gE2=gE2, e1sq=e1sq, g1=g1, Lam=Lam, gl1=gl1, s=s_, Egap=Egap, gg=gg, perm=perm, lam=lam)

    def fun(self, x):
        p, n, hp, hn = self.unpack(x)
        w = p - n; H2 = hp - hn
        c = self.core(w, H2, perm=self.perm, absw=p + n, absh=hp + hn)
        a_E, a_L = c['Egap'], c['Lam']
        lev = np.sqrt(max(a_E * (2 * a_L - a_E), 1e-30))
        dA = a_E / lev; dE = (a_L - a_E) / lev
        # objective grads wrt w (for L1 part handled through p,n), H2
        # Lambda = lam1 + 0.25 sum s^2 ; d/dp = 0.5 s (since |w| -> p+n), d/dn = 0.5 s
        gw_lam1, gH_lam1 = c['gl1']
        f = lev
        gw = dA * gw_lam1 + dE * c['gg'][0]
        gpn_l2 = dA * 0.5 * np.broadcast_to(c['s'][:, None, :], w.shape)
        ghpn_l2 = dA * 0.5 * c['s']
        gH = dA * gH_lam1 + dE * c['gg'][1]
        # constraints
        cons = [((c['e1sq'] - self.G) / self.G, (c['g1'][0] / self.G, c['g1'][1] / self.G)),
                ((c['E2'] - self.G) / self.G, (c['gE2'] / self.G, np.zeros_like(H2))),
                ((self.F - c['Egap']) / 1e-4, (-c['gg'][0] / 1e-4, -c['gg'][1] / 1e-4)),
                ((self.lam0_min - c['lam0']) / 1e-6, (-c['g0'][0] / 1e-6, -c['g0'][1] / 1e-6))]
        self.last = c; self.last_cons = [cc[0] for cc in cons]
        for i, (ci, (gwi, gHi)) in enumerate(cons):
            t = self.mu[i] + self.rho[i] * ci
            if t > 0:
                f += (t * t - self.mu[i] ** 2) / (2 * self.rho[i])
                gw = gw + t * gwi; gH = gH + t * gHi
            else:
                f += -self.mu[i] ** 2 / (2 * self.rho[i])
        gp = gw + gpn_l2; gn = -gw + gpn_l2
        ghp = gH + ghpn_l2; ghn = -gH + ghpn_l2
        return f, np.concatenate([gp.ravel(), gn.ravel(), ghp.ravel(), ghn.ravel()])

    def run(self, w0, H20, mu=(2e-3, 3.3, 6e-4, 0.0), rho=(1.0, 300.0, 1.0, 1.0), outer=8, inner=300, verbose=True, lam0_min=0.0):
        x = np.concatenate([np.maximum(w0, 0).ravel(), np.maximum(-w0, 0).ravel(),
                            np.maximum(H20, 0).ravel(), np.maximum(-H20, 0).ravel()])
        bounds = [(0, None)] * x.size
        self.mu = list(mu); self.rho = list(rho); self.lam0_min = lam0_min
        c0 = self.core(w0, H20)
        self.perm = c0['perm']
        self.i0 = int(np.argmin(np.abs(c0['lam'])))
        hist = []
        for it in range(outer):
            t = time.time()
            r = minimize(self.fun, x, jac=True, method='L-BFGS-B', bounds=bounds,
                         options={'maxiter': inner, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-12})
            x = r.x
            self.fun(x)
            cs = self.last_cons
            c = self.last
            for i in range(4):
                self.mu[i] = max(0.0, self.mu[i] + self.rho[i] * cs[i])
                if cs[i] > 1e-6:
                    self.rho[i] *= 4
            p, n, hp, hn = self.unpack(x)
            w = p - n; H2 = hp - hn
            ex = self.m.metrics(w, H2)
            hist.append(ex)
            if verbose:
                print(f'  AL {it}: nit {r.nit} {time.time()-t:.0f}s err1 {ex["error_1"]*1e3:.6f} err2 {ex["error_2"]*1e3:.6f} '
                      f'gap-floor {ex["E_gap"]-3.914898:.3e} Lam {ex["Lambda"]:.6f} leff {ex["lambda_eff"]:.7f} mu {[f"{v:.3g}" for v in self.mu]}', flush=True)
        p, n, hp, hn = self.unpack(x)
        return p - n, hp - hn, hist


class ScalarFit(ALFit):
    """min Lambda + kappa*E_gap + mu1*e1sq + mu2*E2 over (p,n,hp,hn) >= 0, |lambda| smoothed."""
    def sfun(self, x):
        p, n, hp, hn = self.unpack(x)
        w = p - n; H2 = hp - hn
        c = self.core(w, H2, perm=self.perm, absw=p + n, absh=hp + hn)
        k, m1, m2 = self.kappa, self.mu1, self.mu2
        vg = max(0.0, self.F - c['Egap']); v1 = max(0.0, c['e1sq'] - self.G1)
        f = c['Lam'] + k * c['Egap'] + m1 * c['e1sq'] + m2 * c['E2'] + self.rho_g * vg * vg + self.rho_1 * v1 * v1
        kg = k - 2 * self.rho_g * vg; k1 = m1 + 2 * self.rho_1 * v1
        gw = c['gl1'][0] + kg * c['gg'][0] + k1 * c['g1'][0] + m2 * c['gE2']
        gH = c['gl1'][1] + kg * c['gg'][1] + k1 * c['g1'][1]
        l1w = 0.5 * np.broadcast_to(c['s'][:, None, :], w.shape); l1h = 0.5 * c['s']
        self.last = c
        return f, np.concatenate([(gw + l1w).ravel(), (-gw + l1w).ravel(), (gH + l1h).ravel(), (-gH + l1h).ravel()])

    def solve(self, x0, maxiter=500):
        bounds = [(0, None)] * x0.size
        r = minimize(self.sfun, x0, jac=True, method='L-BFGS-B', bounds=bounds,
                     options={'maxiter': maxiter, 'maxcor': 40, 'ftol': 1e-16, 'gtol': 1e-12})
        return r

    def to_target(self, w0, H20, target_err, kappa=3.998, mu1=62.0, mu2=1e5, eps=1e-5, iters=10, maxiter=500, verbose=True,
                  rho_g=1e6, rho_1=1e10, e1_target=0.0199984):
        self.kappa, self.mu1, self.eps = kappa, mu1, eps
        self.rho_g, self.rho_1, self.G1 = rho_g, rho_1, e1_target ** 2
        self.i0 = None
        c0 = self.core(w0, H20); self.perm = c0['perm']
        x0 = np.concatenate([np.maximum(w0, 0).ravel(), np.maximum(-w0, 0).ravel(),
                             np.maximum(H20, 0).ravel(), np.maximum(-H20, 0).ravel()])
        G = target_err ** 2
        lo = hi = None; best = None; x = x0; mu = mu2
        for it in range(iters):
            self.mu2 = mu
            t = time.time()
            r = self.solve(x, maxiter=maxiter)
            p, n, hp, hn = self.unpack(r.x)
            w = p - n; H2 = hp - hn
            ex = self.m.metrics(w, H2)
            if verbose:
                print(f'   mu2 {mu:.4g}: nit {r.nit} {time.time()-t:.0f}s err1 {ex["error_1"]*1e3:.6f} err2 {ex["error_2"]*1e3:.6f} '
                      f'gap-floor {ex["E_gap"]-3.914898:.3e} Lam {ex["Lambda"]:.6f} leff {ex["lambda_eff"]:.7f}', flush=True)
            x = r.x
            if ex['E2'] <= G:
                hi = mu; best = (w.copy(), H2.copy(), ex, mu)
            else:
                lo = mu
            if hi is None:
                mu *= 2
            elif lo is None:
                mu /= 2
            else:
                mu = np.sqrt(lo * hi)
            if best is not None and lo is not None and hi / lo < 1.05:
                break
        return best
