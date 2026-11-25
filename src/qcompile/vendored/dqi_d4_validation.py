"""Reversible validation of synthesized D4 polynomials against syndrome moments."""

from functools import lru_cache

from qcompile.dqi.decoder import _divide
from qcompile.dqi.field import GF4096


@lru_cache(maxsize=4)
def quotient_columns(geometry: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    """Linear map from moments to Q mod P/X² and the two low coefficients of Q."""
    if len(geometry) < 7 or geometry[:2] != (0, 0) or not geometry[2] or geometry[-1] != 1:
        raise ValueError("Expected a monic geometry with exactly two factors of X")
    field = GF4096()
    modulus = list(geometry[2:])
    degree = len(geometry) - 1
    columns = []
    for shift in range(1, degree + 1):
        q = list(geometry[shift:])
        _, remainder = _divide(q, modulus, field)
        pad = [*remainder, *([0] * (degree - 2 - len(remainder)))]
        columns.append(tuple([*pad, q[0], q[1] if len(q) > 1 else 0]))
    return tuple(columns)


def xor_quotient(builder, reference, syndrome, target, geometry):
    """XOR the quotient's CRT coordinates into a disjoint word bank."""
    columns = quotient_columns(tuple(geometry))
    if len(syndrome) != len(columns) or len(target) != len(columns):
        raise ValueError("The quotient and syndrome must match the geometry")
    for source, column in zip(syndrome, columns, strict=True):
        for word, constant in zip(target, column, strict=True):
            if constant:
                reference.cx(builder, source, word, constant)


def zero_words(builder, reference, words, flag=None):
    """Compute or erase a clean all-zero predicate with a ladder over word flags."""
    flags = [reference.zero_flag(builder, word) for word in words]
    builder.x(flags)
    if flag is None:
        flag = reference.zero_flag(builder, flags)
    else:
        reference.clear_flag(builder, flags, flag)
    builder.x(flags)
    for word_flag, word in reversed(list(zip(flags, words, strict=True))):
        reference.clear_flag(builder, word, word_flag)
    return flag


def xor_invalid_rational(builder, reference, quotient, banks, geometry, invalid):
    """XOR a rejection flag for wrong degrees, zero D, or unmatched moments.

    The banks must be wide enough to contain the untruncated reconstruction.
    Polynomial arithmetic checks modulo both X² and W=P/X². Multiplication
    by X modulo W is invertible because W has a nonzero constant.
    """
    modulus = geometry[2:]
    degree = len(geometry) - 1
    n, d = banks
    if degree % 2 or len(quotient) != degree or len(n) != len(d) or len(d) < degree // 2 + 2:
        raise ValueError("Expected full-width quotient and untruncated polynomial banks")
    limit = degree // 2
    residue = [builder.alloc_qubits(12) for _ in range(degree - 2)]
    low = [builder.alloc_qubits(12) for _ in range(2)]
    factors = [(index, coefficient) for index, coefficient in enumerate(modulus[1:-1], 1) if coefficient]
    xor_product = reference.ar.mul_xor0

    def rotate(reverse=False):
        if reverse:
            first = residue.pop(0)
            reference.scale(builder, first, reference.inv(modulus[0]))
            for index, coefficient in factors:
                reference.cx(builder, first, residue[index - 1], coefficient)
            residue.append(first)
        else:
            last = residue.pop()
            for index, coefficient in factors:
                reference.cx(builder, last, residue[index - 1], coefficient)
            reference.scale(builder, last, modulus[0])
            residue.insert(0, last)

    def multiply(reverse=False):
        for coefficient in d[:limit + 1] if reverse else reversed(d[:limit + 1]):
            if not reverse:
                rotate()
            for source, word in zip(quotient[:-2], residue, strict=True):
                xor_product(builder, source, coefficient, word)
            if reverse:
                rotate(reverse=True)

    def add_low_and_numerator():
        for word, target in zip(n[:limit], residue, strict=False):
            builder.cx(word, target)
        builder.cx(n[0], low[0])
        builder.cx(n[1], low[1])
        xor_product(builder, quotient[-2], d[0], low[0])
        xor_product(builder, quotient[-2], d[1], low[1])
        xor_product(builder, quotient[-1], d[0], low[1])

    multiply()
    add_low_and_numerator()
    checks = residue + low + n[limit:] + d[limit + 1:]
    within_bounds = zero_words(builder, reference, checks)
    zero_denominator = zero_words(builder, reference, d[:limit + 1])
    builder.x(zero_denominator)
    builder.x(invalid)
    builder.ccx(within_bounds, zero_denominator, invalid)
    builder.x(zero_denominator)

    zero_words(builder, reference, d[:limit + 1], zero_denominator)
    zero_words(builder, reference, checks, within_bounds)
    add_low_and_numerator()
    multiply(reverse=True)
    for word in residue + low:
        builder.free(word)
