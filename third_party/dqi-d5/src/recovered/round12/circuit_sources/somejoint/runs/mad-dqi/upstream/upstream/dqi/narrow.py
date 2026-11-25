"""Use seven bits for the five EEA pointers into 73-word arrays.

All field arithmetic is v2. The halting counter remains eight bits, and the
reference's 222 forward and reverse steps are unchanged.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import build  # noqa: E402
from recursive import RecursiveBuilder  # noqa: E402


class NarrowBuilder(RecursiveBuilder):
    def __init__(self):
        super().__init__()
        self.pointer_allocations = 0

    def alloc_qubits(self, width):
        # In the imported top-level builder, the first five 8-bit allocations
        # are n_A, n_B, n_a, n_b and n_q. The next is the halting counter.
        # Internal arithmetic uses self.native and does not pass this hook.
        if width == 8 and self.pointer_allocations < 5:
            self.pointer_allocations += 1
            return self.native.alloc_qubits(7)
        return self.native.alloc_qubits(width)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    start = time.monotonic()
    builder = NarrowBuilder()
    circuit = build(builder)
    assert builder.pointer_allocations == 5
    circuit.to_file(str(args.output), format='kmb')
    with args.output.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    stats = circuit.operation_statistics()
    print(json.dumps({'num_qubits': circuit.num_qubits, 'toffoli_count': stats.num_toffoli_like,
                      't_count': stats.num_t_like, 'num_ops': len(circuit), 'sha256': digest,
                      'build_seconds': time.monotonic() - start}, indent=2))


if __name__ == '__main__':
    main()
