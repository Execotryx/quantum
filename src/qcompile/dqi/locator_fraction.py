"""In-place locator and evaluator on the regular linear-quotient chart."""

from functools import cache
from typing import Any

from .field import GF4096
from .inverse_action import _scale
from .quotient import FieldProduct
from .subtower import inverse_xor
from .tower import _xor_map, multiply_xor


@cache
def _inverse_powers(length: int) -> tuple[int, ...]:
    """Factor the unit-series inverse exponent into maps f -> f*f**stride."""
    exponent = 1
    strides = []
    for bit in range(1, (length - 1).bit_length()):
        stride = 1 << bit
        if (exponent + 1) & ((stride << 1) - 1):
            exponent *= 1 + stride
            strides.append(stride)
    return tuple(strides)


@cache
def _frobenius(stride: int) -> tuple[int, ...]:
    field = GF4096()
    columns = tuple(1 << bit for bit in range(12))
    while stride > 1:
        columns = tuple(field.mul(value, value) for value in columns)
        stride //= 2
    return columns


def _invert_word(builder: Any, word: Any) -> None:
    inverse = builder.alloc_qubits(12)
    inverse_xor(builder, word, inverse, borrow_source=True)
    inverse_xor(builder, inverse, word, borrow_source=True)
    builder.swap(word, inverse)
    builder.free(inverse)


def _invert_unit_tail(builder: Any, words: list[Any], multiply: FieldProduct) -> None:
    strides = _inverse_powers(len(words))
    if not strides:
        return
    squared = builder.alloc_qubits(12)
    for stride in strides:
        columns = _frobenius(stride)
        # Every source index is below the destination. Descending updates
        # preserve the coefficients of the input to this power map.
        for j in range(len(words) - 1, stride - 1, -1):
            for i in range(1, j // stride + 1):
                source = j - stride * i
                if source == 0:
                    _xor_map(builder, words[i], words[j], columns)
                else:
                    _xor_map(builder, words[i], squared, columns)
                    multiply(builder, words[source], squared, words[j])
                    _xor_map(builder, words[i], squared, columns)
    builder.free(squared)


def _series_inverse(builder: Any, words: list[Any], multiply: FieldProduct) -> None:
    """Invert a finite formal series with a nonzero constant."""
    constant, tail = words[0], words[1:]
    if tail:
        _scale(builder, constant, [], tail, multiply, undo=False)
    _invert_unit_tail(builder, words, multiply)
    if tail:
        _scale(builder, constant, [], tail, multiply, undo=False)
    _invert_word(builder, constant)


def _continuant_layout(words: list[Any]) -> list[tuple[Any, Any, list[Any], list[Any]]]:
    steps = []
    denominator: list[Any] = []
    numerator: list[Any] = []
    for index in range(len(words) - 2, -1, -2):
        a, b = words[index:index + 2]
        steps.append((a, b, denominator, numerator))
        denominator, numerator = [*numerator, b], [*denominator, a]
    return steps


def _fold(builder: Any, a: Any, b: Any, denominator: list[Any], numerator: list[Any],
          multiply: FieldProduct, *, adjoint: bool) -> None:
    """Replace (D,N,a,b) by ((a*z+b)*D/a+N/a,D/a)."""
    if adjoint:
        _invert_word(builder, a)
        if denominator:
            _scale(builder, a, [], denominator, multiply, undo=True)
    else:
        _scale(builder, a, [b], numerator, multiply, undo=False)
    if denominator:
        if adjoint:
            builder.cx(denominator[-1], b)
        for i, (coefficient, output) in enumerate(zip(denominator, numerator, strict=True)):
            multiply(builder, b, coefficient, output)
            if i:
                builder.cx(denominator[i - 1], output)
        if not adjoint:
            builder.cx(denominator[-1], b)
            _scale(builder, a, [], denominator, multiply, undo=False)
    if adjoint:
        _scale(builder, a, [b], numerator, multiply, undo=True)
    else:
        _invert_word(builder, a)


def regular_locator_evaluator(builder: Any, syndromes: list[Any], *, adjoint: bool = False,
                              multiply: FieldProduct = multiply_xor) -> tuple[list[Any], list[Any]]:
    """Use the syndrome bank for a monic locator and evaluator, or restore it.

    The error weight must be half the input length. The proper rational
    function at infinity must have a nonzero linear quotient at each
    Euclidean step, and its denominator must have nonzero constant.
    The return lists name the physical output words in ascending order.
    The locator's final coefficient one is implicit.
    """
    if not syndromes or len(syndromes) % 2 or any(len(word) != 12 for word in syndromes):
        raise ValueError("locator chart requires an even, nonempty bank of field words")
    steps = _continuant_layout(syndromes)
    a, b, old_d, old_n = steps[-1]
    denominator, numerator = [*old_n, b], [*old_d, a]
    constant, coefficients = denominator[0], denominator[1:]
    if adjoint:
        _invert_word(builder, constant)
        _scale(builder, constant, coefficients, numerator, multiply, undo=True)
    else:
        for offset in range(0, len(syndromes), 2):
            _series_inverse(builder, syndromes[offset:], multiply)
    for a, b, d, n in (reversed(steps) if adjoint else steps):
        _fold(builder, a, b, d, n, multiply, adjoint=adjoint)
    if adjoint:
        for offset in reversed(range(0, len(syndromes), 2)):
            _series_inverse(builder, syndromes[offset:], multiply)
    else:
        _scale(builder, constant, coefficients, numerator, multiply, undo=False)
        _invert_word(builder, constant)
    return [constant, *reversed(coefficients)], list(reversed(numerator))
