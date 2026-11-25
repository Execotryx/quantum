# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Numerical phase compiler passes for the finite normalization tail.

These passes consume mathematical coefficient and angle dictionaries produced
by the from-parameters fitter.  They never consume a compiled circuit.  The
public ``generate_profile`` entry point recomputes that fitter before applying
the pass; the file CLI is a research/review interface for our own model outputs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from balanced_model import balanced_state, geometry_uses_balanced_state
from numerical_core import Parameters, signed_row_sum
from phase_geometry import geometry_data, column, correction
from profiles import canonical_bytes, phase_angle_table, profile_resources
from residual_phase_fit import synthesis_charge

DENOMINATOR = 1 << 64


def _require_geometry(model, angles):
    p = Parameters(**model['parameters'])
    actual = (p.output_fraction_bits, p.derivative_fraction_bits,
              p.residual_bits, p.low_width, p.high_shift, p.n_p,
              model['r_storage_shift'], model['main_first_logical_shift'],
              angles['high_mode'], angles['high_width'])
    if actual != (26, 25, 14, 20, 19, 10, 1, 12, 'complement', 8):
        raise ValueError(f'This phase proof is specialized to the selected geometry: {actual}')
    if model.get('rounding_source_mask', 0) or model.get('rounding_q_mask', 0) or model.get('rounding_constant', 0):
        raise ValueError('The zero-residual certificate assumes the floor main correction.')
    return p


def zero_residual_words(model):
    """Compute U(q=0) from the quadratic and the exact integer row semantics."""
    p = Parameters(**model['parameters'])
    rows = sorted(model['coefficients'], key=lambda r: r['address'])
    a = np.array([r['a'] for r in rows], dtype=np.int64)
    b = np.array([r['b'] for r in rows], dtype=np.int64)
    c = np.array([r['c'] for r in rows], dtype=np.int64)
    h = np.array([r['high_anchor'] for r in rows], dtype=np.int64)
    q = np.zeros(len(rows), dtype=np.int64)
    full = b-signed_row_sum(c, q, p.first_row_fraction_bits, p.residual_bits)
    r = full >> model['r_storage_shift']
    t = signed_row_sum(r, q, model['main_first_logical_shift'], p.residual_bits)
    if model.get('consuming_odd_last_row'):
        # At q = 0 the odd last row contributes 2*q13 - 1 = -1 inside the floor.
        t = t-1
    y = a-(t >> 1)
    u = y-(h << p.high_shift)+(1 << p.high_shift)
    if np.any(u < 0) or np.any(u >= (1 << p.low_width)):
        raise AssertionError('The zero-residual output exceeds its unsigned word.')
    return [dict(address=i, high=int(h[i]-1), derivative=int(r[i]), y=int(y[i]),
                 output_unsigned=int(u[i]), phase_tail_word=int(u[i] >> 16))
            for i in range(len(rows))]


def _data(model, angles):
    with geometry_uses_balanced_state():
        high, low, k, raw_error, tolerance = geometry_data(
            model, angles['high_mode'], high_routing_width=angles['high_width'])
    features = [(r['kind'], r['bit']) for r in angles['features']]
    weights = np.array([r['nudge_turn_numerator']/DENOMINATOR*1e12
                        for r in angles['features']])
    error = raw_error+correction(high, low, k, weights, features, angles['high_width'])
    return high, low, k, error, tolerance


def _erase_angles(result, indices):
    complete = {(r['kind'], r['bit']): r['turn_numerator']
                for r in phase_angle_table(result)}
    for row in result['features']:
        key = (row['kind'], row['bit'])
        if key in indices:
            row['nudge_turn_numerator'] -= complete[key]
            row['omitted'] = True
    result['phase_features'] -= len(indices)


def _certificate(angles, error, tolerance, baseline, details):
    margin = tolerance-np.abs(error)
    minimum = float(margin.min())*1e-12
    angles.update(status='PASS' if minimum > 0 else 'FAIL',
                  inputs_checked=len(error),
                  min_remaining_tolerance_turns=minimum,
                  worst_margin_x=int(margin.argmin())+1,
                  worst_error_over_tolerance=float((np.abs(error)/tolerance).max()),
                  worst_error_x=int((np.abs(error)/tolerance).argmax())+1,
                  baseline_min_remaining_tolerance_turns=baseline['min_remaining_tolerance_turns'],
                  synthesis_equivalents=synthesis_charge(minimum, angles['phase_features'],
                                                         angles.get('fixed_T_gates', 0)),
                  baseline_synthesis_equivalents=synthesis_charge(
                      baseline['min_remaining_tolerance_turns'], baseline['phase_features'],
                      baseline.get('fixed_T_gates', 0)),
                  rare_phase_certificate=details)
    angles['synthesis_saving'] = angles['baseline_synthesis_equivalents']-angles['synthesis_equivalents']
    return angles


