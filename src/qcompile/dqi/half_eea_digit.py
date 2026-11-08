"""Coherent quotient digit and reversible polynomial EEA monomial step.

The quotient is explicit retained history. A zero selected denominator is a
flagged no-op on the polynomial rows, and the inverse clears both records.
"""

from typing import Any

from .subtower import inverse_xor
from .tower import multiply_xor


def quotient_eea_digit(builder: Any, left_rows: list[list[Any]], right_rows: list[list[Any]],
                       numerator_degree: int, shift: int, quotient: Any, zero: Any,
                       *, adjoint: bool = False) -> None:
    """Apply/reverse one selected monomial division digit on R, A and B rows.

    All registers are disjoint. Forward quotient and zero flag start at zero.
    The selected numerator/denominator positions must be the actual leading
    coefficients for an EEA division step; terms shifted past the row width
    must vanish. A zero selected denominator is flagged and leaves rows intact.
    The adjoint requires an output from this forward operation.
    """
    if len(left_rows) != 3 or len(right_rows) != 3 or len(quotient) != 12:
        raise ValueError("EEA digit needs remainder, A and B row pairs")
    width = len(left_rows[0])
    if (width < 1 or not 0 <= shift <= numerator_degree < width
            or any(len(row) != width for row in (*left_rows, *right_rows))):
        raise ValueError("invalid EEA digit width or selected degrees")
    if any(len(word) != 12 for row in (*left_rows, *right_rows) for word in row):
        raise ValueError("EEA digit requires 12-bit field words")
    numerator = left_rows[0][numerator_degree]
    denominator = right_rows[0][numerator_degree - shift]
    inverse = builder.alloc_qubits(12)

    def quotient_xor() -> None:
        inverse_xor(builder, denominator, inverse)
        multiply_xor(builder, numerator, inverse, quotient)
        inverse_xor(builder, denominator, inverse)

    def update() -> None:
        for left, right in zip(left_rows, right_rows, strict=True):
            for i in range(width - shift):
                multiply_xor(builder, quotient, right[i], left[i + shift])

    def route() -> None:
        builder.x(zero)
        for left, right in zip(left_rows, right_rows, strict=True):
            for a, b in zip(left, right, strict=True):
                builder.cswap(zero, a, b)
        builder.x(zero)

    if adjoint:
        route()
        update()
        quotient_xor()
        builder.flip_if_equal(denominator, 0, target=zero)
    else:
        builder.flip_if_equal(denominator, 0, target=zero)
        quotient_xor()
        update()
        route()
    builder.free(inverse)
