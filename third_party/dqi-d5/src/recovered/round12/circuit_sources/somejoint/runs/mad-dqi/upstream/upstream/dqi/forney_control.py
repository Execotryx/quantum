"""Move the Forney location control into the three-bit base reciprocal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import build, km  # noqa: E402
from quotient import ControlledQuotientBuilder, DirectQuotientDecoder  # noqa: E402


class _ForneyBuilder:
    """Replace located=flag*omega by a controlled denominator reciprocal."""

    def __init__(self, builder):
        self.builder = builder
        self.header_allocations = 0
        self.inverse = self.located = self.flag = self.omega = None
        self.products = 0

    def __getattr__(self, name):
        return getattr(self.builder, name)

    def alloc_qubits(self, width):
        if self.header_allocations == 3:
            return self.builder.alloc_qubits(width)
        assert width == (12, 12, 1)[self.header_allocations]
        self.header_allocations += 1
        if self.header_allocations == 2:
            self.located = km.array([])
            return self.located
        out = self.builder.alloc_qubits(width)
        if self.header_allocations == 1:
            self.inverse = out
        else:
            self.flag = out[0]
        return out

    def init_gf2_inverse_with_scaffold(self, input, *, target='alloc', field=None):
        assert target is self.inverse and self.flag is not None
        assert len(input) == 12 and field.modulus == 0x1053
        return self.builder.init_controlled_inverse(input, self.flag, target=target)

    def del_gf2_inverse_with_scaffold(self, input, *, target, scaffold, field=None):
        assert target is self.inverse and field.modulus == 0x1053
        self.builder.del_controlled_inverse(input, self.flag, target=target, scaffold=scaffold)

    def init_and(self, lhs, rhs, target='alloc'):
        if target is not self.located:
            return self.builder.init_and(lhs, rhs, target)
        assert lhs == self.flag and self.omega is None
        self.omega = rhs
        return target

    def del_and(self, lhs, rhs, target):
        if target is not self.located:
            return self.builder.del_and(lhs, rhs, target)
        assert lhs == self.flag and rhs is self.omega
        self.omega = None

    def gf2_phase_by_product(self, lhs, rhs, *, mask, field=None):
        assert lhs is self.located and rhs is self.inverse and self.omega is not None
        self.products += 1
        self.builder.gf2_phase_by_product(self.omega, rhs, mask=mask, field=field)


class ControlledForneyDecoder(DirectQuotientDecoder):
    def _chien_search_and_forney_mbuc(self, builder, reg_b, error_mbuc, n_b, n_B):
        proxy = _ForneyBuilder(builder)
        super()._chien_search_and_forney_mbuc(proxy, reg_b, error_mbuc, n_b, n_B)
        assert proxy.header_allocations == 3 and proxy.omega is None
        assert proxy.products == min((1 << self.field.degree) - 1, len(error_mbuc))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    start = time.monotonic()
    builder = ControlledQuotientBuilder()
    circuit = build(builder, iterations=218, decoder_type=ControlledForneyDecoder)
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
