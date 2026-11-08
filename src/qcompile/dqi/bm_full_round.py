"""Circular-layout wrapper around the native signed-counter BM round."""

from typing import Any

from .bm_circular import template_indices
from .bm_counter_round import round_with_counter


def full_round(builder: Any, locator: list[Any], template: list[Any], syndromes: list[Any],
               r: int, counter: Any, branch: Any, history: Any, *, adjoint: bool = False) -> None:
    width = len(locator)
    if width != len(template) or width != len(syndromes) // 2 + 1 or not 1 <= r <= len(syndromes) <= 70:
        raise ValueError("invalid full BM round dimensions")
    active = min(r + 1, width)
    shifted = [template[i] for i in template_indices(r, width)[:active]]
    round_with_counter(builder, locator[:active], shifted, syndromes, r - 1,
                       counter, branch, history, adjoint=adjoint)
