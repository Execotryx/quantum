"""Reversible scaled evaluator over the syndrome register itself."""

from collections.abc import Sequence
from typing import Any

from .subtower import inverse_xor
from .tower import multiply_xor


def inplace_evaluator(builder: Any, locator: Sequence[Any], syndromes: Sequence[Any],
                      *, adjoint: bool = False) -> None:
    """Replace a syndrome prefix with the truncated locator convolution.

    The locator constant must be nonzero, and all input words must be
    disjoint. The adjoint takes the evaluator words in the same physical
    syndrome registers. Other syndrome registers belong to the caller.
    """
    count = len(syndromes)
    if not 1 <= count <= 35 or len(locator) < count:
        raise ValueError("expected a syndrome prefix and its locator coefficients")
    if any(len(word) != 12 for word in (*locator, *syndromes)):
        raise ValueError("the evaluator requires 12-bit field words")
    inverse = builder.alloc_qubits(12)
    work = builder.alloc_qubits(12)
    inverse_xor(builder, locator[0], inverse)
    for i in (range(count) if adjoint else reversed(range(count))):
        target = syndromes[i]
        if adjoint:
            for j in range(1, i + 1):
                multiply_xor(builder, locator[j], syndromes[i - j], target)
        scale, clear = (inverse, locator[0]) if adjoint else (locator[0], inverse)
        multiply_xor(builder, scale, target, work)
        multiply_xor(builder, clear, work, target)
        for a, b in zip(target, work, strict=True):
            builder.swap(a, b)
        if not adjoint:
            for j in range(1, i + 1):
                multiply_xor(builder, locator[j], syndromes[i - j], target)
    inverse_xor(builder, locator[0], inverse)
    builder.free(work)
    builder.free(inverse)
