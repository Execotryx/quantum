"""Fixed-degree multi-digit polynomial EEA division with exact history."""

from typing import Any

from .subtower import inverse_xor
from .tower import multiply_xor


def quotient_division(builder: Any, left_rows: list[list[Any]], right_rows: list[list[Any]],
                      numerator_degree: int, denominator_degree: int, quotients: list[Any], zero: Any,
                      *, adjoint: bool = False) -> None:
    """Divide using all fixed quotient digits, then exchange the three row pairs.

    All registers are disjoint. Forward quotient words and zero flag start at
    zero. Selected degrees must be actual leading positions and omitted shifted
    high terms must vanish. A zero selected denominator is a flagged no-op.
    The inverse requires corresponding forward outputs and retained history.
    """
    if len(left_rows) != 3 or len(right_rows) != 3:
        raise ValueError("division needs remainder, A and B row pairs")
    width = len(left_rows[0])
    if (width < 1 or not 0 <= denominator_degree <= numerator_degree < width
            or any(len(row) != width for row in (*left_rows, *right_rows))):
        raise ValueError("invalid row shape or selected degrees")
    max_shift = numerator_degree - denominator_degree
    if len(quotients) != max_shift + 1:
        raise ValueError("one history word is required per quotient digit")
    if any(len(word) != 12 for row in (*left_rows, *right_rows) for word in row):
        raise ValueError("division requires 12-bit row words")
    if any(len(word) != 12 for word in quotients):
        raise ValueError("quotient history words must be 12 bits")
    denominator = right_rows[0][denominator_degree]
    inverse = builder.alloc_qubits(12)

    def route() -> None:
        builder.x(zero)
        for left, right in zip(left_rows, right_rows, strict=True):
            for a, b in zip(left, right, strict=True):
                builder.cswap(zero, a, b)
        builder.x(zero)

    def digit(shift: int, *, reverse: bool) -> None:
        numerator = left_rows[0][denominator_degree + shift]
        quotient = quotients[shift]
        if not reverse:
            multiply_xor(builder, numerator, inverse, quotient)
        for left, right in zip(left_rows, right_rows, strict=True):
            for i in range(width - shift):
                multiply_xor(builder, quotient, right[i], left[i + shift])
        if reverse:
            multiply_xor(builder, numerator, inverse, quotient)

    if adjoint:
        route()
    else:
        builder.flip_if_equal(denominator, 0, target=zero)
    inverse_xor(builder, denominator, inverse)
    shifts = range(max_shift + 1) if adjoint else range(max_shift, -1, -1)
    for shift in shifts:
        digit(shift, reverse=adjoint)
    inverse_xor(builder, denominator, inverse)
    if adjoint:
        builder.flip_if_equal(denominator, 0, target=zero)
    else:
        route()
    builder.free(inverse)
