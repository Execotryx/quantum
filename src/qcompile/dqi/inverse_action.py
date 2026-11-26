"""Fixed-degree Euclidean inverse action on a polynomial register."""

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


def _reconstruct(builder: Any, modulus: list[Any], divisor: list[Any], words: list[Any],
                 multiply: FieldProduct, *, adjoint: bool) -> None:
    """Map packed (Q, C) to C + polynomial_part(A*Q/D) without another bank."""
    k = len(divisor)
    if adjoint:
        _rotate(builder, words, len(words) - k)
    tail = list(reversed(words[k:]))
    packed = [*reversed(words[:k]), *tail]
    a, d = modulus[::-1], divisor[::-1]
    # On the reversed coefficients the quotient is a truncated series
    # action A_rev / D_rev. First counteract that action on the dirty C tail.
    if adjoint:
        _series_inplace(builder, packed, d, multiply, adjoint=False)
        _series_inplace(builder, packed, a, multiply, adjoint=True)
        _series_inplace(builder, tail, a, multiply, adjoint=False)
        _series_inplace(builder, tail, d, multiply, adjoint=True)
    else:
        _series_inplace(builder, tail, d, multiply, adjoint=False)
        _series_inplace(builder, tail, a, multiply, adjoint=True)
        _series_inplace(builder, packed, a, multiply, adjoint=False)
        _series_inplace(builder, packed, d, multiply, adjoint=True)
        _rotate(builder, words, k)


def _scale(builder: Any, factor: Any, normal: list[Any], data: list[Any], multiply: FieldProduct,
           *, undo: bool) -> None:
    reciprocal = builder.alloc_qubits(12)
    inverse_xor(builder, factor, reciprocal, borrow_source=True)
    scale, clear = (factor, reciprocal) if undo else (reciprocal, factor)
    work = builder.alloc_qubits(12)
    for word in (*normal, *data):
        multiply(builder, scale, word, work)
        erase_product(builder, clear, work, word)
        builder.swap(word, work)
    builder.free(work)
    inverse_xor(builder, factor, reciprocal, borrow_source=True)
    builder.free(reciprocal)


def inverse_action(builder: Any, modulus: list[Any], divisor: list[Any], words: list[Any],
                   remainder_degrees: tuple[int, ...], *, adjoint: bool = False,
                   multiply: FieldProduct = multiply_xor) -> None:
    """Replace X by X/D mod A, or apply its inverse, for a supplied Euclidean degree chart.

    A and D are monic and only their lower coefficients are stored. X has
    degree less than A. The chart lists each nonzero remainder degree
    down to the constant gcd. The caller must establish the chart; no
    input-dependent routing is performed here. A and D are restored.
    """
    _inverse_actions(builder, modulus, divisor, [words], remainder_degrees, multiply, adjoint=adjoint)


def _inverse_actions(builder: Any, modulus: list[Any], divisor: list[Any], banks: list[list[Any]],
                     remainder_degrees: tuple[int, ...], multiply: FieldProduct, *, adjoint: bool) -> None:
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
                _reconstruct(builder, a, d, x, multiply, adjoint=True)
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
        _scale(builder, factor, remainder, payload if adjoint else [], multiply, undo=True)
        _packed_divide(builder, a, d, multiply, adjoint=True)
        for source, target in zip(d, a[len(a) - degree:], strict=True):
            builder.cx(source, target)

        for x in xs:
            if adjoint:
                _packed_divide(builder, x, d, multiply, adjoint=True)
            else:
                _reconstruct(builder, a, d, x, multiply, adjoint=False)

    apply(modulus, divisor, banks, 0)


def odd_forney_inplace(builder: Any, locator: list[Any], words: list[Any], half_chart: tuple[int, ...],
                       *, adjoint: bool = False, multiply: FieldProduct = multiply_xor) -> None:
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
    if any(len(word) != 12 for word in (*locator, *words)):
        raise ValueError("in-place Forney requires 12-bit words")

    even, dh = locator[::2], locator[1::2]
    derivative = [word for coefficient in dh for word in (coefficient, None)]
    if adjoint:
        _reconstruct(builder, locator, derivative, words, multiply, adjoint=True)
    else:
        for i, coefficient in enumerate(dh):
            multiply(builder, words[-1], coefficient, words[2 * i])

    # E mod D is one monic reduction. The even and odd locator slots already
    # hold its mutable remainder and the half-degree divisor, respectively.
    for coefficient, target in zip(dh, even[:-1], strict=True):
        multiply(builder, even[-1], coefficient, target)
    r = half_chart[0]
    payloads = [words[:-1:2], words[1::2]]
    payload = words[:-1]
    remainder, factor = even[:r], even[r]
    _scale(builder, factor, remainder, [] if adjoint else payload, multiply, undo=False)
    if r:
        _inverse_actions(builder, dh, remainder, payloads, half_chart[1:], multiply, adjoint=adjoint)
    _scale(builder, factor, remainder, payload if adjoint else [], multiply, undo=True)
    for coefficient, target in zip(dh, even[:-1], strict=True):
        multiply(builder, even[-1], coefficient, target)

    if adjoint:
        for i, coefficient in enumerate(dh):
            multiply(builder, words[-1], coefficient, words[2 * i])
    else:
        _reconstruct(builder, locator, derivative, words, multiply, adjoint=False)
