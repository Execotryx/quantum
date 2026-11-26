"""In-place rounded signed products with retained guard bits."""

from typing import Any

import numpy as np

from .direct import Words


def _ripple_add(builder: Any, source: Any, target: Any, initial: Any, *,
                control: Any = None, extend: Any = None, dirty: Any = None) -> None:
    equal_width = len(source) == len(target)
    stages = len(source) - int(equal_width)
    for i in range(stages):
        a, b = source[i], target[i]
        c = source[i - 1] if i else initial
        builder.cx(a, b)
        builder.cx(a, c)
        builder.ccx(b, c, a)

    if equal_width:
        a, b = source[-1], target[-1]
        c = source[-2] if stages else initial
        builder.cx(a, c)
        if control is None:
            builder.cx(c, b)
        else:
            builder.ccx(control, c, b)
        builder.cx(a, c)
    else:
        c = source[-1]
        high = target[len(source):]
        active = c
        if control is not None:
            builder.init_and(control, c, extend)
            active = extend
        if dirty is None:
            builder.iadd(1, target=high, control=active)
        else:
            # Add an arbitrary dirty word with the carry, then subtract
            # the same word. Both equal-width ripples restore that word.
            _ripple_add(builder, dirty[:len(high)], high, active)
        if control is not None:
            builder.del_and(control, c, extend)
        if dirty is not None:
            builder.x(high)
            _ripple_add(builder, dirty[:len(high)], high, extend)
            builder.x(high)

    for i in range(stages - 1, -1, -1):
        a, b = source[i], target[i]
        c = source[i - 1] if i else initial
        builder.ccx(b, c, a)
        builder.cx(a, b)
        # c still holds the XOR of the original source bit and carry-in.
        if control is None:
            builder.cx(c, b)
        else:
            builder.ccx(control, c, b)
        builder.cx(a, c)


def add_with_borrowed_carry(builder: Any, source: Any, target: Any, scratch: Any, *,
                            control: Any = None, subtract: bool = False, dirty: Any = None) -> None:
    """Add or subtract using the source words as the ripple carry chain.

    Both scratch qubits start clean. An optional disjoint dirty word avoids
    allocating a native incrementer above the source width. All operands
    other than the target are restored, including a supplied control.
    """
    if not 1 <= len(source) <= len(target) or len(scratch) < 2:
        raise ValueError("borrowed carry requires a nonempty source, target, and two scratch qubits")
    if dirty is not None and len(dirty) < len(target) - len(source):
        raise ValueError("the dirty word must span the upper target")
    if subtract:
        builder.x(target)
    _ripple_add(builder, source, target, scratch[0], control=control, extend=scratch[1], dirty=dirty)
    if subtract:
        builder.x(target)


def row_sum(magnitude: Words, signed: Words, bits: int, guard: int, *, signed_digits: bool = False) -> Words:
    """Accumulate binary rows at guard-bit precision."""
    total = np.zeros_like(magnitude)
    for bit in range(bits):
        shift = guard + bit - bits - int(signed_digits)
        row = magnitude << shift if shift >= 0 else magnitude >> -shift
        if bit == bits - 1:
            row = -row
        digit = (signed >> bit) & 1
        total += (2 * digit - 1 if signed_digits else digit) * row
    if signed_digits:
        total -= magnitude >> (bits + 1 - guard)
    return total


def rounded_product(builder: Any, magnitude: Any, signed: Any, accumulator: Any, guard: int,
                    *, negate: bool = False, round_before_negation: bool = False,
                    adjoint: bool = False, scratch: Any = None, carry: Any = None, dirty: Any = None,
                    signed_digits: bool = False) -> None:
    """Add a rounded product to the high accumulator bits, retaining the guards.

    The signed input is a fractional two's-complement word. The other input
    is unsigned. The guard bits start zero and carry the discarded fraction
    until the adjoint. Negation can round before changing the product sign.
    Optional clean scratch uses measured partial products with an ungated add.
    Carry scratch opts into the source-borrowing ripple. The dirty pool
    may include other multiplier bits, and is disjoint from the accumulator
    and magnitude. The selected row control is excluded before borrowing.
    Signed-digit rows use unconditional adders. A fixed negative half-row
    removes the midpoint bias introduced by the signed digits.
    """
    if not len(magnitude) or not len(signed) or not 1 <= guard < len(accumulator):
        raise ValueError("rounded product requires operands, guard bits, and a high accumulator")
    if scratch is not None and len(scratch) < len(magnitude):
        raise ValueError("partial-product scratch must fit the magnitude")
    if dirty is not None and carry is None:
        raise ValueError("dirty upper workspace requires the borrowed-carry adder")
    if signed_digits and (scratch is not None or guard > len(signed) + 1):
        raise ValueError("signed digits require an unmeasured row and guard within the signed width plus one")
    bias = (1 << (guard - 1)) - int(negate and round_before_negation)
    if not adjoint:
        builder.gf2_iadd(bias, target=accumulator[:guard])
    rows = range(-int(signed_digits), len(signed))
    order = reversed(rows) if adjoint else rows
    for bit in order:
        shift = max(bit, 0) + guard - len(signed) - int(signed_digits)
        target = accumulator[max(0, shift):]
        start = max(0, -shift)
        row = magnitude[start:start + len(target)]
        if not len(row):
            continue
        control = signed[bit] if bit >= 0 else None
        upper = None if dirty is None else [wire for wire in dirty if control is None or wire.id != control.id]
        subtract = negate ^ adjoint ^ (bit in (-1, len(signed) - 1))
        apply = builder.isub if subtract else builder.iadd
        if signed_digits and control is not None:
            # Complementing the target conjugates addition into subtraction.
            if not subtract:
                builder.x(target)
            builder.cx(control, target)
            if carry is None:
                builder.iadd(row, target=target)
            else:
                add_with_borrowed_carry(builder, row, target, carry, dirty=upper)
            builder.cx(control, target)
            if not subtract:
                builder.x(target)
        elif scratch is None:
            if carry is None:
                if control is None:
                    apply(row, target=target)
                else:
                    apply(row, target=target, control=control)
            else:
                add_with_borrowed_carry(builder, row, target, carry, control=control, subtract=subtract, dirty=upper)
        else:
            products = scratch[:len(row)]
            builder.init_and(control, row, products)
            if carry is None:
                apply(products, target=target)
            else:
                add_with_borrowed_carry(builder, products, target, carry, subtract=subtract, dirty=upper)
            builder.del_and(control, row, products)
    if adjoint:
        builder.gf2_iadd(bias, target=accumulator[:guard])
