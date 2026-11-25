# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Exact single-word move costs (two-body E2 exact; h1' effects first order)."""
import sys, time, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N


def helper_ok(old, new):
    return (((old >> 7) ^ (old >> 6)) & 1) == (((new >> 7) ^ (new >> 6)) & 1)


class Coster:
    def __init__(self, model, words, edges, w, H2):
        self.m = model; self.words = np.asarray(words, dtype=np.int64); self.edges = edges
        self.w = w; self.H2 = H2
        R, B, C = w.shape
        m = model
        self.Wm = np.zeros((R * B, R * C))
        for r in range(R):
            self.Wm[r * B:(r + 1) * B, r * C:(r + 1) * C] = w[r]
        self.g = self.Wm.T @ m.K @ self.Wm
        Woff = H2 - w.sum(axis=1)
        self.coef = np.einsum('rbc,rc->rb', w, Woff).reshape(-1)
        ref = m.ref
        h1p = ref.h1_base - (m.U.T * self.coef) @ m.U
        self.h1p = h1p
        lam, phi = np.linalg.eigh(h1p)
        self.lam, self.phi = lam, phi
        from scipy.optimize import linear_sum_assignment
        ov = np.abs(m.V1 @ phi)
        qi, ii = linear_sum_assignment(-ov)
        ml = np.empty_like(lam); ml[qi] = lam[ii]
        self.ml = ml                       # eigenvalue assigned to one-body row j
        self.R1 = (m.V1.T * ml) @ m.V1 - h1p
        base = m.metrics(w, H2)
        self.base = base

    def two_body(self, rows, newV):
        """rows: two-body indices b (0..1143); newV: (n,76) new unit vectors.
        Returns dE2 (exact), d_err1sq, dE_gap, dLam1 (first order in h1')."""
        m = self.m; ref = m.ref
        Ynew = ref.pack(newV)
        TYnew = Ynew @ ref.Tp
        aNew = TYnew @ m.Y.T                          # (n,1144): y'^T T y_b'
        aSelf = np.einsum('ij,ij->i', TYnew, Ynew)
        idx = np.arange(len(rows))
        aNew[idx, rows] = aSelf
        dA = aNew - m.A[rows]
        kNew = (newV @ m.U.T) ** 2
        kNew[idx, rows] = 1.0
        dK = kNew - m.K[rows]
        dK[idx, rows] = 0.0
        wb = self.Wm[rows]                            # (n,352)
        s = dK @ self.Wm                              # (n,352)
        gs = s @ self.g                               # (n,352)
        term_g = 4 * np.einsum('ij,ij->i', wb, gs) + 2 * (np.einsum('ij,ij->i', wb, wb) * np.einsum('ij,ij->i', s, s)
                                                          + np.einsum('ij,ij->i', wb, s) ** 2)
        WdA = dA @ self.Wm
        term_t = 2 * np.einsum('ij,ij->i', wb, WdA) - dA[idx, rows] * np.einsum('ij,ij->i', wb, wb)
        dE2 = term_g - 2 * term_t
        # h1' = base - sum_b coef_b u_b u_b^T ; first-order eigenvalue shifts
        cb = self.coef[rows]
        old = m.U[rows]
        pn = newV @ self.phi; po = old @ self.phi
        dlam = -cb[:, None] * (pn ** 2 - po ** 2)      # (n,76)
        dLam1 = (dlam * np.sign(self.lam)[None, :]).sum(1)
        dEgap = ((np.sign(self.lam) - 1)[None, :] * dlam).sum(1)
        # error_1: R1 = sum_j ml_j v_j v_j^T - h1'; dh1' = -cb (u'u'^T - uu^T)
        # d(sum ml v v^T) = sum_j dml_j v_j v_j^T where dml follows assignment of dlam
        # use perm: ml = lam[assign]; compute via V1 projections
        V1 = m.V1
        # map eigen index -> row: ml[q] = lam[i] ; build permutation
        d_err = np.zeros(len(rows))
        perm = self.perm_rows()
        Pn = V1 @ newV.T; Po = V1 @ old.T            # (76, n)
        for i in range(len(rows)):
            dml = dlam[i, perm]                       # dml[row] = dlam[eig assigned to row]
            # <R1, sum_j dml_j v_j v_j^T> = sum_j dml_j v_j^T R1 v_j ; <R1, cb(u'u'^T-uu^T)>
            lin = np.dot(dml, self.vRv) + cb[i] * (newV[i] @ self.R1 @ newV[i] - old[i] @ self.R1 @ old[i])
            d_err[i] = 2 * lin
        return dE2, d_err, dEgap, dLam1

    def perm_rows(self):
        if not hasattr(self, '_perm'):
            from scipy.optimize import linear_sum_assignment
            ov = np.abs(self.m.V1 @ self.phi)
            qi, ii = linear_sum_assignment(-ov)
            perm = np.empty(N, dtype=int); perm[qi] = ii
            self._perm = perm
            self.vRv = np.einsum('jp,pq,jq->j', self.m.V1, self.R1, self.m.V1)
        return self._perm

    def one_body(self, rows, newV):
        """exact d(error_1^2) for replacing one-body row a by newV."""
        out = np.zeros(len(rows))
        for i, a in enumerate(rows):
            v = self.m.V1[a]; vn = newV[i]
            D = self.ml[a] * (np.outer(vn, vn) - np.outer(v, v))
            out[i] = 2 * np.sum(self.R1 * D) + np.sum(D * D)
        return out


