# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Refit integer coefficients against already computed frozen phase angles.

This is a numerical-design pass, not a semantics-preserving gate rewrite.
Every proposed coefficient is evaluated on all original inputs in its segment.
The quantum arithmetic and its all-outcome cleanup identities remain unchanged.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from full_r_model import (Parameters, coefficient_seed, signed_row_sum,
                          _anchor_candidates, full_r_state,
                          full_r_table_words, validate_full_r)


def nudge_tables(angles):
    weights = np.array([r['nudge_turn_numerator']/2**64*1e12 for r in angles['features']])
    low_width = angles.get('low_width', 20)
    high_width = angles.get('high_width', 8)
    maximum_shift = angles.get('maximum_shift', 10)
    high_mode = angles.get('high_mode', 'cyclic')
    high_weights = np.empty((maximum_shift+1, high_width))
    low_weights = np.empty((maximum_shift+1, low_width))
    high_features = sum(row['kind'].startswith('high') for row in angles['features'])
    feature_weights = {(row['kind'], row['bit']): value
                       for row, value in zip(angles['features'], weights)}
    for k in range(maximum_shift+1):
        for bit in range(high_width):
            if high_mode == 'padded':
                position = bit+k
                high_weights[k, bit] = weights[position] if position < high_features else 0
            elif high_mode == 'complement':
                position = (bit+k) % high_width
                high_weights[k, bit] = feature_weights.get(('high_complement_base', position), 0)
                high_weights[k, bit] += sum(feature_weights['high_complement_overflow', j]
                                           for j in range(k, maximum_shift) if j % high_width == position)
            else:
                position = (bit+k) % high_width
                high_weights[k, bit] = weights[position]+sum(weights[high_width+j] for j in range(k) if j % high_width == position)
        for bit in range(low_width):
            position = (bit+k) % low_width
            low_weights[k, bit] = weights[high_features+position]+(weights[high_features+low_width+position] if position < k else 0)
    bits10 = ((np.arange(1024)[:, None] >> np.arange(10)) & 1).astype(float)
    bits_high = ((np.arange(1 << high_width)[:, None] >> np.arange(high_width)) & 1).astype(float)
    upper_width = low_width-10
    bits_upper = ((np.arange(1 << upper_width)[:, None] >> np.arange(upper_width)) & 1).astype(float)
    return (high_weights @ bits_high.T,
            low_weights[:, :10] @ bits10.T,
            low_weights[:, 10:] @ bits_upper.T)


def evaluate(a, high, correction, k, target, tolerance, tables,
             *, high_shift=19, phase_fraction_bits=37):
    htab, ltab, utab = tables
    low = a-correction-(high << high_shift)
    unsigned = low+(1 << high_shift)
    nudge = htab[k, high-1]+ltab[k, unsigned & 1023]+utab[k, unsigned >> 10]
    error = (np.ldexp((a-correction).astype(float), k-phase_fraction_bits)-target)*1e12+nudge
    margins = tolerance-np.abs(error)
    return float(margins.min()), float((np.abs(error)/tolerance).max()), margins


