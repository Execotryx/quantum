# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Canonical arithmetic for values that select circuit coefficients or angles.

The only inexact arithmetic here is explicit IEEE-754 binary64 arithmetic.
Square-root samples are rounded with integer comparisons, Taylor seeds use a
fixed Decimal context, and every reduction/linear solve has a declared order.
No BLAS, LAPACK, host logarithm, coefficient cache or compiled circuit is used.
NumPy supplies elementwise arithmetic and storage, not numerical decisions.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import isqrt, ldexp

import numpy as np


def inverse_sqrt_integer(value):
    """Correctly round 1/sqrt(value) to normal binary64, ties to even.

    The benchmark's positive integer inputs are small enough that neither
    overflow nor subnormal arithmetic is involved.  The midpoint comparison
    is exact even when the real answer is exceptionally close to a midpoint.
    """
    value = int(value)
    if value < 1:
        raise ValueError('An inverse-square-root input must be positive.')
    exponent = ((value-1).bit_length()+1)//2
    shift = 52+exponent
    squared_scale = 1 << (2*shift)
    significand = isqrt(squared_scale//value)
    comparison = value*(2*significand+1)**2-4*squared_scale
    if comparison < 0 or (comparison == 0 and significand & 1):
        significand += 1
    return ldexp(float(significand), -shift)


def inverse_sqrt_integers(values):
    """Elementwise canonical inverse square roots in the input array's order."""
    values = np.asarray(values)
    result = np.fromiter((inverse_sqrt_integer(value) for value in values.flat),
                         dtype=np.float64, count=values.size)
    return result.reshape(values.shape)


def dyadic_inverse_sqrt(numerators, denominator_exponent):
    """Canonical 1/sqrt(numerators/2**denominator_exponent)."""
    exponent = int(denominator_exponent)
    if exponent < 0:
        raise ValueError('This coefficient fitter requires a dyadic denominator.')
    # An odd exponent is made even by doubling the radicand.  The final
    # power-of-two scaling is exact, so the sole rounding is the integer one.
    values = np.asarray(numerators, dtype=np.int64) << (exponent & 1)
    return np.ldexp(inverse_sqrt_integers(values), (exponent+1)//2)


def taylor_seed(address, parameters):
    """Derive corrected Taylor seeds using a fixed, portable Decimal context."""
    p = parameters
    exponent, index = divmod(int(address), 1 << p.segment_bits)
    residual_scale = 1 << p.residual_bits
    with localcontext() as context:
        context.prec = 80
        context.rounding = ROUND_HALF_EVEN
        midpoint = (Decimal(((1 << p.segment_bits)+index)*(2*residual_scale)
                            +residual_scale-1)/Decimal(2*residual_scale))
        root = (Decimal(2)**(p.segment_bits+2-exponent)/midpoint).sqrt()
        intercept = root-35*root/(16384*midpoint**4)
        derivative = root/(2*midpoint)+15*root/(256*midpoint**3)
        curvature = 3*root/(8*midpoint**2)+35*root/(512*midpoint**4)
        return (float(intercept*(1 << p.output_fraction_bits)),
                float(derivative*(1 << p.derivative_fraction_bits)),
                float(curvature*(1 << p.derivative_fraction_bits)))


def ordered_sum(values, axis=0):
    """Binary64 reduction using an explicit adjacent-pair tree.

    Each tree level is a separate elementwise addition.  This avoids both
    CPU-dependent SIMD reduction trees and fused multiply/add instructions.
    """
    work = np.moveaxis(np.asarray(values, dtype=np.float64), axis, 0)
    if not len(work):
        return np.zeros(work.shape[1:], dtype=np.float64)
    while len(work) > 1:
        count = len(work)//2
        combined = work[:2*count:2]+work[1:2*count:2]
        if len(work) & 1:
            combined = np.concatenate((combined, work[-1:]), axis=0)
        work = combined
    return work[0]


def matvec(matrix, vector):
    return ordered_sum(np.asarray(matrix)*np.asarray(vector), axis=1)


def transpose_matvec(matrix, vector):
    return ordered_sum(np.asarray(matrix)*np.asarray(vector)[:, None], axis=0)


def dot(left, right):
    return float(ordered_sum(np.asarray(left)*np.asarray(right)))


def gram(matrix):
    """Gram matrix with the same pair tree for each matrix entry."""
    matrix = np.asarray(matrix, dtype=np.float64)
    # Columns are processed separately to bound temporary storage independently
    # of the number of phase features.  No NumPy sum/matmul reduction is used.
    result = np.empty((matrix.shape[1], matrix.shape[1]), dtype=np.float64)
    for column in range(matrix.shape[1]):
        result[column] = ordered_sum(matrix*matrix[:, column, None], axis=0)
    return result


def solve(matrix, vector):
    """Deterministic partial-pivot Gaussian solve with first-index tie breaks."""
    matrix = np.array(matrix, dtype=np.float64, copy=True)
    vector = np.array(vector, dtype=np.float64, copy=True)
    dimension = len(vector)
    if matrix.shape != (dimension, dimension):
        raise ValueError('The canonical solver requires a square matrix.')
    for column in range(dimension):
        pivot = column+int(np.argmax(np.abs(matrix[column:, column])))
        if matrix[pivot, column] == 0:
            raise ArithmeticError('Canonical regularized LP system is singular.')
        if pivot != column:
            matrix[[column, pivot]] = matrix[[pivot, column]]
            vector[[column, pivot]] = vector[[pivot, column]]
        factors = matrix[column+1:, column]/matrix[column, column]
        products = factors[:, None]*matrix[column, column+1:]
        matrix[column+1:, column+1:] -= products
        vector[column+1:] -= factors*vector[column]
        matrix[column+1:, column] = 0
    result = np.empty(dimension, dtype=np.float64)
    for row in range(dimension-1, -1, -1):
        remaining = dot(matrix[row, row+1:], result[row+1:])
        result[row] = (vector[row]-remaining)/matrix[row, row]
    if not np.all(np.isfinite(result)):
        raise ArithmeticError('Canonical LP solve produced a nonfinite direction.')
    return result


with localcontext() as _context:
    _context.prec = 80
    _context.rounding = ROUND_HALF_EVEN
    _LOG_TWO = float(Decimal(2).ln())


def logarithm(values):
    """Deterministic binary64 natural log for barrier line-search decisions.

    For m in [1,2), log(m)=2*atanh((m-1)/(m+1)).  Twenty-two terms bound the
    exact-series tail by 2/(45*3**45)/(1-1/9), below binary64 roundoff.  A
    Decimal-derived ln(2) handles the exact frexp exponent.  This routine's
    purpose is a fixed numerical objective; no log value is a circuit angle.
    """
    values = np.asarray(values, dtype=np.float64)
    if np.any(values <= 0):
        raise ValueError('Canonical logarithm requires positive arguments.')
    mantissa, exponent = np.frexp(values)
    mantissa = mantissa*2
    exponent = exponent-1
    ratio = (mantissa-1)/(mantissa+1)
    square = ratio*ratio
    polynomial = np.full(values.shape, 1/43, dtype=np.float64)
    for denominator in range(41, 0, -2):
        polynomial = 1/denominator+square*polynomial
    return 2*ratio*polynomial+exponent*_LOG_TWO


def lowest_indices(values, count):
    """Select the lowest values, breaking exact ties by original input index."""
    values = np.asarray(values)
    count = min(int(count), len(values))
    if count <= 0:
        return np.empty(0, dtype=np.int64)
    cutoff = np.partition(values, count-1)[count-1]
    below = np.flatnonzero(values < cutoff)
    equal = np.flatnonzero(values == cutoff)
    return np.concatenate((below, equal[:count-len(below)]))


def turn_numerator(value, *, fractional_bits=64):
    """Round an LP value in 1e-12-turn units to a dyadic, exactly and evenly."""
    return round(Fraction.from_float(float(value))*(1 << fractional_bits)/10**12)
