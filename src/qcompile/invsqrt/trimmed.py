"""Build and prove a high-bit-trimmed v4 inverse-square-root circuit."""

from typing import Any

import numpy as np

from .direct import DirectFormat, Words, _binary_count, _binary_shift, _load_table, phase64
from .unlookup import unlookup


class TrimmedFormat(DirectFormat):
    @property
    def widths(self) -> tuple[int, ...]:
        return tuple(width - 1 for width in super().widths)


def prove_chunk(fmt: TrimmedFormat, table: tuple[tuple[int, ...], ...], xs: Words) -> None:
    """Check every intermediate subtraction, output bound and original phase."""
    exponent = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    left = fmt.n_p - exponent
    normalized = xs << (2 * left)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    indices = (normalized >> low_width) - (1 << fmt.segment_bits)
    words = np.asarray(table, dtype=np.int64)[indices]
    value = words[:, -1]
    for stage in range(len(fmt.fractional) - 2, -1, -1):
        accumulator = words[:, stage].copy()
        mask = (1 << fmt.widths[stage]) - 1
        for bit in range(low_width):
            shift = fmt.fractional[stage] - fmt.fractional[stage + 1] + bit - 2 * fmt.n_p
            term = value << shift if shift >= 0 else value >> -shift
            accumulator -= ((normalized >> bit) & 1) * (term & mask)
            if np.any(accumulator < 0) or np.any(accumulator > mask):
                raise OverflowError("trimmed Horner intermediate would wrap")
        value = accumulator
    scaled = value << left
    if np.any(scaled >= 1 << fmt.output_fractional):
        raise OverflowError("trimmed output would lose its high bit")
    trimmed = scaled.astype(np.uint64) << np.uint64(64 - fmt.output_fractional)
    original_fmt = DirectFormat(fmt.n_p, fmt.segment_bits, fmt.fractional, fmt.fused,
                                fmt.reuse_lookup, fmt.binary_normalization, fmt.measurement_unlookup)
    if not np.array_equal(trimmed, phase64(original_fmt, table, xs)):
        raise ValueError("trimmed phase differs from the frozen control")


def build_circuit(km: Any, primitives: Any, fmt: TrimmedFormat, table: tuple[tuple[int, ...], ...]) -> Any:
    """Build only the frozen v4 layout with narrower clean coefficient registers."""
    if not (fmt.fused and fmt.reuse_lookup and fmt.binary_normalization and fmt.measurement_unlookup):
        raise ValueError("trimmed circuit requires the v4 architecture")
    if len(table) != 3 * (1 << fmt.segment_bits) or any(
        len(row) != len(fmt.widths) or any(word < 0 or word >= 1 << width
            for word, width in zip(row, fmt.widths, strict=True)) for row in table
    ):
        raise ValueError("table has a nonzero trimmed bit or invalid shape")
    builder = km.CircuitBuilder()
    x = builder.create_quantum_register(2 * fmt.n_p + 2, name="x")
    flags = builder.alloc_qubits(fmt.n_p.bit_length())
    _binary_count(builder, x, flags, fmt.n_p)
    _binary_shift(builder, False, flags, x[::2], x[1::2])
    output = builder.alloc_qubits(fmt.output_fractional)
    coefs = [output[:fmt.widths[0]], *(builder.alloc_qubits(width) for width in fmt.widths[1:])]
    path = builder.alloc_qubits(fmt.segment_bits + 1)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    address = x[low_width:]
    _load_table(builder, address, path, coefs, table)
    builder.free(path)
    scratch = builder.alloc_qubits(max(fmt.widths))

    def rows(stage: int, inverse: bool) -> None:
        acc, operand = coefs[stage:stage + 2]
        for bit in range(low_width):
            shift = fmt.fractional[stage] - fmt.fractional[stage + 1] + bit - 2 * fmt.n_p
            terms = [(operand[i], i + shift) for i in range(max(0, -shift),
                     min(len(operand), len(acc) - shift))]
            if terms:
                primitives._add_row(builder, inverse, x[bit], terms, acc, scratch, subtract=True)

    for stage in range(len(coefs) - 2, -1, -1):
        rows(stage, False)
    _binary_shift(builder, False, flags, output)
    primitives._phase_by_bits(builder, output)
    _binary_shift(builder, True, flags, output)
    for stage in range(len(coefs) - 1):
        rows(stage, True)
    builder.free(scratch)
    unlookup(builder, address, coefs, table)
    _binary_shift(builder, True, flags, x[::2], x[1::2])
    _binary_count(builder, x, flags, fmt.n_p)
    for register in (*coefs[1:], output, flags):
        builder.free(register)
    return builder.finish_circuit()
