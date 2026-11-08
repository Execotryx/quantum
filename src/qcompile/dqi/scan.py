"""Classical evaluator/reciprocal and an exact runtime-mask phase kernel.

The polynomial routines are an oracle for development, not a circuit emitter.
The native kernel consumes already evaluated sigma, omega and reciprocal words.
"""

from typing import Any

from .bilinear import product_tensor
from .decoder import _add, _divide, _multiply, _trim
from .field import GF4096
from .tower import inverse_xor, multiply_xor


def evaluator(syndromes: list[int], locator: list[int], field: GF4096) -> list[int]:
    """Return (locator * syndrome series) mod z**degree(locator)."""
    locator = _trim(locator[:])
    if locator == [0] or len(syndromes) < len(locator) - 1:
        raise ValueError("invalid locator or too few syndromes")
    degree = len(locator) - 1
    if not degree:
        return [0]
    return _trim(_multiply(locator, syndromes[:degree], field)[:degree])


def derivative_reciprocal(locator: list[int], field: GF4096) -> list[int]:
    """Return inverse(locator') modulo locator; return zero for weight zero.

    Reject repeated roots: the reciprocal does not exist in that case.
    """
    locator = _trim(locator[:])
    if locator == [0]:
        raise ValueError("zero locator")
    if len(locator) == 1:
        return [0]
    derivative = _trim([locator[i] if i % 2 else 0 for i in range(1, len(locator))])
    previous, current = locator, derivative
    t_previous, t_current = [0], [1]
    while current != [0]:
        quotient, remainder = _divide(previous, current, field)
        previous, current = current, remainder
        t_previous, t_current = t_current, _add(t_previous, _multiply(quotient, t_current, field))
    if len(previous) != 1 or previous[0] == 0:
        raise ValueError("locator derivative is not invertible modulo locator")
    inverse = field.inv(previous[0])
    scaled = [field.mul(value, inverse) for value in t_previous]
    return _divide(scaled, locator, field)[1]


def evaluator_xor(builder: Any, locator: list[Any], syndromes: list[Any], omega: list[Any]) -> None:
    """XOR the truncated locator-syndrome product into disjoint output words."""
    if len(locator) != len(omega) + 1 or len(syndromes) < len(omega):
        raise ValueError("invalid evaluator coefficient shapes")
    if any(len(word) != 12 for word in (*locator, *syndromes, *omega)):
        raise ValueError("evaluator requires 12-bit words")
    for index, target in enumerate(omega):
        for i in range(index + 1):
            multiply_xor(builder, locator[i], syndromes[index - i], target)


def quadratic_reciprocal_xor(builder: Any, locator: list[Any], reciprocal: list[Any]) -> None:
    """XOR 1/sigma' for valid degree-at-most-two locators into reciprocal.

    For degree two, square-freeness requires sigma[1] != 0. The constant
    weight-zero locator maps to zero via the inverse primitive's zero behavior.
    Invalid non-square-free locators are outside this circuit's input contract.
    """
    if len(locator) != 3 or len(reciprocal) != 2:
        raise ValueError("quadratic reciprocal requires three locator and two output words")
    if any(len(word) != 12 for word in (*locator, *reciprocal)):
        raise ValueError("quadratic reciprocal requires 12-bit words")
    inverse_xor(builder, locator[1], reciprocal[0])


def phase_at_position(builder: Any, sigma: Any, omega: Any, reciprocal: Any, mask: Any) -> None:
    """Apply the exact mask phase for evaluated words, then clear scratch.

    Applies (-1)**parity(mask & (omega * reciprocal)) iff sigma is zero.
    Inputs are disjoint 12-bit registers and mask is a classical 12-bit word.
    """
    if any(len(reg) != 12 for reg in (sigma, omega, reciprocal, mask)):
        raise ValueError("phase kernel requires four 12-bit words")
    flags = builder.alloc_qubits(11)
    transformed = builder.alloc_qubits(12)
    builder.x(sigma)
    builder.init_and(sigma[0], sigma[1], flags[0])
    for index in range(2, 12):
        builder.init_and(flags[index - 2], sigma[index], flags[index - 1])
    builder.x(sigma)

    tensor = product_tensor()
    def transform() -> None:
        for bit, control in enumerate(mask):
            builder.push_condition(control)
            for i, row in enumerate(tensor):
                for j, word in enumerate(row):
                    if word >> bit & 1:
                        builder.cx(omega[i], transformed[j])
            builder.pop_condition()

    transform()
    for i in range(12):
        builder.ccz(flags[-1], transformed[i], reciprocal[i])
    transform()
    builder.x(sigma)
    for index in range(11, 1, -1):
        builder.del_and(flags[index - 2], sigma[index], flags[index - 1])
    builder.del_and(sigma[0], sigma[1], flags[0])
    builder.x(sigma)
    builder.free(transformed)
    builder.free(flags)


def phase_scan(builder: Any, field: Any, locator: list[Any], omega: list[Any],
               reciprocal: list[Any], masks: list[Any]) -> None:
    """Scan positions using root alpha**-j and restore every input coefficient.

    Coefficient registers are disjoint polynomial-basis words in ascending order.
    ``omega`` and ``reciprocal`` each have one fewer word than ``locator``.
    """
    if not locator or len(omega) != len(locator) - 1 or len(reciprocal) != len(omega):
        raise ValueError("invalid phase-scan coefficient shapes")
    if not 1 <= len(masks) <= 4095:
        raise ValueError("phase scan requires between 1 and 4095 positions")
    if any(len(word) != 12 for word in (*locator, *omega, *reciprocal, *masks)):
        raise ValueError("phase scan requires 12-bit words")
    evaluations = [builder.alloc_qubits(12) for _ in range(3)]
    groups = (locator, omega, reciprocal)
    powers = GF4096().exp

    def evaluate() -> None:
        for coefficients, target in zip(groups, evaluations, strict=True):
            for coefficient in coefficients:
                builder.cx(coefficient, target)

    for position, mask in enumerate(masks):
        evaluate()
        phase_at_position(builder, evaluations[0], evaluations[1], evaluations[2], mask)
        evaluate()
        if position + 1 < len(masks):
            for coefficients in groups:
                for index, coefficient in enumerate(coefficients[1:], 1):
                    builder.gf2_imul(powers[-index % 4095], target=coefficient, field=field)
    for coefficients in groups:
        for index, coefficient in enumerate(coefficients[1:], 1):
            builder.gf2_idiv(powers[-index * (len(masks) - 1) % 4095], target=coefficient, field=field)
    for register in evaluations:
        builder.free(register)
