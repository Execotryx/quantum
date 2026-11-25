#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Pack five independent own prefix triples from authenticated prior bases.

This constructs basis metadata only. It does not infer a circuit or cost gain.
Each source basis is re-evaluated on the exact supplied word table before its
triples enter the catalogue. Product matching and full proofs remain separate.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import numpy as np
from planner import basis
from prefix_basis_descent import setup


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    ap.add_argument('--k', type=int, required=True)
    ap.add_argument('--basis', type=Path, action='append', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    assert sha(args.words) == args.expected_sha256
    with np.load(args.words, allow_pickle=False) as z:
        W = z['angle_words' if 'angle_words' in z.files else 'words'].astype(np.uint8)
    prefix = hashlib.sha256(W.tobytes()).hexdigest()
    triples, seen, sources = [], set(), []
    for p in args.basis:
        b = json.loads(p.read_text())
        assert b['target_prefix_sha256'] == prefix and b['k'] == args.k
        bp, _, rows, B, info = setup(W, b, args.k, True)
        assert all(q['rank'] == 74 for q in info)
        sources.append(dict(path=str(p), sha256=sha(p)))
        for i in range(5):
            t = rows[3*i:3*i+3]
            space = tuple(sorted([0, t[0], t[1], t[2], t[0]^t[1],
                                  t[0]^t[2], t[1]^t[2], t[0]^t[1]^t[2]]))
            assert len(set(space)) == 8
            if space in seen:
                continue
            seen.add(space)
            triples.append(dict(rows=t, retained_kernel_span=len(bp.F[i]),
                                source=str(p), source_sha256=sha(p), block=i))
    assert math.comb(len(triples), 5) <= 1_000_000, 'Split the catalogue before enumeration'
    best, count = None, 0
    for c in itertools.combinations(range(len(triples)), 5):
        rows = [r for i in c for r in triples[i]['rows']]
        if len(basis(rows)) != 15:
            continue
        count += 1
        spans = [triples[i]['retained_kernel_span'] for i in c]
        key = (min(spans), sum(spans), c)
        if best is None or key > best[0]:
            best = key, rows
    assert best is not None
    key, rows = best
    bp, _, _, B, info = setup(W, dict(rows=rows), args.k, True)
    state = dict(k=args.k, rows=rows, B=B, block_info=info,
        target_prefix_sha256=prefix, source_npz_sha256=sha(args.words),
        selected_indices=key[2], triple_catalogue=triples,
        valid_basis_count=count, sources=sources, script_sha256=sha(__file__),
        scope='OWN_BASIS_ONLY; native compilation and full package gates remain required')
    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / f'k{args.k}_basis.json'
    assert not destination.exists()
    destination.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(dict(status='BASIS_PACKING_CHECKED', path=str(destination),
        sha256=sha(destination), triples=len(triples), valid_bases=count,
        retained_kernel_spans=[len(f) for f in bp.F])), flush=True)


if __name__ == '__main__':
    main()
