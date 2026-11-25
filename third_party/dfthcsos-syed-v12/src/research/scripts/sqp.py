# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Equality-constrained SQP with an L-BFGS Hessian for the weight refit.

min Lambda(w, H2)  s.t.  E2 = G2,  E_gap = F,  lambda_0 = 0,  [e1sq = G1 when active]
Tiny weights (|w| < tiny) and tiny H2 entries are frozen; other signs are fixed, so
Lambda_2 is smooth. lambda_0 (the near-zero h1' eigenvalue) uses its non-negative branch
and is held at 0 by the constraint. Exact metrics are re-evaluated by fastchem.
"""
import time
import numpy as np
from alfit import ALFit


class LBFGS:
    def __init__(self, m=30):
        self.m = m; self.S = []; self.Y = []
        self.gamma = 1.0

    def update(self, s, y):
        sy = s @ y
        if sy <= 1e-12 * np.sqrt((s @ s) * (y @ y)):
            return
        self.S.append(s); self.Y.append(y)
        if len(self.S) > self.m:
            self.S.pop(0); self.Y.pop(0)
        self.gamma = sy / (y @ y)

    def apply_inv(self, q):
        q = q.copy(); al = []
        for s, y in zip(reversed(self.S), reversed(self.Y)):
            a = (s @ q) / (s @ y); al.append(a); q -= a * y
        q *= self.gamma
        for (s, y), a in zip(zip(self.S, self.Y), reversed(al)):
            b = (y @ q) / (s @ y); q += (a - b) * s
        return q


class SQP:
    def __init__(self, model, w0, H20, G2, G1, F, tiny=1e-6):
        self.al = ALFit(model)
        self.al.eps = 0.0
        self.m = model
        self.w0 = w0.copy(); self.H20 = H20.copy()
        self.fw = np.abs(w0) > tiny; self.fh = np.abs(H20) > tiny
        self.sw = np.sign(w0); self.sh = np.sign(H20)
        c0 = self.al.core(w0, H20)
        self.al.perm = c0['perm']
        self.al.i0 = int(np.argmin(np.abs(c0['lam'])))
        self.G2, self.G1, self.F = G2, G1, F
        self.x = self.pack(w0, H20)
        self.B = LBFGS(30)
        self.B.gamma = 1e-6
        self.zmask = np.zeros(self.x.shape, dtype=bool)
        self.surrogate = False  # True: constraint 3 uses the smooth off-diagonal surrogate of err1^2
        self.s_ratio = c0['e1sq'] / max(c0['S'], 1e-30)
        self.muS = 0.0          # smooth price on the least-squares err1 surrogate (Lambda per unit err1^2)
        self.mu1 = 0.0          # linear price on err1^2 in the objective (Lambda per unit)
        self.e1_hard = True     # False: err1 is never a hard constraint
        self.kappa = 71.23
        self.wpen = np.array([60.0, 0.2, 0.2, 2.0])   # merit weights per scaled constraint (Lambda units)
        self.ineq = [False, False, False, True]   # E_gap held at floor+margin (equality)

    def rebind(self, model):
        """new vectors (words changed): keep x, frozen sets and curvature memory."""
        self.m = model
        perm_old, i0_old = self.al.perm, self.al.i0
        self.al = ALFit(model); self.al.eps = 0.0
        w, H2 = self.unpack(self.x)
        c0 = self.al.core(w, H2)
        self.al.perm = c0['perm']
        self.al.i0 = int(np.argmin(np.abs(c0['lam'])))

    def unpack(self, x):
        nw = int(self.fw.sum())
        w = self.w0.copy(); H2 = self.H20.copy()
        w[self.fw] = x[:nw]; H2[self.fh] = x[nw:]
        return w, H2

    def pack(self, w, H2):
        return np.concatenate([w[self.fw], H2[self.fh]])

    def evaluate(self, x):
        w, H2 = self.unpack(x)
        absw = np.where(self.fw, self.sw * w, np.abs(w)); absh = np.where(self.fh, self.sh * H2, np.abs(H2))
        c = self.al.core(w, H2, perm=self.al.perm, absw=absw, absh=absh)
        l1w = 0.5 * c['s'][:, None, :] * self.sw; l1h = 0.5 * c['s'] * self.sh
        k = self.kappa; m1 = self.mu1
        gf = self.pack(c['gl1'][0] + l1w + k * c['gg'][0] + m1 * c['g1'][0], c['gl1'][1] + l1h + k * c['gg'][1] + m1 * c['g1'][1])
        if self.surrogate:
            c3 = (self.s_ratio * c['S'] - self.G1) / self.G1; j3 = self.s_ratio * self.pack(*c['gS']) / self.G1
        else:
            c3 = (c['e1sq'] - self.G1) / self.G1; j3 = self.pack(*c['g1']) / self.G1
        cons = [(c['E2'] - self.G2) / self.G2, (self.F - c['Egap']) * 1e3, c['lam0'] * 1e3, c3]
        J = [self.pack(c['gE2'], np.zeros_like(H2)) / self.G2, -self.pack(*c['gg']) * 1e3, self.pack(*c['g0']) * 1e3, j3]
        J = np.array(J)
        if self.zmask.any():
            gf = np.where(self.zmask, 0.0, gf); J = np.where(self.zmask[None, :], 0.0, J)
        fobj = c['Lam'] + k * (c['Egap'] - self.F) + m1 * (c['e1sq'] - self.G1)
        if self.muS:
            fobj += self.muS * (self.s_ratio * c['S'] - self.G1)
            gf = gf + self.muS * self.s_ratio * np.where(self.zmask, 0.0, self.pack(*c['gS']))
        return fobj, gf, np.array(cons), J, c

    def run(self, iters=300, verbose=True, e1_slack=-2e-5):
        x = self.x
        B = self.B
        f, g, cc, J, c = self.evaluate(x)
        fails = 0
        nu = np.zeros(4); mu_pen = 10.0
        hist = []
        t0 = time.time()
        for it in range(iters):
            act = [i for i in range(4) if (not self.ineq[i]) or (cc[i] > e1_slack and (i != 3 or self.e1_hard))]
            Ja = J[act]; ca = cc[act]
            # QP: d = -Binv (g + Ja^T nu), Ja d = -ca
            Bg = B.apply_inv(g); BJ = np.array([B.apply_inv(r) for r in Ja])
            M = Ja @ BJ.T
            rhs = ca - Ja @ Bg
            try:
                nua = np.linalg.solve(M, rhs)
            except np.linalg.LinAlgError:
                nua = np.linalg.lstsq(M, rhs, rcond=None)[0]
            d = -(Bg + BJ.T @ nua)
            if self.zmask.any():
                d = np.where(self.zmask, 0.0, d)
            nu = np.zeros(4); nu[act] = nua
            self.wpen = np.maximum(self.wpen, 1.5 * np.abs(nu))
            def merit(f_, c_):
                v = sum(self.wpen[i] * (max(0.0, c_[i]) if self.ineq[i] else abs(c_[i])) for i in range(4) if i != 3 or self.e1_hard)
                return f_ + v
            m0 = merit(f, cc)
            gl_old = g + J.T @ nu
            step = 1.0; ok = False
            for ls in range(30):
                xn = x + step * d
                fn, gn, cn, Jn, cnn = self.evaluate(xn)
                if merit(fn, cn) <= m0 - 1e-4 * step * (abs(g @ d) + 1e-30) or merit(fn, cn) < m0:
                    ok = True; break
                step *= 0.5
            if not ok:
                fails += 1
                if verbose:
                    print(f'  line search failed at it {it} (fail {fails})', flush=True)
                if fails > 4:
                    break
                g0 = B.gamma
                B.S.clear(); B.Y.clear(); B.gamma = g0 * 1e-3
                continue
            gl_new = gn + Jn.T @ nu
            s = xn - x; y = gl_new - gl_old
            # Powell damping toward a positive-definite update
            if s @ y < 0.2 * (s @ (s / B.gamma)):
                Bs = s / B.gamma
                th = 0.8 * (s @ Bs) / max(s @ Bs - s @ y, 1e-300)
                y = th * y + (1 - th) * Bs
            B.update(s, y)
            x, f, g, cc, J, c = xn, fn, gn, cn, Jn, cnn
            # variables that crossed zero: clamp to zero and hold there (fixed-sign L1 model stays exact);
            # the curvature memory is kept
            sx = self.pack(self.sw, self.sh)
            crossed = (sx * x < 0)
            if crossed.any():
                x = np.where(crossed, 0.0, x)
                self.zmask = self.zmask | crossed
                f, g, cc, J, c = self.evaluate(x)
            self.x = x
            if verbose and (it % 10 == 0 or it == iters - 1):
                ex = self.m.metrics(*self.unpack(x))
                print(f'  it {it} step {step:.3g} Lam {f:.6f} cons {[f"{v:.2e}" for v in cc]} | exact err1 {ex["error_1"]*1e3:.6f} '
                      f'err2 {ex["error_2"]*1e3:.6f} gap-floor {ex["E_gap"]-3.914898:.3e} leff {ex["lambda_eff"]:.7f} ({time.time()-t0:.0f}s)', flush=True)
            hist.append(f)
        return self.unpack(x)


def restore(sq, maxit=12, tol=1e-7, verbose=False, h2_only=False):
    """Gauss-Newton min-norm feasibility restoration on the active constraints (E2, E_gap,
    lambda_0 equalities; err1 only if violated), with backtracking on the weighted violation."""
    x = sq.x
    f, g, cc, J, c = sq.evaluate(x)
    rng4 = [i for i in range(4) if i != 3 or sq.e1_hard]
    def viol(cv):
        return sum((max(0.0, cv[i]) if sq.ineq[i] else abs(cv[i])) for i in rng4)
    for it in range(maxit):
        act = [i for i in rng4 if (not sq.ineq[i]) or cc[i] > 0]
        v0 = viol(cc) if not h2_only else sum((max(0.0, cc[i]) if sq.ineq[i] else abs(cc[i])) for i in range(1, 4))
        if v0 < tol:
            break
        Ja = J[act].copy(); ca = cc[act]
        if h2_only:
            Ja[:, :int(sq.fw.sum())] = 0.0       # move H2 only: E2 does not depend on H2
            keep = [j for j, i in enumerate(act) if i != 0]
            Ja = Ja[keep]; ca = ca[keep]
            if not len(keep):
                break
        try:
            y = np.linalg.solve(Ja @ Ja.T, ca)
        except np.linalg.LinAlgError:
            y = np.linalg.lstsq(Ja @ Ja.T, ca, rcond=None)[0]
        d = -Ja.T @ y
        step = 1.0; ok = False
        for ls in range(25):
            xn = x + step * d
            fn, gn, cn, Jn, cnn = sq.evaluate(xn)
            vn = viol(cn) if not h2_only else sum((max(0.0, cn[i]) if sq.ineq[i] else abs(cn[i])) for i in range(1, 4))
            if vn < v0:
                ok = True; break
            step *= 0.5
        if not ok:
            break
        x, f, g, cc, J, c = xn, fn, gn, cn, Jn, cnn
        if verbose:
            print(f'   restore {it}: violation {viol(cc):.3e} step {step:.3g}', flush=True)
    sq.x = x
    return sq.unpack(x)
