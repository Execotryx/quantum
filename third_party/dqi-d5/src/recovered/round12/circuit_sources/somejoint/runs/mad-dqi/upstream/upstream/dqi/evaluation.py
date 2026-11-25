"""42-Toffoli GF(4096) products and a 66-Toffoli inverse.

Use a quartic extension over GF(8) for full products and a cubic extension
over GF(4) for the GF(64) products inside the quadratic-tower inverse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import build  # noqa: E402
from sweep import ReducedSweepDecoder  # noqa: E402
from cubic import CubicBuilder  # noqa: E402


class EvaluationBuilder(CubicBuilder):
    def __init__(self):
        super().__init__(decompositions=((6, 2), (12, 3)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    start = time.monotonic()
    builder = EvaluationBuilder()
    circuit = build(builder, decoder_type=ReducedSweepDecoder)
    assert builder.pointer_allocations == 5
    circuit.to_file(str(args.output), format='kmb')
    with args.output.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    stats = circuit.operation_statistics()
    print(json.dumps({'num_qubits': circuit.num_qubits, 'toffoli_count': stats.num_toffoli_like,
                      't_count': stats.num_t_like, 'num_ops': len(circuit), 'sha256': digest,
                      'build_seconds': time.monotonic() - start,
                      'bases': {n: {'subdegree': q.subdegree, 'beta': q.beta, 'theta': q.theta,
                                    'relation': q.relation, 'weights': q.weights}
                                for n, q in builder.evaluation_bases.items()}}, indent=2))


if __name__ == '__main__':
    main()
