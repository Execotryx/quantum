# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Mathematical definitions used by the from-source coefficient compiler.

This module has no circuit or coefficient-file inputs.  The small integer
search uses analytic derivatives as its starting point and certifies the
actual rounded partial-product arithmetic on every reachable mantissa.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from canonical_numeric import dyadic_inverse_sqrt, taylor_seed


@dataclass(frozen=True)
class Parameters:
    residual_bits: int = 14
    output_fraction_bits: int = 27
    derivative_fraction_bits: int = 25
    segment_bits: int = 7
    n_p: int = 10
    precision_bits: int = 24
    rounding: str = 'nearest'
    address_sharing: bool = True

    def __post_init__(self):
        if self.residual_bits+self.segment_bits != self.width-1:
            raise ValueError('The mantissa and segment widths do not match n_p.')
        if min(self.n_p, self.segment_bits, self.residual_bits) < 1:
            raise ValueError('Register widths must be positive.')
        if self.rounding not in ('nearest', 'floor'):
            raise ValueError('Unknown partial-row rounding rule.')
        if self.high_shift < 1:
            raise ValueError('The output precision is too small.')

    @property
    def width(self):
        return 2*self.n_p+2

    @property
    def max_x(self):
        return 3*(2**self.n_p-2)**2

    @property
    def num_segments(self):
        return 2 << self.segment_bits

    @property
    def phase_fraction_bits(self):
        return self.output_fraction_bits+self.n_p+1

    @property
    def high_shift(self):
        return self.output_fraction_bits-self.segment_bits

    @property
    def low_width(self):
        return self.high_shift+1

    @property
    def high_width(self):
        return self.segment_bits+1

    @property
    def first_row_fraction_bits(self):
        return self.residual_bits+1

    @property
    def second_row_fraction_bits(self):
        return self.residual_bits+1-self.output_fraction_bits+self.derivative_fraction_bits


def rounded_shift(value, shift, rounding='nearest'):
    """Integer floor(value/2**shift+1/2), with explicit tie behavior."""
    if shift <= 0:
        return value << -shift
    result = value >> shift
    if rounding == 'nearest':
        result = result+((value >> (shift-1)) & 1)
    return result


def signed_row_sum(operand, q, frac_bits, bits=14, rounding='nearest'):
    result = np.zeros_like(q, dtype=np.int64)
    for i in range(bits):
        term = rounded_shift(operand, frac_bits-i, rounding)
        result += (((q >> i) & 1)*2-1)*term
    return result


def coefficient_seed(address, p):
    """Taylor coefficients with cubic and quartic Chebyshev corrections.

    For t in [-1/2,1/2], T3(2t) gives the cubic's linear correction
    3t/16, and T4(2t) gives the quartic's quadratic correction t*t/4-1/128.
    The exhaustive integer search, rather than this seed, selects the table.
    """
    return taylor_seed(address, p)


def segment_inputs(address, p, *, reachable=True):
    e, j = divmod(address, 1 << p.segment_bits)
    d = 1 << p.residual_bits
    q = np.arange(0, d, 2 if e == 0 else 1, dtype=np.int64)
    if not reachable:
        return q
    normalized = ((1 << p.segment_bits)+j)*(d >> (1-e))+(q >> (1-e))
    candidate = normalized.copy()
    valid = np.ones_like(q, dtype=bool)
    for _ in range(p.n_p+1):
        excessive = candidate > p.max_x
        if not excessive.any():
            break
        valid &= ~excessive | ((candidate & 3) == 0)
        candidate = np.where(excessive, candidate >> 2, candidate)
    valid &= (candidate >= 1) & (candidate <= p.max_x)
    return q[valid]


def target_values(address, q, p):
    e, j = divmod(address, 1 << p.segment_bits)
    numerator = (((1 << p.segment_bits)+j) << p.residual_bits)+q
    return dyadic_inverse_sqrt(numerator, p.residual_bits+p.segment_bits+2-e)


def _anchor_candidates(mid, correction_min, correction_max, p,
                       *, residue=0, modulus=1):
    step = 1 << p.high_shift
    half = 1 << (p.low_width-1)
    max_h = (1 << p.high_width)-1
    center = math.floor(mid/step)
    candidates = set()
    for h in range(max(0, center-2), min(max_h, center+3)+1):
        a_min = h*step-half+correction_max
        a_max = h*step+half-1+correction_min
        if a_min > a_max:
            continue
        first = a_min+(residue-a_min) % modulus
        last = a_max-(a_max-residue) % modulus
        if first > last:
            continue
        below = math.floor((mid-residue)/modulus)*modulus+residue
        for a in (below, below+modulus):
            a = min(max(a, first), last)
            if -half <= a-h*step < half:
                candidates.add((int(a), int(h)))
    return sorted(candidates)