def merge_singleton(model, baseline):
    """Replace high base bit2 by bit2 OR [k=10]; omit low overflow9.

    Only the base-bit2 rotation sees the modified bit. Other rotations and
    the high routing word continue to use their original values.
    """
    _require_geometry(model, baseline)
    high, low, k, error, tolerance = _data(model, baseline)
    old = column(high, low, k, 'high_complement_base', 2, 8).astype(bool)
    tail = column(high, low, k, 'low_overflow', 9, 8).astype(bool)
    new = old | (k == 10)
    delta = new.astype(np.int8)-old.astype(np.int8)
    if not np.array_equal(delta, tail.astype(np.int8)):
        raise AssertionError('The singleton phase-feature identity failed.')
    support = np.flatnonzero(tail)+1
    if support.tolist() != [2]:
        raise AssertionError('The low overflow9 singleton is not the certified input x=2.')
    theta = {(r['kind'], r['bit']): r['turn_numerator'] for r in phase_angle_table(baseline)}
    difference = theta['high_complement_base', 2]-theta['low_overflow', 9]
    error += (difference/DENOMINATOR*1e12)*tail
    result = copy.deepcopy(baseline)
    _erase_angles(result, {('low_overflow', 9)})
    result['rare_phase_pass'] = 'singleton-high-or-k10-v1'
    result['phase_feature_transforms'] = [dict(
        kind='high_complement_base', bit=2, original='rotated_high[2]',
        replacement='rotated_high[2] OR (k == 10)',
        scope='only this rotation; restore before every other high phase feature')]
    return _certificate(result, error, tolerance, baseline, dict(
        proof_domain='every integer x in 1..3133452',
        exact_boolean_identity='low_overflow9 = (k == 10) AND NOT rotated_high[2]',
        removed_features=[dict(kind='low_overflow', bit=9)],
        changed_inputs=support.tolist(), angle_difference_numerator=difference,
        turn_denominator=DENOMINATOR))


