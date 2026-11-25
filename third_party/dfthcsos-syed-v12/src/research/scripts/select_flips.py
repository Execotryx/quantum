# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Parity-code flip selection on batches 9-14 with an envelope (Lagrangian) cost."""
import sys, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from parity_code import decode_coset, parity_bit1, in_S
from fastchem import Ref, Model, decode, N


def select(words, a, t, v, cost, batches=range(9, 15), ref_batch=8):
    W2 = words.copy(); tot = 0.0; nfl = 0
    P = parity_bit1(words, ref_batch)
    for b in batches:
        sel = np.nonzero((t >= 5 * b) & (t < 5 * b + 5))[0]
        c = np.full(1220, np.inf); arg = np.full(1220, -1)
        order = np.argsort(cost[sel])
        for i in sel[order][::-1]:
            pass
        for i in sel:
            if cost[i] < c[a[i]]:
                c[a[i]] = cost[i]; arg[a[i]] = i
        D = parity_bit1(words, b) ^ P
        val, F, s = decode_coset(D, c)
        assert in_S(D ^ F)
        for addr in np.nonzero(F)[0]:
            i = arg[addr]; W2[a[i], t[i]] = v[i]
        tot += val; nfl += int(F.sum())
    for b in batches:
        assert in_S(parity_bit1(W2, b) ^ P)
    return W2, tot, nfl


if __name__ == '__main__':
    z = np.load(ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/submission.npz')
    words = z['angle_words'].astype(np.int64); edges = z['tree_edges']; w = z['W']; H2 = z['H2_I']
    fc = np.load(ROOT / 'work/flipcost_v18_b9_14.npz'); h1 = np.load(ROOT / 'work/flipcost_v18_b9_14_h1.npz')['h1']
    a, t, v, res = fc['a'], fc['t'], fc['v'], fc['res']
    ref = Ref()
    kg = float(sys.argv[1]); ke = float(sys.argv[2]); tag = sys.argv[3]
    cost = 98227.0 * res[:, 0] + kg * h1[:, 1] + ke * np.maximum(h1[:, 0], 0)
    W2, tot, nfl = select(words, a, t, v, cost)
    m = Model(ref); m.set_vectors(decode(W2, edges)); r = m.metrics(w, H2)
    pred_E2 = None
    print(f'{tag}: flips {nfl} pred cost {tot:.4f} | exact err1 {r["error_1"]*1e3:.4f} err2 {r["error_2"]*1e3:.6f} '
          f'gap-floor {r["E_gap"]-3.914898:.4e} Lam {r["Lambda"]:.5f} leff {r["lambda_eff"]:.6f}', flush=True)
    np.save(ROOT / f'work/W_{tag}.npy', W2)
