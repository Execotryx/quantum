# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Sequential word polish for coded batches (our own): one exactly priced move at a time.

Same move set and prices as word_polish.py (+/-8, +/-16, +/-32 on two-body rows of columns 45-74;
bits 0-2 of every word and the bit7^bit6 helper are kept, so the LSB codes and both parity codes
stay). Moves in different rows overlap strongly in E2 (batches of independently priced moves
overshoot, measured), so here the best move is applied alone, the model row is updated in place
(K, A, Y, TY rows; about 0.1 s) and the leading candidates are re-priced before the next pick.
A full re-pricing is done every `refresh` moves. Then exact_refit2.Valley2 re-fits the weights.
"""
import sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18
from flipcost import Coster, price, helper_ok
from exact_refit import feasible
from word_polish import refit, G2


def update_row(m, b, unew):
    ref = m.ref
    m.U[b] = unew
    y = ref.pack(unew[None, :])[0]
    m.Y[b] = y
    ty = y @ ref.Tp
    m.TY[b] = ty
    arow = m.Y @ ty
    m.A[b, :] = arow; m.A[:, b] = arow
    krow = (m.U @ unew) ** 2
    m.K[b, :] = krow; m.K[:, b] = krow


def build(W, cols, steps):
    out = []
    for t in cols:
        for st in steps:
            new = (W[:, t] + st) % 256
            ok = helper_ok(W[:, t], new); ok[:N] = False
            idx = np.nonzero(ok)[0]
            out.append(np.stack([idx, np.full(len(idx), t), np.full(len(idx), st)], 1))
    return np.concatenate(out)


def price_cands(co, W, C, nu_abs, kg, eta):
    old = W[C[:, 0], C[:, 1]]
    v = (old + C[:, 2]) % 256
    ok = helper_ok(old, v)
    a, tt, vv, res = price(co, list(zip(C[:, 0].tolist(), C[:, 1].tolist(), v.tolist())))
    dL = nu_abs * res[:, 0] + res[:, 3] + kg * res[:, 2] + eta * res[:, 1]
    dL[~ok] = np.inf
    return dL, v


def greedy(ref, m, W, edges, w, H2, nu_abs, kg, eta, cols, steps, max_moves=400, top=1500, refresh=40, thr=5e-5,
           seconds=240, verbose=True):
    t0 = time.time()
    W = W.copy()
    C = build(W, cols, steps)
    co = Coster(m, W, edges, w, H2)
    dL, _ = price_cands(co, W, C, nu_abs, kg, eta)
    n = 0; since = 0; tot = 0.0
    while n < max_moves and time.time() - t0 < seconds:
        pool = np.argsort(dL)[:top]
        if since >= refresh:
            dL, _ = price_cands(co, W, C, nu_abs, kg, eta); since = 0
            pool = np.argsort(dL)[:top]
        else:
            dl, _ = price_cands(co, W, C[pool], nu_abs, kg, eta)
            dL[pool] = dl
        i = pool[int(np.argmin(dL[pool]))]
        if dL[i] > -thr:
            if since == 0:
                break
            since = refresh                     # force a full re-pricing before giving up
            continue
        a, t, st = (int(x) for x in C[i])
        W[a, t] = (W[a, t] + st) % 256
        update_row(m, a - N, decode(W[a:a + 1], edges)[0])
        tot += float(dL[i]); n += 1; since += 1
        co = Coster(m, W, edges, w, H2)
        if verbose and n % 25 == 0:
            e = co.base
            print(f'      {n} moves, predicted sum {tot:+.4f}: err1 {e["error_1"]*1e3:.4f} err2 {e["error_2"]*1e3:.6f} '
                  f'gap-floor {e["E_gap"]-3.914898:+.3e} Lam {e["Lambda"]:.6f} ({time.time()-t0:.0f}s)', flush=True)
        if co.base['error_1'] > 0.01996:
            eta = 20000.0
    return W, n, tot


def main(start, tag, cycles=2, max_moves=400, nu_rel=None, kg=10.0, eta=0.0, seconds=240):
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    W0 = W.copy()
    ref = Ref(); t0 = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    e = m.metrics(w, H2); show('start', e)
    best = e['lambda_eff'] if feasible(e) else None
    nu_rel = nu_rel or 100.0
    cols = list(range(45, 75)); steps = (8, -8, 16, -16, 32, -32)
    for cy in range(cycles):
        W, n, tot = greedy(ref, m, W, edges, w, H2, nu_rel / G2, kg, eta, cols, steps, max_moves=max_moves, seconds=seconds)
        m = Model(ref); m.set_vectors(decode(W, edges))          # fresh model: no accumulated update error
        e = m.metrics(w, H2)
        show(f'cycle {cy}: {n} moves, predicted {tot:+.4f}, {time.time()-t0:.0f}s', e)
        w, H2, nu_rel, cc = refit(m, w, H2, nu_rel)
        e = m.metrics(w, H2)
        show(f'cycle {cy} refit (nu {nu_rel:.2f}, c {cc:+.2e}, cells changed vs start {int((W != W0).sum())}, {time.time()-t0:.0f}s)', e)
        np.savez(ROOT / f'work/last_{tag}.npz', words=W, w=w, H2=H2)
        if feasible(e) and (best is None or e['lambda_eff'] < best - 1e-9):
            best = e['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            np.savez(ROOT / f'work/cand_{tag}_words.npz', words=W)
            print(f'   kept feasible (cycle {cy}): lambda_eff {best:.7f}', flush=True)
        if n == 0:
            break
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], cycles=int(a[3]) if len(a) > 3 else 2, max_moves=int(a[4]) if len(a) > 4 else 400,
         nu_rel=float(a[5]) if len(a) > 5 else None, seconds=float(a[6]) if len(a) > 6 else 240)
