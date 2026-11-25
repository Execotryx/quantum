# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Official evaluate_words (packaged FCIDUMP, unmodified verifier code) on a candidate npz."""
import sys, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'inputs/chem_pack'))
from fastchem import official
sys.path.insert(0, str(ROOT / 'scripts'))
from relations import structure

def main(path):
    z = np.load(path)
    v18 = np.load(ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/submission.npz')
    W = z['words'].astype(np.int64); w = z['w']; H2 = z['H2']
    o = official(W, w, H2, v18['tree_edges'])
    o = {k: (bool(v) if isinstance(v, (bool, np.bool_)) else float(v)) for k, v in o.items()}
    rel = [structure(W, k)[0]['rel_nonlinear_payload'] for k in range(15)]
    changed = np.nonzero((W != v18['angle_words']).any(0))[0]
    o['payload_relations'] = rel
    from parity_code import parity_bit1, parity_bit, in_S, in_S2
    W18 = v18['angle_words'].astype(np.int64)
    o['bit1_code_9_14'] = bool(all(in_S(parity_bit1(W, b) ^ parity_bit1(W, 8)) for b in range(9, 15)))
    o['bit2_code_9_14'] = bool(all(in_S2(parity_bit(W, b, 2) ^ parity_bit(W, 8, 2)) for b in range(9, 15)))
    hb = lambda X, b: ((X[:, 5 * b:5 * b + 5] >> 7) ^ (X[:, 5 * b:5 * b + 5] >> 6)) & 1
    o['helpers_ok'] = bool(all(np.array_equal(hb(W, b), hb(W, 0)) for b in range(15)))
    o['lsb_unchanged'] = bool(np.array_equal(W & 1, W18 & 1))
    o['changed_columns'] = [int(changed.min()), int(changed.max())] if len(changed) else []
    o['changed_cells'] = int((W != v18['angle_words']).sum())
    o['gates_19999'] = bool(o['error_1'] <= 0.019999 and o['error_2'] <= 0.019999 and o['gap_in_domain'] and o['E_gap'] > 3.914898 and o['Lambda'] > 49)
    print(json.dumps(o))
    return o

if __name__ == '__main__':
    main(sys.argv[1])
