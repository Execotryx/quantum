# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Cost-aware probe for one additional diagonal residual-parity correction.

The coefficient table is unchanged.  A parity of unmodified upper residual
bits costs Clifford gates around one rotation.  This pass accepts it only
when the exhaustive margin gives a lower total rotation-synthesis charge.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from full_r_model import Parameters
from phase_geometry import geometry_data, column, correction
from margin_lp import barrier_lp


def synthesis_charge(margin, count, fixed_t=1):
    if margin <= 0:
        return float('inf')
    epsilon = math.pi*margin/count
    return (count*(0.56*math.log2(1/epsilon)+5.3)+fixed_t)/4


def fit_residual_phase_corrections(model, baseline, masks, *, verbose=True):
    p = Parameters(**model['parameters'])
    high_width = baseline.get('high_width', p.high_width)
    features = [(r['kind'], r['bit']) for r in baseline['features']]
    high, low, ks, error, tolerance = geometry_data(model, baseline.get('high_mode', 'cyclic'), high_routing_width=high_width)
    xs = np.arange(1, len(ks)+1, dtype=np.int64)
    normalized = xs << (2*ks.astype(np.int64))
    exponent = (normalized >> (p.width-1)) & 1
    q = ((normalized << (1-exponent)) & ((1 << p.residual_bits)-1)).astype(np.uint16)
    del normalized, exponent, xs
    initial_weights = np.array([r['nudge_turn_numerator']/2**64*1e12 for r in baseline['features']])
    initial_margin = tolerance-np.abs(error+correction(high, low, ks, initial_weights, features, high_width))
    baseline_cost = synthesis_charge(float(initial_margin.min())*1e-12, len(features), baseline.get('fixed_T_gates', 0))
    results = []
    for mask in masks:
        if mask == 0:
            extra = np.ones(len(q), dtype=np.uint8)
        else:
            extra = np.zeros(len(q), dtype=np.uint8)
            for bit in range(p.residual_bits):
                if mask >> bit & 1:
                    extra ^= ((q >> bit) & 1).astype(np.uint8)
        active = set(map(int, np.argpartition(initial_margin, 128)[:128]))
        active.update(map(int, np.linspace(0, len(q)-1, 256, dtype=np.int64)))
        point = np.concatenate((initial_weights, [0, float(initial_margin.min())-1]))
        best_margin, best = float(initial_margin.min()), np.concatenate((initial_weights, [0]))
        history = []
        for exchange in range(25):
            indices = np.array(sorted(active), dtype=np.int64)
            h, l, k = high[indices], low[indices], ks[indices]
            matrix = np.column_stack([column(h, l, k, name, bit, high_width).astype(float)
                                      for name, bit in features]+[extra[indices].astype(float)])
            point, solver = barrier_lp(matrix, error[indices], tolerance[indices],
                                       angle_bound=100, initial=point)
            corrected = (error+correction(high, low, ks, point[:-2], features, high_width)+
                         point[-2]*extra)
            margins = tolerance-np.abs(corrected)
            minimum = float(margins.min())
            if minimum > best_margin:
                best_margin, best = minimum, point[:-1].copy()
            history.append(dict(exchange=exchange, margin=minimum, lp_margin=float(point[-1]), **solver))
            if float(point[-1])-minimum < 2e-5:
                break
            old_size = len(active)
            active.update(map(int, np.argpartition(margins, 128)[:128]))
            if len(active) == old_size:
                break
        numerators = [int(round(v*1e-12*2**64)) for v in best]
        frozen = np.array([v/2**64*1e12 for v in numerators])
        final_error = error+correction(high, low, ks, frozen[:-1], features, high_width)+frozen[-1]*extra
        margins = tolerance-np.abs(final_error)
        final_margin = float(margins.min())*1e-12
        count = len(features)+int(numerators[-1] != 0)
        cost = synthesis_charge(final_margin, count, baseline.get('fixed_T_gates', 0))
        result = copy.deepcopy(baseline)
        for record, numerator in zip(result['features'], numerators[:-1]):
            record['nudge_turn_numerator'] = numerator
        result['extra_phase_features'] = [dict(kind='global' if mask == 0 else 'residual_parity',
                                                residual_mask=mask,
                                                turn_numerator=numerators[-1], turn_denominator=1 << 64)]
        result.update(phase_features=count, min_remaining_tolerance_turns=final_margin,
                      worst_error_over_tolerance=float((np.abs(final_error)/tolerance).max()),
                      worst_margin_x=int(margins.argmin())+1,
                      worst_error_x=int((np.abs(final_error)/tolerance).argmax())+1,
                      history=history, baseline_synthesis_equivalents=baseline_cost,
                      synthesis_equivalents=cost, synthesis_saving=baseline_cost-cost,
                      status='PASS' if final_margin > 0 else 'FAIL')
        results.append(result)
        if verbose:
            print(dict(mask=mask, margin=final_margin, charge=cost,
                       saving=baseline_cost-cost, angle_numerator=numerators[-1]), flush=True)
    return results


