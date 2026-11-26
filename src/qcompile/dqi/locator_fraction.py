"""In-place locator and evaluator on the regular linear-quotient chart."""

from functools import cache
from typing import Any, NamedTuple

from .field import GF4096
from .inverse_action import _reciprocal, _scale, _scale_words
from .quotient import (
    FieldProduct, _interpolated_product_range, _interpolation_width, _product_range, _series_inplace, _truncate_inplace,
)
from .subtower import inverse_xor
from .tower import ProjectedFieldProduct, _xor_map, multiply_xor


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


class _ProductBand(NamedTuple):
    left: range
    right: range
    output: range
    first: int


def _product_bands(low: int, high: int, stride: int, first: int) -> tuple[dict[int, _ProductBand], int]:
    """Find profitable convolution bands whose sources lie below this block."""
    bands = {}
    savings = 0
    for residue in range(min(stride, high - low)):
        pairs = [(j - stride * i, i, j)
                 for j in range(low + residue, high, stride)
                 for i in range(max(first, (j - low) // stride + 1), min(low, (j - first) // stride + 1))]
        if not pairs:
            continue
        left, right, output = zip(*pairs, strict=True)
        a = range(min(left), max(left) + 1, stride)
        b = range(min(right), max(right) + 1)
        out = range(min(output), max(output) + 1, stride)
        length = _interpolation_width(len(a), len(b), len(out))
        if length < len(pairs):
            bands[output[0] % stride] = _ProductBand(a, b, out, (out.start - a.start) // stride - b.start)
            savings += len(pairs) - length
    return bands, savings


@cache
def _power_blocks(length: int, stride: int, first: int) -> tuple[tuple[int, int, dict[int, _ProductBand]], ...]:
    # Maximize the savings over scalar products by splitting into contiguous blocks.
    best = [0] * (length + 1)
    cuts = [0] * (length + 1)
    for high in range(1, length + 1):
        for low in range(high):
            _, savings = _product_bands(low, high, stride, first)
            if best[low] + savings > best[high]:
                best[high], cuts[high] = best[low] + savings, low
    blocks = []
    high = length
    while high:
        low = cuts[high]
        bands, _ = _product_bands(low, high, stride, first)
        blocks.append((low, high, bands))
        high = low
    return tuple(blocks)


def _invert_unit_tail(builder: Any, words: list[Any], multiply: FieldProduct, *, first: int = 1) -> None:
    """Invert a unit series whose nonconstant coefficients start at first."""
    strides = _inverse_powers((len(words) - 1) // first + 1)
    if not strides:
        return
    for stride in strides:
        columns = _frobenius(stride)
        for low, high, bands in _power_blocks(len(words), stride, first):
            squared = builder.alloc_qubits(12)
            # Descend through overlapping terms before the cross-block update.
            # Each interpolated band reads only words below the output block.
            for j in range(high - 1, max(low, first * stride) - 1, -1):
                for i in range(first, (j - first) // stride + 1):
                    source = j - stride * i
                    if source < low and i < low and j % stride in bands:
                        continue
                    _xor_map(builder, words[i], squared, columns)
                    multiply(builder, words[source], squared, words[j])
                    _xor_map(builder, words[i], squared, columns)
                if j % stride == 0:
                    i = j // stride
                    _xor_map(builder, words[i], words[j], columns)
            builder.free(squared)
            for left, right, output, coefficient in bands.values():
                _interpolated_product_range(builder, [words[i] for i in left], [words[i] for i in right],
                                            [words[i] for i in output], coefficient, multiply, right_columns=columns)


def _series_inverse(builder: Any, words: list[Any], multiply: FieldProduct) -> None:
    """Invert a finite formal series with a nonzero constant."""
    constant, tail = words[0], words[1:]
    if tail:
        _scale(builder, constant, [], tail, multiply, undo=False)
    _invert_unit_tail(builder, words, multiply)
    if tail:
        _scale(builder, constant, [], tail, multiply, undo=False)
    _invert_word(builder, constant)


def blocked_suffix_inplace(builder: Any, words: list[Any], previous: list[Any], current: list[Any],
                           *, adjoint: bool = False, multiply: FieldProduct = multiply_xor) -> None:
    """Map G to D*G/(1+t²*E*G) on the supplied regular prefix chart.

    The disjoint ascending coefficient banks supply E, whose constant is
    nonzero, and the positive-degree coefficients of D, whose constant
    is one. The entire prefolded suffix G is overwritten and the summary
    banks are preserved.
    """
    if not words or not previous or any(len(word) != 12 for word in (*words, *previous, *current)):
        raise ValueError("blocked suffix requires 12-bit field words and a nonempty previous denominator")
    if adjoint:
        _series_inplace(builder, words, current, multiply, adjoint=True)
    _truncate_inplace(builder, words, previous, multiply, adjoint=False, compact=True)
    # Invert 1+t²*Z, with Z=E*G. Its constant and linear coefficient
    # stay one and zero, so neither occupies a field register.
    _invert_unit_tail(builder, [None, None, *words], multiply, first=2)
    _truncate_inplace(builder, words, previous, multiply, adjoint=True, compact=True)
    if not adjoint:
        _series_inplace(builder, words, current, multiply, adjoint=False)


def _advance_numerator_block(builder: Any, numerator: list[Any], denominator_tail: list[Any],
                             multiply: ProjectedFieldProduct, reciprocal: Any, *, adjoint: bool) -> None:
    """Advance a rational sequence by one block of denominator degree."""
    # In the reversed polynomial basis the shift multiplies by x**degree
    # modulo the locator. The low half of that dividend is zero. Pack the
    # quotient first, then compute its product with the locator's low half.
    low = denominator_tail[::-1]
    if adjoint:
        _series_inplace(builder, numerator[::-1], low[1:], multiply, adjoint=True, scales=(reciprocal, low[0]))
    _series_inplace(builder, numerator, denominator_tail, multiply, adjoint=not adjoint)
    if not adjoint:
        _series_inplace(builder, numerator[::-1], low[1:], multiply, adjoint=False, scales=(low[0], reciprocal))


def prefold_raw_suffix(builder: Any, words: list[Any], numerator: list[Any], denominator_tail: list[Any],
                      *, adjoint: bool = False, multiply: ProjectedFieldProduct) -> None:
    """Overwrite raw suffix Y with D*Y + B_shifted, preserving the prefix pair.

    The numerator and the unit-constant denominator's tail have equal
    physical length k. The denominator lead must be nonzero. B/D matches
    the first 2*k terms of the original series, and words begins at 2*k.
    All coefficient lists are ascending and disjoint.
    """
    if not words or not numerator or len(numerator) != len(denominator_tail):
        raise ValueError("raw suffix prefold requires matched prefix polynomials and a nonempty suffix")
    if any(len(word) != 12 for word in (*words, *numerator, *denominator_tail)):
        raise ValueError("raw suffix prefold requires 12-bit field words")
    if not adjoint:
        _series_inplace(builder, words, denominator_tail, multiply, adjoint=False)
    correction_length = min(len(numerator), len(words))
    with _reciprocal(builder, denominator_tail[-1], compact_inner=True) as reciprocal:
        for _ in range(2):
            _advance_numerator_block(builder, numerator, denominator_tail, multiply, reciprocal, adjoint=False)
        for coefficient, target in zip(numerator[:correction_length], words[:correction_length], strict=True):
            builder.cx(coefficient, target)
        for _ in range(2):
            _advance_numerator_block(builder, numerator, denominator_tail, multiply, reciprocal, adjoint=True)
    if adjoint:
        _series_inplace(builder, words, denominator_tail, multiply, adjoint=True)


def _projective_fold(builder: Any, a: Any, b: Any, denominator: list[Any], numerator: list[Any],
                     multiply: ProjectedFieldProduct, *, adjoint: bool) -> None:
    """Replace (D,N,a,b) by ((a*z+b)*D+N,D)."""
    if not adjoint:
        _product_range(builder, [b, a], denominator[:-1], numerator, 0, multiply)
    head = denominator[-1]
    with _reciprocal(builder, head, compact_inner=True) as reciprocal:
        if adjoint:
            _scale_words(builder, [a], reciprocal, head, multiply)
            multiply(builder, a, denominator[-2], b)
            _scale_words(builder, [b], reciprocal, head, multiply)
        else:
            _scale_words(builder, [b], head, reciprocal, multiply)
            multiply(builder, a, denominator[-2], b)
            _scale_words(builder, [a], head, reciprocal, multiply)
    if adjoint:
        _product_range(builder, [b, a], denominator[:-1], numerator, 0, multiply)


def projective_continuant(builder: Any, words: list[Any], unit: Any, *,
                          adjoint: bool = False, multiply: ProjectedFieldProduct) -> tuple[list[Any], list[Any]]:
    """Fold a regular linear-quotient tape to an ascending (D,N) pair.

    Every slope is nonzero. The extra word starts clean in the forward
    direction and is returned clean by the adjoint. D retains its explicit
    leading coefficient, and neither polynomial is normalized.
    """
    if not words or len(words) % 2 or any(len(word) != 12 for word in (*words, unit)):
        raise ValueError("projective continuant requires pairs of 12-bit words and a 12-bit unit register")
    denominator, numerator = [words[-1], words[-2]], [unit]
    steps = []
    for index in range(len(words) - 4, -1, -2):
        a, b = words[index:index + 2]
        steps.append((a, b, denominator, numerator))
        denominator, numerator = [*numerator, b, a], denominator
    if not adjoint:
        builder.x(unit[0])
    for a, b, d, n in (reversed(steps) if adjoint else steps):
        _projective_fold(builder, a, b, d, n, multiply, adjoint=adjoint)
    if adjoint:
        builder.x(unit[0])
    return denominator, numerator


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