def fuse_zero_residual_tail(model, baseline, first_removed=6):
    """Move selected low overflow rotations into the early high phase.

    On k>=first_removed+1, q=0.  Add U0[19] to the high integer before
    routing; at high overflow j>first_removed, add the disjoint feature
    (k>j)*low_overflow[j-1] and compensate its T/S/Z part exactly.
    """
    p = _require_geometry(model, baseline)
    if first_removed not in (6, 7, 8, 9):
        raise ValueError('The finite-tail certificate supports cutoffs6..9.')
    high, low, k, error, tolerance = _data(model, baseline)
    threshold = first_removed+1
    indices = np.flatnonzero(k >= threshold)
    xs = indices.astype(np.int64)+1
    state = balanced_state(xs, model)
    if np.any(state['q']):
        raise AssertionError('A supposedly zero residual is nonzero.')
    words = zero_residual_words(model)
    table = np.array([r['output_unsigned'] for r in words], dtype=np.int64)
    address = state['address']
    u = state['low']+(1 << p.high_shift)
    if not np.array_equal(u, table[address]):
        raise AssertionError('The table-only low word differs from the full arithmetic.')
    original_h = state['high']-1
    new_h = original_h+((u >> 19) & 1)
    if np.any(new_h >= 256):
        raise AssertionError('The incremented high coefficient requires an overflow treatment.')
    kk = k[indices].astype(np.int64)
    shift = kk % 8
    new_rotated = (((new_h << shift) | (new_h >> (8-shift))) & 255).astype(np.uint32)
    theta = {(r['kind'], r['bit']): r['turn_numerator'] for r in phase_angle_table(baseline)}
    nudges = {(r['kind'], r['bit']): r['nudge_turn_numerator'] for r in baseline['features']}
    delta = ((new_h-original_h) << (64-baseline['high_fraction_bits']+kk)).astype(np.int64)
    # A high-integer change also changes all fitted high-angle nudges.
    old_rotated = high[indices]
    for row in baseline['features']:
        kind, bit = row['kind'], row['bit']
        if kind.startswith('high') and row['nudge_turn_numerator']:
            before = column(old_rotated, low[indices], kk, kind, bit, 8).astype(np.int64)
            after = column(new_rotated, low[indices], kk, kind, bit, 8).astype(np.int64)
            delta += row['nudge_turn_numerator']*(after-before)
    added = []
    for j in range(first_removed+1, 10):
        value = column(high[indices], low[indices], kk, 'low_overflow', j-1, 8).astype(np.int64)*(kk > j)
        expected = ((u >> (19+j-kk)) & 1)*(kk > j)
        if not np.array_equal(value, expected):
            raise AssertionError('The early low-overflow selector is incorrect.')
        extra_angle = (1 << (64+j-18))+nudges['high_complement_overflow', j]
        delta += extra_angle*value
        added.append(dict(kind='high_complement_overflow', bit=j,
                          added_feature=f'(k > {j}) AND U0[{19+j}-k]',
                          disjoint_from_original=True,
                          compensation_turn_numerator=1 << (64+j-10),
                          turn_denominator=DENOMINATOR,
                          added_support_inputs=xs[value.astype(bool)].tolist()))
    removed = []
    for j in range(first_removed, 10):
        value = column(high[indices], low[indices], kk, 'low_overflow', j, 8).astype(np.int64)
        delta -= theta['low_overflow', j]*value
        removed.append(dict(kind='low_overflow', bit=j))
    error[indices] += delta.astype(float)/DENOMINATOR*1e12
    result = copy.deepcopy(baseline)
    _erase_angles(result, {('low_overflow', j) for j in range(first_removed, 10)})
    # Only j7 requires a T correction; j8 andj9 are Clifford S and Z.
    result['fixed_T_gates'] += int(first_removed < 7)
    result['rare_phase_pass'] = f'zero-residual-tail-from-{first_removed}-v1'
    result['phase_feature_transforms'] = added
    result['high_value_transform'] = dict(
        condition=f'k >= {threshold}', before_routing='H-1 + U0[19]',
        normal_value='H-1', restore_after_high_phase=True,
        coefficient_function='U0 = Y(q=0) - H*2**19 + 2**19')
    result['zero_residual_phase_words'] = words
    return _certificate(result, error, tolerance, baseline, dict(
        proof_domain='every integer x in 1..3133452',
        removed_features=removed, threshold_shift=threshold,
        zero_residual_inputs=len(indices), changed_inputs=xs[delta != 0].tolist(),
        maximum_absolute_phase_change_turns=float(np.abs(delta.astype(float)).max())/DENOMINATOR,
        maximum_incremented_high=int(new_h.max()),
        additional_T_rotations=int(first_removed < 7),
        tail_worst_error_over_tolerance=float((np.abs(error[indices])/tolerance[indices]).max()),
        tail_minimum_remaining_tolerance_turns=float((tolerance[indices]-np.abs(error[indices])).min())*1e-12))


def generate_profile(*, pass_name='singleton', verbose=False):
    """Deterministically recompute coefficients/angles, then apply the pass."""
    from balanced_alias_profiles import generate_balanced_alias_profile
    from canonical_phase_nudges import canonicalize_nudges
    result = generate_balanced_alias_profile(verbose=verbose)
    result.pop('profile_sha256', None)
    baseline = canonicalize_nudges(result['model'], result['angles'])
    if pass_name == 'singleton':
        angles = merge_singleton(result['model'], baseline)
    else:
        if pass_name not in ('tail', 'tail41', 'tail42', 'tail43'):
            raise ValueError('Unknown rare-phase pass.')
        first_removed = {'tail': 6, 'tail41': 6, 'tail42': 7, 'tail43': 8}[pass_name]
        angles = fuse_zero_residual_tail(result['model'], baseline, first_removed)
    if angles['status'] != 'PASS':
        raise ArithmeticError('The rare-phase pass failed exhaustive numerical validation.')
    result.update(profile_name=result['profile_name']+'_'+pass_name,
                  angles=angles, phase_angles=phase_angle_table(angles),
                  resources=profile_resources(result['model'], angles))
    result['profile_sha256'] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(prog='rare_phase_pass')
    parser.add_argument('--pass-name', choices=('singleton', 'tail', 'tail41', 'tail42', 'tail43'), default='singleton')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate_profile(pass_name=args.pass_name, verbose=True)
    args.output.write_bytes(canonical_bytes(result))
    value = result.get('angles', result)
    print(json.dumps({k: value[k] for k in ('status', 'phase_features', 'fixed_T_gates',
                     'min_remaining_tolerance_turns', 'worst_error_over_tolerance',
                     'synthesis_equivalents', 'synthesis_saving')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
