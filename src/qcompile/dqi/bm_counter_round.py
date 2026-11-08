"""Coherent routed BM arithmetic and signed-counter transition.

The shifted template is still an input. A branch bit and retain-history word
are allocated by the caller and retained until the inverse round.
"""

from typing import Any

from .bm_arithmetic_round import _replace_discrepancy, _retain_history, discrepancy_xor
from .bm_prepared_round import routed_update_with_multiplier


def _toggle_branch(builder: Any, delta: Any, counter: Any, branch: Any) -> None:
    """XOR (Delta != 0 and signed counter >= 0) into branch."""
    zero = builder.alloc_qubits(1)[0]
    builder.flip_if_equal(delta, 0, target=zero)
    builder.x(zero)
    builder.x(counter[-1])
    builder.ccx(zero, counter[-1], branch)
    builder.x(counter[-1])
    builder.x(zero)
    builder.flip_if_equal(delta, 0, target=zero)
    builder.free(zero)


def _counter_step(builder: Any, counter: Any, branch: Any, *, adjoint: bool) -> None:
    """Apply d -> -d on replace, d -> d+1 otherwise, modulo counter width."""
    if adjoint:
        builder.x(branch)
        builder.isub(1, target=counter, control=branch)
        builder.x(branch)
        builder.isub(1, target=counter, control=branch)
        for wire in counter:
            builder.cx(branch, wire)
    else:
        for wire in counter:
            builder.cx(branch, wire)
        builder.iadd(1, target=counter, control=branch)
        builder.x(branch)
        builder.iadd(1, target=counter, control=branch)
        builder.x(branch)


def round_with_counter(builder: Any, sigma: list[Any], shifted_tau: list[Any], syndromes: list[Any],
                       index: int, counter: Any, branch: Any, history: Any,
                       *, adjoint: bool = False) -> None:
    """Compute branch, arithmetic, and signed counter; retain exact history.

    Exact restoration requires a clean forward branch and history. The
    shifted template constant must be zero when the discrepancy is nonzero.
    The reverse input must be a corresponding forward output.
    This does not prepare the virtual shift, update age, or address a stack.
    """
    if len(counter) < 2:
        raise ValueError("signed counter must have at least two bits")
    if len(history) != 12:
        raise ValueError("history must be a 12-bit word")
    delta = builder.alloc_qubits(12)
    inverse = builder.alloc_qubits(12)
    if adjoint:
        _counter_step(builder, counter, branch, adjoint=True)
        builder.cx(history, delta)
        _replace_discrepancy(builder, sigma[0], branch, delta, inverse)
        routed_update_with_multiplier(builder, sigma, shifted_tau, delta, branch, adjoint=True)
        _retain_history(builder, delta, branch, history)
        _toggle_branch(builder, delta, counter, branch)
        discrepancy_xor(builder, sigma, syndromes, index, delta)
    else:
        discrepancy_xor(builder, sigma, syndromes, index, delta)
        _toggle_branch(builder, delta, counter, branch)
        _retain_history(builder, delta, branch, history)
        routed_update_with_multiplier(builder, sigma, shifted_tau, delta, branch)
        builder.cx(history, delta)
        _replace_discrepancy(builder, sigma[0], branch, delta, inverse)
        _counter_step(builder, counter, branch, adjoint=False)
    builder.free(inverse)
    builder.free(delta)
