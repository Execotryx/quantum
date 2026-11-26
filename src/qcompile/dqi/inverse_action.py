"""Fixed-degree Euclidean inverse action on a polynomial register."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .bilinear import erase_product
from .quotient import FieldProduct, _high_reduce, _product_range, _series_inplace
from .subtower import inverse_xor
from .tower import multiply_xor


def _packed_divide(builder: Any, words: list[Any], divisor: list[Any], multiply: FieldProduct,
                   *, adjoint: bool) -> None:
    """Pack X = D*C + E as E followed by C for a monic D."""
    degree = len(divisor)
    low, high = words[:degree], words[degree:]
    if not adjoint:
        _high_reduce(builder, high, divisor, multiply, adjoint=False)
    _product_range(builder, high, divisor, low, 0, multiply)
    if adjoint:
        _high_reduce(builder, high, divisor, multiply, adjoint=True)


def _reverse(builder: Any, words: list[Any]) -> None:
    for i in range(len(words) // 2):
        builder.swap(words[i], words[-1 - i])


def _rotate(builder: Any, words: list[Any], count: int) -> None:
    _reverse(builder, words[:count])
    _reverse(builder, words[count:])
    _reverse(builder, words)


def _extend_series(builder: Any, modulus: list[Any], divisor: list[Any], words: list[Any],
                   multiply: FieldProduct, *, adjoint: bool) -> None:
    """Extend the child's reversed quotient series and add the packed C tail."""
    k = len(divisor)
    if adjoint:
        _rotate(builder, words, len(words) - k)
    prefix = words[:k][::-1]
    tail = list(reversed(words[k:]))
    a, d = modulus[::-1], divisor[::-1]
    # The child holds the first k terms of Q_rev / D_rev. The new series
    # is Q_rev / D_rev + z**k C_rev / A_rev. Multiply the dirty tail by
    # D_rev so tail division does not propagate its old contents.
    _series_inplace(builder, tail, d, multiply, adjoint=False)
    if not adjoint:
        _series_inplace(builder, tail, a, multiply, adjoint=True)
    _product_range(builder, prefix, d, tail[:len(d)], k - 1, multiply)
    if adjoint:
        _series_inplace(builder, tail, a, multiply, adjoint=False)
    _series_inplace(builder, tail, d, multiply, adjoint=True)
    if not adjoint:
        _rotate(builder, words, k)


def _polynomial_basis(builder: Any, modulus: list[Any], banks: list[list[Any]],
                      multiply: FieldProduct, *, to_polynomial: bool) -> None:
    for words in banks:
        _series_inplace(builder, words[::-1], modulus[::-1], multiply, adjoint=not to_polynomial)


@contextmanager
def _reciprocal(builder: Any, factor: Any, *,
                extend_zero: bool = False, compact_inner: bool = False) -> Iterator[Any]:
    if factor is None:
        yield None
        return
    flag = builder.alloc_qubits(1)[0] if extend_zero else None
    if flag is not None:
        builder.flip_if_equal(factor, 0, target=flag)
        builder.cx(flag, factor[0])
    reciprocal = builder.alloc_qubits(12)
    inverse_xor(builder, factor, reciprocal, borrow_source=True, compact_inner=compact_inner)
    try:
        yield reciprocal
    finally:
        inverse_xor(builder, factor, reciprocal, borrow_source=True, compact_inner=compact_inner)
        builder.free(reciprocal)
        if flag is not None:
            builder.cx(flag, factor[0])
            builder.flip_if_equal(factor, 0, target=flag)
            builder.free(flag)


def _scale_words(builder: Any, words: list[Any], scale: Any, clear: Any, multiply: FieldProduct) -> None:
    if scale is None or not words:
        return
    work = builder.alloc_qubits(12)
    for word in words:
        multiply(builder, scale, word, work)
        erase_product(builder, clear, work, word)
        builder.swap(word, work)
    builder.free(work)


def _scale(builder: Any, factor: Any, normal: list[Any], data: list[Any], multiply: FieldProduct,
           *, undo: bool, extend_zero: bool = False) -> None:
    with _reciprocal(builder, factor, extend_zero=extend_zero) as inverse:
        scale, clear = (factor, inverse) if undo else (inverse, factor)
        _scale_words(builder, normal + data, scale, clear, multiply)


