# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Full derivative, small-width inverse-square-root model fitted from math.

The model has one main Horner product, with no separately evaluated high
derivative.  Its precision and optional output/address aliases are parameters.
The default profile uses a 20-bit unsigned derivative during curvature,
erases two low bits, and evaluates into a 20-bit signed output word.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path

import numpy as np

from numerical_core import (
    Parameters, coefficient_seed, segment_inputs, target_values,
    signed_row_sum, _anchor_candidates,
)


def benchmark_parameters():
    return Parameters(n_p=10, segment_bits=7, residual_bits=14,
                      precision_bits=24, output_fraction_bits=26,
                      derivative_fraction_bits=27, address_sharing=False)


def fit_full_r(p=None, *, radius_b=20, radius_c=64,
               curvature_storage_shift=4, derivative_storage_shift=2,
               verbose=False, allow_truncated_rounding=False,
               b_residue_offset=0, low_alias_bits=0,
               derivative_alias_bit=None, curvature_copy_low_bits=0,
               curvature_copy_derivative_high_bits=0, derivative_split_bit=11,
               known_derivative_lsb=0, derivative_lsb_from_low_bit=None,
               derivative_lsb_low_xor=0, derivative_lsb_curvature_bit=None):
    """Fit every coefficient by deterministic exhaustive residual checks.

    Only Python's standard library and numpy are used. Seeds are analytic
    derivatives with Chebyshev corrections; all accepted integer coefficients
    are checked against the actual separately rounded partial rows.
    """
    p = p or benchmark_parameters()
    if p.address_sharing or p.rounding != 'nearest':
        raise ValueError('This geometry uses explicit coefficient encoding and nearest rows.')
    minimum_curvature_shift = (0 if derivative_storage_shift == 0 else
                               1 if derivative_storage_shift == 1 else derivative_storage_shift+1)
    if derivative_storage_shift not in (0, 1, 2, 3) or curvature_storage_shift < minimum_curvature_shift:
        raise ValueError('This implementation certifies zero or quadratic low-bit cleanup.')
    if derivative_storage_shift == 3 and not allow_truncated_rounding:
        raise ValueError('Three discarded derivative bits are a numerical probe, not a certified cleanup kernel.')
    minimum_shift = p.second_row_fraction_bits-p.residual_bits+1
    if derivative_storage_shift >= 2 and minimum_shift < derivative_storage_shift+1 and not allow_truncated_rounding:
        raise ValueError('A main row would read a nonzero discarded derivative bit.')
    # A provably zero bit can be omitted even when a later row shifts left:
    # RN((2*r)/2**s) == RN(r/2**(s-1)) for every integer s.
    c_modulus = 1 << curvature_storage_shift
    if known_derivative_lsb not in (0, 1) or (known_derivative_lsb and derivative_storage_shift != 1):
        raise ValueError('A known nonzero low bit requires one-bit derivative storage compression.')
    if known_derivative_lsb:
        b_residue_offset = 1
    b_modulus = 1 << derivative_storage_shift
    variable_low_bit = derivative_lsb_from_low_bit is not None
    if derivative_lsb_low_xor not in (0, 1):
        raise ValueError('The output/derivative parity offset must be a bit.')
    if variable_low_bit:
        if derivative_lsb_from_low_bit != 0 or derivative_storage_shift not in (0, 1) or low_alias_bits or known_derivative_lsb:
            raise ValueError('This profile aliases variable B parity to A bit zero.')
        b_modulus = 1
    if derivative_lsb_curvature_bit is not None:
        if derivative_lsb_curvature_bit != 1 or not variable_low_bit or derivative_storage_shift:
            raise ValueError('The final derivative parity alias uses C bit one with full derivative storage.')
    elif variable_low_bit and curvature_storage_shift < 2:
        raise ValueError('A variable curvature parity must be included in the final derivative alias.')
    if low_alias_bits < 0 or low_alias_bits > p.high_shift:
        raise ValueError('Invalid output/address alias count.')
    if curvature_copy_low_bits < 0 or low_alias_bits+curvature_copy_low_bits > p.high_shift:
        raise ValueError('Invalid curvature/output alias count.')
    if derivative_alias_bit is not None:
        if derivative_storage_shift:
            raise ValueError('The derivative address alias requires no low-bit omission.')
        b_modulus = 2
    rows = []
    for address in range(p.num_segments):
        q = segment_inputs(address, p)
        if not len(q):
            q = segment_inputs(address, p, reachable=False)
        target = target_values(address, q, p)
        scaled = target*2.0**p.output_fraction_bits
        tolerance = target*2.0**(p.output_fraction_bits-p.precision_bits)
        _, b_seed, c_seed = coefficient_seed(address, p)
        best = None
        first_c = max(0, round(c_seed)-radius_c)
        first_c += (-first_c) % c_modulus
        for c in range(first_c, round(c_seed)+radius_c+1, c_modulus):
            if c >= (1 << (p.residual_bits+1)):
                raise ValueError('The curvature telescope needs an additional high-bit term.')
            curvature = signed_row_sum(c, q, p.first_row_fraction_bits,
                                       p.residual_bits, p.rounding)
            first_b = round(b_seed)-radius_b
            b_residue = (b_residue_offset if derivative_alias_bit is None else
                         ((address >> derivative_alias_bit) & 1))
            first_b += (-c//2+b_residue-first_b) % b_modulus
            for b in range(first_b, round(b_seed)+radius_b+1, b_modulus):
                if curvature_copy_derivative_high_bits:
                    copy_mask = (1 << curvature_copy_derivative_high_bits)-1
                    if ((c >> curvature_storage_shift) & copy_mask) != ((b >> derivative_split_bit) & copy_mask):
                        continue
                prefix_min, prefix_max = b-c//2, b+c//2
                if prefix_min < 0:
                    continue
                r_full = b-curvature
                r = r_full >> derivative_storage_shift
                correction = signed_row_sum(
                    r_full if known_derivative_lsb or variable_low_bit else r, q,
                    p.second_row_fraction_bits if known_derivative_lsb or variable_low_bit else p.second_row_fraction_bits-derivative_storage_shift,
                    p.residual_bits, p.rounding)
                required = scaled+correction
                midpoint = (float(required.min())+float(required.max()))/2
                correction_min = int(correction.min())
                correction_max = int(correction.max())
                a_residue = ((address & ((1 << low_alias_bits)-1)) |
                             (((c >> curvature_storage_shift) & ((1 << curvature_copy_low_bits)-1)) << low_alias_bits))
                a_modulus = 1 << (low_alias_bits+curvature_copy_low_bits)
                if variable_low_bit:
                    a_residue = ((b & 1)^derivative_lsb_low_xor) | (((c >> curvature_storage_shift) & ((1 << curvature_copy_low_bits)-1)) << 1)
                    if derivative_lsb_curvature_bit is not None:
                        a_residue ^= (c >> derivative_lsb_curvature_bit) & 1
                    a_modulus = 1 << (1+curvature_copy_low_bits)
                for a, high in _anchor_candidates(midpoint, correction_min,
                                                   correction_max, p,
                                                   residue=a_residue, modulus=a_modulus):
                    errors = np.abs(a-required)/tolerance
                    worst = float(errors.max())
                    key = (worst, a, b, c, abs(a-(high << p.high_shift)), high)
                    if best is None or key < best[0]:
                        best = (key, int(q[errors.argmax()]),
                                int(r_full.min()), int(r_full.max()),
                                int(r.min()), int(r.max()),
                                a-correction_max, a-correction_min,
                                prefix_min, prefix_max)
        if best is None:
            raise ValueError(f'No legal full-derivative candidate at address {address}.')
        (key, at, full_min, full_max, r_min, r_max,
         y_min, y_max, prefix_min, prefix_max) = best
        worst, a, b, c, _, high = key
        rows.append(dict(
            address=address, a=a, b=b, c=c,
            high_anchor=high, low_constant=a-(high << p.high_shift),
            r_initial=b >> derivative_storage_shift,
            r_full_min=full_min, r_full_max=full_max,
            r_prefix_min=prefix_min, r_prefix_max=prefix_max,
            r_min=r_min, r_max=r_max,
            y_min=y_min, y_max=y_max,
            low_min=y_min-(high << p.high_shift),
            low_max=y_max-(high << p.high_shift),
            worst_relative_to_tolerance=worst, at_q=at,
        ))
        if verbose and (address % 32 == 0 or worst >= 1):
            print(f'address {address:3d}: error/tol={worst:.9f}', flush=True)
    result = dict(
        model_schema='full-r-horner-v1', parameters=asdict(p),
        radius_b=radius_b, radius_c=radius_c,
        c_storage_shift=curvature_storage_shift,
        c_storage_width=(max(r['c'] for r in rows) >> curvature_storage_shift).bit_length(),
        r_storage_shift=derivative_storage_shift,
        r_storage_width=max(r['r_max'] for r in rows).bit_length(),
        r_full_width=max(r['r_prefix_max'] for r in rows).bit_length(),
        r_signed=False, low_width=p.low_width, high_width=p.high_width,
        high_shift=p.high_shift, phase_fraction_bits=p.phase_fraction_bits,
        clean_low_bits=('uncertified_three_bit_probe' if derivative_storage_shift == 3 else
                        'low_output_alias' if variable_low_bit else 'zero_and_quadratic' if derivative_storage_shift == 2 else
                        (('constant_one' if known_derivative_lsb else 'constant_zero') if derivative_storage_shift == 1 else 'none')),
        derivative_quantization=('truncate_then_round' if allow_truncated_rounding else 'exact_bit_omission'),
        cleanup_quadratic_constant=(b_residue_offset >> 1) & 1,
        initial_derivative_low_bits=b_residue_offset & ((1 << derivative_storage_shift)-1),
        known_derivative_lsb=known_derivative_lsb,
        derivative_lsb_from_low_bit=derivative_lsb_from_low_bit,
        derivative_lsb_low_xor=derivative_lsb_low_xor,
        derivative_lsb_curvature_bit=derivative_lsb_curvature_bit,
        virtual_output_low_bit=variable_low_bit,
        output_physical_width=p.low_width-int(variable_low_bit),
        low_alias_bits=low_alias_bits,
        derivative_alias_bit=derivative_alias_bit,
        curvature_copy_low_bits=curvature_copy_low_bits,
        curvature_copy_derivative_high_bits=curvature_copy_derivative_high_bits,
        derivative_split_bit=derivative_split_bit,
        shared_L={i: i for i in range(low_alias_bits)},
        shared_R={} if derivative_alias_bit is None else {0: derivative_alias_bit},
        shared_C_from_L={i: (1 if variable_low_bit else low_alias_bits)+i for i in range(curvature_copy_low_bits)},
        shared_C_from_Bhi={i: i for i in range(curvature_copy_derivative_high_bits)},
        worst_relative_to_tolerance=max(r['worst_relative_to_tolerance'] for r in rows),
        coefficients=rows,
    )
    result['kernel_parameters'] = full_r_kernel_parameters(result)
    return result


def full_r_kernel_parameters(data):
    p = Parameters(**data['parameters'])
    return dict(
        residual_width=p.residual_bits,
        output_width=p.low_width, output_fraction=p.output_fraction_bits,
        high_phase_width=p.high_width,
        high_phase_fraction=p.phase_fraction_bits-p.high_shift,
        low_phase_fraction=p.phase_fraction_bits,
        derivative_logical_width=data['r_full_width'],
        derivative_logical_fraction=p.derivative_fraction_bits,
        derivative_storage_width=data['r_storage_width'],
        derivative_storage_fraction=p.derivative_fraction_bits-data['r_storage_shift'],
        derivative_storage_shift=data['r_storage_shift'],
        derivative_signed=False,
        initial_derivative_low_bits=data.get('initial_derivative_low_bits', 0),
        initial_derivative_lsb_from_curvature_bit=(1 if data['r_storage_shift'] == 1 and data['c_storage_shift'] == 1 else None),
        known_derivative_lsb=data.get('known_derivative_lsb', 0),
        derivative_lsb_from_low_bit=data.get('derivative_lsb_from_low_bit'),
        derivative_lsb_low_xor=data.get('derivative_lsb_low_xor', 0),
        derivative_lsb_curvature_bit=data.get('derivative_lsb_curvature_bit'),
        main_row_constant_offsets=[(0 if p.second_row_fraction_bits-i >= 2 else
                                    (1 if p.second_row_fraction_bits-i >= 0 else 1 << (i-p.second_row_fraction_bits)))
                                   *data.get('known_derivative_lsb', 0)
                                   for i in range(p.residual_bits)],
        main_row_variable_lsb_weights=[(0 if p.second_row_fraction_bits-i >= 2 else
                                       (1 if p.second_row_fraction_bits-i >= 0 else 1 << (i-p.second_row_fraction_bits)))
                                      *int(data.get('derivative_lsb_from_low_bit') is not None and data['r_storage_shift'] == 1)
                                      for i in range(p.residual_bits)],
        virtual_output_low_bit=data.get('virtual_output_low_bit', False),
        output_physical_width=data.get('output_physical_width', p.low_width),
        virtual_main_parity_source_mask=((1 << 0) ^ (1 << p.second_row_fraction_bits)
                                         if data.get('derivative_lsb_from_low_bit') is not None else 0),
        virtual_main_parity_constant=data.get('derivative_lsb_low_xor', 0),
        final_output_lsb_source_mask=(((1 << 0) ^ (1 << p.second_row_fraction_bits) ^
                                       ((1 << (p.second_row_fraction_bits-p.residual_bits))
                                        if p.second_row_fraction_bits >= p.residual_bits else 0))
                                      if data.get('derivative_lsb_from_low_bit') is not None else 0),
        cleanup_quadratic_constant=data.get('cleanup_quadratic_constant', 0),
        curvature_storage_width=data['c_storage_width'],
        curvature_storage_fraction=p.derivative_fraction_bits-data['c_storage_shift'],
        curvature_storage_shift=data['c_storage_shift'],
        curvature_signed=False,
        rounding='nearest_ties_to_positive_infinity',
    )


def mark_output_parity_alias(data, xor=0):
    """Certify an existing coefficient table's reusable output least bit.

    The curvature rows have total unsigned magnitude floor(C/2), so their
    sum has that same parity independently of every residual sign.  Thus
    R0=B0 XOR C1.  The check below proves A0=R0 XOR ``xor`` for the complete
    table, permitting the main stage to represent its least target bit as
    an affine function of the unchanged derivative source wires.
    """
    if data['r_storage_shift'] or xor not in (0, 1):
        raise ValueError('This pass certifies a fully stored derivative source.')
    p = Parameters(**data['parameters'])
    for row in data['coefficients']:
        if not 0 <= row['c'] < (1 << p.first_row_fraction_bits):
            raise ValueError('The curvature parity telescope has a high tail.')
        if (row['a'] ^ row['b'] ^ (row['c'] >> 1)) & 1 != xor:
            raise ValueError('The output and final derivative parities are not aliased.')
    data.update(derivative_lsb_from_low_bit=0,
                derivative_lsb_low_xor=xor,
                derivative_lsb_curvature_bit=1 if any(row['c'] & 2 for row in data['coefficients']) else None,
                virtual_output_low_bit=True,
                output_physical_width=p.low_width-1)
    data['kernel_parameters'] = full_r_kernel_parameters(data)
    return data


def reanchor_nearest_unsigned(data):
    """Change only the exact high/low split, keeping A, B and C unchanged.

    The physical high coefficient is H-1, so H=2**high_width is legal.
    Choosing the nearest H with upper ties gives initial unsigned low word
    U in [2**(W-2), 3*2**(W-2)), whose highest two bits have XOR one.
    A full interval check certifies that all evaluated low words still fit.
    """
    p = Parameters(**data['parameters'])
    step = 1 << p.high_shift
    changed = []
    for row in data['coefficients']:
        high = (row['a']+step//2)//step
        if not 1 <= high <= (1 << p.high_width):
            raise ValueError('Nearest anchor is outside the unsigned high frame.')
        low_min, low_max = row['y_min']-high*step, row['y_max']-high*step
        if not -step <= low_min <= low_max < step:
            raise ValueError('Nearest anchor would overflow the evaluated low word.')
        if high != row['high_anchor']:
            changed.append(row['address'])
        row.update(high_anchor=high, low_constant=row['a']-high*step,
                   low_min=low_min, low_max=low_max)
        unsigned = row['low_constant']+step
        if ((unsigned >> (p.low_width-1)) ^ (unsigned >> (p.low_width-2))) & 1 != 1:
            raise AssertionError('The nearest-anchor top-bit alias failed.')
    data['nearest_anchor_pass'] = dict(
        changed_addresses=changed,
        physical_high_frame='H-1',
        initial_output_top_xor_bits=[p.low_width-2, p.low_width-1],
        initial_output_top_xor_constant=1)
    data['physical_table_words'] = full_r_table_words(data)
    data['physical_table_words_unsigned_cyclic'] = full_r_table_words(data, unsigned_cyclic=True)
    return data


def full_r_table_words(data, *, unsigned_cyclic=False):
    p = Parameters(**data['parameters'])
    result = []
    for row in data['coefficients']:
        known_initial = row['b']
        if data['r_storage_shift'] == 1 and data['c_storage_shift'] == 1:
            known_initial += row['c']//2
        if data.get('derivative_lsb_from_low_bit') is None and (known_initial & ((1 << data['r_storage_shift'])-1)) != data.get('initial_derivative_low_bits', 0):
            raise ValueError('Initial derivative low bits need an additional initializer.')
        if unsigned_cyclic:
            high = row['high_anchor']-1
            low = row['low_constant']+(1 << (p.low_width-1))
            if not 0 <= high < (1 << p.high_width) or not 0 <= low < (1 << p.low_width):
                raise ValueError('Unsigned cyclic phase frame is outside its table widths.')
        else:
            high = row['high_anchor']
            low = row['low_constant'] & ((1 << p.low_width)-1)
        result.append(dict(
            address=row['address'], phase_high=high,
            output_low=low,
            derivative_initial=row['b'] >> data['r_storage_shift'],
            derivative_lsb=row['b'] & 1,
            curvature=row['c'] >> data['c_storage_shift'],
        ))
    return result


def full_r_state(xs, data):
    p = Parameters(**data['parameters'])
    xs = np.asarray(xs).astype(np.int64, copy=False)
    if np.any(xs < 1) or np.any(xs > p.max_x):
        raise ValueError('Input is outside the benchmark domain.')
    norm = xs.copy()
    k = np.zeros_like(xs)
    for j in reversed(range(p.n_p.bit_length())):
        shift = 2 << j
        if shift >= p.width:
            continue
        enabled = (norm >> (p.width-shift)) == 0
        norm = np.where(enabled, norm << shift, norm)
        k += enabled.astype(np.int64) << j
    exponent = (norm >> (p.width-1)) & 1
    aligned = norm << (1-exponent)
    q = aligned & ((1 << p.residual_bits)-1)
    address = (exponent << p.segment_bits) | ((aligned >> p.residual_bits) & ((1 << p.segment_bits)-1))
    table = np.array([[r['a'], r['b'], r['c'], r['high_anchor']]
                      for r in data['coefficients']], dtype=np.int64)
    a, b, c, high = table[address].T
    r_full = b-signed_row_sum(c, q, p.first_row_fraction_bits,
                              p.residual_bits, p.rounding)
    r = r_full >> data['r_storage_shift']
    full_main = data.get('known_derivative_lsb', 0) or data.get('derivative_lsb_from_low_bit') is not None
    y = a-signed_row_sum(r_full if full_main else r, q,
                         p.second_row_fraction_bits if full_main else p.second_row_fraction_bits-data['r_storage_shift'],
                         p.residual_bits, p.rounding)
    return dict(x=xs, normalized=norm, k=k, address=address, q=q,
                a=a, b=b, c=c, r_full=r_full, r=r, high=high,
                y=y, low=y-(high << p.high_shift))


def validate_full_r(data, *, chunk_size=262144):
    p = Parameters(**data['parameters'])
    result = dict(status='PASS', inputs_checked=p.max_x,
                  worst_error_over_tolerance=0.0, worst_x=0,
                  min_remaining_tolerance_turns=float('inf'),
                  r_full_min=1 << 62, r_full_max=0,
                  r_min=1 << 62, r_max=0,
                  low_min=1 << 62, low_max=-(1 << 62))
    for first in range(1, p.max_x+1, chunk_size):
        xs = np.arange(first, min(first+chunk_size, p.max_x+1), dtype=np.int64)
        state = full_r_state(xs, data)
        expected = 1/np.sqrt(xs)
        actual = np.ldexp(state['y'].astype(float), state['k']-p.phase_fraction_bits)
        error = np.abs(actual-expected)
        tolerance = np.ldexp(expected, -p.precision_bits)
        ratio = error/tolerance
        at = int(ratio.argmax())
        if ratio[at] > result['worst_error_over_tolerance']:
            result['worst_error_over_tolerance'] = float(ratio[at])
            result['worst_x'] = int(xs[at])
        result['min_remaining_tolerance_turns'] = min(result['min_remaining_tolerance_turns'], float((tolerance-error).min()))
        for key in ('r_full', 'r', 'low'):
            result[key+'_min'] = min(result[key+'_min'], int(state[key].min()))
            result[key+'_max'] = max(result[key+'_max'], int(state[key].max()))
        # Certify the exact all-outcome cleanup polynomial, independently of
        # the implementation's arithmetic gates or measurement seed.
        expected_low_bit = (((state['a'] >> data['derivative_lsb_from_low_bit']) & 1)^data.get('derivative_lsb_low_xor', 0)
                            if data.get('derivative_lsb_from_low_bit') is not None else data.get('known_derivative_lsb', 0))
        if (data['r_storage_shift'] or data.get('derivative_lsb_from_low_bit') is not None) and np.any((state['r_full'] & 1) != expected_low_bit):
            raise AssertionError('Derivative low bit does not equal its known constant.')
        if data['r_storage_shift'] == 2:
            quadratic = np.zeros_like(xs)
            c, q = state['c'], state['q']
            for i in range(p.residual_bits):
                shift = p.first_row_fraction_bits-i
                term_parity = ((c >> shift) ^ (c >> (shift-1))) & 1
                quadratic ^= ((q >> i) & 1)*term_parity
            quadratic ^= data.get('cleanup_quadratic_constant', 0)
            if not np.array_equal((state['r_full'] >> 1) & 1, quadratic):
                raise AssertionError('Derivative low-bit cleanup polynomial failed.')
    if result['worst_error_over_tolerance'] >= 1:
        result['status'] = 'FAIL'
    if not 0 <= result['r_min'] <= result['r_max'] < (1 << data['r_storage_width']):
        result['status'] = 'FAIL'
    if not 0 <= result['r_full_min'] <= result['r_full_max'] < (1 << data['r_full_width']):
        result['status'] = 'FAIL'
    if not -(1 << (p.low_width-1)) <= result['low_min'] <= result['low_max'] < (1 << (p.low_width-1)):
        result['status'] = 'FAIL'
    return result


def benchmark_full_r_model(*, validate=True, verbose=False):
    data = fit_full_r(verbose=verbose)
    data['physical_table_words'] = full_r_table_words(data)
    if validate:
        data['validation'] = validate_full_r(data)
        if data['validation']['status'] != 'PASS':
            raise ValueError('The fitted full-R model failed exhaustive validation.')
    return data


