# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Weights-only polish of h1' for frozen words (our own): gradient steps on coef_rb = w_rb . Woff_r.

The h1'-preserving refit (exact_refit2.Valley2) holds coef at its start value, so after the word
polish coef is still v18's. Here Lambda = Lambda_1(coef) + Lambda_2*(coef) is differentiated with
respect to coef by the envelope theorem:
  dLambda_2*/dcoef_rb = g_p / Woff_p             (pivot gradient of the converged refit)
  dLambda_1/dcoef_rb  = - u_rb^T Phi sgn(lam) Phi^T u_rb
  gap term            = kappa_gap * d(eigenvalue gap)/dcoef_rb, kappa_gap from the Woff scaling
A step coef -> coef - t G is applied through the pivot weights with Woff held (H2 follows), then the
refit lands on the gates again. A step is kept only if the exact lambda_eff falls and error_1 stays
inside its gate. Words are not touched, so compiled loaders stay valid.
"""
import sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18
from exact_refit import e2_and_grad, feasible
from exact_refit2 import Valley2
from word_polish import refit


def coef_gradient(m, w, H2, nu_rel):
    vy = Valley2(m, w, H2)
    wv, H2v, absw = vy.build(vy.x0)
    s = absw.sum(1) + np.abs(H2v)
    E2, gE2 = e2_and_grad(m, wv)
    ga = 0.5 * np.broadcast_to(s[:, None, :], wv.shape)
    gw = 0.5 * (s * np.sign(H2v))[:, None, :] + (nu_rel / vy.G2) * gE2
    gp = np.take_along_axis(gw + ga * np.sign(wv), vy.piv[..., None], axis=2)[..., 0]
    dl2 = gp / vy.Wp
    dLda = 0.5 * float(np.sum(s * np.sign(H2v) * vy.Woff)) + float(np.sum(-dl2 * vy.coef0))
    kg = -dLda / float(np.sum(vy.Woff ** 2))
    U = m.U
    h1p = m.ref.h1_base - (U.T * vy.coef0.ravel()) @ U
    lam, phi = np.linalg.eigh(h1p)
    sg = np.sign(lam)
    ul = np.einsum('bp,pq,bq->b', U, (phi * sg) @ phi.T, U)
    ug = np.einsum('bp,pq,bq->b', U, (phi * (sg - 1)) @ phi.T, U)
    G = dl2.ravel() - ul - kg * ug
    return G.reshape(vy.coef0.shape), kg, vy


def apply_step(vy, w, H2, G, t):
    """coef -> coef - t G through the pivot weights; Woff unchanged (H2 follows)."""
    wn = w.copy()
    dwp = (-t * G) / vy.Wp
    R, B = G.shape
    rr, bb = np.indices((R, B))
    wn[rr, bb, vy.piv] += dwp
    H2n = H2 + (wn - w).sum(1)
    return wn, H2n


def main(start, tag, nu_rel, steps=4, t0=None):
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    ref = Ref(); t_start = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    e = m.metrics(w, H2); show('start', e)
    best = e['lambda_eff']
    t = t0
    for it in range(steps):
        G, kg, vy = coef_gradient(m, w, H2, nu_rel)
        gn = float(np.linalg.norm(G))
        if t is None:
            t = 0.02 / gn                      # first trial: predicted first-order gain 0.02 |G|
        print(f'   step {it}: |G| {gn:.4f} max |G| {np.abs(G).max():.4f} gap price {kg:.3f}; trial t {t:.3e} '
              f'(predicted {-t * gn * gn:+.4f} Lambda)', flush=True)
        wn, H2n = apply_step(vy, w, H2, G, t)
        wn, H2n, nu_n, cc = refit(m, wn, H2n, nu_rel, outer=4, inner=1500)
        en = m.metrics(wn, H2n)
        show(f'   step {it} trial (nu {nu_n:.2f}, c {cc:+.2e}, {time.time()-t_start:.0f}s)', en)
        if feasible(en) and en['lambda_eff'] < best - 1e-7:
            best = en['lambda_eff']; w, H2, nu_rel = wn, H2n, nu_n
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            print(f'   kept feasible (step {it}): lambda_eff {best:.7f}', flush=True)
            t *= 2.0
        else:
            t *= 0.3
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], float(a[3]), steps=int(a[4]) if len(a) > 4 else 4)
