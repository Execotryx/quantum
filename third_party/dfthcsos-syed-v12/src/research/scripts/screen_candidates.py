#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Fast-model screen, explicitly not official qualification.

Optionally re-round only the modified early batch's one-body rows, preserving
the newly imposed per-column LSB codes and the high helpers.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from fastchem import Ref, Model, decode
from onebody import coded_columns, reround
from pipeline import h1prime, show


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('candidates', nargs='+', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reround-columns', default='')
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    with np.load(root / 'baseline_C/submission.npz') as z:
        edges = z['tree_edges']
    ref = Ref()
    results = []
    for candidate in args.candidates:
        start = time.time()
        with np.load(candidate) as c:
            words, w, H2 = c['words'].astype(np.int64), c['w'], c['H2']
        m = Model(ref)
        m.set_vectors(decode(words, edges))
        before = m.metrics(w, H2)
        show(candidate.name + ' before', before)
        item = {'candidate': str(candidate.resolve()), 'method': 'fastchem exact formula; NOT official qualification',
                'before': before}
        if args.reround_columns:
            cols = [int(x) for x in args.reround_columns.split(',')]
            words2, _ = reround(words, edges, h1prime(m, w, H2), coded_columns(words), set(),
                                sweeps=40, verbose=False, cols=cols)
            m.set_vectors(decode(words2, edges))
            after = m.metrics(w, H2)
            show(candidate.name + ' after restricted one-body reround', after)
            path = candidate.with_name(candidate.stem + '_ob.npz')
            np.savez(path, words=words2, w=w, H2=H2)
            item.update({'after_restricted_onebody': after, 'rerounded_file': str(path),
                         'onebody_cells_changed': int((words2[:76] != words[:76]).sum())})
        item['seconds'] = time.time() - start
        results.append(item)
        args.out.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