def candidates(words, batches, steps=(2, -2)):
    """All single-word moves that flip bit 1 and keep bit 0 and the bit7^bit6 helper."""
    W = np.asarray(words, dtype=np.int64)
    out = []
    for b in batches:
        for j in range(5):
            t = 5 * b + j
            for st in steps:
                new = (W[:, t] + st) % 256
                ok = helper_ok(W[:, t], new)
                for a in np.nonzero(ok)[0]:
                    out.append((int(a), t, int(new[a])))
    return out


def price(coster, cands, chunk=2048):
    words = coster.words
    n = len(cands)
    res = np.zeros((n, 4))
    a_arr = np.array([c[0] for c in cands]); t_arr = np.array([c[1] for c in cands]); v_arr = np.array([c[2] for c in cands])
    for s in range(0, n, chunk):
        sl = slice(s, min(n, s + chunk))
        rows = a_arr[sl]
        Wn = words[rows].copy()
        Wn[np.arange(len(rows)), t_arr[sl]] = v_arr[sl]
        Vn = decode(Wn, coster.edges)
        two = rows >= N
        if two.any():
            dE2, derr, dg, dl = coster.two_body(rows[two] - N, Vn[two])
            res[np.arange(sl.start, sl.stop)[two]] = np.stack([dE2, derr, dg, dl], 1)
        if (~two).any():
            res[np.arange(sl.start, sl.stop)[~two], 1] = coster.one_body(rows[~two], Vn[~two])
    return a_arr, t_arr, v_arr, res


if __name__ == '__main__':
    z = np.load(ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/submission.npz')
    words = z['angle_words'].astype(np.int64); edges = z['tree_edges']; w = z['W']; H2 = z['H2_I']
    ref = Ref(); m = Model(ref); m.set_vectors(decode(words, edges))
    co = Coster(m, words, edges, w, H2)
    t = time.time()
    cands = candidates(words, range(9, 15))
    a, tt, v, res = price(co, cands)
    print('candidates', len(cands), 'seconds', time.time() - t, flush=True)
    np.savez(ROOT / 'work/flipcost_v18_b9_14.npz', a=a, t=tt, v=v, res=res)
    dE2 = res[:, 0]
    print('dE2 quantiles', np.quantile(dE2, [0, .01, .1, .25, .5, .75, .9, .99, 1]).tolist())
    print('dead (|dE2|<1e-15 and |derr|<1e-15)', int(np.sum((np.abs(dE2) < 1e-15) & (np.abs(res[:, 1]) < 1e-15))))
    print('base', co.base)
