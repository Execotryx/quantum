# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Fast exact DF-THC metric model for word/weight co-design (our own code).

error_2^2 = ||G - T||^2 with G = sum_k X_k (x) X_k, X_k = sum_b w_bk u_b u_b^T,
T = tei + (S (x) I + I (x) S)/2. Expanded through the packed symmetric pair
space (p <= q, off-diagonal scaled by sqrt 2), so that every quantity reduces to
1144 x 1144 matrices: K_bb' = (u_b . u_b')^2 and A_bb' = y_b^T T y_b'.
The official verifier remains the only acceptance gate.
"""
import sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs/chem_pack'))
CACHE = ROOT / 'work/ref_cache.npz'
N = 76


def decode(words, edges, brot=8):
    """Official decoding (reconstruct_u_vectors), vectorized over rows."""
    ang = np.asarray(words, dtype=np.float64) / (1 << (brot - 1))
    v = np.zeros((ang.shape[0], N))
    v[:, 0] = 1.0
    for t, (p, c) in enumerate(edges):
        pv = v[:, p].copy(); cv = v[:, c].copy()
        th = np.pi * ang[:, t]
        co = np.cos(th); si = np.sin(th)
        v[:, p] = co * pv - si * cv
        v[:, c] = si * pv + co * cv
    return v


def load_reference_cached():
    if CACHE.exists():
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    from dfthcsos.scoreinfra.reference import load_reference, check_fcidump, load_fixed_shifts, ELECTRONS
    ref = load_reference(check_fcidump())
    fs = load_fixed_shifts()
    out = {'oei': np.asarray(ref['oei'], dtype=np.float64), 'tei': np.asarray(ref['tei'], dtype=np.float64),
           'ecore': np.float64(ref['ecore']), 'electrons': np.int64(ref['electrons'])}
    for k, v in fs.items():
        out['fs_' + k] = np.asarray(v)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **out)
    return out


class Ref:
    def __init__(self):
        from dfthcsos.scoreinfra.dfthc_math import symmetric_from_lower
        from dfthcsos.scoreinfra.reference import UPPER_ENERGY
        r = load_reference_cached()
        self.oei = r['oei']; tei = r['tei']
        self.ecore = float(r['ecore']); self.eta = int(r['electrons'])
        self.E_upper = UPPER_ENERGY
        # fixed shifts (S from Hsym_lower rounded to float32, beta_1 from H1_I)
        S = np.asarray(symmetric_from_lower(r['fs_Hsym_lower'], N), dtype=np.float64)
        self.S = S
        self.beta_1 = float(r['fs_H1_I']) - 0.5 * float(np.trace(S))
        self.h1_thc = self.oei - 0.5 * np.einsum('prrq->pq', tei)
        self.h1_base = self.h1_thc - 0.5 * self.eta * S + self.beta_1 * np.eye(N)
        # full T for norm
        T = tei.copy()
        d = np.arange(N)
        T[:, :, d, d] += 0.5 * S[:, :, None]
        T[d, d, :, :] += 0.5 * S[None, :, :]
        self.Tnorm2 = float(np.sum(T * T))
        iu = np.triu_indices(N)
        self.iu = iu
        sc = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
        self.sc = sc
        Tp = T[iu[0], iu[1]][:, iu[0], iu[1]]
        self.Tp = Tp * sc[:, None] * sc[None, :]
        del T, tei

    def pack(self, U):
        """rows u -> packed vec(u u^T) with sqrt2 scaling (so <M,N> = m.n)."""
        Y = U[:, self.iu[0]] * U[:, self.iu[1]]
        return Y * self.sc[None, :]


class Model:
    """Weights + vectors -> metrics. w: (R,B,C) lowercase, H2: (R,C) = w_B."""
    def __init__(self, ref, R=8, B=143, C=44):
        self.ref = ref; self.R, self.B, self.C = R, B, C

    def set_vectors(self, V):
        """V: (76 + R*B, N) unit rows."""
        ref = self.ref
        self.V1 = V[:N].copy()
        self.U = V[N:].copy()
        t = time.time()
        self.Y = ref.pack(self.U)                     # (1144, 2926)
        self.TY = self.Y @ ref.Tp                      # (1144, 2926)
        self.A = self.TY @ self.Y.T                   # (1144, 1144)
        self.K = (self.U @ self.U.T) ** 2             # (1144, 1144)
        self.t_pre = time.time() - t

    def metrics(self, w, H2, need_err1=True):
        ref = self.ref
        R, B, C = self.R, self.B, self.C
        Wm = np.zeros((R * B, R * C))                 # block-diagonal weight matrix
        for r in range(R):
            Wm[r * B:(r + 1) * B, r * C:(r + 1) * C] = w[r]
        g = Wm.T @ self.K @ Wm                         # <X_k, X_l>
        AW = self.A @ Wm
        tg = np.einsum('bk,bk->k', Wm, AW)             # <X_k, T X_k>
        E2 = float(np.sum(g * g) - 2 * np.sum(tg) + ref.Tnorm2)
        Woff = H2 - w.sum(axis=1)                      # (R,C)
        coef = np.einsum('rbc,rc->rb', w, Woff).reshape(-1)   # sum_c W_off w_bc
        h1p = ref.h1_base - (self.U.T * coef) @ self.U
        lam, phi = np.linalg.eigh(h1p)
        out = {'error_2': float(np.sqrt(max(E2, 0.0))), 'E2': E2}
        if need_err1:
            ov = np.abs(self.V1 @ phi)
            qi, ii = linear_sum_assignment(-ov)
            ml = np.empty_like(lam); ml[qi] = lam[ii]
            rec = (self.V1.T * ml) @ self.V1
            out['error_1'] = float(np.linalg.norm(rec - h1p))
        lam1 = float(np.sum(np.abs(lam)))
        lam2 = float(0.25 * np.sum((np.abs(w).sum(axis=1) + np.abs(H2)) ** 2))
        Lam = lam1 + lam2
        E_SOS = ref.ecore - ref.eta * ref.beta_1 - (lam1 - float(np.sum(lam))) - 0.5 * float(np.sum(Woff ** 2))
        E_gap = ref.E_upper - E_SOS
        out.update({'Lambda': Lam, 'E_SOS': E_SOS, 'E_gap': E_gap,
                    'lambda_eff': float(np.sqrt(E_gap * (2 * Lam - E_gap))) if 0 < E_gap < 2 * Lam else float('nan')})
        return out


def official(words, w, H2, edges, npz_like=None):
    """Official evaluate_words on in-memory arrays (uses packaged FCIDUMP)."""
    from dfthcsos.verify import load_inputs, evaluate_words
    R, B, C = w.shape
    params = {'U': np.zeros((R, B, N)), 'W': w, 'H2_I': H2, 'H1_I': np.float64(0.0),
              'Hsym_lower': np.zeros(N * (N + 1) // 2)}
    inputs = load_inputs(params)
    return evaluate_words(inputs, np.asarray(words, dtype=np.int64), np.asarray(edges, dtype=np.int64), 8)
