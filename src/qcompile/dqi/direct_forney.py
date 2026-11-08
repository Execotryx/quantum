"""Exact direct-derivative DQI phase scan for a supplied locator.

This computes each derivative inverse at its scan position. It avoids a
reciprocal-polynomial circuit but does not construct the locator itself.
"""

from typing import Any

from .field import GF4096
from .scan import evaluator_xor, phase_at_position
from .subtower import inverse_xor


def direct_scan(builder: Any, field: Any, locator: list[Any], omega: list[Any], masks: list[Any]) -> None:
    """Apply all runtime-mask phases, restoring locator and evaluator words.

    The locator is nonzero and square-free for nonzero errors. The weight-zero
    constant locator is allowed; non-square-free inputs are outside the contract.
    All quantum words are disjoint and use the pinned polynomial field basis.
    """
    if not locator or len(omega) != len(locator) - 1 or not 1 <= len(masks) <= 4095:
        raise ValueError("invalid direct scan shape")
    if any(len(word) != 12 for word in (*locator, *omega, *masks)):
        raise ValueError("direct scan requires 12-bit words")
    evaluated_sigma = builder.alloc_qubits(12)
    evaluated_omega = builder.alloc_qubits(12)
    derivative = builder.alloc_qubits(12)
    reciprocal = builder.alloc_qubits(12)
    powers = GF4096().exp

    def evaluate() -> None:
        for i, word in enumerate(locator):
            builder.cx(word, evaluated_sigma)
            if i % 2:
                builder.cx(word, derivative)
        for word in omega:
            builder.cx(word, evaluated_omega)

    for position, mask in enumerate(masks):
        evaluate()
        # Current coefficients carry X**i with X=alpha**-position.
        # Multiplying odd terms by 1/X yields sigma'(X).
        if position:
            builder.gf2_imul(powers[position], target=derivative, field=field)
        inverse_xor(builder, derivative, reciprocal)
        phase_at_position(builder, evaluated_sigma, evaluated_omega, reciprocal, mask)
        inverse_xor(builder, derivative, reciprocal)
        if position:
            builder.gf2_idiv(powers[position], target=derivative, field=field)
        evaluate()
        if position + 1 < len(masks):
            for words in (locator, omega):
                for index, word in enumerate(words[1:], 1):
                    builder.gf2_imul(powers[-index % 4095], target=word, field=field)
    for words in (locator, omega):
        for index, word in enumerate(words[1:], 1):
            builder.gf2_idiv(powers[-index * (len(masks) - 1) % 4095], target=word, field=field)
    for register in (reciprocal, derivative, evaluated_omega, evaluated_sigma):
        builder.free(register)


def evaluator_and_scan(builder: Any, field: Any, locator: list[Any],
                       syndromes: list[Any], masks: list[Any]) -> None:
    """Construct evaluator, run exact direct scan, and uncompute evaluator."""
    if not locator or len(syndromes) < len(locator) - 1:
        raise ValueError("invalid locator or syndrome shape")
    omega = [builder.alloc_qubits(12) for _ in range(len(locator) - 1)]
    evaluator_xor(builder, locator, syndromes, omega)
    direct_scan(builder, field, locator, omega, masks)
    evaluator_xor(builder, locator, syndromes, omega)
    for word in omega:
        builder.free(word)
