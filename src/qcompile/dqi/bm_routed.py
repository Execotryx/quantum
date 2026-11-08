"""Exact rescaled, routed BM rounds with explicit branch-specific history.

Classical development fixture, using polynomial coefficients in ascending order
and the project's S[0] == S_1 convention. No coefficient or history cutoff.
"""

from dataclasses import dataclass
from typing import Any

from .bm_reference import discrepancy
from .decoder import _add, _trim


@dataclass(frozen=True)
class State:
    sigma: tuple[int, ...]
    tau: tuple[int, ...]
    counter: int


@dataclass(frozen=True)
class History:
    replace: bool
    retained_discrepancy: int


def _scale(poly: tuple[int, ...] | list[int], factor: int, field: Any) -> list[int]:
    return _trim([field.mul(value, factor) for value in poly])


def _shift(poly: tuple[int, ...]) -> list[int]:
    return [0] if poly == (0,) else [0, *poly]


def _unshift(poly: list[int] | tuple[int, ...]) -> list[int]:
    if not poly or poly[0]:
        raise ValueError("shifted template has nonzero constant coefficient")
    return _trim(list(poly[1:])) if len(poly) > 1 else [0]


def step(state: State, syndromes: list[int], index: int, field: Any) -> tuple[State, History]:
    if not 0 <= index < len(syndromes) or not state.sigma or not state.sigma[0]:
        raise ValueError("invalid routed BM state or round")
    delta = discrepancy(list(state.sigma), syndromes, index, field)
    shifted = _shift(state.tau)
    if not delta:
        return State(state.sigma, tuple(shifted), state.counter + 1), History(False, 0)
    alpha = field.mul(delta, state.sigma[0])
    if state.counter >= 0:
        # Conditional routing swaps sigma with shifted tau, then applies the
        # same multiply-add used by the retain branch, with inverse(alpha).
        sigma = _add(shifted, _scale(state.sigma, field.inv(alpha), field))
        return State(tuple(sigma), state.sigma, -state.counter), History(True, 0)
    sigma = _add(list(state.sigma), _scale(shifted, alpha, field))
    return State(tuple(sigma), tuple(shifted), state.counter + 1), History(False, delta)


def reverse_step(state: State, history: History, syndromes: list[int], index: int, field: Any) -> State:
    if not state.sigma or not state.sigma[0]:
        raise ValueError("invalid output locator constant")
    if history.replace:
        if history.retained_discrepancy or not state.tau or not state.tau[0]:
            raise ValueError("invalid replace history or template")
        delta = field.inv(state.sigma[0])
        old_sigma = state.tau
        alpha = field.mul(delta, old_sigma[0])
        shifted = _add(list(state.sigma), _scale(old_sigma, field.inv(alpha), field))
        old_tau = _unshift(shifted)
        old_counter = -state.counter
    else:
        delta = history.retained_discrepancy
        field.symbol(delta)
        old_sigma = tuple(_add(list(state.sigma), _scale(state.tau, field.mul(delta, state.sigma[0]), field)))
        old_tau = _unshift(state.tau)
        old_counter = state.counter - 1
    previous = State(tuple(old_sigma), tuple(old_tau), old_counter)
    replay, replay_history = step(previous, syndromes, index, field)
    if replay != state or replay_history != history:
        raise ValueError("history does not invert routed BM round")
    return previous


def forward(syndromes: list[int], field: Any) -> tuple[State, list[History]]:
    state = State((1,), (1,), 0)
    history = []
    for index in range(len(syndromes)):
        state, entry = step(state, syndromes, index, field)
        history.append(entry)
    return state, history


def reverse(state: State, history: list[History], syndromes: list[int], field: Any) -> State:
    if len(history) != len(syndromes):
        raise ValueError("one branch record per round is required")
    for index in range(len(syndromes) - 1, -1, -1):
        state = reverse_step(state, history[index], syndromes, index, field)
    if state != State((1,), (1,), 0):
        raise ValueError("history does not restore routed BM initialization")
    return state
