"""Reduced routed BM shared multiply-add primitive, with supplied metadata."""

from typing import Any

from .tower import multiply_xor


def routed_update(builder: Any, sigma: list[Any], shifted_tau: list[Any],
                  multiplier: Any, replace: Any, *, adjoint: bool = False) -> None:
    """Route rows, then XOR multiplier*template into locator.

    Inputs are disjoint equal-length rows of 12-bit words. The caller supplies
    alpha on retain and inverse(alpha) on replace. This does not compute branch
    controls, shift the template, manage history, or emit a complete BM round.
    """
    if not sigma or len(sigma) != len(shifted_tau) or len(multiplier) != 12:
        raise ValueError("invalid routed BM slice shape")
    if any(len(word) != 12 for word in (*sigma, *shifted_tau)):
        raise ValueError("routed BM slice requires 12-bit words")

    def route() -> None:
        for locator_word, template_word in zip(sigma, shifted_tau, strict=True):
            builder.cswap(replace, locator_word, template_word)

    if not adjoint:
        route()
    for locator_word, template_word in zip(sigma, shifted_tau, strict=True):
        multiply_xor(builder, multiplier, template_word, locator_word)
    if adjoint:
        route()
