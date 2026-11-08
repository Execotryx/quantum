"""Half-degree characteristic-two Bezout construction for DQI reciprocals.

Classical derivation with explicit Euclidean quotient history. A reversible
quantum EEA and fixed-width history have not yet been emitted.
"""

from dataclasses import dataclass
from typing import Any

from .decoder import _add, _divide, _multiply, _trim


@dataclass(frozen=True)
class Bezout:
    even: tuple[int, ...]
    odd: tuple[int, ...]
    a: tuple[int, ...]
    b: tuple[int, ...]
    quotients: tuple[tuple[int, ...], ...]
    gcd: int
    reciprocal: tuple[int, ...]


def _sqrt(value: int, field: Any) -> int:
    # The inverse of Frobenius x -> x^2 is x -> x^(2^(b-1)).
    degree = (field.order + 1).bit_length() - 1
    for _ in range(degree - 1):
        value = field.mul(value, value)
    return value


def _square(poly: list[int] | tuple[int, ...], field: Any) -> list[int]:
    result = [0] * (2 * len(poly) - 1)
    for i, value in enumerate(poly):
        result[2 * i] = field.mul(value, value)
    return _trim(result)


def split_locator(locator: list[int], field: Any) -> tuple[list[int], list[int]]:
    """Return E,O with sigma=E**2 + z*O**2, ascending coefficients."""
    locator = _trim(locator[:])
    if not locator or locator == [0] or not locator[0]:
        raise ValueError("locator must have a nonzero constant coefficient")
    for value in locator:
        field.symbol(value)
    even = _trim([_sqrt(value, field) for value in locator[::2]])
    odd = _trim([_sqrt(value, field) for value in locator[1::2]]) if len(locator) > 1 else [0]
    return even, odd


def bezout_reciprocal(locator: list[int], field: Any) -> Bezout:
    """Find A*E+B*O=1 and Psi=(z*A**2+B**2) mod sigma.

    A constant locator is the no-phase zero-weight case, with Psi=0. A
    nonconstant locator whose derivative is not invertible is rejected.
    """
    locator = _trim(locator[:])
    even, odd = split_locator(locator, field)
    previous, current = even[:], odd[:]
    a_previous, a_current = [1], [0]
    b_previous, b_current = [0], [1]
    quotients = []
    while current != [0]:
        quotient, remainder = _divide(previous, current, field)
        quotients.append(tuple(quotient))
        previous, current = current, remainder
        a_previous, a_current = a_current, _add(a_previous, _multiply(quotient, a_current, field))
        b_previous, b_current = b_current, _add(b_previous, _multiply(quotient, b_current, field))
    if len(previous) != 1 or not previous[0]:
        raise ValueError("locator derivative is not invertible")
    gcd = previous[0]
    scale = field.inv(gcd)
    a = [field.mul(value, scale) for value in a_previous]
    b = [field.mul(value, scale) for value in b_previous]
    if len(locator) == 1:
        reciprocal = [0]
    else:
        candidate = _add([0, *_square(a, field)], _square(b, field))
        reciprocal = _divide(candidate, locator, field)[1]
    return Bezout(tuple(even), tuple(odd), tuple(a), tuple(b), tuple(quotients), gcd, tuple(reciprocal))


def reverse_remainders(gcd: int, quotients: tuple[tuple[int, ...], ...],
                       field: Any) -> tuple[list[int], list[int]]:
    """Reverse Euclidean remainders using every saved quotient exactly."""
    previous, current = [gcd], [0]
    for quotient in reversed(quotients):
        previous, current = _add(current, _multiply(list(quotient), previous, field)), previous
    return previous, current
