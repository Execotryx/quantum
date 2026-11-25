# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Research model with a virtual guard bit and one final main truncation.

Y = A - floor(sum_i d_i RN(R / 2**(s_i-1)) / 2).
The parity of the entire sum is an affine function of unchanged R bits.
Initializing a virtual target low bit to that parity makes the final low bit
zero, so the quotient can be evaluated without an extra stored output wire.
This module reads no compiled circuit or coefficient cache when fitting.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from canonical_numeric import inverse_sqrt_integers

import phase_geometry
import joint_refine
from full_r_model import (full_r_state as ordinary_state, full_r_table_words,
                          reanchor_nearest_unsigned)
from numerical_core import (Parameters, coefficient_seed, segment_inputs,
                             target_values, signed_row_sum, _anchor_candidates)


def sum_parity_mask(first_shift, rows, source_width):
    mask = 0
    for i in range(rows):
        shift = first_shift-i
        if shift == 0:
            mask ^= 1
        elif shift > 0:
            mask ^= (1 << shift) | (1 << (shift-1))
    return mask & ((1 << source_width)-1)


def parity(values, mask):
    result = np.zeros_like(values)
    for bit in range(int(mask).bit_length()):
        if mask >> bit & 1:
            result ^= (values >> bit) & 1
    return result


def main_correction(stored, q, first_shift, rows, model):
    fine = signed_row_sum(stored, q, first_shift, rows)
    if model.get('consuming_odd_last_row'):
        # A-even consuming arithmetic: the last signed row uses the odd
        # operand 2R+1, and the single final truncation is a floor.
        if (model.get('rounding_source_mask', 0) or model.get('rounding_q_mask', 0)
                or model.get('rounding_constant', 0)):
            raise ValueError('The consuming expression has no separate rounding direction.')
        return (fine+2*((q >> (rows-1)) & 1)-1) >> 1
    direction = (parity(stored, model.get('rounding_source_mask', 0)) ^
                 parity(q, model.get('rounding_q_mask', 0)) ^
                 model.get('rounding_constant', 0))
    return (fine >> 1)+((fine & 1)*direction)


def set_rounding_metadata(model, source_mask=0, q_mask=0, constant=0):
    p = Parameters(**model['parameters'])
    total = sum_parity_mask(model['main_first_logical_shift'], p.residual_bits,
                            model['r_storage_width'])
    model.update(rounding_source_mask=source_mask, rounding_q_mask=q_mask,
                  rounding_constant=constant, fine_sum_parity_mask=total,
                  virtual_initial_parity_source_mask=total^source_mask,
                  virtual_initial_parity_q_mask=q_mask,
                  virtual_initial_parity_constant=constant,
                  virtual_final_parity_source_mask=source_mask,
                  virtual_final_parity_q_mask=q_mask,
                  virtual_final_parity_constant=constant)
    return model


