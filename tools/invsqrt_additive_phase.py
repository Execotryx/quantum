"""Screen direct parity rotations and two additive tables on one legal octave."""

import argparse
from decimal import Decimal, localcontext
from math import log2, pi
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from qcompile.io import sha256, write_json


FRACTION_BITS = 20
OCTAVE_START = 1 << FRACTION_BITS
RELATIVE_TOLERANCE = 2.0**-24
INPUT_WIDTH = 22


def walsh(values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Apply the unnormalized Walsh transform in place to a copy."""
    transformed = values.copy()
    for bit in range(FRACTION_BITS):
        stage = transformed.reshape(-1, 2, 1 << bit)
        even, odd = stage[:, 0, :].copy(), stage[:, 1, :].copy()
        stage[:, 0, :] = even + odd
        stage[:, 1, :] = even - odd
    return transformed


def parity_rotation_screen() -> dict:
    """Allow a free constant and any coefficients on a fixed set of parities."""
    values = np.sqrt(OCTAVE_START / np.arange(OCTAVE_START, 2 * OCTAVE_START))
    coefficients = walsh(values) / OCTAVE_START
    order = np.argsort(-np.abs(coefficients[1:]), kind="stable") + 1
    ordered = coefficients[order]
    error = np.sqrt(np.cumsum(ordered[::-1] ** 2))[::-1]
    allowed = float(np.sqrt(np.mean(values**2)) * RELATIVE_TOLERANCE)
    minimum = int(np.flatnonzero(error <= allowed)[0])
    # Use a weaker rotation lower bound than the numerical crossing. Give
    # every point the largest possible tolerance as unused synthesis slack.
    conservative_count = 700
    if error[conservative_count] <= allowed:
        raise ValueError("The conservative lower bound is unsupported")
    max_margin_turns = RELATIVE_TOLERANCE / np.sqrt(OCTAVE_START)
    eps = pi * max_margin_turns / conservative_count
    cost = INPUT_WIDTH * conservative_count * (0.56 * log2(1 / eps) + 5.3) / 4
    truncated = []
    for count in (512, 1024, 2048):
        approximation = np.zeros_like(coefficients)
        approximation[0] = coefficients[0]
        approximation[order[:count]] = ordered[:count]
        residual_fraction = np.abs(walsh(approximation) / values - 1) / RELATIVE_TOLERANCE
        truncated.append({
            "nonconstant_terms": count,
            "worst_tolerance_fraction": float(residual_fraction.max()),
        })
    return {
        "domain": "one unwrapped phase sum with one elementary rotation per input parity",
        "numerical_rms_minimum_nonconstant_terms": minimum,
        "rms_over_limit_at_700_terms": float(error[conservative_count] / allowed),
        "conservative_fine_rotation_count": conservative_count,
        "rotation_only_cost_floor_at_input_width": float(cost),
        "truncated_series": truncated,
    }


def two_table_screen() -> dict:
    """Use a four-corner mixed difference to bound additively separated tables."""
    rows = []
    with localcontext() as context:
        context.prec = 55
        for prefix in range(FRACTION_BITS - 1):
            for upper in range(1, FRACTION_BITS - prefix):
                lower = FRACTION_BITS - prefix - upper
                hi = ((1 << upper) - 1) << lower
                lo = (1 << lower) - 1
                corners = tuple(OCTAVE_START + offset for offset in (0, hi, lo, hi + lo))
                a, b, c, d = (1 / Decimal(x).sqrt() for x in corners)
                ratio = abs(a - b - c + d) * (1 << 24) / (a + b + c + d)
                rows.append({
                    "prefix_bits": prefix,
                    "upper_bits": upper,
                    "lower_bits": lower,
                    "rectangular_table_entries": ((1 << upper) + (1 << lower)) << prefix,
                    "witness_inputs": corners,
                    "minimum_tolerance_fraction": float(ratio),
                })
    surviving = sorted((row for row in rows if row["minimum_tolerance_fraction"] <= 1),
                       key=lambda row: row["rectangular_table_entries"])
    affordable = min((row for row in rows if row["rectangular_table_entries"] <= 16384),
                     key=lambda row: row["minimum_tolerance_fraction"])
    return {
        "domain": "one contiguous upper/lower split per common prefix, with no mixed term",
        "splits": len(rows),
        "smallest_layout_not_excluded_by_four_corners": surviving[0],
        "best_four_corner_bound_with_at_most_16384_entries": affordable,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_json(args.output, {
        "classification": "structure_specific_phase_approximation_screen",
        "driver_sha256": sha256(Path(__file__)),
        "input_range_inclusive": [OCTAVE_START, 2 * OCTAVE_START - 1],
        "relative_tolerance": RELATIVE_TOLERANCE,
        "parity_rotations": parity_rotation_screen(),
        "two_additive_tables": two_table_screen(),
    })


if __name__ == "__main__":
    main()
