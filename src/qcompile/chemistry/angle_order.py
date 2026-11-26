"""Commute disjoint Givens rotations to reduce mixed address ranks."""

from functools import lru_cache
from math import exp
from random import Random

import numpy as np
import numpy.typing as npt

from .representation import validate_tree


def _rank(rows: list[int]) -> int:
    pivots: dict[int, int] = {}
    for row in rows:
        while row:
            pivot = row.bit_length()
            if pivot not in pivots:
                pivots[pivot] = row
                break
            row ^= pivots[pivot]
    return len(pivots)


def _mixed_forms(words: npt.NDArray[np.int64], brot: int, low_bits: int
                 ) -> tuple[tuple[int, ...], ...]:
    """Extract mixed high/low ANF forms after dropping off-domain coefficients."""
    rows, width = words.shape
    universe = 1 << (rows - 1).bit_length()
    low_size = 1 << low_bits
    coeffs = np.zeros((universe, width), dtype=np.int64)
    coeffs[:rows] = words
    for bit in range((universe - 1).bit_length()):
        stride = 1 << bit
        blocks = coeffs.reshape(-1, 2, stride, width)
        blocks[:, 1, :, :] ^= blocks[:, 0, :, :]
    # The legal addresses form an initial integer interval, so a monomial
    # with mask >= rows never contributes to a legal address.
    coeffs[rows:] = 0
    mixed = coeffs.reshape(-1, low_size, width)[1:, 1:]
    return tuple(tuple(int.from_bytes(np.packbits((mixed[:, low, column] >> bit) & 1,
                                                 bitorder="little").tobytes(), "little")
                       for low in range(low_size - 1) for bit in range(brot))
                 for column in range(width))


def search_angle_order(words: npt.ArrayLike, edges: npt.ArrayLike, *, brot: int, batch: int,
                       low_bits: int, seed: int, proposals: int, require_change: bool = False
                       ) -> tuple[tuple[int, ...], int, int]:
    """Return a legal rotation order and before/after mixed-rank sums.

    This ranks one split monomial basis as a proxy for synthesis. The
    returned costs count neither shared products nor cache lifetimes.
    A matched compiler experiment can request the best changed schedule.
    """
    table = np.asarray(words)
    if (table.ndim != 2 or table.shape[0] < 4 or not table.shape[1] or table.dtype.kind not in "iu"
            or not 1 <= brot <= 52 or not 1 <= batch <= table.shape[1]
            or not 1 <= low_bits < (table.shape[0] - 1).bit_length() or proposals < 1
            or np.any(table < 0) or np.any(table >= 1 << brot)):
        raise ValueError("invalid angle order search dimensions")
    tree = validate_tree(edges, table.shape[1] + 1, 0)
    endpoints = [frozenset(edge) for edge in tree.tolist()]
    forms = _mixed_forms(table.astype(np.int64, copy=False), brot, low_bits)
    zeros = (0,) * len(forms[0])
    padded = (*forms, zeros)
    columns = len(forms)
    low_count = (1 << low_bits) - 1

    @lru_cache(maxsize=4096)
    def transition(previous: tuple[int, ...], current: tuple[int, ...]) -> int:
        deltas = [tuple(x ^ y for x, y in zip(padded[a], padded[b], strict=True))
                  for a, b in zip(previous, current, strict=True)]
        return sum(_rank([delta[low * brot + bit] for delta in deltas for bit in range(brot)])
                   for low in range(low_count))

    origin = tuple(range(columns))

    def cost(order: tuple[int, ...]) -> int:
        blank = (columns,) * batch
        padding = (columns,) * (-columns % batch)
        full = blank + order + padding
        return sum(transition(full[end - 2 * batch:end - batch], full[end - batch:end])
                   for end in range(2 * batch, len(full) + 1, batch))

    order = origin
    initial = value = cost(origin)
    winner = None if require_change else (initial, origin)
    rng = Random(seed)
    # Rotations can cross only a contiguous run of gates on disjoint
    # vertices. The move therefore preserves every noncommuting pair.
    for step in range(proposals):
        start = rng.randrange(columns)
        direction = rng.choice((-1, 1))
        end = start
        while 0 <= end + direction < columns and endpoints[order[start]].isdisjoint(endpoints[order[end + direction]]):
            end += direction
        if start == end:
            continue
        stop = rng.randrange(min(start, end), max(start, end) + 1)
        if stop == start:
            continue
        moved = list(order)
        moved.insert(stop, moved.pop(start))
        candidate = tuple(moved)
        charge = cost(candidate)
        if candidate != origin and (winner is None or charge < winner[0]):
            winner = charge, candidate
        temperature = 4 * (1 - step / proposals) + 0.25
        if charge <= value or rng.random() < exp((value - charge) / temperature):
            value, order = charge, candidate
    if winner is None:
        raise ValueError("the search found no commuting change")
    return winner[1], initial, winner[0]
