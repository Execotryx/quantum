"""Reversible radix-4 Booth decoder and signed, truncated row slice."""

from typing import Any


def toggle_magnitudes(builder: Any, low: Any, middle: Any, high: Any,
                      one: Any, two: Any, parity: Any, *, inverse: bool = False) -> None:
    """XOR the flags for |low + middle - 2*high| equal to one or two.

    The parity and flag scratch must start at zero. Apply the gates in reverse
    order to erase the flags. The decoder has no measurement operations.
    """
    if not inverse:
        builder.cx(middle, one)
        builder.cx(low, one)
    builder.cx(high, parity)
    builder.cx(middle, parity)
    builder.x(one)
    builder.ccx(one, parity, two)
    builder.x(one)
    builder.cx(middle, parity)
    builder.cx(high, parity)
    if inverse:
        builder.cx(low, one)
        builder.cx(middle, one)


def signed_row(builder: Any, low: Any, middle: Any, high: Any, operand: Any,
               target: Any, scratch: Any, shift: int, *, subtract: bool = False) -> None:
    """Add a signed Booth row, with arithmetic right shifts and modular target.

    Scratch comprises four clean qubits. Negative products are rounded toward
    negative infinity by adding one to the magnitude if discarded bits are
    nonzero. The effective sign may be inverted by ``subtract``.
    """
    if len(scratch) < 4:
        raise ValueError("four clean decoder and rounding qubits required")
    one, two, parity = scratch[:3]
    correction = scratch[3]
    toggle_magnitudes(builder, low, middle, high, one, two, parity)
    if subtract:
        builder.x(high)
    builder.cx(high, target)
    for amount, flag in ((1, one), (2, two)):
        start = shift + amount - 1
        if 0 <= start < len(target):
            builder.iadd(operand[:len(target) - start], target=target[start:], control=flag)
        elif start < 0:
            dropped = min(-start, len(operand))
            if dropped < len(operand):
                builder.iadd(operand[dropped:], target=target, control=flag)
            # Arithmetic shift of a negative word is minus the ceiling of its
            # magnitude. The sign for rounding is the original digit sign,
            # even when subtraction inverts the effective target operation.
            builder.x(parity)
            builder.flip_if_equal(operand[:dropped], 0, target=parity)
            if subtract:
                builder.x(high)
            builder.multi_controlled_x([high, flag, parity], correction)
            builder.iadd(1, target=target, control=correction)
            builder.multi_controlled_x([high, flag, parity], correction)
            if subtract:
                builder.x(high)
            builder.flip_if_equal(operand[:dropped], 0, target=parity)
            builder.x(parity)
    builder.cx(high, target)
    if subtract:
        builder.x(high)
    toggle_magnitudes(builder, low, middle, high, one, two, parity, inverse=True)
