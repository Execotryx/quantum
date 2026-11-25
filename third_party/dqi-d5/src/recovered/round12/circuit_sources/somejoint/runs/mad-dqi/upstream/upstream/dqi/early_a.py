"""Read the first completed EEA pair satisfying the degree criterion.

The reference reads B after another division transfers the finished A pair
there. Stop at that earlier boundary and run Chien/Forney directly on A.
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
from evaluation import EvaluationBuilder  # noqa: E402


class EarlyADecoder(ReducedSweepDecoder):
    def _synchronized_eea(self, builder, reg_a, reg_b, n_A, n_B, n_a, n_b,
                          n_q, flag, counter, halting_counter, *, n_iters, is_adjoint):
        self.readout = (reg_a, n_a, n_A)
        super()._synchronized_eea(builder, reg_a, reg_b, n_A, n_B, n_a, n_b,
                                  n_q, flag, counter, halting_counter,
                                  n_iters=n_iters, is_adjoint=is_adjoint)

    def _update_halting_counter(self, builder, n_A, n_B, n_b,
                                halting_counter, flag, is_c3, *, is_adjoint):
        _, n_a, saved_n_A = self.readout
        assert saved_n_A is n_A
        with builder.mark('early_a_halting_counter'):
            work = builder.alloc_qubits(2)
            ctrl, busy = work
            builder.init_and(is_c3, flag, ctrl)
            builder.flip_if_less_than(n_a, n_A, target=busy, control=ctrl)
            builder.cx(busy, ctrl)
            if is_adjoint:
                builder.isub(1, target=halting_counter, control=ctrl)
            else:
                builder.iadd(1, target=halting_counter, control=ctrl)
            builder.cx(busy, ctrl)
            builder.flip_if_less_than(n_a, n_A, target=busy, control=ctrl)
            builder.del_and(is_c3, flag, ctrl)
            builder.free(work)

    def _chien_search_and_forney_mbuc(self, builder, reg_b, error_mbuc, n_b, n_B):
        reg_a, n_a, n_A = self.readout
        super()._chien_search_and_forney_mbuc(builder, reg_a, error_mbuc, n_a, n_A)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--iterations', type=int, default=218)
    args = p.parse_args()
    start = time.monotonic()
    builder = EvaluationBuilder()
    circuit = build(builder, iterations=args.iterations, decoder_type=EarlyADecoder)
    assert builder.pointer_allocations == 5
    circuit.to_file(str(args.output), format='kmb')
    with args.output.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    stats = circuit.operation_statistics()
    print(json.dumps({'iterations': args.iterations, 'num_qubits': circuit.num_qubits,
                      'toffoli_count': stats.num_toffoli_like, 't_count': stats.num_t_like,
                      'num_ops': len(circuit), 'sha256': digest,
                      'build_seconds': time.monotonic() - start}, indent=2))


if __name__ == '__main__':
    main()
