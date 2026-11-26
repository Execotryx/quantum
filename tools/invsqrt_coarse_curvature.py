"""Screen a quadratic with shared curvature on the full Invsqrt domain."""

import argparse
from functools import partial
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from invsqrt_segmented_pilot import MAX_X, NORMALIZED_BITS, PRECISION
from qcompile.invsqrt.direct import Words
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.io import identity, sha256, write_json


FORMATS = (
    (5, 5, 15), (6, 6, 14), (6, 6, 13), (6, 6, 12), (6, 5, 14),
    (7, 7, 13), (7, 6, 10), (8, 6, 8), (8, 5, 8), (8, 5, 6), (8, 4, 8),
)


def _minimax_affine(samples: NDArray[np.float64], u: NDArray[np.float64]) -> Words:
    """Minimize the sampled residual span over integer slopes."""
    secants = np.diff(samples, axis=1) / np.diff(u)
    low = np.floor(secants.min(axis=1)).astype(np.int64)
    high = np.ceil(secants.max(axis=1)).astype(np.int64)
    while np.any(low < high):
        mid = (low + high) // 2
        residual = samples - mid[:, None] * u
        rising = (low == high) | (np.ptp(residual, axis=1) <= np.ptp(residual - u, axis=1))
        low = np.where(rising, low, mid + 1)
        high = np.where(rising, mid, high)
    residual = samples - low[:, None] * u
    intercept = np.rint((residual.min(axis=1) + residual.max(axis=1)) / 2).astype(np.int64)
    return np.stack((intercept, low), axis=1)


def fit(address_bits: int, curvature_bits: int, tail_bits: int) -> tuple[Words, Words]:
    """Fit affine terms after fixing the grouped curvature and truncated local word."""
    low = NORMALIZED_BITS - address_bits
    step, stride = 1 << low, 1 << (low - tail_bits)
    fine, coarse = 1 << address_bits, 1 << curvature_bits
    midpoints = (np.arange(fine, 4 * fine) + 0.5) / fine
    curvature_midpoints = (np.arange(coarse, 4 * coarse) + 0.5) / coarse
    scale = 1 << PRECISION
    curvature = np.rint(scale * (3 / 8) / (fine**2 * curvature_midpoints**2.5)).astype(np.int64)
    local = np.unique(np.concatenate((
        np.linspace(0, step - 1, 257, dtype=np.int64),
        np.arange(0, step, stride),
        np.arange(stride - 1, step, stride),
    ))) - step // 2
    u = local / step
    upper = (local // stride) * stride / step
    shared = curvature[np.arange(len(midpoints)) >> (address_bits - curvature_bits)]
    samples = scale * (midpoints[:, None] + u[None, :] / fine)**-0.5 - shared[:, None] * (u * upper)
    return _minimax_affine(samples, u), curvature


def phase(xs: Words, *, address_bits: int, curvature_bits: int, tail_bits: int,
          affine: Words, curvature: Words) -> NDArray[np.uint64]:
    exponents = np.searchsorted([4**k for k in range(11)], xs, side="right") - 1
    normalized = xs << (NORMALIZED_BITS - 2 * exponents)
    low = NORMALIZED_BITS - address_bits
    step = 1 << low
    local = (normalized % step) - step // 2
    address = (normalized >> low) - (1 << address_bits)
    c2 = curvature[address >> (address_bits - curvature_bits)]
    slope = affine[address, 1] + ((c2 * (local >> (low - tail_bits)) + (1 << (tail_bits - 1))) >> tail_bits)
    result = affine[address, 0] + ((slope * local + step // 2) >> low)
    return result.astype(np.uint64) << (64 - PRECISION - exponents).astype(np.uint64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = []
    for address_bits, curvature_bits, tail_bits in FORMATS:
        affine, curvature = fit(address_bits, curvature_bits, tail_bits)
        simulate = partial(phase, address_bits=address_bits, curvature_bits=curvature_bits,
                           tail_bits=tail_bits, affine=affine, curvature=curvature)
        rows.append({
            "address_bits": address_bits, "curvature_bits": curvature_bits, "tail_bits": tail_bits,
            "affine_rows": len(affine), "curvature_rows": len(curvature),
            "affine_table_sha256": identity(affine.tolist()),
            "curvature_table_sha256": identity(curvature.tolist()),
            "margins": scan_phase(simulate, MAX_X),
        })
    write_json(args.output, {
        "classification": "independent_integer_phase_model",
        "driver_sha256": sha256(Path(__file__)),
        "fractional_bits": PRECISION,
        "inputs": MAX_X,
        "lanes": rows,
    })


if __name__ == "__main__":
    main()
