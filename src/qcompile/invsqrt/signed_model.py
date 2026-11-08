"""Model radix-4 Booth digits with per-row signed arithmetic truncation."""

import numpy as np
from numpy.typing import NDArray

from .direct import DirectFormat, Words


def booth_digits(values: Words, width: int) -> tuple[Words, ...]:
    """Return little-endian radix-4 digits in [-2, 2] for unsigned words."""
    if width < 1 or np.any(values < 0) or np.any(values >= 1 << width):
        raise ValueError("word outside digit width")
    digits = []
    for i in range((width + 2) // 2):
        low = (values >> (2 * i - 1)) & 1 if i else np.zeros_like(values)
        middle = (values >> (2 * i)) & 1
        high = (values >> (2 * i + 1)) & 1
        digits.append(low + middle - 2 * high)
    return tuple(digits)


def signed_phase64(fmt: DirectFormat, table: tuple[tuple[int, ...], ...], xs: Words) -> NDArray[np.uint64]:
    """Exact model of signed row arithmetic and target-width modular accumulation."""
    x_bits = 2 * fmt.n_p + 2
    if np.any(xs < 1) or np.any(xs >= 1 << x_bits):
        raise ValueError("input outside the normalized register domain")
    exponents = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    left_shift = fmt.n_p - exponents
    normalized = xs << (2 * left_shift)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    indices = (normalized >> low_width) - (1 << fmt.segment_bits)
    words = np.asarray(table, dtype=np.int64)[indices]
    digits = booth_digits(normalized & ((1 << low_width) - 1), low_width)
    value = words[:, -1]
    for j in range(len(fmt.fractional) - 2, -1, -1):
        product = np.zeros_like(xs)
        mask = (1 << fmt.widths[j]) - 1
        for i, digit in enumerate(digits):
            shift = fmt.fractional[j] - fmt.fractional[j + 1] + 2 * i - 2 * fmt.n_p
            term = digit * value
            term = term << shift if shift >= 0 else term >> -shift
            product = (product + term) & mask
        value = (words[:, j] - product) & mask
    return (value << left_shift).astype(np.uint64) << np.uint64(64 - fmt.output_fractional)
