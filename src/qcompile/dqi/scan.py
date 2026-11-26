"""Classical evaluator/reciprocal and an exact runtime-mask phase kernel.

The polynomial routines are an oracle for development, not a circuit emitter.
The native kernel consumes already evaluated sigma, omega and reciprocal words.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import cache
from typing import Any

from .bilinear import product_tensor
from .decoder import _add, _divide, _multiply, _trim
from .field import GF4096
from .quotient import FieldProduct, quotient_prepare
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


@cache
def _phase_columns() -> tuple[tuple[tuple[int, int], ...], ...]:
    tensor = product_tensor()
    return tuple(tuple((i, bit) for i, row in enumerate(tensor) for bit in range(12) if row[j] >> bit & 1)
                 for j in range(12))


@contextmanager
def _root_flag(builder: Any, sigma: Any) -> Iterator[Any]:
    flags = builder.alloc_qubits(11)
    builder.x(sigma)
    builder.init_and(sigma[0], sigma[1], flags[0])
    for index in range(2, 12):
        builder.init_and(flags[index - 2], sigma[index], flags[index - 1])
    builder.x(sigma)
    yield flags[-1]
    builder.x(sigma)
    for index in range(11, 1, -1):
        builder.del_and(flags[index - 2], sigma[index], flags[index - 1])
    builder.del_and(sigma[0], sigma[1], flags[0])
    builder.x(sigma)
    builder.free(flags)


def phase_at_position(builder: Any, sigma: Any, omega: Any, reciprocal: Any, mask: Any) -> None:
    """Apply the mask phase of omega * reciprocal iff sigma is zero."""
    if any(len(reg) != 12 for reg in (sigma, omega, reciprocal, mask)):
        raise ValueError("phase kernel requires four 12-bit words")

    # The root flag implies sigma[0] is zero when the phase is enabled.
    # XOR one parity column into that bit and restore it before the next column.
    # A classical control makes each ccx call emit only conditional CNOTs.
    with _root_flag(builder, sigma) as root:
        parity = sigma[0]
        for j, column in enumerate(_phase_columns()):
            controls = [mask[bit] for _, bit in column]
            sources = [omega[i] for i, _ in column]
            builder.ccx(controls, sources, parity)
            builder.ccz(root, parity, reciprocal[j])
            builder.ccx(controls, sources, parity)


def _residue_phase(builder: Any, sigma: Any, residue: Any, mask: Any) -> None:
    with _root_flag(builder, sigma) as root:
        builder.ccz(root, residue, mask)


def phase_scan(builder: Any, field: Any, locator: list[Any], omega: list[Any],
               reciprocal: list[Any], masks: list[Any]) -> None:
    """Scan positions using root alpha**-j and restore every input coefficient.

    Coefficient registers are disjoint polynomial-basis words in ascending order.
    ``omega`` and ``reciprocal`` each have one fewer word than ``locator``.
    """
    if not locator or len(omega) != len(locator) - 1 or len(reciprocal) != len(omega):
        raise ValueError("invalid phase-scan coefficient shapes")
    _scan_evaluations(builder, field, (locator, omega, reciprocal), masks, phase_at_position)


def residue_scan(builder: Any, field: Any, locator: list[Any], residue: list[Any], masks: list[Any]) -> None:
    """Phase a supplied (omega / locator') mod locator and restore both inputs."""
    if not locator or len(residue) != len(locator) - 1:
        raise ValueError("invalid residue-scan coefficient shapes")
    _scan_evaluations(builder, field, (locator, residue), masks, _residue_phase)


def prepared_residue_scan(builder: Any, field: Any, modulus: list[Any], omega: list[Any],
                          reciprocal: list[Any], masks: list[Any], *,
                          multiply: FieldProduct = multiply_xor) -> None:
    """Prepare the residue, phase it, and restore a supplied monic locator and reciprocal.

    The active degree is fixed by the register layout. The implicit leading locator
    coefficient is one, its constant is nonzero, and reciprocal is the
    derivative inverse modulo the locator.
    """
    residue = [builder.alloc_qubits(12) for _ in omega]
    quotient_prepare(builder, omega, reciprocal, modulus, residue, multiply=multiply)
    _scan_evaluations(builder, field, (modulus, residue), masks, _residue_phase, monic=True)
    quotient_prepare(builder, omega, reciprocal, modulus, residue, adjoint=True, multiply=multiply)
    for word in residue:
        builder.free(word)


def _scan_evaluations(builder: Any, field: Any, groups: tuple[list[Any], ...],
                      masks: list[Any], kernel: Callable[..., None], *, monic: bool = False) -> None:
    if not 1 <= len(masks) <= 4095:
        raise ValueError("phase scan requires between 1 and 4095 positions")
    if any(len(word) != 12 for group in (*groups, masks) for word in group):
        raise ValueError("phase scan requires 12-bit words")
    evaluations = [builder.alloc_qubits(12) for _ in groups]
    powers = GF4096().exp

    def evaluate(position: int) -> None:
        for coefficients, target in zip(groups, evaluations, strict=True):
            for coefficient in coefficients:
                builder.cx(coefficient, target)
        if monic:
            leading = powers[-len(groups[0]) * position % 4095]
            builder.x([wire for bit, wire in enumerate(evaluations[0]) if leading >> bit & 1])

    for position, mask in enumerate(masks):
        evaluate(position)
        kernel(builder, *evaluations, mask)
        evaluate(position)
        if position + 1 < len(masks):
            for coefficients in groups:
                for index, coefficient in enumerate(coefficients[1:], 1):
                    builder.gf2_imul(powers[-index % 4095], target=coefficient, field=field)
    for coefficients in groups:
        for index, coefficient in enumerate(coefficients[1:], 1):
            builder.gf2_idiv(powers[-index * (len(masks) - 1) % 4095], target=coefficient, field=field)
    for register in evaluations:
        builder.free(register)
