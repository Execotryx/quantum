"""Controlled fixed-width padding of reversed locator and evaluator banks."""

from functools import cache
from typing import Any

from .field import GF4096
from .quotient import _scaled_xor


@cache
def padding_factors() -> tuple[tuple[int, int], ...]:
    """Choose 17 distinct dilations of one monic irreducible quadratic."""
    field = GF4096()
    image = {field.mul(value, value) ^ value for value in range(4096)}
    constant = next(value for value in range(4096) if value not in image)
    slopes = field.exp[:17 * 137:137]
    return tuple((slope, field.mul(constant, field.mul(slope, slope))) for slope in slopes)


def _toggle_below(builder: Any, word: Any, stop: int, target: Any) -> None:
    """XOR the comparison using the disjoint binary prefixes below stop."""
    for bit in range(len(word)):
        if stop & (1 << bit):
            builder.flip_if_equal(word[bit:], (stop >> bit) - 1, target=target)


def _multiply_reversed(builder: Any, bank: list[Any], linear: int, constant: int, control: Any,
                       work: Any, *, leading_one: bool, adjoint: bool) -> None:
    def add_lead() -> None:
        for word, coefficient in ((bank[0], linear), (bank[1], constant)):
            for bit, target in enumerate(word):
                if coefficient >> bit & 1:
                    builder.cx(control, target)

    if leading_one and adjoint:
        add_lead()
    # An enabled step starts at degree at most 33. Both high reversed
    # tail slots are zero on that branch and have no outgoing products.
    order = range(len(bank) - 2) if adjoint else range(len(bank) - 3, -1, -1)
    for index in order:
        source = bank[index]
        for bit, helper in zip(source, work, strict=True):
            builder.init_and(control, bit, helper)
        _scaled_xor(builder, work, bank[index + 1], linear)
        _scaled_xor(builder, work, bank[index + 2], constant)
        for bit, helper in zip(source, work, strict=True):
            builder.del_and(control, bit, helper)
    if leading_one and not adjoint:
        add_lead()


def pad_reversed_banks(builder: Any, locator: list[Any], evaluator: list[Any], degree: Any,
                       *, adjoint: bool = False) -> None:
    """Lift a degree-0..35 pair to degree 35 and undo it on the same wires.

    Locator words start below the implicit monic head, and evaluator words
    start at degree w-1, both in descending order with zero tails in the
    original pair. The six-bit degree is unchanged. At fixed output size
    a factor x is implicit for even w. All other factors are root-free in
    the field. The routine preserves the physical layout.
    """
    if len(locator) != 35 or len(evaluator) != 35 or len(degree) != 6:
        raise ValueError("fixed-width padding requires two 35-word banks and six degree bits")
    if any(len(word) != 12 for bank in (locator, evaluator) for word in bank):
        raise ValueError("padding requires 12-bit field words")
    # Multiplying by a quadratic does not change parity. Only the five
    # high degree bits choose how many quadratics to apply.
    half_degree = degree[1:]
    indexed = tuple(enumerate(padding_factors()))
    flag = builder.alloc_qubits(1)[0]
    work = builder.alloc_qubits(12)
    for index, (linear, constant) in reversed(indexed) if adjoint else indexed:
        _toggle_below(builder, half_degree, 17 - index, flag)
        _multiply_reversed(builder, locator, linear, constant, flag, work, leading_one=True, adjoint=adjoint)
        _multiply_reversed(builder, evaluator, linear, constant, flag, work, leading_one=False, adjoint=adjoint)
        _toggle_below(builder, half_degree, 17 - index, flag)
    builder.free(work)
    builder.free(flag)
