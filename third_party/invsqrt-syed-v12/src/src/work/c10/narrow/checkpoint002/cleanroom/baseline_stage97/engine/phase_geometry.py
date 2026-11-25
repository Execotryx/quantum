# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Generalized mathematical angle fitting for cyclic or padded high phases.

This experimental module shares the selected model's mathematical arithmetic
but permits a different low-word precision and a padded high phase.  It reads
only parameters and coefficient dictionaries, never compiled gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from full_r_model import Parameters, full_r_state
from margin_lp import barrier_lp
from canonical_numeric import inverse_sqrt_integers, lowest_indices, turn_numerator


def geometry_features(p, high_mode='cyclic', high_routing_width=None):
    high_width = p.high_width if high_routing_width is None else high_routing_width
    if high_mode == 'cyclic':
        high = [('high_base', i) for i in range(high_width)]
        high += [('high_overflow', i) for i in range(p.n_p)]
    elif high_mode == 'complement':
        high_fraction = p.phase_fraction_bits-p.high_shift
        high = [('high_complement_base', i) for i in range(high_width)
                if i-high_fraction+high_width*sum(j % high_width == i for j in range(p.n_p)) < -3]
        high += [('high_complement_overflow', i) for i in range(p.n_p)]
    elif high_mode == 'padded':
        high_fraction = p.phase_fraction_bits-p.high_shift
        high = [('high_padded', i) for i in range(high_fraction-3)]
    else:
        raise ValueError('Unknown high-phase geometry.')
    low = [('low_base', i) for i in range(p.low_width)]
    low += [('low_overflow', i) for i in range(p.n_p)]
    return high+low


def geometry_data(model, high_mode='cyclic', chunk_size=262144, high_routing_width=None):
    p = Parameters(**model['parameters'])
    high_width = p.high_width if high_routing_width is None else high_routing_width
    if high_width < p.high_width:
        raise ValueError('The routing word is shorter than the coefficient word.')
    n = p.max_x
    high = np.empty(n, dtype=np.uint32)
    low = np.empty(n, dtype=np.uint32)
    ks = np.empty(n, dtype=np.uint8)
    error = np.empty(n, dtype=float)
    tolerance = np.empty(n, dtype=float)
    for first in range(1, n+1, chunk_size):
        xs = np.arange(first, min(first+chunk_size, n+1), dtype=np.int64)
        state = full_r_state(xs, model)
        sl = slice(first-1, first-1+len(xs))
        hv = state['high']-1
        lv = state['low']+(1 << p.high_shift)
        k = state['k']
        if high_mode != 'padded':
            hs = k % high_width
            high[sl] = ((hv << hs) | (hv >> (high_width-hs))) & ((1 << high_width)-1)
        else:
            high[sl] = hv << k
        low[sl] = ((lv << k) | (lv >> (p.low_width-k))) & ((1 << p.low_width)-1)
        ks[sl] = k
        target = inverse_sqrt_integers(xs)
        actual = np.ldexp(state['y'].astype(float), k-p.phase_fraction_bits)
        error[sl] = (actual-target)*1e12
        tolerance[sl] = np.ldexp(target, -p.precision_bits)*1e12
        high_scaled = high[sl].astype(np.int64)
        low_scaled = low[sl].astype(np.int64)
        for j in range(p.n_p):
            if high_mode != 'padded':
                high_scaled += ((1 << high_width)-1)*((high[sl] >> (j % high_width)) & 1).astype(np.int64)*(k > j)*(1 << j)
            low_scaled += ((1 << p.low_width)-1)*((low[sl] >> j) & 1).astype(np.int64)*(k > j)*(1 << j)
        if not np.array_equal(high_scaled, hv << k) or not np.array_equal(low_scaled, lv << k):
            raise AssertionError('Phase extraction identity failed.')
        if high_mode == 'complement':
            complemented = high[sl].astype(np.int64)
            for j in range(p.n_p):
                wire_bit = ((high[sl] >> (j % high_width)) & 1).astype(np.int64)
                complemented += ((1 << high_width)-1)*wire_bit*(1 << j)
                complemented -= ((1 << high_width)-1)*wire_bit*(k <= j)*(1 << j)
            if not np.array_equal(complemented, hv << k):
                raise AssertionError('Complementary phase identity failed.')
    return high, low, ks, error, tolerance