def fit_balanced(p, *, radius_b=12, radius_c=32,
                 curvature_storage_shift=2, derivative_storage_shift=0,
                 guard_bits=1, verbose=True, curvature_low_alias=False,
                 low_alias_bits=0, free_derivative_bit1=False,
                 dynamic_output_lsb_from_derivative=False):
    if guard_bits != 1:
        raise ValueError('Only the affine one-guard-bit kernel is certified.')
    if derivative_storage_shift not in (0, 1, 2):
        raise ValueError('The probe supports zero, affine, or quadratic derivative cleanup.')
    if derivative_storage_shift == 2 and curvature_storage_shift < 3:
        raise ValueError('Two-bit derivative cleanup requires C to be a multiple of eight.')
    if free_derivative_bit1 and derivative_storage_shift != 2:
        raise ValueError('A table-initialized bit1 is only used by the two-bit cleanup probe.')
    if dynamic_output_lsb_from_derivative and (low_alias_bits or curvature_low_alias):
        raise ValueError('This probe fits only the dynamic derivative/output low-bit alias.')
    cstep, bstep = 1 << curvature_storage_shift, 1 << derivative_storage_shift
    if free_derivative_bit1:
        bstep = 2
    rows = []
    main_shift = p.second_row_fraction_bits-derivative_storage_shift-guard_bits
    for address in range(p.num_segments):
        q = segment_inputs(address, p)
        if not len(q):
            q = segment_inputs(address, p, reachable=False)
        scaled = target_values(address, q, p)*2.0**p.output_fraction_bits
        tolerance = scaled*2.0**-p.precision_bits
        _, bseed, cseed = coefficient_seed(address, p)
        cfirst = max(0, round(cseed)-radius_c)
        cfirst += -cfirst % cstep
        best = None
        for c in range(cfirst, round(cseed)+radius_c+1, cstep):
            curvature = signed_row_sum(c, q, p.first_row_fraction_bits, p.residual_bits)
            bfirst = round(bseed)-radius_b
            bfirst += (-c//2-bfirst) % bstep
            for b in range(bfirst, round(bseed)+radius_b+1, bstep):
                full = b-curvature
                if int(full.min()) < 0:
                    continue
                stored = full >> derivative_storage_shift
                fine = signed_row_sum(stored, q, main_shift, p.residual_bits)
                correction = fine >> guard_bits
                if dynamic_output_lsb_from_derivative:
                    correction = correction-(stored & 1)
                required = scaled+correction
                midpoint = (float(required.min())+float(required.max()))/2
                cmin, cmax = int(correction.min()), int(correction.max())
                residue = address & ((1 << low_alias_bits)-1)
                if curvature_low_alias:
                    residue |= ((c >> curvature_storage_shift) & 1) << low_alias_bits
                modulus = 1 << (low_alias_bits+int(curvature_low_alias))
                if dynamic_output_lsb_from_derivative:
                    modulus = 2
                for a, high in _anchor_candidates(midpoint, cmin, cmax, p,
                                                  residue=residue,modulus=modulus):
                    error = np.abs(a-required)/tolerance
                    key = (float(error.max()), a, b, c,
                           abs(a-(high << p.high_shift)), high)
                    if best is None or key < best[0]:
                        best = (key, dict(address=address, a=a, b=b, c=c,
                                         high_anchor=high, low_constant=a-(high << p.high_shift),
                                         r_initial=b >> derivative_storage_shift,
                                         r_full_min=int(full.min()), r_full_max=int(full.max()),
                                         r_prefix_min=b-c//2, r_prefix_max=b+c//2,
                                         r_min=int(stored.min()), r_max=int(stored.max()),
                                         y_min=a-cmax, y_max=a-cmin,
                                         low_min=a-cmax-(high << p.high_shift),
                                         low_max=a-cmin-(high << p.high_shift),
                                         worst_relative_to_tolerance=float(error.max()),
                                         at_q=int(q[error.argmax()])))
        if best is None:
            raise ArithmeticError(f'No bounded balanced candidate at address {address}.')
        rows.append(best[1])
        if verbose and (address % 32 == 0 or best[0][0] >= 1):
            print(f'address {address}: ratio {best[0][0]:.9f}', flush=True)
    rwidth = max(row['r_max'] for row in rows).bit_length()
    result = dict(model_schema='balanced-guard-main-v1', parameters=asdict(p),
                  guard_bits=guard_bits, main_first_logical_shift=main_shift,
                  c_storage_shift=curvature_storage_shift,
                  c_storage_width=(max(row['c'] for row in rows) >> curvature_storage_shift).bit_length(),
                  r_storage_shift=derivative_storage_shift, r_storage_width=rwidth,
                  r_full_width=max(row['r_prefix_max'] for row in rows).bit_length(),
                  low_width=p.low_width, high_width=p.high_width, high_shift=p.high_shift,
                  phase_fraction_bits=p.phase_fraction_bits,
                  low_alias_bits=low_alias_bits,
                  shared_L={i:i for i in range(low_alias_bits)},
                  curvature_copy_low_bits=int(curvature_low_alias),
                  shared_C_from_L={0:low_alias_bits} if curvature_low_alias else {},
                  known_derivative_lsb=0, initial_derivative_low_bits=0,
                  derivative_lsb_from_low_bit=None,
                  virtual_initial_parity_source_mask=sum_parity_mask(main_shift,p.residual_bits,rwidth),
                  virtual_final_parity_source_mask=0,
                  output_physical_width=p.low_width, output_logical_width=p.low_width+1,
                  worst_relative_to_tolerance=max(row['worst_relative_to_tolerance'] for row in rows),
                  coefficients=rows)
    if free_derivative_bit1:
        result['derivative_initial_bit1_from_table'] = True
    if dynamic_output_lsb_from_derivative:
        result['dynamic_output_lsb_from_derivative'] = True
        result['output_base_coefficient_even'] = True
    set_rounding_metadata(result)
    result['physical_table_words'] = balanced_table_words(result)
    result['physical_table_words_unsigned_cyclic'] = balanced_table_words(result, unsigned_cyclic=True)
    return result


def balanced_table_words(model, *, unsigned_cyclic=False):
    if not model.get('derivative_initial_bit1_from_table'):
        return full_r_table_words(model, unsigned_cyclic=unsigned_cyclic)
    p=Parameters(**model['parameters'])
    records=[]
    for row in model['coefficients']:
        if row['b'] & 1 or row['c'] & 7:
            raise AssertionError('The two-bit probe requires even B and C divisible by eight.')
        high=row['high_anchor']-int(unsigned_cyclic)
        low=(row['low_constant']+(1 << (p.low_width-1)) if unsigned_cyclic
             else row['low_constant'] & ((1 << p.low_width)-1))
        if unsigned_cyclic and not (0<=high<(1 << p.high_width) and 0<=low<(1 << p.low_width)):
            raise AssertionError('Unsigned coefficient framing overflowed.')
        records.append(dict(address=row['address'],phase_high=high,output_low=low,
                            derivative_initial=row['b'] >> 2,derivative_lsb=0,
                            derivative_initial_bit1=(row['b'] >> 1)&1,
                            curvature=row['c'] >> model['c_storage_shift']))
    return records


def reanchor_balanced_nearest(model):
    """Exact nearest high/low split, including the explicit B1 initializer."""
    if not model.get('derivative_initial_bit1_from_table'):
        return reanchor_nearest_unsigned(model)
    p=Parameters(**model['parameters'])
    step=1 << p.high_shift
    changed=[]
    for row in model['coefficients']:
        high=(row['a']+step//2)//step
        if not 1<=high<=(1 << p.high_width):
            raise ValueError('Nearest high anchor does not fit its unsigned frame.')
        low_min=row['y_min']-high*step
        low_max=row['y_max']-high*step
        if not -step<=low_min<=low_max<step:
            raise ValueError('Nearest reanchoring would overflow the evaluated low word.')
        if high!=row['high_anchor']:
            changed.append(row['address'])
        row.update(high_anchor=high,low_constant=row['a']-high*step,
                   low_min=low_min,low_max=low_max)
        unsigned=row['low_constant']+step
        if ((unsigned >> (p.low_width-1)) ^ (unsigned >> (p.low_width-2))) & 1 != 1:
            raise AssertionError('The two highest initial target bits are not complementary.')
    model['nearest_anchor_pass']=dict(
        changed_addresses=changed,physical_high_frame='H-1',
        initial_output_top_xor_bits=[p.low_width-2,p.low_width-1],
        initial_output_top_xor_constant=1)
    model['physical_table_words']=balanced_table_words(model)
    model['physical_table_words_unsigned_cyclic']=balanced_table_words(model,unsigned_cyclic=True)
    return model


def balanced_state(xs, model):
    state = ordinary_state(xs, model)
    p = Parameters(**model['parameters'])
    fine = signed_row_sum(state['r'], state['q'], model['main_first_logical_shift'], p.residual_bits)
    state['fine_main_sum'] = fine
    correction = main_correction(state['r'], state['q'], model['main_first_logical_shift'], p.residual_bits, model)
    if model.get('dynamic_output_lsb_from_derivative'):
        if np.any(state['a'] & 1):
            raise AssertionError('The table base for a dynamic output LSB must be even.')
        state['a_base'] = state['a']
        state['a'] = state['a']+(state['r'] & 1)
    state['y'] = state['a']-correction
    state['low'] = state['y']-(state['high'] << p.high_shift)
    parity = np.zeros_like(fine)
    mask = model.get('fine_sum_parity_mask', sum_parity_mask(model['main_first_logical_shift'],p.residual_bits,model['r_storage_width']))
    for bit in range(mask.bit_length()):
        if mask >> bit & 1:
            parity ^= (state['r'] >> bit) & 1
    if not np.array_equal(parity, fine & 1):
        raise AssertionError('The virtual initial parity is not the fine-sum parity.')
    if model['r_storage_shift'] and np.any(state['r_full'] & 1):
        raise AssertionError('A supposedly omitted derivative bit was nonzero.')
    if model['r_storage_shift'] == 2:
        quadratic = np.zeros_like(state['q'])
        if model.get('derivative_initial_bit1_from_table'):
            quadratic ^= (state['b'] >> 1) & 1
        for i in range(p.residual_bits):
            shift = p.first_row_fraction_bits-i
            term_parity = ((state['c'] >> shift) ^
                           (state['c'] >> (shift-1))) & 1
            quadratic ^= ((state['q'] >> i) & 1)*term_parity
        if not np.array_equal(quadratic, (state['r_full'] >> 1) & 1):
            raise AssertionError('The second discarded derivative bit is not its cleanup polynomial.')
    return state


def validate_balanced(model, chunk_size=262144):
    p = Parameters(**model['parameters'])
    worst, margin = 0.0, float('inf')
    for first in range(1,p.max_x+1,chunk_size):
        xs = np.arange(first,min(first+chunk_size,p.max_x+1),dtype=np.int64)
        state = balanced_state(xs,model)
        target = inverse_sqrt_integers(xs)
        error = np.abs(np.ldexp(state['y'].astype(float),state['k']-p.phase_fraction_bits)-target)
        tolerance = np.ldexp(target,-p.precision_bits)
        worst=max(float((error/tolerance).max()),worst)
        margin=min(margin,float((tolerance-error).min()))
        if not -(1 << p.high_shift) <= int(state['low'].min()) <= int(state['low'].max()) < (1 << p.high_shift):
            raise AssertionError('Balanced output exceeded its signed word.')
    return dict(status='PASS' if margin>0 else 'FAIL',inputs_checked=p.max_x,
                worst_error_over_tolerance=worst,min_remaining_tolerance_turns=margin)


def refit_a_rounding(model, source_mask=0, q_mask=0, constant=0):
    result=set_rounding_metadata(copy.deepcopy(model),source_mask,q_mask,constant)
    p=Parameters(**model['parameters'])
    for old in result['coefficients']:
        q=segment_inputs(old['address'],p)
        if not len(q):q=segment_inputs(old['address'],p,reachable=False)
        target=target_values(old['address'],q,p)*2.0**p.output_fraction_bits
        full=old['b']-signed_row_sum(old['c'],q,p.first_row_fraction_bits,p.residual_bits)
        stored=full >> model['r_storage_shift']
        corr=main_correction(stored,q,result['main_first_logical_shift'],p.residual_bits,result)
        required=target+corr; midpoint=(float(required.min())+float(required.max()))/2
        cmin,cmax=int(corr.min()),int(corr.max());best=None
        for a,high in _anchor_candidates(midpoint,cmin,cmax,p):
            ratio=np.abs(a-required)/(target*2**-24)
            key=(float(ratio.max()),a,abs(a-(high << p.high_shift)),high)
            if best is None or key<best[0]:best=(key,int(q[ratio.argmax()]))
        key,at=best;worst,a,_,high=key
        old.update(a=a,high_anchor=high,low_constant=a-(high << p.high_shift),
                   y_min=a-cmax,y_max=a-cmin,low_min=a-cmax-(high << p.high_shift),
                   low_max=a-cmin-(high << p.high_shift),worst_relative_to_tolerance=worst,at_q=at)
    result['worst_relative_to_tolerance']=max(row['worst_relative_to_tolerance'] for row in result['coefficients'])
    result['physical_table_words']=full_r_table_words(result)
    result['physical_table_words_unsigned_cyclic']=full_r_table_words(result,unsigned_cyclic=True)
    return result


def refine_balanced(model, angles, **kwargs):
    originals=(joint_refine.signed_row_sum,joint_refine.full_r_state,joint_refine.validate_full_r)
    def guarded_sum(operand,q,frac,bits=14,rounding='nearest'):
        if np.ndim(operand)==0:
            return signed_row_sum(operand,q,frac,bits,rounding)
        return main_correction(operand,q,frac-model['guard_bits'],bits,model)
    joint_refine.signed_row_sum=guarded_sum
    joint_refine.full_r_state=balanced_state
    joint_refine.validate_full_r=validate_balanced
    try:
        return joint_refine.refine_coefficients(model,angles,**kwargs)
    finally:
        joint_refine.signed_row_sum,joint_refine.full_r_state,joint_refine.validate_full_r=originals


@contextmanager
def geometry_uses_balanced_state(low_padding=0):
    # Dependency injection is confined to this isolated numerical process;
    # no production file or module source is modified.
    previous = phase_geometry.full_r_state
    previous_parameters = phase_geometry.Parameters
    previous_features = phase_geometry.geometry_features
    phase_geometry.full_r_state = balanced_state
    if low_padding:
        class PhaseParameters:
            def __init__(self, **kwargs):
                self.base = previous_parameters(**kwargs)
            def __getattr__(self, key):
                return getattr(self.base,key)
            @property
            def low_width(self):
                return self.base.low_width+low_padding
        def features(p, *args, **kwargs):
            return [(kind,bit) for kind,bit in previous_features(p,*args,**kwargs)
                    if not (kind=='low_overflow' and bit >= p.n_p-low_padding)]
        phase_geometry.Parameters = PhaseParameters
        phase_geometry.geometry_features = features
    try:
        yield
    finally:
        phase_geometry.full_r_state = previous
        phase_geometry.Parameters = previous_parameters
        phase_geometry.geometry_features = previous_features


def fit_angles(model, low_padding=0, **kwargs):
    with geometry_uses_balanced_state(low_padding):
        result=phase_geometry.fit_geometry_angles(model, high_mode='complement',
                                                  angle_bound=100, **kwargs)
    if low_padding:
        p=Parameters(**model['parameters'])
        result.update(low_coefficient_width=p.low_width,low_padding_bits=low_padding,
                       zero_low_overflow_bits=list(range(p.n_p-low_padding,p.n_p)))
    return result


