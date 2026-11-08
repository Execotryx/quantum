"""One routed BM arithmetic round with caller-supplied branch and template.

Computes discrepancy from sigma and the syndrome prefix, preserves the retain
history word, applies the shared update, and clears transient arithmetic. The
caller must prepare a valid branch and virtual shifted template; counter, age,
stack addressing and their reverse are outside this slice.
"""

from typing import Any

from .bm_prepared_round import routed_update_with_multiplier
from .subtower import inverse_xor
from .tower import multiply_xor


def discrepancy_xor(builder: Any, sigma: list[Any], syndromes: list[Any], index: int, target: Any) -> None:
    """XOR the next syndrome convolution into an arbitrary target word."""
    if not sigma or not 0 <= index < len(syndromes) or len(target) != 12:
        raise ValueError("invalid discrepancy shape or index")
    if any(len(word) != 12 for word in (*sigma, *syndromes)):
        raise ValueError("discrepancy requires 12-bit words")
    for i, word in enumerate(sigma[:index + 1]):
        multiply_xor(builder, word, syndromes[index - i], target)


def _retain_history(builder: Any, delta: Any, replace: Any, history: Any) -> None:
    builder.x(replace)
    for source, target in zip(delta, history, strict=True):
        builder.ccx(replace, source, target)
    builder.x(replace)


def _replace_discrepancy(builder: Any, sigma0: Any, replace: Any, delta: Any, inverse: Any) -> None:
    inverse_xor(builder, sigma0, inverse)
    for source, target in zip(inverse, delta, strict=True):
        builder.ccx(replace, source, target)
    inverse_xor(builder, sigma0, inverse)


def arithmetic_round(builder: Any, sigma: list[Any], shifted_tau: list[Any],
                     syndromes: list[Any], index: int, replace: Any, history: Any,
                     *, adjoint: bool = False) -> None:
    """Apply or reverse the arithmetic round, leaving only retain history live.

    Forward requires history and scratch zero, shifted_tau[0]=0 and a valid
    replace flag: replace implies a nonzero computed discrepancy. Reverse takes
    the forward outputs and original branch flag. Inputs are disjoint.
    """
    if len(history) != 12:
        raise ValueError("history must be a 12-bit word")
    delta = builder.alloc_qubits(12)
    inverse = builder.alloc_qubits(12)

    if adjoint:
        builder.cx(history, delta)
        _replace_discrepancy(builder, sigma[0], replace, delta, inverse)
        routed_update_with_multiplier(builder, sigma, shifted_tau, delta, replace, adjoint=True)
        _retain_history(builder, delta, replace, history)
        discrepancy_xor(builder, sigma, syndromes, index, delta)
    else:
        discrepancy_xor(builder, sigma, syndromes, index, delta)
        _retain_history(builder, delta, replace, history)
        routed_update_with_multiplier(builder, sigma, shifted_tau, delta, replace)
        builder.cx(history, delta)
        _replace_discrepancy(builder, sigma[0], replace, delta, inverse)
    builder.free(inverse)
    builder.free(delta)
