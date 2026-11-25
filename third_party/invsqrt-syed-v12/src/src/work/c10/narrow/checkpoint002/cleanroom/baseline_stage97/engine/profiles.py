# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Formatting and resource summaries for freshly generated numerical profiles.

The selected release derives its model in balanced_alias_profiles and its
phase transformation in rare_phase_pass. This module accepts their in-memory
results; it contains no saved coefficient/angle table or profile catalogue.
"""
from __future__ import annotations

import json
import math

def canonical_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def phase_angle_table(angles):
    """Exact numerator/2**64 turn angles, in physical phase-gate order.

    The Z_POW exponent is twice the turn angle.  ``nudge_turn_numerator``
    is retained so older callers can continue adding the same correction to
    their analytic baseline angle.
    """
    records = []
    high_fraction = angles.get('high_fraction_bits', 18)
    low_fraction = angles.get('low_fraction_bits', 37)
    high_width = angles.get('high_width', 8)
    low_width = angles.get('low_width', 20)
    for feature in angles['features']:
        kind, bit = feature['kind'], feature['bit']
        if kind in ('high_base', 'high_padded'):
            base = 1 << (64-high_fraction+bit)
        elif kind == 'high_overflow':
            base = ((1 << high_width)-1) << (64-high_fraction+bit)
        elif kind == 'high_complement_base':
            base = 1 << (64-high_fraction+bit)
            base += sum(((1 << high_width)-1) << (64-high_fraction+j)
                        for j in range(angles['maximum_shift']) if j % high_width == bit)
        elif kind == 'high_complement_overflow':
            base = -((1 << high_width)-1) << (64-high_fraction+bit)
        elif kind == 'low_base':
            base = 1 << (64-low_fraction+bit)
        elif kind == 'low_overflow':
            base = ((1 << low_width)-1) << (64-low_fraction+bit)
        else:
            raise ValueError(f'Unknown cyclic phase feature {kind}.')
        records.append(dict(feature, turn_numerator=base+feature['nudge_turn_numerator'],
                            turn_denominator=1 << 64))
    return records


def profile_resources(model, angles):
    coefficients = model['coefficients']
    maximum_c = max(row['c'] for row in coefficients)
    bound = maximum_c//2
    residual_bits = model['parameters']['residual_bits']
    first = min(i for i in range(residual_bits)
                if (maximum_c+(1 << (residual_bits-i))) >> (residual_bits+1-i))
    n = angles['phase_features']
    margin = angles['min_remaining_tolerance_turns']
    epsilon = math.pi*margin/n
    t_count = n*(0.56*math.log2(1/epsilon)+5.3)+angles.get('fixed_T_gates', 0)
    return dict(
        curvature_max=maximum_c, curvature_signed_bound=bound,
        curvature_low_window_width=bound.bit_length()+1,
        first_nonzero_curvature_row=first, nonzero_curvature_rows=residual_bits-first,
        derivative_logical_width=model['r_full_width'],
        derivative_storage_width=model['r_storage_width'],
        output_width=model['low_width'],
        output_physical_width=model.get('output_physical_width', model['low_width']),
        high_phase_coefficient_width=model['high_width'],
        high_phase_routing_width=angles.get('high_width', model['high_width']),
        high_phase_padding_qubits=angles.get('high_width', model['high_width'])-model['high_width'],
        rotations=n, predicted_synthesis_epsilon=epsilon,
        predicted_synthesis_T=t_count,
        predicted_synthesis_Toffoli_equivalents=t_count/4,
    )

