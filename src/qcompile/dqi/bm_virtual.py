"""Routed BM with a virtual power-of-z template shift.

The base has a nonzero constant coefficient and is retained unchanged through
zero/retain rounds. This is a classical decodable-domain fixture, not a circuit.
"""

from dataclasses import dataclass
from typing import Any

from .bm_reference import discrepancy
from .bm_routed import History
from .decoder import _add


@dataclass(frozen=True)
class VirtualState:
    sigma: tuple[int, ...]
    base: tuple[int, ...]
    age: int
    counter: int


def _scaled(poly: tuple[int, ...], factor: int, field: Any) -> list[int]:
    return [field.mul(value, factor) for value in poly]


def _shifted(base: tuple[int, ...], amount: int, radius: int) -> list[int]:
    if not base or not base[0] or amount < 1:
        raise ValueError("invalid virtual template")
    if amount + len(base) - 1 > radius:
        raise ValueError("nonzero update would exceed locator radius")
    return [0] * amount + list(base)


def step(state: VirtualState, syndromes: list[int], index: int, radius: int,
         field: Any) -> tuple[VirtualState, History]:
    if not 0 <= index < len(syndromes) or state.age < 0 or not state.sigma or not state.sigma[0]:
        raise ValueError("invalid virtual routed state or round")
    delta = discrepancy(list(state.sigma), syndromes, index, field)
    if not delta:
        return VirtualState(state.sigma, state.base, state.age + 1, state.counter + 1), History(False, 0)
    shifted = _shifted(state.base, state.age + 1, radius)
    alpha = field.mul(delta, state.sigma[0])
    if state.counter >= 0:
        result = _add(shifted, _scaled(state.sigma, field.inv(alpha), field))
        return VirtualState(tuple(result), state.sigma, 0, -state.counter), History(True, 0)
    result = _add(list(state.sigma), [field.mul(alpha, value) for value in shifted])
    return VirtualState(tuple(result), state.base, state.age + 1, state.counter + 1), History(False, delta)


def reverse_step(state: VirtualState, history: History, syndromes: list[int], index: int,
                 radius: int, field: Any) -> VirtualState:
    if not state.sigma or not state.sigma[0]:
        raise ValueError("invalid virtual locator")
    if history.replace:
        if history.retained_discrepancy or state.age != 0 or not state.base or not state.base[0]:
            raise ValueError("invalid virtual replace history")
        delta = field.inv(state.sigma[0])
        old_sigma = state.base
        alpha = field.mul(delta, old_sigma[0])
        shifted = _add(list(state.sigma), _scaled(old_sigma, field.inv(alpha), field))
        offset = next((i for i, value in enumerate(shifted) if value), None)
        if offset is None or offset < 1:
            raise ValueError("replace did not preserve a nonzero shifted template")
        previous = VirtualState(old_sigma, tuple(shifted[offset:]), offset - 1, -state.counter)
    else:
        if state.age < 1:
            raise ValueError("cannot reverse virtual shift at age zero")
        delta = history.retained_discrepancy
        field.symbol(delta)
        if delta:
            shifted = _shifted(state.base, state.age, radius)
            correction = [field.mul(field.mul(delta, state.sigma[0]), value) for value in shifted]
            old_sigma = tuple(_add(list(state.sigma), correction))
        else:
            old_sigma = state.sigma
        previous = VirtualState(old_sigma, state.base, state.age - 1, state.counter - 1)
    replay, replay_history = step(previous, syndromes, index, radius, field)
    if replay != state or replay_history != history:
        raise ValueError("history does not invert virtual routed round")
    return previous


def forward(syndromes: list[int], radius: int, field: Any) -> tuple[VirtualState, list[History]]:
    state = VirtualState((1,), (1,), 0, 0)
    history = []
    for index in range(len(syndromes)):
        state, entry = step(state, syndromes, index, radius, field)
        history.append(entry)
    return state, history


def reverse(state: VirtualState, history: list[History], syndromes: list[int],
            radius: int, field: Any) -> VirtualState:
    if len(history) != len(syndromes):
        raise ValueError("one history entry per round is required")
    for index in range(len(syndromes) - 1, -1, -1):
        state = reverse_step(state, history[index], syndromes, index, radius, field)
    if state != VirtualState((1,), (1,), 0, 0):
        raise ValueError("history does not restore virtual initialization")
    return state
