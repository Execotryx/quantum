"""Classical (sigma, g) end-state bijection and a two-bank W3 harness.

The transfer is a reversible oracle construction, not a finite-width circuit:
its forward and inverse polynomial computations still need reversible emitters.
"""

from typing import Any

from .bm_reference import forward
from .decoder import _divide, _multiply
from .scan import derivative_reciprocal, evaluator


def degree_bits(syndrome_count: int) -> int:
    if syndrome_count < 2 or syndrome_count % 2:
        raise ValueError("syndrome count must be positive and even")
    return (syndrome_count // 2).bit_length()


def pack(syndromes: list[int], field: Any) -> tuple[int, list[int]]:
    """Map a decodable syndrome to weight and fixed-size sigma/g word bank."""
    n = len(syndromes)
    degree_bits(n)
    for value in syndromes:
        field.symbol(value)
    locator, _, degree, _ = forward(syndromes, field)
    if degree > n // 2 or len(locator) != degree + 1 or locator[0] != 1:
        raise ValueError("syndrome locator outside the registered decoding domain")
    if degree == 0:
        if any(syndromes):
            raise ValueError("nonzero syndrome has zero locator degree")
        return 0, [0] * n
    omega = evaluator(syndromes, locator, field)
    psi = derivative_reciprocal(locator, field)
    g = _divide(_multiply(omega, psi, field), locator, field)[1]
    bank = locator[1:] + g + [0] * (degree - len(g)) + [0] * (n - 2 * degree)
    return degree, bank


def unpack(weight: int, bank: list[int], field: Any) -> list[int]:
    """Recover the syndrome from a canonical weight and sigma/g bank."""
    n = len(bank)
    degree_bits(n)
    if type(weight) is not int or not 0 <= weight <= n // 2:
        raise ValueError("weight outside the registered decoding radius")
    for value in bank:
        field.symbol(value)
    if any(bank[2 * weight:]):
        raise ValueError("nonzero unused bank words")
    if weight == 0:
        return [0] * n
    locator = [1, *bank[:weight]]
    if locator[-1] == 0:
        raise ValueError("locator has lower degree than the weight register")
    # Invertibility is required even though reconstruction itself multiplies
    # by the derivative; it rejects repeated-root encodings.
    derivative_reciprocal(locator, field)
    derivative = [locator[i] if i % 2 else 0 for i in range(1, len(locator))]
    omega = _divide(_multiply(bank[weight:2 * weight], derivative, field), locator, field)[1]
    values: list[int] = []
    for k in range(n):
        value = omega[k] if k < len(omega) else 0
        for i in range(1, min(weight, k) + 1):
            value ^= field.mul(locator[i], values[k - i])
        values.append(value)
    # This verifies the encoding is canonical for the recovered recurrence;
    # domain membership (split roots and nonzero errors) is a caller contract.
    if pack(values, field) != (weight, bank):
        raise ValueError("bank is not a canonical syndrome encoding")
    return values


def transfer_forward(source: list[int], field: Any) -> tuple[list[int], int, list[int]]:
    """Two-bank oracle transfer: (S, 0, 0) -> (0, w, bank)."""
    weight, bank = pack(source, field)
    reconstructed = unpack(weight, bank, field)
    return [a ^ b for a, b in zip(source, reconstructed, strict=True)], weight, bank


def transfer_reverse(source: list[int], weight: int, bank: list[int],
                     field: Any) -> tuple[list[int], int, list[int]]:
    """Inverse oracle transfer: (0, w, bank) -> (S, 0, 0)."""
    if any(source) or len(source) != len(bank):
        raise ValueError("inverse transfer requires a clean source bank")
    recovered = unpack(weight, bank, field)
    recovered_weight, recovered_bank = pack(recovered, field)
    return recovered, weight ^ recovered_weight, [a ^ b for a, b in zip(bank, recovered_bank, strict=True)]
