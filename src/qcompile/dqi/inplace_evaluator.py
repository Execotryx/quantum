"""Reversible scaled evaluator over the syndrome register itself."""

from collections.abc import Sequence
from typing import Any

from .quotient import FieldProduct, _truncate_inplace
from .tower import multiply_xor


def inplace_evaluator(builder: Any, locator: Sequence[Any], syndromes: Sequence[Any],
                      *, adjoint: bool = False, multiply: FieldProduct = multiply_xor) -> None:
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
    _truncate_inplace(builder, list(syndromes), list(locator[:count]), multiply,
                      adjoint=adjoint, compact=True)
