"""Reversible multiplication in a monic polynomial quotient over GF(4096).

This primitive accepts a fixed public degree and quantum modulus coefficients.
"""

from collections.abc import Callable, Sequence
from functools import cache
from typing import Any

from .bilinear import erase_product
from .decoder import _divide, _multiply
from .field import GF4096
from .subtower import inverse_xor
from .tower import multiply_xor

_FIELD = GF4096()
FieldProduct = Callable[[Any, Sequence[Any], Sequence[Any], Sequence[Any]], None]


@cache
def _interpolation(length: int) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """Columns of the inverse Vandermonde matrix at distinct field points."""
    points = _FIELD.exp[:length]
    polynomial = [1]
    for point in points:
        polynomial = _multiply(polynomial, [point, 1], _FIELD)
    columns = []
    for point in points:
        basis, remainder = _divide(polynomial, [point, 1], _FIELD)
        if remainder != [0]:
            raise ValueError("Invalid interpolation point")
        scale = _FIELD.inv(_FIELD.evaluate(basis, point))
        columns.append((point, tuple(_FIELD.mul(scale, value) for value in basis)))
    return tuple(columns)


@cache
def _linear_pairs(scale: int) -> tuple[tuple[int, int], ...]:
    return tuple((i, j) for i, column in enumerate(_FIELD.fixed_map(scale))
                 for j in range(12) if column >> j & 1)


def _scaled_xor(builder: Any, source: Any, target: Any, scale: int) -> None:
    pairs = _linear_pairs(scale)
    if pairs:
        builder.cx([source[i] for i, _ in pairs], [target[j] for _, j in pairs])


def _product_range(builder: Any, left: Sequence[Any], right: Sequence[Any],
                   target: Sequence[Any], first: int, multiply: FieldProduct) -> None:
    """XOR only the requested coefficients of an ordinary polynomial product."""
    if not target:
        return
    stop = first + len(target)
    pairs = [(i, j) for i in range(len(left))
             for j in range(max(0, first - i), min(len(right), stop - i))
             if left[i] is not None and right[j] is not None]
    length = len(left) + len(right) - 1
    if len(pairs) <= length or length > _FIELD.order:
        for i, j in pairs:
            multiply(builder, left[i], right[j], target[i + j - first])
        return

    a, b, product = [builder.alloc_qubits(12) for _ in range(3)]
    for point, weights in _interpolation(length):
        def evaluate() -> None:
            for words, destination in ((left, a), (right, b)):
                scale = 1
                for word in words:
                    if word is not None:
                        _scaled_xor(builder, word, destination, scale)
                    scale = _FIELD.mul(scale, point)

        evaluate()
        multiply(builder, a, b, product)
        for word, scale in zip(target, weights[first:stop], strict=True):
            _scaled_xor(builder, product, word, scale)
        erase_product(builder, a, b, product)
        evaluate()
    for word in (a, b, product):
        builder.free(word)


