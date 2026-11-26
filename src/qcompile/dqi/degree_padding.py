"""Controlled fixed-width padding of reversed locator and evaluator banks."""

from functools import cache
from typing import Any

from .decoder import _multiply
from .field import GF4096
from .quotient import _scaled_xor
from .subtower import _change_basis


_FIELD = GF4096()
_DILATION = 137


@cache
def padding_factors() -> tuple[tuple[int, int], ...]:
    """Choose 17 distinct dilations of one monic irreducible quadratic."""
    image = {_FIELD.mul(value, value) ^ value for value in range(4096)}
    constant = next(value for value in range(4096) if value not in image)
    slopes = _FIELD.exp[:17 * _DILATION:_DILATION]
    return tuple((slope, _FIELD.mul(constant, _FIELD.mul(slope, slope))) for slope in slopes)


@cache
def _blocks() -> tuple[tuple[int, ...], ...]:
    blocks = []
    prefix = [1]
    for count, (linear, constant) in enumerate(padding_factors()[:16], 1):
        prefix = _multiply(prefix, [1, linear, constant], _FIELD)
        if count & (count - 1) == 0:
            blocks.append(tuple(prefix))
    return tuple(blocks)


@cache
def _coordinates(scale: int) -> tuple[int, ...]:
    return tuple(_FIELD.fixed_map(scale))


def _controlled_block(builder: Any, bank: list[Any], prefix: tuple[int, ...], shift: int,
                      source_count: int, control: Any, work: Any, *,
                      leading_one: bool, adjoint: bool) -> None:
    """Apply F(z) g(alpha**shift z), with a possibly implicit leading unit."""
    def add_lead() -> None:
        for word, coefficient in zip(bank, prefix[1:]):
            for bit, target in enumerate(word):
                if coefficient >> bit & 1:
                    builder.cx(control, target)

    if leading_one and adjoint:
        add_lead()
    order = range(source_count) if adjoint else range(source_count - 1, -1, -1)
    for index in order:
        exponent = shift * (index + int(leading_one))
        scale = _FIELD.exp[exponent % 4095]
        diagonal = _FIELD.exp[-exponent % 4095] if adjoint else scale
        if diagonal == 1 and len(prefix) == 1:
            continue
        source = bank[index]
        for bit, helper in zip(source, work, strict=True):
            builder.init_and(control, bit, helper)
        for target, coefficient in zip(bank[index + 1:], prefix[1:]):
            _scaled_xor(builder, work, target, coefficient if adjoint else _FIELD.mul(scale, coefficient))
        if diagonal != 1:
            _scaled_xor(builder, work, source, diagonal ^ 1)
            # Erase the product in its original basis. The temporary
            # basis change also cancels when the control is zero.
            _change_basis(builder, source, _coordinates(diagonal), undo=True)
        for bit, helper in zip(source, work, strict=True):
            builder.del_and(control, bit, helper)
        if diagonal != 1:
            _change_basis(builder, source, _coordinates(diagonal), undo=False)
    if leading_one and not adjoint:
        add_lead()


def _toggle_count(builder: Any, degree: Any, count: Any) -> None:
    half = degree[1:]
    # Subtract from binary 10001. The borrows into bits 2, 3, 4
    # are the ORs of the intervening bits starting at bit 1.
    builder.cx(half, count)
    builder.x(count[0])
    builder.cx(half[1], count[2])
    builder.x(count[3])
    builder.flip_if_equal(half[1:3], 0, target=count[3])
    builder.flip_if_equal(half[1:4], 0, target=count[4])


def _pad_reversed(builder: Any, banks: tuple[tuple[list[Any], bool], ...], degree: Any, *, adjoint: bool) -> None:
    if len(degree) != 6 or any(len(bank) != 35 for bank, _ in banks):
        raise ValueError("fixed-width padding requires 35-word banks and six degree bits")
    if any(len(word) != 12 for bank, _ in banks for word in bank):
        raise ValueError("padding requires 12-bit field words")
    # For F_k the product of the first k factors, let T_k(g) =
    # F_k(z) g(alpha**(137*k) z). Then T_i T_j = T_(i+j).
    # Pre-scaling by the inverse dilation leaves exactly F_k(z) g(z).
    count = builder.alloc_qubits(5)
    _toggle_count(builder, degree, count)
    work = builder.alloc_qubits(12)
    powers = [(flag, 1 << bit, prefix) for bit, (flag, prefix) in enumerate(zip(count, _blocks(), strict=True))]
    stages: list[tuple[Any, int, tuple[int, ...], int]] = [
        (flag, size, (1,), -size * _DILATION) for flag, size, _ in powers[1:]
    ]
    # Cancel the first block's pre-scaling against its dilation.
    flag, size, prefix = powers[0]
    stages.append((flag, size, prefix, 0))
    stages += [(flag, size, prefix, size * _DILATION) for flag, size, prefix in powers[1:]]
    for flag, size, prefix, shift in reversed(stages) if adjoint else stages:
        # With this bit enabled, at least size factors remain before the
        # block. The preceding reversed prefix has at most 35-2*size words.
        capacity = 35 - 2 * size
        for bank, leading_one in banks:
            _controlled_block(builder, bank, prefix, shift, capacity, flag, work,
                              leading_one=leading_one, adjoint=adjoint)
    builder.free(work)
    _toggle_count(builder, degree, count)
    builder.free(count)


def pad_reversed_locator(builder: Any, locator: list[Any], degree: Any, *, adjoint: bool = False) -> None:
    """Pad the compact monic locator alone for a chart test."""
    _pad_reversed(builder, ((locator, True),), degree, adjoint=adjoint)


def pad_reversed_banks(builder: Any, locator: list[Any], evaluator: list[Any], degree: Any,
                       *, adjoint: bool = False) -> None:
    """Lift a degree-0..35 pair to degree 35 and undo it on the same wires.

    Locator words start below the implicit monic head, and evaluator words
    start at degree w-1, both in descending order with zero tails in the
    original pair. The six-bit degree is unchanged. At fixed output size
    a factor x is implicit for even w. All other factors are root-free in
    the field. The routine preserves the physical layout.
    """
    _pad_reversed(builder, ((locator, True), (evaluator, False)), degree, adjoint=adjoint)
