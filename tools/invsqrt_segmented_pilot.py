"""Screen two centered-polynomial inverse-square-root schedules numerically."""

import argparse
from functools import partial
from fractions import Fraction
from math import isqrt
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from qcompile.invsqrt.direct import Words
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.io import identity, write_json

FORMATS = ((4, 4), (5, 3))
PRECISION = 29
NORMALIZED_BITS = 20
MAX_X = 3 * (2**10 - 2)**2


def centered_table(address_bits: int, degree: int) -> Words:
    scale = 1 << address_bits
    rows = []
    for address in range(scale, 4 * scale):
        midpoint = Fraction(2 * address + 1, 2 * scale)
        coefficient = Fraction(1 << PRECISION)
        row = []
        for power in range(degree + 1):
            if power:
                coefficient *= Fraction(2 * power - 1, 2 * power) / (scale * midpoint)
            squared = coefficient**2 / midpoint
            rounded = isqrt(squared.numerator // squared.denominator)
            half = Fraction((2 * rounded + 1)**2, 4)
            rounded += int(squared > half or (squared == half and rounded % 2 == 1))
            row.append((-1)**power * rounded)
        rows.append(row)
    return np.asarray(rows, dtype=np.int64)


def phase(xs: Words, *, address_bits: int, table: Words) -> NDArray[np.uint64]:
    exponents = np.searchsorted([4**k for k in range(11)], xs, side="right") - 1
    normalized = xs << (NORMALIZED_BITS - 2 * exponents)
    low_bits = NORMALIZED_BITS - address_bits
    step = 1 << low_bits
    local = (normalized % step) - step // 2
    words = table[(normalized >> low_bits) - (1 << address_bits)]
    value = words[:, -1]
    for j in range(table.shape[1] - 2, -1, -1):
        value = words[:, j] + ((value * local + step // 2) >> low_bits)
    return value.astype(np.uint64) << (64 - PRECISION - exponents).astype(np.uint64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = []
    for address_bits, degree in FORMATS:
        table = centered_table(address_bits, degree)
        margins = scan_phase(partial(phase, address_bits=address_bits, table=table), MAX_X)
        rows.append({
            "address_bits": address_bits, "degree": degree, "intervals": len(table),
            "table_sha256": identity(table.tolist()),
            "coefficient_magnitude_bits": [int(value).bit_length() for value in np.abs(table).max(axis=0)],
            "margins": margins,
        })
    write_json(args.output, {
        "classification": "integer_phase_model_only",
        "fractional_bits": PRECISION, "lanes": rows,
        "input_bits": 22, "preserved_input_plus_separate_accumulator_qubits": 22 + PRECISION,
        "scope": "Quantized Horner arithmetic with exact normalization and dyadic phase conversion. "
                 "No reversible implementation or charge for coefficient access, rotations or cleanup.",
    })


if __name__ == "__main__":
    main()
