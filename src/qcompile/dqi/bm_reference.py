"""Exact normalized BM recurrence and its registered-history inverse.

This is a classical derivation fixture, not the rescaled routed circuit. The
auxiliary polynomial is unbounded here; its width must be proved separately
before translating this recurrence into finite quantum registers.
"""

from dataclasses import dataclass

from .decoder import _add, _trim
from .field import GF4096


@dataclass(frozen=True)
class History:
    replace: bool
    retained_discrepancy: int | None


def _scale(poly: list[int], factor: int, field: GF4096) -> list[int]:
    return _trim([field.mul(value, factor) for value in poly])


def _shift(poly: list[int]) -> list[int]:
    return [0] if poly == [0] else [0, *poly]


def _unshift(poly: list[int]) -> list[int]:
    if not poly or poly[0]:
        raise ValueError("auxiliary polynomial is not divisible by z")
    return _trim(poly[1:]) if len(poly) > 1 else [0]


def discrepancy(locator: list[int], syndromes: list[int], index: int, field: GF4096) -> int:
    result = 0
    for i in range(min(index, len(locator) - 1) + 1):
        result ^= field.mul(locator[i], syndromes[index - i])
    return result


def forward(syndromes: list[int], field: GF4096) -> tuple[list[int], list[int], int, list[History]]:
    """Emit normalized locator C and T=z**offset*B/previous-discrepancy."""
    locator, auxiliary, degree = [1], [0, 1], 0
    history = []
    for index in range(len(syndromes)):
        delta = discrepancy(locator, syndromes, index, field)
        replace = delta != 0 and 2 * degree <= index
        old_locator = locator
        locator = _add(locator, _scale(auxiliary, delta, field))
        if replace:
            auxiliary = _shift(_scale(old_locator, field.inv(delta), field))
            degree = index + 1 - degree
        else:
            auxiliary = _shift(auxiliary)
        history.append(History(replace, None if replace else delta))
    return locator, auxiliary, degree, history


def reverse(syndromes: list[int], locator: list[int], auxiliary: list[int], degree: int,
            history: list[History], field: GF4096) -> tuple[list[int], list[int], int]:
    """Undo each round, reconstructing replace discrepancies from T[1]."""
    if len(history) != len(syndromes):
        raise ValueError("one history entry is required per syndrome")
    for index in range(len(syndromes) - 1, -1, -1):
        entry = history[index]
        if entry.replace:
            if entry.retained_discrepancy is not None or len(auxiliary) < 2 or auxiliary[1] == 0:
                raise ValueError("invalid replace history")
            delta = field.inv(auxiliary[1])
            old_locator = _scale(_unshift(auxiliary), delta, field)
            old_auxiliary = _scale(_add(locator, old_locator), field.inv(delta), field)
            old_degree = index + 1 - degree
        else:
            if entry.retained_discrepancy is None:
                raise ValueError("missing retained discrepancy")
            delta = entry.retained_discrepancy
            old_auxiliary = _unshift(auxiliary)
            old_locator = _add(locator, _scale(old_auxiliary, delta, field))
            old_degree = degree
        if (old_degree < 0 or discrepancy(old_locator, syndromes, index, field) != delta
                or entry.replace != (delta != 0 and 2 * old_degree <= index)):
            raise ValueError("history does not invert the BM round")
        locator, auxiliary, degree = old_locator, old_auxiliary, old_degree
    if (locator, auxiliary, degree) != ([1], [0, 1], 0):
        raise ValueError("history does not restore the initialized state")
    return locator, auxiliary, degree
