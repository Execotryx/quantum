# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Rebuild the frozen circuits without rerunning optimization.

Run with a Python environment containing NumPy and the supplied kickmix.
The output directory contains only .kmb circuit files for official verify.py.
The default words are the frozen submission's angle_words. Weight-only
changes in that NPZ do not alter the resulting circuits.
"""
import argparse, hashlib, json, os, sys
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
import kickmix as km
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'compiler'))
from emit_plan import emit as emit_regular
from emit_k0 import emit as emit_first

def complete(words):
    assert words.shape == (1220, 75)
    a = np.zeros((1232, 75), dtype=np.uint8)
    a[:1220] = words
    f = a.reshape(77, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    f[76, 4:] = 0
    for b in range(7):
        for h in range(77):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    assert np.array_equal(a[:1220], words)
    return a

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--submission', type=Path, default=ROOT / 'submission.npz')
    p.add_argument('--output', type=Path, default=ROOT / 'rebuilt_circuits')
    p.add_argument('--source-output', type=Path, default=ROOT / 'rebuilt_sources')
    args = p.parse_args()
    with np.load(args.submission, allow_pickle=False) as z:
        words = complete(z['angle_words'])
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    args.source_output.mkdir(parents=True, exist_ok=True)
    results = []
    for k in range(15):
        state = json.loads((ROOT / 'plans' / f'angle_k_{k}.json').read_text())
        source = args.source_output / f'angle_k_{k}.kmx'
        report = (emit_first if k == 0 else emit_regular)(state, words, source)
        circ = km.Circuit.from_file(source)
        binary = args.output / f'angle_k_{k}.kmb'
        circ.to_file(binary, format='kmb')
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        expected = manifest['loaders'][k]
        if expected.get('sha256'):
            assert digest == expected['sha256'], ('Nonidentical rebuild', k, digest)
        if expected.get('toffoli_per_call'):
            assert report['toffoli_count'] == expected['toffoli_per_call']
        results.append({'k': k, 'sha256': digest, 'toffoli_per_call': report['toffoli_count']})
        print(json.dumps(results[-1]), flush=True)
    (args.output.parent / 'rebuild_verification.json').write_text(json.dumps(results, indent=2) + '\n')

if __name__ == '__main__': main()