def refine_coefficients(model, angles, *, target_margin_units=0.2,
                         radius_b=12, radius_c=32, a_radius=2,
                         verbose=True, nearest_anchor=None):
    result = copy.deepcopy(model)
    p = Parameters(**model['parameters'])
    if nearest_anchor is None:
        nearest_anchor = 'nearest_anchor_pass' in model
    xs = np.arange(1, p.max_x+1, dtype=np.int64)
    state = full_r_state(xs, model)
    order = np.argsort(state['address'], kind='stable')
    addresses = state['address'][order]
    q_all, k_all, xs_all = state['q'][order], state['k'][order], xs[order]
    del state, xs
    target_all = 1/np.sqrt(xs_all)
    tolerance_all = np.ldexp(target_all, -24)*1e12
    tables = nudge_tables(angles)
    eval_options = dict(high_shift=p.high_shift, phase_fraction_bits=p.phase_fraction_bits)
    boundaries = np.searchsorted(addresses, np.arange(257))
    changed = []
    segment_margins = []
    for address, old in enumerate(model['coefficients']):
        sl = slice(int(boundaries[address]), int(boundaries[address+1]))
        q, k = q_all[sl], k_all[sl]
        target, tolerance = target_all[sl], tolerance_all[sl]
        if not len(q):
            segment_margins.append(float('inf'))
            continue
        def main_correction(b, c):
            full = b-signed_row_sum(c, q, p.first_row_fraction_bits, p.residual_bits)
            stored = full >> model['r_storage_shift']
            full_main = model.get('known_derivative_lsb', 0) or model.get('derivative_lsb_from_low_bit') is not None
            corr = signed_row_sum(full if full_main else stored, q,
                                  p.second_row_fraction_bits if full_main else p.second_row_fraction_bits-model['r_storage_shift'],
                                  p.residual_bits)
            return full, stored, corr
        old_full, old_r, old_correction = main_correction(old['b'], old['c'])
        old_margin, old_ratio, _ = evaluate(old['a'], old['high_anchor'], old_correction,
                                            k, target, tolerance, tables, **eval_options)
        if old_margin >= target_margin_units:
            segment_margins.append(old_margin)
            continue
        best = ((-old_margin, old_ratio, old['a'], old['b'], old['c'], old['high_anchor']), copy.deepcopy(old))
        _, b_seed, c_seed = coefficient_seed(address, p)
        c_step = 1 << model['c_storage_shift']
        b_step = 1 << model['r_storage_shift']
        variable_low_bit = model.get('derivative_lsb_from_low_bit') is not None
        if variable_low_bit:
            b_step = 1
        derivative_alias_bit = model.get('derivative_alias_bit')
        if derivative_alias_bit is not None:
            b_step = 2
        low_alias_bits = model.get('low_alias_bits', 0)
        curvature_copy_low_bits = model.get('curvature_copy_low_bits', 0)
        alias_modulus = 1 << (low_alias_bits+curvature_copy_low_bits)
        if variable_low_bit:
            alias_modulus = 1 << (max(1, low_alias_bits)+curvature_copy_low_bits)
        first_c = max(0, round(c_seed)-radius_c)
        first_c += (-first_c) % c_step
        target_scaled = np.ldexp(target, p.phase_fraction_bits-k)
        for c in range(first_c, round(c_seed)+radius_c+1, c_step):
            alias_residue = ((address & ((1 << low_alias_bits)-1)) |
                             (((c >> model['c_storage_shift']) & ((1 << curvature_copy_low_bits)-1)) << low_alias_bits))
            first_b = round(b_seed)-radius_b
            residue = (model.get('initial_derivative_low_bits', 0)
                       if derivative_alias_bit is None else ((address >> derivative_alias_bit) & 1))
            first_b += (-c//2+residue-first_b) % b_step
            for b in range(first_b, round(b_seed)+radius_b+1, b_step):
                current_alias_residue = alias_residue
                if variable_low_bit:
                    parity = (b & 1)^model.get('derivative_lsb_low_xor', 0)
                    if model.get('derivative_lsb_curvature_bit') is not None:
                        parity ^= (c >> model['derivative_lsb_curvature_bit']) & 1
                    if low_alias_bits and parity != (address & 1):
                        continue
                    current_alias_residue = ((address & ((1 << low_alias_bits)-1)) | parity |
                                             (((c >> model['c_storage_shift']) & ((1 << curvature_copy_low_bits)-1)) << max(1, low_alias_bits)))
                c_b_aliases = model.get('curvature_copy_derivative_high_bits', 0)
                if c_b_aliases:
                    copy_mask = (1 << c_b_aliases)-1
                    if ((c >> model['c_storage_shift']) & copy_mask) != ((b >> model.get('derivative_split_bit', 11)) & copy_mask):
                        continue
                full, stored, correction = main_correction(b, c)
                if int(full.min()) < 0 or int(full.max()) >= (1 << model['r_full_width']):
                    continue
                required = target_scaled+correction
                midpoint = (float(required.min())+float(required.max()))/2
                cmin, cmax = int(correction.min()), int(correction.max())
                candidates = set()
                seeds = _anchor_candidates(midpoint, cmin, cmax, p,
                                           residue=current_alias_residue,
                                           modulus=alias_modulus)
                if nearest_anchor:
                    midpoint_int = math.floor(midpoint)
                    seeds += [(a, (a+(1 << (p.high_shift-1))) >> p.high_shift)
                              for a in range(midpoint_int-a_radius-2, midpoint_int+a_radius+3)]
                for a, high in seeds:
                    for candidate_a in range(a-a_radius, a+a_radius+1):
                        if candidate_a % alias_modulus != current_alias_residue:
                            continue
                        if nearest_anchor:
                            high = (candidate_a+(1 << (p.high_shift-1))) >> p.high_shift
                            if not 1 <= high <= (1 << p.high_width):
                                continue
                        lo = candidate_a-(high << p.high_shift)
                        if -(1 << p.high_shift) <= lo < (1 << p.high_shift) and -(1 << p.high_shift) <= lo-cmax and lo-cmin < (1 << p.high_shift):
                            candidates.add((candidate_a, high))
                for a, high in sorted(candidates):
                    margin, ratio, _ = evaluate(a, high, correction, k, target, tolerance, tables, **eval_options)
                    key = (-margin, ratio, a, b, c, high)
                    if key < best[0]:
                        raw = np.abs(a-required)/(target_scaled*2**-24)
                        at = int(raw.argmax())
                        row = dict(address=address, a=a, b=b, c=c,
                                   high_anchor=high, low_constant=a-(high << p.high_shift),
                                   r_initial=b >> model['r_storage_shift'],
                                   r_full_min=int(full.min()), r_full_max=int(full.max()),
                                   r_prefix_min=b-c//2, r_prefix_max=b+c//2,
                                   r_min=int(stored.min()), r_max=int(stored.max()),
                                   y_min=a-cmax, y_max=a-cmin,
                                   low_min=a-cmax-(high << p.high_shift),
                                   low_max=a-cmin-(high << p.high_shift),
                                   worst_relative_to_tolerance=float(raw.max()), at_q=int(q[at]),
                                   refined_absolute_margin_units=margin,
                                   refined_worst_error_ratio=ratio)
                        best = (key, row)
        result['coefficients'][address] = best[1]
        segment_margins.append(-best[0][0])
        if any(best[1][key] != old[key] for key in ('a', 'b', 'c', 'high_anchor')):
            changed.append(address)
        if verbose:
            print(f'address {address}: margin {old_margin:.6g} -> {-best[0][0]:.6g}; raw ratio {best[1]["worst_relative_to_tolerance"]:.8g}', flush=True)
    result['worst_relative_to_tolerance'] = max(r['worst_relative_to_tolerance'] for r in result['coefficients'])
    result['physical_table_words'] = full_r_table_words(result)
    result['physical_table_words_unsigned_cyclic'] = full_r_table_words(result, unsigned_cyclic=True)
    result['raw_validation'] = validate_full_r(result)
    result.pop('validation', None)
    if 'coefficient_angle_refinement' in result:
        result.setdefault('refinement_history', []).append(result['coefficient_angle_refinement'])
    result['coefficient_angle_refinement'] = dict(changed_addresses=changed,
                                                 frozen_angle_margin_turns=min(segment_margins)*1e-12,
                                                 target_margin_units=target_margin_units,
                                                 radius_b=radius_b, radius_c=radius_c,
                                                 a_radius=a_radius)
    if nearest_anchor:
        result['coefficient_angle_refinement']['nearest_anchor'] = True
    return result


