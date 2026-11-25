# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Numerical profile for the A-even consuming main arithmetic, from source.

The balanced affine profile is recomputed first.  Around each of its rows a
bounded joint search then selects new coefficients for the modified integer
expression

    R = (B - curvature(C, q)) >> 1,
    F = sum_i (2 q_i - 1) RN(R / 2**(12-i)) + (2 q_13 - 1),
    y = A - floor(F / 2),

subject to A even, B even, and stored curvature bit zero equal to the old
low-word bit one, which is physical address bit one of the retained affine
frame.  Every A on the exact admissible interval of every (B, C) candidate is
ranked by its integer margin against the integer-square-root target; the
maximum-margin candidate is kept, ties broken by the smallest (A, B, C).
The 43 phase angles are then fitted by the unchanged pipeline, and only the
exhaustive all-input certificate decides acceptance: the raw dyadic margin
of a few rows is negative by design and is repaired by the fitted angles.
No coefficient, angle or circuit file is read.
"""
from __future__ import annotations

import copy
import hashlib
from math import isqrt

import numpy as np

SCALE = 1 << 32
RADIUS_B = 12
RADIUS_C = 32


def segment_residuals(address, maximum):
    """All residual values of one normalized address that occur on the task domain."""
    exponent, mantissa = divmod(address, 128)
    q = np.arange(0, 16384, 2 if exponent == 0 else 1, dtype=np.int64)
    normalized = ((128+mantissa) << 14)+q
    candidate = normalized >> (1-exponent)
    valid = np.ones(len(q), dtype=bool)
    for _ in range(11):
        excessive = candidate > maximum
        if not excessive.any():
            break
        valid &= ~excessive | ((candidate & 3) == 0)
        candidate = np.where(excessive, candidate >> 2, candidate)
    return q[valid & (candidate >= 1) & (candidate <= maximum)]


def target_intervals(address, q):
    """Centres and half-widths of the allowed y interval, in units of 2**-32."""
    exponent, mantissa = divmod(address, 128)
    normalized = ((128+mantissa) << 14)+q
    roots = [isqrt((1 << (141-exponent))//int(value)) for value in normalized]
    return (np.array([(value+1) >> 1 for value in roots], dtype=np.int64),
            np.array([value >> 25 for value in roots], dtype=np.int64))


def curvature_sum(c, q):
    answer = np.zeros_like(q)
    for index in range(14):
        shift = 15-index
        answer += (2*((q >> index) & 1)-1)*((c+(1 << (shift-1))) >> shift)
    return answer


def consuming_correction(b, c, q):
    """floor(F/2) and the stored derivative for every (B, q) pair."""
    stored = (b[:, None]-curvature_sum(c, q)[None, :]) >> 1
    fine = np.zeros_like(stored)
    for index in range(14):
        shift = 12-index
        sign = 2*((q[None, :] >> index) & 1)-1
        fine += sign*(((stored+(1 << (shift-1))) >> shift) if shift > 0 else stored << -shift)
    fine += 2*((q[None, :] >> 13) & 1)-1
    return fine >> 1, stored


def _ceil_div(a, b):
    return -((-int(a))//int(b))


def _ceil_grid(value, modulus, residue):
    return residue+modulus*_ceil_div(value-residue, modulus)


def _floor_grid(value, modulus, residue):
    return residue+modulus*((value-residue)//modulus)


def search_address(address, old, maximum):
    q = segment_residuals(address, maximum)
    target, tolerance = target_intervals(address, q)
    alias = (old['a'] >> 1) & 1
    b = np.arange(_ceil_grid(max(0, old['b']-RADIUS_B), 2, 0),
                  _floor_grid(min(262142, old['b']+RADIUS_B), 2, 0)+1, 2, dtype=np.int64)
    curvatures = range(_ceil_grid(max(0, old['c']-RADIUS_C), 16, 8*alias),
                       _floor_grid(min(2040, old['c']+RADIUS_C), 16, 8*alias)+1, 16)
    base = old['high_anchor'] << 19
    best = None
    for c in curvatures:
        correction, stored = consuming_correction(b, c, q)
        required = target[None, :]+correction*SCALE
        left = (required-tolerance[None, :]).max(axis=1)
        right = (required+tolerance[None, :]).min(axis=1)
        low_correction, high_correction = correction.min(axis=1), correction.max(axis=1)
        low_stored, high_stored = stored.min(axis=1), stored.max(axis=1)
        for index, candidate_b in enumerate(b):
            lower, upper = int(left[index]), int(right[index])
            word_low = max(base-(1 << 19)+int(high_correction[index]), base-(1 << 18))
            word_high = min(base+(1 << 19)-1+int(low_correction[index]), base+(1 << 18)-1)
            if address == 0:
                zero = int(np.searchsorted(q, 0))
                word_high = min(word_high, (1 << 27)-1+int(correction[index, zero]))
            if not (0 <= int(low_stored[index]) and int(high_stored[index]) < (1 << 17)):
                continue
            first, last = _ceil_grid(word_low, 2, 0), _floor_grid(word_high, 2, 0)
            if first > last:
                continue
            low = _ceil_grid(max(word_low, _ceil_div(lower+2, SCALE)), 2, 0)
            high = _floor_grid(min(word_high, (upper-2)//SCALE), 2, 0)
            candidates = set(range(low, high+1, 2)) if low <= high else set()
            centre = 2*((lower+upper)//(4*SCALE))
            candidates.update(min(max(value, first), last) for value in (centre, centre+2))
            for a in candidates:
                margin = min(a*SCALE-lower, upper-a*SCALE)-1
                key = (-margin, a, int(candidate_b), c)
                if best is None or key < best[0]:
                    best = (key, dict(a=a, b=int(candidate_b), c=c, margin_y32=margin,
                                      r_min=int(low_stored[index]), r_max=int(high_stored[index]),
                                      y_min=a-int(high_correction[index]),
                                      y_max=a-int(low_correction[index])))
    if best is None:
        raise ArithmeticError(f'No consuming coefficient row exists for address {address}.')
    return best[1], len(q)


def consuming_model(base):
    """The balanced model with every row refitted for the consuming expression."""
    from balanced_model import balanced_table_words
    from numerical_core import Parameters
    p = Parameters(**base['parameters'])
    if {int(bit): int(wire) for bit, wire in base.get('shared_L', {}).items()} != {0: 0, 1: 1}:
        raise ValueError('The consuming refit starts from the two-bit affine low-word alias profile.')
    model = copy.deepcopy(base)
    checked, margins = 0, []
    for address, row in enumerate(model['coefficients']):
        if row['address'] != address:
            raise ValueError('The coefficient rows must be in original address order.')
        new, count = search_address(address, row, p.max_x)
        checked += count
        margins.append(new['margin_y32'])
        high = row['high_anchor']
        if new['a'] & 1 or new['b'] & 1 or ((new['c'] >> 3) ^ (row['a'] >> 1)) & 1 or new['c'] & 7:
            raise AssertionError('A refitted row lost its even or address-alias residue.')
        low_min, low_max = new['y_min']-(high << p.high_shift), new['y_max']-(high << p.high_shift)
        if not -(1 << p.high_shift) <= low_min <= low_max < (1 << p.high_shift):
            raise AssertionError('A refitted low word leaves its literal range.')
        unsigned = new['a']-(high << p.high_shift)+(1 << p.high_shift)
        if ((unsigned >> 18) ^ (unsigned >> 19)) & 1 != 1:
            raise AssertionError('The nearest initial top-bit relation was lost.')
        for stale in ('at_q', 'certified_raw_phase_margin_turns', 'margin_minimum_k',
                      'r_full_max', 'r_full_min', 'r_prefix_max', 'r_prefix_min',
                      'worst_relative_to_tolerance'):
            row.pop(stale, None)
        row.update(a=new['a'], b=new['b'], c=new['c'], low_constant=new['a']-(high << p.high_shift),
                   r_initial=new['b'] >> 1, r_min=new['r_min'], r_max=new['r_max'],
                   y_min=new['y_min'], y_max=new['y_max'], low_min=low_min, low_max=low_max,
                   consuming_raw_margin_y32=new['margin_y32'])
    if max(row['r_max'] for row in model['coefficients']).bit_length() != model['r_storage_width']:
        raise AssertionError('The refitted stored derivative changed its width.')
    if (max(row['c'] for row in model['coefficients']) >> model['c_storage_shift']).bit_length() != model['c_storage_width']:
        raise AssertionError('The refitted stored curvature changed its width.')
    model.pop('worst_relative_to_tolerance', None)
    model.pop('coefficient_alias_raw_margin_turns', None)
    model.update(
        consuming_odd_last_row=True, low_alias_bits=0, shared_L={},
        shared_C_from_address={0: 1}, address_frame_alias_bits=2,
        consuming_refit=dict(radius_b=RADIUS_B, radius_c=RADIUS_C, inputs_checked=checked,
            minimum_raw_margin_y32=min(margins),
            raw_nonpositive_addresses=[i for i, margin in enumerate(margins) if margin <= 0],
            acceptance='angle-fitted exhaustive certificate only',
            residues='A = 0 (mod 2), B = 0 (mod 2), C = 8*old_A1 (mod 16)'))
    model['physical_table_words'] = balanced_table_words(model)
    model['physical_table_words_unsigned_cyclic'] = balanced_table_words(model, unsigned_cyclic=True)
    return model


def generate_consuming_profile(*, verbose=False):
    """Recompute the balanced profile, refit it, and fit the selected tail43 angles."""
    from balanced_alias_profiles import generate_balanced_alias_profile
    from balanced_model import fit_angles
    from canonical_phase_nudges import canonicalize_nudges
    from profiles import canonical_bytes, phase_angle_table, profile_resources
    from rare_phase_pass import fuse_zero_residual_tail
    base = generate_balanced_alias_profile(verbose=verbose)
    model = consuming_model(base['model'])
    fitted = fit_angles(model, verbose=verbose)
    if fitted['status'] != 'PASS':
        raise ArithmeticError('The consuming coefficient table has no positive fitted phase margin.')
    baseline = canonicalize_nudges(model, fitted)
    angles = fuse_zero_residual_tail(model, baseline, 8)
    if angles['status'] != 'PASS':
        raise ArithmeticError('The consuming tail pass failed exhaustive numerical validation.')
    result = dict(profile_name='g25_r17_balanced_c8_A_even_consuming_tail43', model=model,
                  angles=angles, phase_angles=phase_angle_table(angles), extra_phase_features=[],
                  resources=profile_resources(model, angles),
                  affine_address_frame=base['affine_address_frame'],
                  base_profile_name=base['profile_name'],
                  base_raw_arithmetic_certificate=base['raw_arithmetic_certificate'])
    result['profile_sha256'] = hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result
