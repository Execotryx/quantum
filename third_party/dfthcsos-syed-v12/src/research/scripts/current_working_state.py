# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Recover the current research arrays from a complete delivered submission."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--submission', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--expected-working-sha256')
    args = ap.parse_args()
    assert not args.output.exists()
    raw = args.submission.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.expected_sha256
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        words = z['angle_words'].astype(np.int64)
        w = z['W'].astype(np.float64)
        H2 = z['H2_I'].astype(np.float64)
        edges = z['tree_edges'].astype(np.int64)
    assert words.shape == (1220, 75) and w.shape == (8, 143, 44)
    assert H2.shape == (8, 44) and edges.shape == (75, 2)
    assert np.all((words >= 0) & (words <= 255))
    buf = io.BytesIO()
    np.savez_compressed(buf, words=words, w=w, H2=H2, tree_edges=edges)
    result = buf.getvalue()
    digest = hashlib.sha256(result).hexdigest()
    if args.expected_working_sha256:
        assert digest == args.expected_working_sha256
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(json.dumps({'status': 'EXACT_CURRENT_ARRAY_EXTRACTION_PASS',
        'submission_sha256': args.expected_sha256, 'working_npz_sha256': digest,
        'word_prefix_sha256': hashlib.sha256(words.astype(np.uint8).tobytes()).hexdigest(),
        'output': str(args.output), 'requires_older_checkpoint': False}))


if __name__ == '__main__':
    main()
