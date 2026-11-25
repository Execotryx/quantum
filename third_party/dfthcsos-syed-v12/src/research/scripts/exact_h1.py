# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Exact single-move effects on error_1, E_gap and Lambda_1 (one eigh per move)."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from fastchem import N


def h1_effects(coster, rows_all, newV):
    """rows_all: address indices; newV: (n,76). returns (n,4): d err1^2, dE_gap, dLam1, d(E_gap)/... exact."""
    m = coster.m; ref = m.ref
    lam0 = coster.lam
    base_lam1 = np.abs(lam0).sum(); base_tr = lam0.sum()
    err0 = coster.base['error_1'] ** 2
    out = np.zeros((len(rows_all), 3))
    V1 = m.V1
    for i, a in enumerate(rows_all):
        if a < N:
            Vn = V1.copy(); Vn[a] = newV[i]
            h1p = coster.h1p; lam = lam0; phi = coster.phi
        else:
            b = a - N
            cb = coster.coef[b]
            u = m.U[b]; un = newV[i]
            h1p = coster.h1p - cb * (np.outer(un, un) - np.outer(u, u))
            lam, phi = np.linalg.eigh(h1p)
            Vn = V1
        ov = np.abs(Vn @ phi)
        qi, ii = linear_sum_assignment(-ov)
        ml = np.empty_like(lam); ml[qi] = lam[ii]
        rec = (Vn.T * ml) @ Vn
        e1 = np.sum((rec - h1p) ** 2)
        lam1 = np.abs(lam).sum(); tr = lam.sum()
        out[i] = (e1 - err0, (lam1 - tr) - (base_lam1 - base_tr), lam1 - base_lam1)
    return out