def _projective_remainder(builder: Any, modulus: list[Any], divisor: list[Any],
                          reduce_banks: list[list[Any]], multiply: FieldProduct, *,
                          adjoint: bool, extend_zero: bool) -> None:
    """Keep a linear quotient in the top two slots and the remainder below."""
    a_head, d_head = modulus[-1], divisor[-1]
    lead, constant = modulus[-2], divisor[-2]

    def update_lower() -> None:
        _product_range(builder, [lead, a_head], divisor[:-1], modulus[:-2], 0, multiply)

    # When A is monic, the quotient slope is the inverse itself. Use scalar
    # products on this outer level to leave the interpolation workspace free.
    if a_head is None:
        with _reciprocal(builder, d_head, extend_zero=extend_zero) as slope:
            def update_monically() -> None:
                for i, word in enumerate(modulus[:-2]):
                    multiply(builder, lead, divisor[i], word)
                    if i:
                        multiply(builder, slope, divisor[i - 1], word)

            if adjoint:
                update_monically()
                _scale_words(builder, [lead], d_head, slope, multiply)
            else:
                _projective_reduce(builder, divisor, reduce_banks, slope, multiply)
            multiply(builder, slope, constant, lead)
            if not adjoint:
                _scale_words(builder, [lead], slope, d_head, multiply)
                update_monically()
            else:
                _projective_reduce(builder, divisor, reduce_banks, slope, multiply)
        return

    if adjoint:
        update_lower()
    with _reciprocal(builder, d_head, extend_zero=extend_zero) as inverse:
        if adjoint:
            _scale_words(builder, [lead], d_head, inverse, multiply)
        else:
            _projective_reduce(builder, divisor, reduce_banks, inverse, multiply)
            _scale_words(builder, [a_head], inverse, d_head, multiply)
        multiply(builder, a_head, constant, lead)
        if adjoint:
            _scale_words(builder, [a_head], d_head, inverse, multiply)
            _projective_reduce(builder, divisor, reduce_banks, inverse, multiply)
        else:
            _scale_words(builder, [lead], inverse, d_head, multiply)
    if not adjoint:
        update_lower()


def _projective_reduce(builder: Any, divisor: list[Any], banks: list[list[Any]],
                       inverse: Any, multiply: FieldProduct) -> None:
    """Add the divisor reduction into each bank without replacing its top word."""
    for words in banks:
        top = words[-1]
        quotient = builder.alloc_qubits(12)
        multiply(builder, inverse, top, quotient)
        for factor, target in zip(divisor[:-1], words[:-1], strict=True):
            multiply(builder, quotient, factor, target)
        erase_product(builder, inverse, top, quotient)
        builder.free(quotient)


def _projective_extend(builder: Any, modulus: list[Any], divisor: list[Any], banks: list[list[Any]],
                       multiply: FieldProduct, *, adjoint: bool, extend_zero: bool) -> None:
    def scale_tails(head: Any) -> None:
        with _reciprocal(builder, head, extend_zero=extend_zero) as inverse:
            scale, clear = (head, inverse) if adjoint else (inverse, head)
            _scale_words(builder, [words[-1] for words in banks], scale, clear, multiply)

    if adjoint:
        for words in banks:
            _rotate(builder, words, 1)
    scale_tails(divisor[-1] if adjoint else modulus[-1])
    for words in banks:
        for coefficient, value in zip(divisor[:-1], words[-2::-1], strict=True):
            multiply(builder, coefficient, value, words[-1])
    scale_tails(modulus[-1] if adjoint else divisor[-1])
    if not adjoint:
        for words in banks:
            _rotate(builder, words, len(words) - 1)


def _toggle_regular(builder: Any, heads: tuple[Any, ...], validity: Any) -> None:
    zeros = builder.alloc_qubits(len(heads))
    for head, flag in zip(heads, zeros, strict=True):
        builder.flip_if_equal(head, 0, target=flag)
    builder.flip_if_equal(zeros, 0, target=validity)
    for head, flag in zip(heads, zeros, strict=True):
        builder.flip_if_equal(head, 0, target=flag)
    builder.free(zeros)


