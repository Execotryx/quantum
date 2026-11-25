# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Canonicalize numerically inactive phase splits and freeze a stable grid.

The high-base/complement-overflow pair has identical support whenever k<=i.
Moving the base nudge to that overflow preserves its sum on those inputs and
changes only the small-input tail.  This is an approximation compiler pass,
not an exact Boolean identity; acceptance requires the full input certificate.
"""
from __future__ import annotations

import copy
import numpy as np

from balanced_model import geometry_uses_balanced_state
from phase_geometry import geometry_data, column, correction
from residual_phase_fit import synthesis_charge


def rounded_multiple(value, step):
    """Integer-only round-to-nearest, ties-to-even, including negative values."""
    quotient, remainder = divmod(int(value), int(step))
    if 2*remainder > step or (2*remainder == step and quotient & 1):
        quotient += 1
    return quotient*step


def canonicalize_nudges(model, baseline, *, fraction_bits=54):
    if baseline.get('rare_phase_pass'):
        raise ValueError('Canonicalize the original phase basis before a rare-feature pass.')
    if baseline['high_mode'] != 'complement' or baseline['high_width'] != 8:
        raise ValueError('The canonical split is specialized to the eight-bit complemented high phase.')
    if not 40 <= fraction_bits <= 64:
        raise ValueError('Unsupported angle grid precision.')
    result = copy.deepcopy(baseline)
    by_key = {(r['kind'], r['bit']): r for r in result['features']}
    for bit in range(2, 7):
        base = by_key['high_complement_base', bit]
        overflow = by_key['high_complement_overflow', bit]
        overflow['nudge_turn_numerator'] += base['nudge_turn_numerator']
        base['nudge_turn_numerator'] = 0
    step = 1 << (64-fraction_bits)
    for row in result['features']:
        row['nudge_turn_numerator'] = rounded_multiple(row['nudge_turn_numerator'], step)
    with geometry_uses_balanced_state():
        high, low, k, error, tolerance = geometry_data(
            model, result['high_mode'], high_routing_width=result['high_width'])
    features = [(r['kind'], r['bit']) for r in result['features']]
    weights = np.array([r['nudge_turn_numerator']/2**64*1e12 for r in result['features']])
    final = error+correction(high, low, k, weights, features, result['high_width'])
    margin = tolerance-np.abs(final)
    minimum = float(margin.min())*1e-12
    result.pop('history', None)
    result.update(status='PASS' if minimum > 0 else 'FAIL', inputs_checked=len(k),
                  min_remaining_tolerance_turns=minimum,
                  worst_margin_x=int(margin.argmin())+1,
                  worst_error_over_tolerance=float((np.abs(final)/tolerance).max()),
                  worst_error_x=int((np.abs(final)/tolerance).argmax())+1,
                  synthesis_equivalents=synthesis_charge(minimum, result['phase_features'],
                                                         result.get('fixed_T_gates', 0)),
                  canonical_nudge_pass=dict(
                      schema='paired-high-nudge-transfer-v1',
                      transferred_high_base_bits=list(range(2, 7)),
                      grid_fraction_bits=fraction_bits,
                      rounding='integer round-to-nearest, ties-to-even',
                      coefficient_model_unchanged=True,
                      proof='exhaustive numerical certificate on every allowed input'))
    if result['status'] != 'PASS':
        raise ArithmeticError('The canonical phase-nudge grid has no positive error margin.')
    return result
