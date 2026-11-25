# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Greedy code-preserving re-rounding of the 76 one-body rows (error_1 only).

h1' is fixed by the weights and two-body vectors; a one-body row v_a enters
R1 = sum_j ml_j v_j v_j^T - h1' only through ml_a v_a v_a^T. Every move keeps
bit 0 where the column is LSB-coded, keeps bit7^bit6 (helper) and keeps the
bit-1 parity of every parity-coded batch at that address.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment
from fastchem import decode, N


def coded_columns(words):
    """columns whose LSB is coded (zero nonlinear coefficients), from the table itself."""
    from relations import anf, positions
    out = np.zeros(75, dtype=bool)
    for t in range(75):
        c = anf(((words[:, t] & 1).astype(np.uint8))[:, None])[:, :, 0]
        out[t] = c[positions('nonlinear')].sum() == 0
    return out


def helper_bit(x):
    return ((x >> 7) ^ (x >> 6)) & 1


def moves_for_row(row, coded, parity_batches, cols=None):
    """list of (tuple of (t, newval))."""
    mv = []
    allowed = set(range(75)) if cols is None else set(cols)
    for t in range(75):
        if t not in allowed:
            continue
        b = t // 5
        if b in parity_batches:
            steps = (4, -4, 8, -8)
        elif coded[t]:
            steps = (2, -2, 4, -4)
        else:
            steps = (1, -1, 2, -2)
        for s in steps:
            nv = (row[t] + s) % 256
            if helper_bit(nv) == helper_bit(row[t]):
                mv.append(((t, int(nv)),))
    for b in parity_batches:
        if 5 * b not in allowed:
            continue
        for j1 in range(5):
            for j2 in range(j1 + 1, 5):
                t1, t2 = 5 * b + j1, 5 * b + j2
                for s1, s2 in ((2, 2), (2, -2), (-2, 2), (-2, -2), (4, 4), (4, -4), (-4, 4), (-4, -4)):
                    if True:
                        n1 = (row[t1] + s1) % 256; n2 = (row[t2] + s2) % 256
                        if helper_bit(n1) == helper_bit(row[t1]) and helper_bit(n2) == helper_bit(row[t2]):
                            mv.append(((t1, int(n1)), (t2, int(n2))))
    return mv


def reround(words, edges, h1p, coded, parity_batches, sweeps=30, verbose=True, cols=None, keep=None):
    W = np.asarray(words, dtype=np.int64).copy()
    lam, phi = np.linalg.eigh(h1p)
    V1 = decode(W[:N], edges)
    ov = np.abs(V1 @ phi); qi, ii = linear_sum_assignment(-ov)
    perm = np.empty(N, dtype=int); perm[qi] = ii
    ml = lam[perm]
    R1 = (V1.T * ml) @ V1 - h1p
    e0 = float(np.sum(R1 * R1))
    for sw in range(sweeps):
        best = []
        for a in range(N):
            mv = moves_for_row(W[a], coded, parity_batches, cols)
            if keep is not None:
                mv = [x for x in mv if keep(W[a], x)]
            if not mv:
                continue
            rows = np.repeat(W[a][None, :], len(mv), axis=0)
            for i, m in enumerate(mv):
                for t, nv in m:
                    rows[i, t] = nv
            Vn = decode(rows, edges)
            v = V1[a]
            # d(e1sq) = 2<R1,D> + |D|^2, D = ml_a (v'v'^T - v v^T)
            q_new = np.einsum('ip,pq,iq->i', Vn, R1, Vn); q_old = v @ R1 @ v
            ov_ = Vn @ v
            DD = ml[a] ** 2 * (2 - 2 * ov_ ** 2)            # |v'v'^T - vv^T|^2 = 2 - 2 (v.v')^2
            d = 2 * ml[a] * (q_new - q_old) + DD
            i = int(np.argmin(d))
            if d[i] < -1e-16:
                best.append((d[i], a, mv[i], Vn[i]))
        if not best:
            break
        best.sort(key=lambda x: x[0])
        applied = 0
        for d, a, m, vn in best:
            # recompute exact delta with current R1 (rows interact through R1)
            v = V1[a]
            D = ml[a] * (np.outer(vn, vn) - np.outer(v, v))
            dd = 2 * np.sum(R1 * D) + np.sum(D * D)
            if dd < -1e-16:
                for t, nv in m:
                    W[a, t] = nv
                V1[a] = vn; R1 = R1 + D; applied += 1
        e = float(np.sum(R1 * R1))
        if verbose:
            print(f'  sweep {sw}: applied {applied}, err1 {np.sqrt(e) * 1e3:.6f} mHa', flush=True)
        if applied == 0:
            break
    return W, float(np.sqrt(np.sum(R1 * R1)))
