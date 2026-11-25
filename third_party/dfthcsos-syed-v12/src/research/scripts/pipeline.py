# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Words -> restricted one-body re-rounding -> joint refit -> H2 polish (repeat)."""
import sys, time, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fastchem import Ref, Model, decode, N
from alfit import ScalarFit
from repair import HRepair
from onebody import reround, coded_columns

V18 = ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/submission.npz'


def h1prime(m, w, H2):
    Woff = H2 - w.sum(1); coef = np.einsum('rbc,rc->rb', w, Woff).reshape(-1)
    return m.ref.h1_base - (m.U.T * coef) @ m.U


def show(tag, ex):
    print(f'{tag}: err1 {ex["error_1"]*1e3:.6f} err2 {ex["error_2"]*1e3:.6f} gap-floor {ex["E_gap"]-3.914898:.3e} '
          f'Lam {ex["Lambda"]:.6f} leff {ex["lambda_eff"]:.7f}', flush=True)


def run(words_path, out_tag, rounds=2, mu2=2.5e4, cols=range(45, 75), parity=range(9, 15), ref=None):
    z = np.load(V18)
    words0 = z['angle_words'].astype(np.int64); edges = z['tree_edges']
    w = z['W'].astype(np.float64); H2 = z['H2_I'].astype(np.float64)
    W = words0 if words_path == 'v18' else np.load(words_path).astype(np.int64)
    coded = coded_columns(words0)
    ref = ref or Ref()
    m = Model(ref); m.set_vectors(decode(W, edges))
    show('start', m.metrics(w, H2))
    for rd in range(rounds):
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(parity), sweeps=40, verbose=False, cols=list(cols))
        m = Model(ref); m.set_vectors(decode(W, edges))
        show(f'r{rd} one-body', m.metrics(w, H2))
        sf = ScalarFit(m)
        best = sf.to_target(w, H2, 0.0199986, mu2=mu2, verbose=False, kappa=71.23, rho_g=1e7)
        if best is None:
            print('no feasible E2 point'); return None
        w, H2, ex, mu2 = best
        show(f'r{rd} refit (mu2 {mu2:.3g})', ex)
        W, _ = reround(W, edges, h1prime(m, w, H2), coded, set(parity), sweeps=40, verbose=False, cols=list(cols))
        m = Model(ref); m.set_vectors(decode(W, edges))
        hr = HRepair(m, w, H2)
        H2, r = hr.solve()
        ex = m.metrics(w, H2)
        show(f'r{rd} polish ({r.message})', ex)
    np.savez(ROOT / f'work/cand_{out_tag}.npz', words=W, w=w, H2=H2)
    return W, w, H2, ex


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], rounds=int(sys.argv[3]) if len(sys.argv) > 3 else 2)
