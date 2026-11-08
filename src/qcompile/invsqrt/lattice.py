"""Search coefficient lattices against the exact emitted Horner recurrence."""

from itertools import product
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from .direct import DirectFormat, Words, phase64


def search_table(
    fmt: DirectFormat,
    table: tuple[tuple[int, ...], ...],
    last: int,
    targets: Callable[[Words], tuple[NDArray[np.uint64], NDArray[np.uint64]]],
    radius: int = 2,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """Minimize each segment's worst relative tolerance use, then maximize margin.

    Each input belongs to exactly one segment. The original row remains in the
    search box. Empty segments retain their original coefficients. Invalid
    coefficient words and wrapping Horner candidates are excluded.
    """
    if len(fmt.fractional) != 3 or len(table) != 3 * (1 << fmt.segment_bits):
        raise ValueError("search requires a complete quadratic table")
    if radius < 0 or last < 1:
        raise ValueError("invalid search domain")
    xs = np.arange(1, last + 1, dtype=np.int64)
    exponents = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    normalized = xs << (2 * (fmt.n_p - exponents))
    indices = (normalized >> (2 * fmt.n_p - fmt.segment_bits)) - (1 << fmt.segment_bits)
    if np.any(indices < 0) or np.any(indices >= len(table)):
        raise ValueError("input outside the normalized table")
    order = np.argsort(indices, kind="stable")
    offsets = np.searchsorted(indices[order], np.arange(len(table) + 1))
    selected = list(table)
    choices = []
    for segment, row in enumerate(table):
        group = xs[order[offsets[segment]:offsets[segment + 1]]]
        if not len(group):
            choices.append((0, 0, 0))
            continue
        target, allowed = targets(group)
        best: tuple[int, int, int] | None = None
        best_offset = (0, 0, 0)
        candidate_table = list(table)
        for delta in product(range(-radius, radius + 1), repeat=3):
            candidate = tuple(word + change for word, change in zip(row, delta, strict=True))
            if any(word < 0 or word >= 1 << width for word, width in zip(candidate, fmt.widths, strict=True)):
                continue
            candidate_table[segment] = candidate
            try:
                observed = phase64(fmt, tuple(candidate_table), group)
            except OverflowError:
                continue
            used = np.abs((observed - target).view(np.int64)).view(np.uint64)
            at_worst = int(np.argmax(used / allowed))
            numerator, denominator = int(used[at_worst]), int(allowed[at_worst])
            margin = int(np.min((allowed - used).view(np.int64)))
            if (best is None or numerator * best[1] < best[0] * denominator
                    or (numerator * best[1] == best[0] * denominator and margin > best[2])):
                best = (numerator, denominator, margin)
                best_offset = delta
        if best is None:
            raise ValueError(f"no valid coefficient candidate for segment {segment}")
        selected[segment] = tuple(word + change for word, change in zip(row, best_offset, strict=True))
        choices.append(best_offset)
    return tuple(selected), tuple(choices)
