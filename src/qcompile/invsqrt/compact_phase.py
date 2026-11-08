"""Exact direct phase accumulation and allowed-gate phase slices."""

from fractions import Fraction
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .direct import DirectFormat, Words


def phase_accumulation(fmt: DirectFormat, table: tuple[tuple[int, ...], ...], xs: Words) -> NDArray[np.uint64]:
    """Apply the v4 quadratic as c0 phase minus column-truncated outer rows.

    This is the exact proposed recurrence, not a circuit or an accuracy claim.
    Each row contribution is phased separately after the inner Horner stage.
    """
    if len(fmt.fractional) != 3 or np.any(xs < 1) or np.any(xs >= 1 << (2 * fmt.n_p + 2)):
        raise ValueError("unsupported phase-accumulation domain")
    exponents = np.searchsorted([4**k for k in range(fmt.n_p + 1)], xs, side="right") - 1
    left = fmt.n_p - exponents
    normalized = xs << (2 * left)
    low_width = 2 * fmt.n_p - fmt.segment_bits
    indices = (normalized >> low_width) - (1 << fmt.segment_bits)
    words = np.asarray(table, dtype=np.int64)[indices]
    inner_product = np.zeros_like(xs)
    for bit in range(low_width):
        shift = fmt.fractional[1] - fmt.fractional[2] + bit - 2 * fmt.n_p
        term = words[:, 2] << shift if shift >= 0 else words[:, 2] >> -shift
        inner_product += ((normalized >> bit) & 1) * (term & ((1 << fmt.widths[1]) - 1))
    inner = words[:, 1] - inner_product
    if np.any(inner < 0):
        raise OverflowError("inner Horner stage would wrap")
    outer_product = np.zeros_like(xs)
    for bit in range(low_width):
        shift = fmt.fractional[0] - fmt.fractional[1] + bit - 2 * fmt.n_p
        term = inner << shift if shift >= 0 else inner >> -shift
        outer_product += ((normalized >> bit) & 1) * (term & ((1 << fmt.widths[0]) - 1))
    if np.any(outer_product > words[:, 0]):
        raise OverflowError("outer subtraction would wrap")
    coefficient_phase = (words[:, 0] << left).astype(np.uint64)
    row_phase = (outer_product << left).astype(np.uint64)
    return (coefficient_phase - row_phase) << np.uint64(64 - fmt.output_fractional)


def phase_product(builder: Any, selector: Any, left: Any, right: Any | None,
                  scratch: Any, exponent: Fraction) -> None:
    """Phase one selected coefficient bit or two-bit product and clean scratch."""
    if right is None:
        if len(scratch) < 1:
            raise ValueError("one scratch qubit required")
        builder.init_and(selector, left, scratch[0])
        builder.z_pow(scratch[0], exponent)
        builder.del_and(selector, left, scratch[0])
    else:
        if len(scratch) < 2:
            raise ValueError("two scratch qubits required")
        builder.init_and(left, right, scratch[0])
        builder.init_and(selector, scratch[0], scratch[1])
        builder.z_pow(scratch[1], exponent)
        builder.del_and(selector, scratch[0], scratch[1])
        builder.del_and(left, right, scratch[0])
