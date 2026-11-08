"""Coherent routed BM update with internally prepared field multiplier.

Discrepancy, branch and the already-shifted template remain caller inputs.
This is a development slice, not a complete syndrome-to-locator round.
"""

from typing import Any

from .bm_circuit import routed_update
from .subtower import inverse_xor
from .tower import multiply_xor


def _select_old_constant(builder: Any, sigma0: Any, template0: Any, replace: Any, output: Any) -> None:
    """XOR the old locator constant from a routed output into output."""
    builder.cx(sigma0, output)
    for a, b, target in zip(sigma0, template0, output, strict=True):
        builder.ccx(replace, a, target)
        builder.ccx(replace, b, target)


def routed_update_with_multiplier(builder: Any, sigma: list[Any], shifted_tau: list[Any],
                                  delta: Any, replace: Any, *, adjoint: bool = False) -> None:
    """Compute alpha=Delta*sigma0, route its inverse on replace, then clear it.

    All registers are disjoint. In forward inputs shifted_tau[0] is zero;
    replace must be false when Delta is zero. The adjoint receives a valid
    output of the forward slice with the same Delta and replace metadata.
    """
    if not sigma or len(sigma) != len(shifted_tau) or len(delta) != 12:
        raise ValueError("invalid routed update shape")
    if any(len(word) != 12 for word in (*sigma, *shifted_tau)):
        raise ValueError("routed update requires 12-bit words")
    alpha = builder.alloc_qubits(12)
    inverse = builder.alloc_qubits(12)
    old_constant = builder.alloc_qubits(12)
    if adjoint:
        _select_old_constant(builder, sigma[0], shifted_tau[0], replace, old_constant)
    else:
        builder.cx(sigma[0], old_constant)
    multiply_xor(builder, delta, old_constant, alpha)
    inverse_xor(builder, alpha, inverse)
    builder.cswap(replace, alpha, inverse)
    routed_update(builder, sigma, shifted_tau, alpha, replace, adjoint=adjoint)
    builder.cswap(replace, alpha, inverse)
    inverse_xor(builder, alpha, inverse)
    multiply_xor(builder, delta, old_constant, alpha)
    if adjoint:
        builder.cx(sigma[0], old_constant)
    else:
        _select_old_constant(builder, sigma[0], shifted_tau[0], replace, old_constant)
    for register in (old_constant, inverse, alpha):
        builder.free(register)
