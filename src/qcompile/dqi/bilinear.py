"""Measurement erasure of a GF(4096) product with exact phase repair."""

from functools import cache
from typing import Any

from .field import GF4096


@cache
def product_tensor() -> tuple[tuple[int, ...], ...]:
    """Output word for each pair of polynomial-basis input bits."""
    field = GF4096()
    return tuple(tuple(field.mul(1 << i, 1 << j) for j in range(12)) for i in range(12))


def erase_product(builder: Any, left: Any, right: Any, product: Any) -> None:
    """Erase a fresh product register and cancel the measurement phase.

    Preconditions: the three 12-qubit registers are disjoint and `product`
    contains exactly left*right. The measurement outcomes are private scratch.
    """
    if any(len(register) != 12 for register in (left, right, product)):
        raise ValueError("product erasure requires three 12-bit registers")
    erase_product_tensor(builder, left, right, product, product_tensor())


def erase_product_tensor(builder: Any, left: Any, right: Any, product: Any,
                         tensor: tuple[tuple[int, ...], ...]) -> None:
    """Erase a fresh bilinear product using its basis-pair output tensor."""
    if len(tensor) != len(left) or any(len(row) != len(right) for row in tensor):
        raise ValueError("product tensor dimensions do not match input registers")
    outcomes = builder.alloc_bits(len(product))
    builder.hmr(product, outcomes)
    for bit, outcome in enumerate(outcomes):
        builder.push_condition(outcome)
        for i, row in enumerate(tensor):
            for j, word in enumerate(row):
                if word >> bit & 1:
                    builder.cz(left[i], right[j])
        builder.pop_condition()
    builder.bit_store(outcomes, False)
    builder.free(outcomes)
