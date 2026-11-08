"""Two-octave minimax table and exact column-truncated integer model."""

from decimal import Decimal, localcontext
from itertools import product
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from .direct import DirectFormat, Words
from .minimax import _fit


def two_octave_table(fmt: DirectFormat) -> tuple[tuple[int, ...], ...]:
    if len(fmt.fractional) != 3 or fmt.segment_bits < 1:
        raise ValueError("two-octave table requires quadratic and positive segment bits")
    segments = 1 << fmt.segment_bits
    with localcontext(prec=64):
        mesh = [Decimal(i) / 128 for i in range(129)]
        rows = []
        for scale in (segments, segments // 2):
            for address in range(segments, 2 * segments):
                roots = [((address + x) / scale).sqrt() for x in mesh]
                coefficients = _fit(mesh, roots, 2)
                words = tuple(round(value * (-scale)**i * (1 << frac))
                              for i, (value, frac) in enumerate(zip(coefficients, fmt.fractional, strict=True)))
                if any(not 0 <= word < 1 << width for word, width in zip(words, fmt.widths, strict=True)):
                    raise ValueError("two-octave coefficient does not fit")
                rows.append(words)
    return tuple(rows)


def normalized_indices(fmt: DirectFormat, xs: Words) -> tuple[Words, Words, Words]:
    if np.any(xs < 1) or np.any(xs >= 1 << (2 * fmt.n_p + 2)):
        raise ValueError("input outside normalized register")
    exponent = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    left_shift = fmt.n_p - exponent
    normalized = xs << (2 * left_shift)
    low = 2 * fmt.n_p - fmt.segment_bits
    if low < 1:
        raise ValueError("two-octave geometry needs a spare fractional bit")
    upper = (normalized >> (2 * fmt.n_p + 1)) & 1
    segments = 1 << fmt.segment_bits
    indices = np.where(upper == 0, (normalized >> low) - segments,
                       normalized >> (low + 1))
    if np.any(indices < 0) or np.any(indices >= 2 * segments):
        raise ValueError("input outside two-octave domain")
    return normalized, left_shift, indices


def phase64(fmt: DirectFormat, table: tuple[tuple[int, ...], ...], xs: Words) -> NDArray[np.uint64]:
    if len(table) != 2 * (1 << fmt.segment_bits):
        raise ValueError("incomplete two-octave table")
    normalized, left_shift, indices = normalized_indices(fmt, xs)
    upper = (normalized >> (2 * fmt.n_p + 1)) & 1
    words = np.asarray(table, dtype=np.int64)[indices]
    value = words[:, -1]
    low_width = 2 * fmt.n_p - fmt.segment_bits
    for j in range(len(fmt.fractional) - 2, -1, -1):
        result = np.zeros_like(xs)
        for bit in range(low_width + 1):
            shift = fmt.fractional[j] - fmt.fractional[j + 1] + bit - 2 * fmt.n_p
            term = value << shift if shift >= 0 else value >> -shift
            control = (normalized >> bit) & 1
            if bit == low_width:
                control &= upper
            result += control * (term & ((1 << fmt.widths[j]) - 1))
        value = words[:, j] - result
        if np.any(value < 0):
            raise OverflowError("two-octave Horner subtraction would wrap")
    return (value << left_shift).astype(np.uint64) << np.uint64(64 - fmt.output_fractional)


def search_table(fmt: DirectFormat, table: tuple[tuple[int, ...], ...], last: int,
                 targets: Callable[[Words], tuple[NDArray[np.uint64], NDArray[np.uint64]]],
                 radius: int = 2) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    if len(table) != 2 * (1 << fmt.segment_bits) or radius < 0 or last < 1:
        raise ValueError("invalid two-octave search domain")
    xs = np.arange(1, last + 1, dtype=np.int64)
    _, _, indices = normalized_indices(fmt, xs)
    order = np.argsort(indices, kind="stable")
    boundaries = np.searchsorted(indices[order], np.arange(len(table) + 1))
    selected = list(table)
    offsets = []
    for segment, row in enumerate(table):
        group = xs[order[boundaries[segment]:boundaries[segment + 1]]]
        if not len(group):
            offsets.append((0, 0, 0))
            continue
        target, allowed = targets(group)
        best: tuple[int, int, int] | None = None
        chosen = (0, 0, 0)
        candidates = list(table)
        for delta in product(range(-radius, radius + 1), repeat=3):
            candidate = tuple(word + change for word, change in zip(row, delta, strict=True))
            if any(word < 0 or word >= 1 << width for word, width in zip(candidate, fmt.widths, strict=True)):
                continue
            candidates[segment] = candidate
            try:
                observed = phase64(fmt, tuple(candidates), group)
            except OverflowError:
                continue
            used = np.abs((observed - target).view(np.int64)).view(np.uint64)
            worst = int(np.argmax(used / allowed))
            numerator, denominator = int(used[worst]), int(allowed[worst])
            margin = int(np.min((allowed - used).view(np.int64)))
            if (best is None or numerator * best[1] < best[0] * denominator
                    or (numerator * best[1] == best[0] * denominator and margin > best[2])):
                best, chosen = (numerator, denominator, margin), delta
        if best is None:
            raise ValueError(f"no valid table candidate at segment {segment}")
        selected[segment] = tuple(word + change for word, change in zip(row, chosen, strict=True))
        offsets.append(chosen)
    return tuple(selected), tuple(offsets)
