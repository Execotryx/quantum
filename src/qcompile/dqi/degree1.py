"""Exact radius-one DQI decoder for two syndrome words.

This reduced-shape circuit supplies no general routed BM or degree-35 solver.
Its supported inputs are zero or a single nonzero error in the scanned positions.
"""

from typing import Any

from .bilinear import erase_product
from .scan import phase_scan
from .subtower import inverse_xor
from .tower import multiply_xor


def emit(builder: Any, field: Any, syndromes: list[Any], masks: list[Any]) -> None:
    """Decode S1,S2, apply their runtime-mask phase and restore all scratch."""
    if len(syndromes) != 2 or not 2 <= len(masks) <= 4095:
        raise ValueError("radius-one decoder requires two syndromes and 2..4095 masks")
    if any(len(word) != 12 for word in (*syndromes, *masks)):
        raise ValueError("radius-one decoder requires 12-bit words")
    inverse_s1 = builder.alloc_qubits(12)
    sigma0 = builder.alloc_qubits(12)
    sigma1 = builder.alloc_qubits(12)
    reciprocal = builder.alloc_qubits(12)
    builder.x(sigma0[0])
    # For a single error, S2/S1 = X; zero input maps to zero.
    inverse_xor(builder, syndromes[0], inverse_s1)
    multiply_xor(builder, syndromes[1], inverse_s1, sigma1)
    inverse_xor(builder, sigma1, reciprocal)
    phase_scan(builder, field, [sigma0, sigma1], [syndromes[0]], [reciprocal], masks)
    inverse_xor(builder, sigma1, reciprocal)
    erase_product(builder, syndromes[1], inverse_s1, sigma1)
    inverse_xor(builder, syndromes[0], inverse_s1)
    builder.x(sigma0[0])
    for register in (reciprocal, sigma1, sigma0, inverse_s1):
        builder.free(register)