def column(high, low, ks, name, bit, high_width):
    if name == 'high_padded':
        return (high >> bit) & 1
    if name.startswith('high'):
        result = (high >> (bit % high_width)) & 1
    else:
        result = (low >> bit) & 1
    if name == 'high_complement_overflow':
        return result*(ks <= bit)
    return result*(ks > bit) if name.endswith('overflow') else result


def correction(high, low, ks, weights, features, high_width):
    result = np.zeros(len(high), dtype=float)
    for (name, bit), value in zip(features, weights):
        if value:
            result += value*column(high, low, ks, name, bit, high_width)
    return result


def fit_geometry_angles(model, *, high_mode='cyclic', angle_bound=10.0,
                         maximum_exchanges=30, batch=128, verbose=True,
                         high_routing_width=None):
    p = Parameters(**model['parameters'])
    high_width = p.high_width if high_routing_width is None else high_routing_width
    features = geometry_features(p, high_mode, high_width)
    high, low, ks, error, tolerance = geometry_data(model, high_mode, high_routing_width=high_width)
    original = tolerance-np.abs(error)
    active = set(map(int, lowest_indices(original, batch)))
    active.update(i*(len(error)-1)//255 for i in range(256))
    point = np.zeros(len(features)+1)
    point[-1] = float(original.min())-1
    best_margin, best = float(original.min()), np.zeros(len(features))
    history = []
    for exchange in range(maximum_exchanges):
        indices = np.array(sorted(active), dtype=np.int64)
        h, l, k = high[indices], low[indices], ks[indices]
        matrix = np.column_stack([column(h, l, k, name, bit, high_width).astype(float)
                                  for name, bit in features])
        point, meta = barrier_lp(matrix, error[indices], tolerance[indices],
                                 angle_bound=angle_bound, initial=point)
        margins = tolerance-np.abs(error+correction(high, low, ks, point[:-1], features, high_width))
        margin = float(margins.min())
        if margin > best_margin:
            best_margin, best = margin, point[:-1].copy()
        record = dict(exchange=exchange, active_inputs=len(active),
                      lp_margin_units=float(point[-1]), all_x_margin_units=margin,
                      worst_x=int(margins.argmin())+1, **meta)
        history.append(record)
        if verbose:
            print(record, flush=True)
        if float(point[-1])-margin < 2e-5:
            break
        before = len(active)
        active.update(map(int, lowest_indices(margins, batch)))
        if len(active) == before:
            break
    numerators = [turn_numerator(value) for value in best]
    frozen = np.array([v/2**64*1e12 for v in numerators])
    final_error = error+correction(high, low, ks, frozen, features, high_width)
    margins = tolerance-np.abs(final_error)
    result = dict(status='PASS' if float(margins.min()) > 0 else 'FAIL',
                  inputs_checked=len(error), phase_features=len(features),
                  high_mode=high_mode, high_value='H-1',
                  low_value=f'L+2**{p.high_shift}', high_width=high_width,
                  high_coefficient_width=p.high_width, high_padding_bits=high_width-p.high_width,
                  low_width=p.low_width, maximum_shift=p.n_p,
                  high_fraction_bits=p.phase_fraction_bits-p.high_shift,
                  low_fraction_bits=p.phase_fraction_bits,
                  angle_bound_turns=angle_bound*1e-12, turn_denominator=2**64,
                  fixed_T_gates=1 if high_mode in ('padded', 'complement') else 0,
                  features=[dict(kind=name, bit=bit, nudge_turn_numerator=v)
                            for (name, bit), v in zip(features, numerators)],
                  original_min_remaining_tolerance_turns=float(original.min())*1e-12,
                  min_remaining_tolerance_turns=float(margins.min())*1e-12,
                  worst_margin_x=int(margins.argmin())+1,
                  worst_error_over_tolerance=float((np.abs(final_error)/tolerance).max()),
                  worst_error_x=int((np.abs(final_error)/tolerance).argmax())+1,
                  history=history)
    if high_mode == 'complement':
        fixed = []
        for bit in range(high_width):
            wraps = sum(j % high_width == bit for j in range(p.n_p))
            exponent = bit-result['high_fraction_bits']+high_width*wraps
            if -3 <= exponent < 0:
                fixed.append(dict(bit=bit, turn_numerator=1 << (64+exponent), turn_denominator=1 << 64))
        result['fixed_high_angles'] = fixed
        result['fixed_T_gates'] = sum(row['turn_numerator'] == 1 << 61 for row in fixed)
    if verbose:
        print(json.dumps({key: result[key] for key in ('status', 'phase_features', 'min_remaining_tolerance_turns', 'worst_error_over_tolerance')}, indent=2))
    return result


