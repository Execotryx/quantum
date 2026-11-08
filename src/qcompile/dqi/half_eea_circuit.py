"""One reversible monomial elimination for half-degree polynomial EEA."""

from typing import Any

from .tower import multiply_xor


def monomial_eea_step(builder: Any, left_rows: list[list[Any]], right_rows: list[list[Any]],
                      quotient: Any, shift: int, *, adjoint: bool = False) -> None:
    """Eliminate q*z**shift across remainder/A/B rows, then exchange rows.

    Every row has the same fixed number of disjoint 12-bit words. Quotient is
    supplied and preserved. This is one EEA step only when its full quotient is
    the supplied monomial and all terms beyond the row width vanish. General
    polynomial quotient control and support checking are not included.
    """
    if len(left_rows) != 3 or len(right_rows) != 3 or len(quotient) != 12:
        raise ValueError("EEA slice needs remainder, A and B row pairs")
    width = len(left_rows[0])
    if width < 1 or not 0 <= shift < width:
        raise ValueError("invalid EEA row width or quotient shift")
    if any(len(row) != width for row in (*left_rows, *right_rows)):
        raise ValueError("EEA row widths differ")
    if any(len(word) != 12 for row in (*left_rows, *right_rows) for word in row):
        raise ValueError("EEA slice requires 12-bit field words")

    def swap() -> None:
        for left, right in zip(left_rows, right_rows, strict=True):
            for a, b in zip(left, right, strict=True):
                builder.swap(a, b)

    if adjoint:
        swap()
    for left, right in zip(left_rows, right_rows, strict=True):
        for i in range(width - shift):
            multiply_xor(builder, quotient, right[i], left[i + shift])
    if not adjoint:
        swap()
