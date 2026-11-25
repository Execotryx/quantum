"""Exact paired transfer for a genuine pole at the second visit to a node."""

from .decoder import _add, _divide, _multiply, _trim
from .field import GF4096


def split_local_pole(
    numerator: list[int], denominator: list[int], head: list[int], kappa: int, field: GF4096,
) -> tuple[list[int], list[int]]:
    """Write N/D = h + q²/(D/R), where R = (N + hD)/q².

    The first visit is finite. The second is a genuine pole precisely
    when the residual is nonzero and is divisible by q for a second
    time. Identically zero residuals use the separate termination path.
    """
    modulus = [kappa, 1, 1]
    if _divide(denominator, modulus, field)[1] == [0]:
        raise ValueError("The first visit must be finite")
    residual = _add(numerator, _multiply(head, denominator, field))
    if residual == [0]:
        raise ValueError("The pair terminates at its first visit")
    continuation, remainder = _divide(residual, [field.mul(kappa, kappa), 0, 1, 0, 1], field)
    if remainder != [0]:
        raise ValueError("The second visit has a finite chart")
    return denominator[:], continuation


def join_local_pole(
    next_numerator: list[int], next_denominator: list[int], head: list[int], kappa: int, field: GF4096,
) -> tuple[list[int], list[int]]:
    """Expand the paired branch with transfer matrix [[h, q²], [1, 0]]."""
    product = _multiply([field.mul(kappa, kappa), 0, 1, 0, 1], next_denominator, field)
    return _add(_multiply(head, next_numerator, field), product), next_numerator[:]


def forward_local_pole_jet(
    state: tuple[int, int, int], head: int, slope: int, factor: int, field: GF4096,
) -> tuple[int, int, int]:
    """Evaluate the forward paired transfer at a different node.

    The third coordinate is L = D² * (N/D)'. With S = N + hD,
    the new pair is (q² D, S). Its derivative numerator is
    q² * (L + h' D²), including points where S is zero.
    """
    if not factor:
        raise ValueError("The evaluation node must differ from the doubled node")
    n, d, derivative = state
    mul = field.mul
    square = mul(factor, factor)
    return mul(square, d), n ^ mul(head, d), mul(square, derivative ^ mul(slope, mul(d, d)))


def reverse_local_pole_jet(
    state: tuple[int, int, int], head: int, slope: int, factor: int, field: GF4096,
) -> tuple[int, int, int]:
    """Invert the evaluated paired transfer without dividing by S."""
    n, d, derivative = state
    mul = field.mul
    inverse_square = field.inv(mul(factor, factor))
    former_denominator = mul(inverse_square, n)
    return (
        d ^ mul(head, former_denominator),
        former_denominator,
        mul(inverse_square, derivative) ^ mul(slope, mul(former_denominator, former_denominator)),
    )


def synthesize_pair(
    tail: tuple[list[int], list[int]], heads: tuple[list[int], list[int]], kappa: int, pole: bool, field: GF4096,
) -> tuple[list[int], list[int]]:
    """Apply the inverse of a regular or local-pole extraction pair to polynomials."""
    numerator, denominator = tail
    first, second = heads
    if pole:
        return join_local_pole(numerator, denominator, first, kappa, field)
    q = [kappa, 1, 1]
    for head in (second, first):
        numerator, denominator = _add(_multiply(head, numerator, field), _multiply(q, denominator, field)), numerator
    return numerator, denominator


def recover_quadratic_tail(jet: tuple[int, int, int], pairs, field: GF4096):
    """Recover a (degree <=2, degree <=1) tail from its jet and full DQI degree bounds."""
    n0, d0, slope = jet
    if not (n0 or d0):
        raise ValueError("Both coordinates of the projective tail vanish")

    def expand(tail):
        for heads, kappa, pole in reversed(pairs):
            tail = synthesize_pair(tail, heads, kappa, pole, field)
        return tail

    # Prefer the smaller terminating/one-sided linear chart when it
    # satisfies the degree constraints of the full problem.
    if d0:
        simple = [n0, field.div(slope, d0)], [d0]
    else:
        simple = [n0], [d0, field.div(slope, n0)]
    n, d = expand(simple)
    if len(n) <= 35 and len(d) <= 36:
        return simple

    columns = tuple(map(expand, (([0, 1], [0]), ([0, 0, 1], [0]), ([0], [0, 1]), ([n0], [d0]))))
    rows = [[d0, 0, n0, slope]]
    for bank, limit in enumerate((35, 36)):
        polys = [column[bank] for column in columns]
        for i in range(limit, max(map(len, polys))):
            rows.append([poly[i] if i < len(poly) else 0 for poly in polys])
    rank = 0
    for col in range(3):
        pivot = next((r for r in range(rank, len(rows)) if rows[r][col]), None)
        if pivot is None:
            raise ValueError("The jet and full degree constraints do not determine this tail")
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        row = rows[rank]
        inverse = field.inv(row[col])
        row[:] = [field.mul(x, inverse) for x in row]
        for r, other in enumerate(rows):
            if r != rank and other[col]:
                scale = other[col]
                other[:] = [a ^ field.mul(scale, b) for a, b in zip(other, row, strict=True)]
        rank += 1
    if any(row[3] for row in rows[3:]):
        raise ValueError("No tail of degree (2, 1) satisfies the full degree constraints")
    return [n0, rows[0][3], rows[1][3]], [d0, rows[2][3]]


def matches_dqi_rational(numerator, denominator, moments, geometry, field: GF4096) -> bool:
    """Certify the reconstructed rational function against the original moments.

    If S is the Laurent series of syndrome moments and Q is the polynomial
    part of P*S, the D4 rational function F satisfies N + Q*D = 0 mod P.
    Within the original degree bounds, this determines the ratio uniquely.
    """
    degree = len(geometry) - 1
    if degree != len(moments) or degree % 2 or not geometry[-1]:
        raise ValueError("The geometry degree must match the even-length syndrome")
    numerator, denominator = _trim(list(numerator)), _trim(list(denominator))
    if denominator == [0] or len(numerator) > degree // 2 or len(denominator) > degree // 2 + 1:
        return False
    quotient = [0] * degree
    for power, coefficient in enumerate(geometry[1:], 1):
        if coefficient:
            for i in range(power):
                quotient[i] ^= field.mul(coefficient, moments[power - 1 - i])
    difference = _add(numerator, _multiply(quotient, denominator, field))
    return _divide(difference, list(geometry), field)[1] == [0]
