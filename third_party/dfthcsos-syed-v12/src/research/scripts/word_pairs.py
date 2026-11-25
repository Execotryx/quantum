# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Sequential word polish with code-safe PAIR moves (our own).

Pair = two words of the same batch (9-14) on the same two-body row, both stepped by +/-2 or both by
+/-4. A pair is allowed only if it keeps, at that address, the bit-1 parity and the bit-2 parity of
the five words of the batch (carries included: the changed bits of the two words must cancel on bits
1 and 2), every word LSB (even steps) and both bit7^bit6 helpers. Pricing, in-place row updates and
the refit are those of word_greedy.py; validity is re-checked against the current words at every
pricing, and the final words are checked by official_check.py (relation counts and both codes).
"""
import sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from pipeline import show, V18
from flipcost import Coster, helper_ok
from exact_refit import feasible
from word_polish import refit, G2
from word_greedy import update_row


def build_pairs(W, batches=range(9, 15)):
    rows = np.arange(N, W.shape[0])
    out = []
    for b in batches:
        for i in range(5):
            for j in range(i + 1, 5):
                t1, t2 = 5 * b + i, 5 * b + j
                for mag in (2, 4):
                    for s1 in (mag, -mag):
                        for s2 in (mag, -mag):
                            o1 = W[rows, t1]; o2 = W[rows, t2]
                            n1 = (o1 + s1) % 256; n2 = (o2 + s2) % 256
                            ok = helper_ok(o1, n1) & helper_ok(o2, n2) & ((((o1 ^ n1) ^ (o2 ^ n2)) & 6) == 0)
                            idx = rows[ok]
                            k = len(idx)
                            out.append(np.stack([idx, np.full(k, t1), np.full(k, s1), np.full(k, t2), np.full(k, s2)], 1))
    return np.concatenate(out)


def price_pairs(co, W, C, nu_abs, kg, eta, chunk=2048):
    n = len(C); dL = np.full(n, np.inf)
    for s in range(0, n, chunk):
        c = C[s:s + chunk]
        r = np.arange(len(c))
        Wn = W[c[:, 0]].copy()
        o1 = Wn[r, c[:, 1]].copy(); n1 = (o1 + c[:, 2]) % 256; Wn[r, c[:, 1]] = n1
        o2 = Wn[r, c[:, 3]].copy(); n2 = (o2 + c[:, 4]) % 256; Wn[r, c[:, 3]] = n2
        ok = helper_ok(o1, n1) & helper_ok(o2, n2) & ((((o1 ^ n1) ^ (o2 ^ n2)) & 6) == 0)
        dE2, derr, dg, dl = co.two_body(c[:, 0] - N, decode(Wn, co.edges))
        v = nu_abs * dE2 + dl + kg * dg + eta * np.maximum(derr, 0.0)
        v[~ok] = np.inf
        dL[s:s + chunk] = v
    return dL


def greedy_pairs(m, W, edges, w, H2, nu_abs, kg, eta, max_moves=600, top=3000, refresh=100, thr=5e-5, seconds=200, batches=range(9, 15)):
    t0 = time.time()
    W = W.copy()
    C = build_pairs(W, batches)
    co = Coster(m, W, edges, w, H2)
    dL = price_pairs(co, W, C, nu_abs, kg, eta)
    print(f'      pair candidates {len(C)}, improving {int((dL < -thr).sum())}, naive sum of row bests '
          f'{sum(min(0.0, dL[C[:, 0] == a].min()) for a in np.unique(C[dL < -thr, 0])):+.4f} ({time.time()-t0:.0f}s)', flush=True)
    n = 0; since = 0; tot = 0.0
    while n < max_moves and time.time() - t0 < seconds:
        if since >= refresh:
            dL = price_pairs(co, W, C, nu_abs, kg, eta); since = 0
            pool = np.argsort(dL)[:top]
        else:
            pool = np.argsort(dL)[:top]
            dL[pool] = price_pairs(co, W, C[pool], nu_abs, kg, eta)
        i = pool[int(np.argmin(dL[pool]))]
        if dL[i] > -thr:
            if since == 0:
                break
            since = refresh
            continue
        a, t1, s1, t2, s2 = (int(x) for x in C[i])
        W[a, t1] = (W[a, t1] + s1) % 256; W[a, t2] = (W[a, t2] + s2) % 256
        update_row(m, a - N, decode(W[a:a + 1], edges)[0])
        tot += float(dL[i]); n += 1; since += 1
        co = Coster(m, W, edges, w, H2)
        if n % 25 == 0:
            e = co.base
            print(f'      {n} pair moves, predicted sum {tot:+.4f}: err1 {e["error_1"]*1e3:.4f} err2 {e["error_2"]*1e3:.6f} '
                  f'gap-floor {e["E_gap"]-3.914898:+.3e} Lam {e["Lambda"]:.6f} ({time.time()-t0:.0f}s)', flush=True)
        if co.base['error_1'] > 0.01996:
            eta = 1e6
    return W, n, tot


def main(start, tag, nu_rel=75.0, kg=10.0, eta=1000.0, seconds=200, cycles=1):
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    W0 = W.copy()
    ref = Ref(); t0 = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    e = m.metrics(w, H2); show('start', e)
    best = e['lambda_eff'] if feasible(e) else None
    for cy in range(cycles):
        W, n, tot = greedy_pairs(m, W, edges, w, H2, nu_rel / G2, kg, eta, seconds=seconds)
        m = Model(ref); m.set_vectors(decode(W, edges))
        e = m.metrics(w, H2)
        show(f'pairs cycle {cy}: {n} moves, predicted {tot:+.4f}, {time.time()-t0:.0f}s', e)
        w, H2, nu_rel, cc = refit(m, w, H2, nu_rel)
        e = m.metrics(w, H2)
        show(f'pairs cycle {cy} refit (nu {nu_rel:.2f}, c {cc:+.2e}, cells changed vs start {int((W != W0).sum())}, {time.time()-t0:.0f}s)', e)
        np.savez(ROOT / f'work/last_{tag}.npz', words=W, w=w, H2=H2)
        if feasible(e) and (best is None or e['lambda_eff'] < best - 1e-9):
            best = e['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            np.savez(ROOT / f'work/cand_{tag}_words.npz', words=W)
            print(f'   kept feasible (pairs cycle {cy}): lambda_eff {best:.7f}', flush=True)
        if n == 0:
            break
    print('BEST', best, flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], nu_rel=float(a[3]) if len(a) > 3 else 75.0, seconds=float(a[4]) if len(a) > 4 else 200,
         cycles=int(a[5]) if len(a) > 5 else 1)


def gap_price(m, w, H2, nu_rel):
    """Lambda gained per Ha of eigenvalue-gap reduction at the refit optimum (envelope theorem on the
    scaling a of Woff: dL/da = 0.5 sum s sgn(H2) Woff + sum_rb mu_rb coef_rb, d(gap)/da = ||Woff||^2)."""
    from exact_refit import e2_and_grad
    from exact_refit2 import Valley2
    vy = Valley2(m, w, H2)
    wv, H2v, absw = vy.build(vy.x0)
    s = absw.sum(1) + np.abs(H2v)
    E2, gE2 = e2_and_grad(m, wv)
    ga = 0.5 * np.broadcast_to(s[:, None, :], wv.shape)
    gw = 0.5 * (s * np.sign(H2v))[:, None, :] + (nu_rel / vy.G2) * gE2
    gp = np.take_along_axis(gw + ga * np.sign(wv), vy.piv[..., None], axis=2)[..., 0]
    dLda = 0.5 * float(np.sum(s * np.sign(H2v) * vy.Woff)) + float(np.sum(-gp / vy.Wp * vy.coef0))
    return -dLda / float(np.sum(vy.Woff ** 2))


def main2(start, tag, nu_rel, seconds=120, cycles=2, max_moves=200, eta=1000.0, discount=0.85):
    """Pair cycles with the gap price recomputed from the refit multipliers before every cycle."""
    z = np.load(V18); edges = z['tree_edges']
    c = np.load(ROOT / start); W = c['words'].astype(np.int64); w = c['w'].astype(np.float64); H2 = c['H2'].astype(np.float64)
    W0 = W.copy()
    ref = Ref(); t0 = time.time()
    m = Model(ref); m.set_vectors(decode(W, edges))
    e = m.metrics(w, H2); show('start', e)
    best = e['lambda_eff'] if feasible(e) else None
    for cy in range(cycles):
        kg = discount * gap_price(m, w, H2, nu_rel)
        print(f'   cycle {cy}: nu {nu_rel:.2f}, gap price {kg:.3f} (discount {discount})', flush=True)
        W, n, tot = greedy_pairs(m, W, edges, w, H2, nu_rel / G2, kg, eta, seconds=seconds, max_moves=max_moves)
        m = Model(ref); m.set_vectors(decode(W, edges))
        e = m.metrics(w, H2)
        show(f'pairs cycle {cy}: {n} moves, predicted {tot:+.4f}, {time.time()-t0:.0f}s', e)
        w, H2, nu_rel, cc = refit(m, w, H2, nu_rel)
        e = m.metrics(w, H2)
        show(f'pairs cycle {cy} refit (nu {nu_rel:.2f}, c {cc:+.2e}, cells changed vs start {int((W != W0).sum())}, {time.time()-t0:.0f}s)', e)
        np.savez(ROOT / f'work/last_{tag}.npz', words=W, w=w, H2=H2)
        if feasible(e) and (best is None or e['lambda_eff'] < best - 1e-9):
            best = e['lambda_eff']
            np.savez(ROOT / f'work/cand_{tag}.npz', words=W, w=w, H2=H2)
            np.savez(ROOT / f'work/cand_{tag}_words.npz', words=W)
            print(f'   kept feasible (pairs cycle {cy}): lambda_eff {best:.7f}', flush=True)
        if n == 0:
            break
    print('BEST', best, flush=True)
