# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Weight refit with exact analytic gradients (our own code).

x = (w (R,B,C), H2 (R,C)). Metrics from fastchem.Model; gradients:
  dE2/dWm = 4 K Wm g - 4 A Wm (block-diagonal entries)
  f(h1'):  d f/d coef_b = -u_b^T Gamma u_b, coef_b = sum_c Woff_c w_bc, Woff = H2 - sum_b w
"""
import numpy as np
from scipy.optimize import linear_sum_assignment
from fastchem import N

GATE = 0.019999
FLOOR = 3.914898


class Fit:
    def __init__(self, model, R=8, B=143, C=44):
        self.m = model; self.R, self.B, self.C = R, B, C
        self.mask = np.zeros((R * B, R * C), dtype=bool)
        for r in range(R):
            self.mask[r * B:(r + 1) * B, r * C:(r + 1) * C] = True

    def Wm(self, w):
        R, B, C = self.R, self.B, self.C
        Wm = np.zeros((R * B, R * C))
        for r in range(R):
            Wm[r * B:(r + 1) * B, r * C:(r + 1) * C] = w[r]
        return Wm

    def unblock(self, G):
        R, B, C = self.R, self.B, self.C
        return np.stack([G[r * B:(r + 1) * B, r * C:(r + 1) * C] for r in range(R)])

    def eval(self, w, H2, perm=None):
        m = self.m; ref = m.ref
        R, B, C = self.R, self.B, self.C
        Wm = self.Wm(w)
        KW = m.K @ Wm
        g = Wm.T @ KW
        AW = m.A @ Wm
        E2 = float(np.sum(g * g) - 2 * np.einsum('bk,bk->', Wm, AW) + ref.Tnorm2)
        gE2 = self.unblock(4 * KW @ g - 4 * AW)
        Woff = H2 - w.sum(axis=1)
        coef = np.einsum('rbc,rc->rb', w, Woff).reshape(-1)
        h1p = ref.h1_base - (m.U.T * coef) @ m.U
        lam, phi = np.linalg.eigh(h1p)
        if perm is None:
            ov = np.abs(m.V1 @ phi)
            qi, ii = linear_sum_assignment(-ov)
            perm = np.empty(N, dtype=int); perm[qi] = ii
        ml = lam[perm]
        R1 = (m.V1.T * ml) @ m.V1 - h1p
        e1sq = float(np.sum(R1 * R1))
        r = np.einsum('jp,pq,jq->j', m.V1, R1, m.V1)
        Pp = phi[:, perm]                               # column j = eigvec assigned to row j
        G1 = 2 * ((Pp * r) @ Pp.T - R1)
        sgn = np.sign(lam)
        Glam1 = (phi * sgn) @ phi.T
        Ggap = (phi * (sgn - 1)) @ phi.T
        lam1 = float(np.abs(lam).sum())
        s = np.abs(w).sum(axis=1) + np.abs(H2)
        lam2 = float(0.25 * np.sum(s ** 2))
        Lam = lam1 + lam2
        Egap = ref.E_upper - (ref.ecore - ref.eta * ref.beta_1 - (lam1 - float(lam.sum())) - 0.5 * float(np.sum(Woff ** 2)))

        def via_h1(Gam):
            gam = np.einsum('bp,pq,bq->b', m.U, Gam, m.U).reshape(R, B)
            gw = -gam[:, :, None] * Woff[:, None, :] + np.einsum('rb,rbc->rc', gam, w)[:, None, :]
            gH = -np.einsum('rb,rbc->rc', gam, w)
            return gw, gH
        g1w, g1H = via_h1(G1)
        gl1w, gl1H = via_h1(Glam1)
        ggw, ggH = via_h1(Ggap)
        ggw = ggw - Woff[:, None, :]; ggH = ggH + Woff
        gl2w = 0.5 * s[:, None, :] * np.sign(w); gl2H = 0.5 * s * np.sign(H2)
        out = {'E2': E2, 'e1sq': e1sq, 'Lambda': Lam, 'E_gap': Egap,
               'error_1': np.sqrt(e1sq), 'error_2': np.sqrt(max(E2, 0)),
               'lambda_eff': float(np.sqrt(Egap * (2 * Lam - Egap))) if 0 < Egap < 2 * Lam else np.nan,
               'g_E2': (gE2, np.zeros_like(H2)), 'g_e1sq': (g1w, g1H),
               'g_Lambda': (gl1w + gl2w, gl1H + gl2H), 'g_Egap': (ggw, ggH), 'perm': perm,
               'min_abs_lam': float(np.min(np.abs(lam)))}
        return out


def flat(t):
    return np.concatenate([t[0].ravel(), t[1].ravel()])