@cache
def _reduction_split(size: int) -> tuple[int, int]:
    """Minimum field-product count among contiguous split schedules."""
    result = (size * (size - 1) // 2, 0)
    for lower in range(1, size):
        upper = size - lower
        cross = min(lower * upper, size + upper - 2)
        result = min(result, (_reduction_split(lower)[0] + _reduction_split(upper)[0] + cross, lower))
    return result


def _high_reduce(builder: Any, high: Sequence[Any], modulus: Sequence[Any], multiply: FieldProduct,
                 *, adjoint: bool) -> None:
    """Turn the high product words into the quotient in-place, or undo it."""
    size, degree = len(high), len(modulus)
    mid = _reduction_split(size)[1] if size <= min(34, degree + 1) else 0
    if not mid:
        order = range(size) if adjoint else range(size - 1, -1, -1)
        for i in order:
            for j in range(max(0, i - degree), i):
                multiply(builder, high[i], modulus[degree + j - i], high[j])
        return

    low, upper = high[:mid], high[mid:]
    first, last = (low, upper) if adjoint else (upper, low)
    _high_reduce(builder, first, modulus, multiply, adjoint=adjoint)
    # Coefficient j in the lower block receives upper[u] * modulus[d+j-mid-u].
    _product_range(builder, upper, modulus[degree - size + 1:], low, len(upper) - 1, multiply)
    _high_reduce(builder, last, modulus, multiply, adjoint=adjoint)


def _check_words(left: list[Any], right: list[Any], modulus: list[Any], target: list[Any]) -> int:
    degree = len(modulus)
    if degree < 1 or any(len(group) != degree for group in (left, right, target)):
        raise ValueError("quotient operands must have the same positive degree")
    if any(len(word) != 12 for word in (*left, *right, *modulus, *target)):
        raise ValueError("quotient multiplication requires 12-bit words")
    return degree


def quotient_multiply_xor(builder: Any, left: list[Any], right: list[Any],
                          modulus: list[Any], target: list[Any], *,
                          multiply: FieldProduct = multiply_xor) -> None:
    """XOR (left*right mod (z**d + modulus)) into a disjoint target.

    Coefficients are ascending, every list has d disjoint 12-bit registers, and
    the modulus has an implicit leading coefficient one. All inputs are
    preserved, including for reducible moduli; scratch is clean on return.
    """
    degree = _check_words(left, right, modulus, target)
    high = [builder.alloc_qubits(12) for _ in range(degree - 1)]
    _product_range(builder, left, right, [*target, *high], 0, multiply)
    if high:
        _high_reduce(builder, high, modulus, multiply, adjoint=False)
        _product_range(builder, high, modulus, target, 0, multiply)
        _high_reduce(builder, high, modulus, multiply, adjoint=True)
        # The two constant input terms cannot contribute to degree >= d.
        _product_range(builder, left[1:], right[1:], high, degree - 2, multiply)
    for word in high:
        builder.free(word)


def _series_inplace(builder: Any, words: list[Any], tail: Sequence[Any], multiply: FieldProduct,
                    *, adjoint: bool, scales: tuple[Any, Any] | None = None) -> None:
    """Multiply by a truncated series or invert it. No scales means unit constant."""
    def apply(bank: list[Any]) -> None:
        size = len(bank)
        split = _reduction_split(size)[1] if size <= 35 else size // 2
        if not split:
            work = builder.alloc_qubits(12) if scales is not None else None
            order = range(size) if adjoint else range(size - 1, -1, -1)
            for i in order:
                word = bank[i]
                sources = range(max(0, i - len(tail)), i)
                if adjoint:
                    for j in sources:
                        factor = tail[i - j - 1]
                        if factor is not None:
                            multiply(builder, bank[j], factor, word)
                if scales is not None and work is not None:
                    multiply(builder, scales[0], word, work)
                    erase_product(builder, scales[1], work, word)
                    builder.swap(word, work)
                if not adjoint:
                    for j in sources:
                        factor = tail[i - j - 1]
                        if factor is not None:
                            multiply(builder, bank[j], factor, word)
            if work is not None:
                builder.free(work)
            return
        mid = size - split
        low, upper = bank[:mid], bank[mid:]
        first, last = (low, upper) if adjoint else (upper, low)
        apply(first)
        # Only the lower coefficients of the replicated cross product fit the bank.
        _product_range(builder, low, tail[:size - 1], upper[:len(tail)], mid - 1, multiply)
        apply(last)

    apply(words)


def _truncate_inplace(builder: Any, words: list[Any], modulus: list[Any], multiply: FieldProduct,
                      *, adjoint: bool) -> None:
    inverse = builder.alloc_qubits(12)
    inverse_xor(builder, modulus[0], inverse)
    scales = (inverse, modulus[0]) if adjoint else (modulus[0], inverse)
    _series_inplace(builder, words, modulus[1:], multiply, adjoint=adjoint, scales=scales)
    inverse_xor(builder, modulus[0], inverse)
    builder.free(inverse)


def quotient_prepare(builder: Any, left: list[Any], right: list[Any], modulus: list[Any],
                     target: list[Any], *, adjoint: bool = False,
                     multiply: FieldProduct = multiply_xor) -> None:
    """Prepare a monic quotient-ring product in a zero output, or unprepare it.

    The constant modulus coefficient must be nonzero. In the adjoint the
    output must hold the exact product of the preserved operands. Uses the
    output bank for the high-part quotient before accumulating the remainder.
    """
    degree = _check_words(left, right, modulus, target)
    if degree == 1:
        multiply(builder, left[0], right[0], target[0])
        return
    high = target[:-1]
    if adjoint:
        _product_range(builder, left, right, target, 0, multiply)
        _truncate_inplace(builder, target, modulus, multiply, adjoint=True)
        _high_reduce(builder, high, modulus, multiply, adjoint=True)
    _product_range(builder, left[1:], right[1:], high, degree - 2, multiply)
    if not adjoint:
        _high_reduce(builder, high, modulus, multiply, adjoint=False)
        _truncate_inplace(builder, target, modulus, multiply, adjoint=False)
        _product_range(builder, left, right, target, 0, multiply)
