"""In-place rounded signed products with retained guard bits."""

from typing import Any

import numpy as np

from .direct import Words


def row_sum(magnitude: Words, signed: Words, bits: int, guard: int) -> Words:
    """Accumulate binary rows at guard-bit precision."""
    total = np.zeros_like(magnitude)
    for bit in range(bits):
        shift = guard + bit - bits
        row = magnitude << shift if shift >= 0 else magnitude >> -shift
        if bit == bits - 1:
            row = -row
        total += ((signed >> bit) & 1) * row
    return total


def rounded_product(builder: Any, magnitude: Any, signed: Any, accumulator: Any, guard: int,
                    *, negate: bool = False, round_before_negation: bool = False,
                    adjoint: bool = False, scratch: Any = None) -> None:
    """Add a rounded product to the high accumulator bits, retaining the guards.

    The signed input is a fractional two's-complement word. The other input
    is unsigned. The guard bits start zero and carry the discarded fraction
    until the adjoint. Negation can round before changing the product sign.
    Optional clean scratch uses measured partial products with an ungated add.
    """
    if not len(magnitude) or not len(signed) or not 1 <= guard < len(accumulator):
        raise ValueError("rounded product requires operands, guard bits, and a high accumulator")
    if scratch is not None and len(scratch) < len(magnitude):
        raise ValueError("partial-product scratch must fit the magnitude")
    bias = (1 << (guard - 1)) - int(negate and round_before_negation)
    if not adjoint:
        builder.gf2_iadd(bias, target=accumulator[:guard])
    order = range(len(signed) - 1, -1, -1) if adjoint else range(len(signed))
    for bit in order:
        shift = bit + guard - len(signed)
        target = accumulator[max(0, shift):]
        start = max(0, -shift)
        row = magnitude[start:start + len(target)]
        if not len(row):
            continue
        apply = builder.isub if negate ^ adjoint ^ (bit == len(signed) - 1) else builder.iadd
        if scratch is None:
            apply(row, target=target, control=signed[bit])
        else:
            products = scratch[:len(row)]
            builder.init_and(signed[bit], row, products)
            apply(products, target=target)
            builder.del_and(signed[bit], row, products)
    if adjoint:
        builder.gf2_iadd(bias, target=accumulator[:guard])