def _projective_action(builder: Any, modulus: list[Any], divisor: list[Any], banks: list[list[Any]],
                       multiply: FieldProduct, *, adjoint: bool, validity: Any = None,
                       heads: tuple[Any, ...] = ()) -> None:
    """Regular chart with a stored nonzero divisor lead and optional monic modulus lead."""
    guarded = validity is not None
    if guarded:
        # The modulus head becomes a quotient slope by a nonzero scale.
        # Every prior divisor head therefore retains its zero predicate.
        heads = (*heads, divisor[-1])
    if len(divisor) == 1:
        if guarded:
            _toggle_regular(builder, heads, validity)
        scalars = [words[0] for words in banks]
        if scalars:
            _scale(builder, modulus[-1], [], scalars, multiply, undo=adjoint, extend_zero=guarded)
            _scale(builder, divisor[-1], [], scalars, multiply, undo=adjoint, extend_zero=guarded)
        return
    if banks and adjoint:
        _projective_extend(builder, modulus, divisor, banks, multiply, adjoint=True, extend_zero=guarded)
    _projective_remainder(builder, modulus, divisor, [] if adjoint else banks, multiply,
                          adjoint=False, extend_zero=guarded)
    _projective_action(builder, divisor, modulus[:-2], [words[:-1] for words in banks], multiply,
                       adjoint=adjoint, validity=validity, heads=heads)
    _projective_remainder(builder, modulus, divisor, banks if adjoint else [], multiply,
                          adjoint=True, extend_zero=guarded)
    if banks and not adjoint:
        _projective_extend(builder, modulus, divisor, banks, multiply, adjoint=False, extend_zero=guarded)


def _toggle_half_remainder(builder: Any, even: list[Any], odd: list[Any], multiply: FieldProduct) -> None:
    for coefficient, target in zip(odd, even[:-1], strict=True):
        multiply(builder, even[-1], coefficient, target)


def projective_chart_xor(builder: Any, locator: list[Any], validity: Any, *,
                         multiply: FieldProduct = multiply_xor) -> None:
    """Toggle validity using only locator coefficients, restoring them on return."""
    if len(locator) < 3 or not len(locator) % 2 or any(len(word) != 12 for word in locator):
        raise ValueError("projective chart test requires a monic odd-degree locator")
    even, odd = locator[::2], locator[1::2]
    _toggle_half_remainder(builder, even, odd, multiply)
    _projective_action(builder, [*odd, None], even[:-1], [], multiply, adjoint=False, validity=validity)
    _toggle_half_remainder(builder, even, odd, multiply)


def inverse_action(builder: Any, modulus: list[Any], divisor: list[Any], words: list[Any],
                   remainder_degrees: tuple[int, ...], *, adjoint: bool = False,
                   multiply: FieldProduct = multiply_xor) -> None:
    """Replace X by X/D mod A, or apply its inverse, for a supplied Euclidean degree chart.

    A and D are monic and only their lower coefficients are stored. X has
    degree less than A. The chart lists each nonzero remainder degree
    down to the constant gcd. The caller must establish the chart; no
    input-dependent routing is performed here. A and D are restored.
    """
    _inverse_actions(builder, modulus, divisor, [words], remainder_degrees, multiply,
                     adjoint=adjoint, raw_output=True)


