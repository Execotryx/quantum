"""Classical routed BM state in the native circular template layout."""

from dataclasses import dataclass
from typing import Any

from .bm_reference import discrepancy
from .bm_routed import History

WIDTH = 36


class UnsupportedRound(ValueError):
    """An active update would read a wrapped nonzero constant."""


@dataclass(frozen=True)
class CircularState:
    sigma: tuple[int, ...]
    template: tuple[int, ...]
    counter: int


def template_indices(round_number: int, width: int) -> list[int]:
    return [(i - round_number) % width for i in range(width)]


def _layout(state: CircularState, syndromes: list[int], r: int) -> tuple[int, list[int]]:
    if (len(state.sigma) != WIDTH or len(state.template) != WIDTH or not state.sigma[0]
            or not 1 <= r <= min(len(syndromes), 70)):
        raise ValueError("invalid circular BM state or round")
    active = min(r + 1, WIDTH)
    return active, template_indices(r, WIDTH)[:active]


def step_circular(state: CircularState, syndromes: list[int], r: int, field: Any) -> tuple[CircularState, History]:
    active, indices = _layout(state, syndromes, r)
    delta = discrepancy(list(state.sigma[:active]), syndromes, r - 1, field)
    if not delta:
        return CircularState(state.sigma, state.template, state.counter + 1), History(False, 0)
    if state.template[indices[0]]:
        raise UnsupportedRound("nonzero wrapped template on active update")
    alpha = field.mul(delta, state.sigma[0])
    template = list(state.template)
    sigma = list(state.sigma)
    replace = state.counter >= 0
    if replace:
        alpha = field.inv(alpha)
    for i, slot in enumerate(indices):
        if replace:
            sigma[i], template[slot] = template[slot] ^ field.mul(alpha, sigma[i]), sigma[i]
        else:
            sigma[i] ^= field.mul(alpha, template[slot])
    counter = -state.counter if replace else state.counter + 1
    return CircularState(tuple(sigma), tuple(template), counter), History(replace, 0 if replace else delta)


def reverse_circular(state: CircularState, history: History, syndromes: list[int], r: int,
                     field: Any) -> CircularState:
    active, indices = _layout(state, syndromes, r)
    template = list(state.template)
    sigma = list(state.sigma)
    delta = history.retained_discrepancy
    if history.replace:
        if delta or not template[indices[0]]:
            raise ValueError("invalid replace history")
        delta = field.inv(sigma[0])
        alpha_inverse = field.inv(field.mul(delta, template[indices[0]]))
        for i, slot in enumerate(indices):
            sigma[i], template[slot] = template[slot], sigma[i] ^ field.mul(alpha_inverse, template[slot])
        counter = -state.counter
    else:
        if delta:
            alpha = field.mul(delta, sigma[0])
            for i, slot in enumerate(indices):
                sigma[i] ^= field.mul(alpha, template[slot])
        counter = state.counter - 1
    if delta and template[indices[0]]:
        raise UnsupportedRound("nonzero wrapped template on active update")
    if ((delta != discrepancy(sigma[:active], syndromes, r - 1, field))
            or history.replace != bool(delta and counter >= 0)):
        raise ValueError("circular BM output does not match its round history")
    return CircularState(tuple(sigma), tuple(template), counter)
