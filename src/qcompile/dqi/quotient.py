"""Reversible multiplication in a monic polynomial quotient over GF(4096).

This development primitive accepts a fixed public degree and quantum modulus
coefficients; it is not yet an efficient full-degree reciprocal circuit.
"""

from typing import Any

from .tower import multiply_xor


def quotient_multiply_xor(builder: Any, left: list[Any], right: list[Any],
                          modulus: list[Any], target: list[Any]) -> None:
    """XOR (left*right mod (z**d + modulus)) into a disjoint target.

    Coefficients are ascending, every list has d disjoint 12-bit registers, and
    the modulus has an implicit leading coefficient one. All inputs are
    preserved, including for reducible moduli; scratch is clean on return.
    """
    degree = len(modulus)
    if degree < 1 or any(len(group) != degree for group in (left, right, target)):
        raise ValueError("quotient operands must have the same positive degree")
    if any(len(word) != 12 for word in (*left, *right, *modulus, *target)):
        raise ValueError("quotient multiplication requires 12-bit words")
    workspace = [builder.alloc_qubits(12) for _ in range(2 * degree - 1)]

    def product() -> None:
        for i, a in enumerate(left):
            for j, b in enumerate(right):
                multiply_xor(builder, a, b, workspace[i + j])

    def reduce(*, reverse: bool) -> None:
        degrees = range(degree, 2 * degree - 1) if reverse else range(2 * degree - 2, degree - 1, -1)
        for k in degrees:
            for i, coefficient in enumerate(modulus):
                multiply_xor(builder, workspace[k], coefficient, workspace[k - degree + i])

    product()
    reduce(reverse=False)
    for source, destination in zip(workspace[:degree], target, strict=True):
        builder.cx(source, destination)
    reduce(reverse=True)
    product()
    for word in workspace:
        builder.free(word)
