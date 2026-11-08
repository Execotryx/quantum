"""Piecewise Taylor phasing with integer coefficient generation and reversible Horner."""

from dataclasses import dataclass
from fractions import Fraction
from math import isqrt
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from .unlookup import unlookup

Words = NDArray[np.int64]


@dataclass(frozen=True)
class DirectFormat:
    n_p: int
    segment_bits: int
    fractional: tuple[int, ...]
    fused: bool = False
    reuse_lookup: bool = False
    binary_normalization: bool = False
    measurement_unlookup: bool = False
    sibling_cnot: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.n_p <= 10 or not 0 <= self.segment_bits <= min(8, 2 * self.n_p):
            raise ValueError("unsupported normalization or segment width")
        if not 2 <= len(self.fractional) <= 5 or not all(1 <= f <= 48 for f in self.fractional):
            raise ValueError("unsupported degree or coefficient precision")

    @property
    def output_fractional(self) -> int:
        return self.fractional[0] + self.n_p

    @property
    def widths(self) -> tuple[int, ...]:
        # u=1 has c0=1. Retain that integer bit through scaling, including when x>1.
        return (self.fractional[0] + 1, *self.fractional[1:])


def coefficient_table(fmt: DirectFormat) -> tuple[tuple[int, ...], ...]:
    """Nearest-even integer Taylor coefficients, stored as positive magnitudes."""
    segments = 1 << fmt.segment_bits
    rows = []
    for address in range(segments, 4 * segments):
        u = Fraction(address, segments)
        factor = Fraction(1)
        row = []
        for degree, (fractional, width) in enumerate(zip(fmt.fractional, fmt.widths, strict=True)):
            if degree:
                factor *= Fraction(2 * degree - 1, 2 * degree) / u
            squared = (factor * (1 << fractional)) ** 2 / u
            floor = isqrt(squared.numerator // squared.denominator)
            midpoint_squared = Fraction((2 * floor + 1) ** 2, 4)
            word = floor + int(squared > midpoint_squared or (squared == midpoint_squared and floor % 2))
            if word >= 1 << width:
                raise ValueError("coefficient does not fit its register")
            row.append(word)
        rows.append(tuple(row))
    return tuple(rows)


def phase64(fmt: DirectFormat, table: tuple[tuple[int, ...], ...], xs: Words) -> NDArray[np.uint64]:
    """Model the phase of the emitted column-truncated arithmetic."""
    x_bits = 2 * fmt.n_p + 2
    if np.any(xs < 1) or np.any(xs >= 1 << x_bits):
        raise ValueError("input outside the normalized register domain")
    exponents = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    left_shift = fmt.n_p - exponents
    normalized = xs << (2 * left_shift)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    indices = (normalized >> low_width) - (1 << fmt.segment_bits)
    words = np.asarray(table, dtype=np.int64)[indices]
    value = words[:, -1]
    for j in range(len(fmt.fractional) - 2, -1, -1):
        product = np.zeros_like(xs)
        for bit in range(low_width):
            shift = fmt.fractional[j] - fmt.fractional[j + 1] + bit - 2 * fmt.n_p
            term = value << shift if shift >= 0 else value >> -shift
            product += ((normalized >> bit) & 1) * (term & ((1 << fmt.widths[j]) - 1))
        value = words[:, j] - product
        if np.any(value < 0):
            raise OverflowError("Horner subtraction would wrap")
    scaled = (value << left_shift).astype(np.uint64)
    return scaled << np.uint64(64 - fmt.output_fractional)


def _load_table(builder: Any, address: Any, path: Any, registers: list[Any], table,
                *, sibling_cnot: bool = False) -> None:
    """XOR a row with a unary prefix traversal and phase-correct temporary ANDs."""
    first = 1 << (len(address) - 2)

    def walk(depth: int, prefix: int, control: Any) -> None:
        remaining = len(address) - depth
        if (prefix + 1) << remaining <= first:
            return
        if remaining == 0:
            for word, register in zip(table[prefix - first], registers, strict=True):
                builder.gf2_iadd(word, target=register, control=control)
            return
        bit = address[remaining - 1]
        if depth == 0:
            builder.x(bit)
            walk(depth + 1, prefix * 2, bit)
            builder.x(bit)
            walk(depth + 1, prefix * 2 + 1, bit)
            return
        flag = path[depth - 1]
        if not sibling_cnot or ((prefix * 2 + 1) << (remaining - 1)) > first:
            builder.x(bit)
            builder.init_and(control, bit, flag)
            if sibling_cnot:
                builder.x(bit)
                walk(depth + 1, prefix * 2, flag)
                # Toggling by the parent changes its left predicate to the right one.
                builder.cx(control, flag)
            else:
                walk(depth + 1, prefix * 2, flag)
                builder.del_and(control, bit, flag)
                builder.x(bit)
                builder.init_and(control, bit, flag)
        else:
            builder.init_and(control, bit, flag)
        walk(depth + 1, prefix * 2 + 1, flag)
        builder.del_and(control, bit, flag)

    walk(0, 0, True)


def _binary_count(builder: Any, x: Any, count: Any, n_p: int) -> None:
    """XOR the leading-zero pair count using a prefix AND ladder."""
    flags = builder.alloc_qubits(n_p)
    pair = builder.alloc_qubits(1)

    def update(k: int, inverse: bool) -> None:
        hi, lo = x[len(x) - 2 * k - 1], x[len(x) - 2 * k - 2]
        builder.x(hi)
        builder.x(lo)
        logical_and = builder.del_and if inverse else builder.init_and
        if k:
            builder.init_and(hi, lo, pair[0])
            logical_and(flags[k - 1], pair[0], flags[k])
            builder.del_and(hi, lo, pair[0])
        else:
            logical_and(hi, lo, flags[k])
        builder.x(lo)
        builder.x(hi)

    for k in range(n_p):
        update(k, False)
        for bit, wire in enumerate(count):
            if (k ^ (k + 1)) >> bit & 1:
                builder.cx(flags[k], wire)
    for k in reversed(range(n_p)):
        update(k, True)
    builder.free(pair)
    builder.free(flags)


def _binary_shift(builder: Any, inverse: bool, count: Any, *lanes: Any) -> None:
    rotate = builder.right_rotate if inverse else builder.left_rotate
    positions = reversed(range(len(count))) if inverse else range(len(count))
    for i in positions:
        for lane in lanes:
            rotate(lane, 1 << i, control=count[i])


def build_circuit(km: Any, primitives: Any, fmt: DirectFormat, table: tuple[tuple[int, ...], ...],
                  *, liveness: dict[str, int] | None = None, builder: Any = None) -> Any:
    """Emit the clean phase oracle using the pinned reference arithmetic primitives."""
    if builder is None:
        builder = km.CircuitBuilder()

    def observe(stage: str) -> None:
        if liveness is not None:
            allocated = builder.num_allocated_qubits
            liveness[stage] = cast(int, allocated() if callable(allocated) else allocated)
    x = builder.create_quantum_register(2 * fmt.n_p + 2, name="x")
    flags = builder.alloc_qubits(fmt.n_p.bit_length() if fmt.binary_normalization else fmt.n_p)
    if fmt.binary_normalization:
        _binary_count(builder, x, flags, fmt.n_p)
        _binary_shift(builder, False, flags, x[::2], x[1::2])
    output = builder.alloc_qubits(fmt.output_fractional + 1)
    coefs = [output[: fmt.widths[0]], *(builder.alloc_qubits(width) for width in fmt.widths[1:])]
    path = builder.alloc_qubits(fmt.segment_bits + 1)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    address = x[low_width:]
    if not fmt.binary_normalization:
        primitives._normalize(builder, False, x, flags)
    _load_table(builder, address, path, coefs, table, sibling_cnot=fmt.sibling_cnot)
    observe("lookup")
    if fmt.reuse_lookup or fmt.measurement_unlookup:
        builder.free(path)

    scratch = builder.alloc_qubits(max(fmt.widths))
    product = None if fmt.fused else builder.alloc_qubits(max(fmt.widths))
    observe("arithmetic")

    def rows(j: int, target: Any, inverse: bool, subtract: bool = False) -> None:
        acc, operand = coefs[j : j + 2]
        for bit in range(low_width):
            shift = fmt.fractional[j] - fmt.fractional[j + 1] + bit - 2 * fmt.n_p
            terms = [
                (operand[i], i + shift) for i in range(max(0, -shift), min(len(operand), len(acc) - shift))
            ]
            if terms:
                primitives._add_row(builder, inverse, x[bit], terms, target, scratch, subtract=subtract)

    def horner_step(j: int, inverse: bool) -> None:
        acc = coefs[j]
        if product is None:
            rows(j, acc, inverse, subtract=True)
            return
        work = product[: len(acc)]
        rows(j, work, False)
        if inverse:
            builder.iadd(work, target=acc)
        else:
            builder.isub(work, target=acc)
        rows(j, work, True)

    stages = range(len(coefs) - 2, -1, -1)
    for j in stages:
        horner_step(j, False)
    if fmt.binary_normalization:
        _binary_shift(builder, False, flags, output)
    else:
        primitives._denormalize(builder, False, flags, output)
    primitives._phase_by_bits(builder, output[:-1])
    observe("phase")
    if fmt.binary_normalization:
        _binary_shift(builder, True, flags, output)
    else:
        primitives._denormalize(builder, True, flags, output)
    for j in reversed(stages):
        horner_step(j, True)

    if product is not None:
        builder.free(product)
    builder.free(scratch)
    if fmt.measurement_unlookup:
        unlookup(builder, address, coefs, table, sibling_cnot=fmt.sibling_cnot)
    else:
        if fmt.reuse_lookup:
            path = builder.alloc_qubits(fmt.segment_bits + 1)
        _load_table(builder, address, path, coefs, table, sibling_cnot=fmt.sibling_cnot)
    observe("after_unlookup")
    if fmt.binary_normalization:
        _binary_shift(builder, True, flags, x[::2], x[1::2])
        _binary_count(builder, x, flags, fmt.n_p)
    else:
        primitives._normalize(builder, True, x, flags)
    for register in (*coefs[1:], output, flags):
        builder.free(register)
    if not fmt.measurement_unlookup:
        builder.free(path)
    return builder.finish_circuit()
