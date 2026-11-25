"""Use six bits for a halting counter that advances at most every fourth step."""

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
from evaluation import EvaluationBuilder  # noqa: E402
from zero_chain import ZeroChainDecoder  # noqa: E402


class CompactCounterBuilder(EvaluationBuilder):
    def __init__(self):
        super().__init__()
        self.halting_allocations = 0

    def alloc_qubits(self, width):
        if width == 8 and self.pointer_allocations == 5 and not self.halting_allocations:
            self.halting_allocations += 1
            return self.native.alloc_qubits(6)
        return super().alloc_qubits(width)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    start = time.monotonic()
    builder = CompactCounterBuilder()
    circuit = build(builder, iterations=218, decoder_type=ZeroChainDecoder)
    assert builder.pointer_allocations == 5 and builder.halting_allocations == 1
    circuit.to_file(str(args.output), format='kmb')
    with args.output.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    stats = circuit.operation_statistics()
    print(json.dumps({'num_qubits': circuit.num_qubits, 'toffoli_count': stats.num_toffoli_like,
                      't_count': stats.num_t_like, 'num_ops': len(circuit), 'sha256': digest,
                      'build_seconds': time.monotonic() - start}, indent=2))


if __name__ == '__main__':
    main()