def _inverse_actions(builder: Any, modulus: list[Any], divisor: list[Any], banks: list[list[Any]],
                     remainder_degrees: tuple[int, ...], multiply: FieldProduct, *,
                     adjoint: bool, raw_output: bool = False) -> None:
    n, k = len(modulus), len(divisor)
    chart = (n, k, *remainder_degrees)
    if not 0 < k < n or any(len(words) != n for words in banks) or chart[-1] != 0:
        raise ValueError("invalid inverse-action shape or endpoint")
    if any(not 0 <= b < a for a, b in zip(chart, chart[1:])):
        raise ValueError("Euclidean degrees must decrease to zero")
    if any(len(word) != 12 for bank in (modulus, divisor, *banks) for word in bank):
        raise ValueError("inverse action requires 12-bit words")

    def apply(a: list[Any], d: list[Any], xs: list[list[Any]], depth: int) -> None:
        degree = len(d)
        for x in xs:
            if adjoint:
                _extend_series(builder, a, d, x, multiply, adjoint=True)
            else:
                _packed_divide(builder, x, d, multiply, adjoint=False)

        # Account for the implicit leading one of A before dividing its bank.
        for source, target in zip(d, a[len(a) - degree:], strict=True):
            builder.cx(source, target)
        _packed_divide(builder, a, d, multiply, adjoint=False)
        r = remainder_degrees[depth]
        remainder, factor = a[:r], a[r]
        payloads = [x[:degree] for x in xs]
        payload = [word for bank in payloads for word in bank]
        _scale(builder, factor, remainder, [] if adjoint else payload, multiply, undo=False)
        if r:
            apply(d, remainder, payloads, depth + 1)
        else:
            _polynomial_basis(builder, d, payloads, multiply, to_polynomial=adjoint)
        _scale(builder, factor, remainder, payload if adjoint else [], multiply, undo=True)
        _packed_divide(builder, a, d, multiply, adjoint=True)
        for source, target in zip(d, a[len(a) - degree:], strict=True):
            builder.cx(source, target)

        for x in xs:
            if adjoint:
                _packed_divide(builder, x, d, multiply, adjoint=True)
            else:
                _extend_series(builder, a, d, x, multiply, adjoint=False)

    if raw_output and adjoint:
        _polynomial_basis(builder, modulus, banks, multiply, to_polynomial=False)
    apply(modulus, divisor, banks, 0)
    if raw_output and not adjoint:
        _polynomial_basis(builder, modulus, banks, multiply, to_polynomial=True)


def odd_forney_inplace(builder: Any, locator: list[Any], words: list[Any], half_chart: tuple[int, ...],
                       *, adjoint: bool = False, multiply: FieldProduct = multiply_xor,
                       projective: bool = False, validity: Any = None) -> None:
    """Apply the derivative inverse using only the monic locator and evaluator banks.

    This fixed odd-degree chart receives the degrees of E mod D and its
    Euclidean successors, where locator(x) = x*D(x*x) + E(x*x).
    The chart ends at a nonzero gcd of degree zero.
    """
    n = len(locator)
    half = n // 2
    if n < 3 or n % 2 == 0 or len(words) != n:
        raise ValueError("in-place Forney requires equal odd-degree banks")
    chart = (half, *half_chart)
    if chart[-1] != 0 or any(not 0 <= b < a for a, b in zip(chart, chart[1:])):
        raise ValueError("invalid half-degree Euclidean chart")
    if projective and half_chart != tuple(range(half - 1, -1, -1)):
        raise ValueError("projective action requires all half-degree drops to be one")
    if validity is not None and not projective:
        raise ValueError("live chart validation requires the projective action")
    if any(len(word) != 12 for word in (*locator, *words)):
        raise ValueError("in-place Forney requires 12-bit words")

    even, dh = locator[::2], locator[1::2]
    derivative = [word for coefficient in dh for word in (coefficient, None)]
    if adjoint:
        _polynomial_basis(builder, locator, [words], multiply, to_polynomial=False)
        _extend_series(builder, locator, derivative, words, multiply, adjoint=True)
    else:
        for i, coefficient in enumerate(dh):
            multiply(builder, words[-1], coefficient, words[2 * i])

    # E mod D is one monic reduction. The even and odd locator slots already
    # hold its mutable remainder and the half-degree divisor, respectively.
    _toggle_half_remainder(builder, even, dh, multiply)
    r = half_chart[0]
    payloads = [words[:-1:2], words[1::2]]
    remainder, factor = even[:r], even[r]
    if projective:
        _projective_action(builder, [*dh, None], [*remainder, factor], payloads, multiply,
                           adjoint=adjoint, validity=validity)
    else:
        payload = words[:-1]
        _scale(builder, factor, remainder, [] if adjoint else payload, multiply, undo=False)
        if r:
            _inverse_actions(builder, dh, remainder, payloads, half_chart[1:], multiply, adjoint=adjoint)
        else:
            _polynomial_basis(builder, dh, payloads, multiply, to_polynomial=adjoint)
        _scale(builder, factor, remainder, payload if adjoint else [], multiply, undo=True)
    _toggle_half_remainder(builder, even, dh, multiply)

    if adjoint:
        for i, coefficient in enumerate(dh):
            multiply(builder, words[-1], coefficient, words[2 * i])
    else:
        _extend_series(builder, locator, derivative, words, multiply, adjoint=False)
        _polynomial_basis(builder, locator, [words], multiply, to_polynomial=True)
