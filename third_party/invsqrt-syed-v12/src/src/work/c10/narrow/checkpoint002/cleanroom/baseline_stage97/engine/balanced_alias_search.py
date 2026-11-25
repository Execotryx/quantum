# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Search A-only residue freedom in the exact balanced Horner arithmetic.

The only inputs are benchmark/search parameters.  For each segment the
search keeps a complete coefficient row for each available A mod8 residue.
The certificate uses every reachable residual and the largest legal x for
that residual, which is the tightest absolute phase-margin constraint.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
import json
import math
from pathlib import Path

import numpy as np

from numerical_core import Parameters, coefficient_seed, segment_inputs, target_values, signed_row_sum


def assemble_residue_model(template, search, frame):
    """Select certified rows; keep numerical indexing in the original frame.

    The physical decoder must apply the declared reversible address frame
    and reindex its lookup table accordingly.  The integer reference keeps
    the original mantissa address so its normalization remains transparent.
    All inputs here are mathematical parameter/search objects, never gates.
    """
    from balanced_model import balanced_table_words
    model=copy.deepcopy(template)
    alias_bits=int(frame['plan']['alias_bits'])
    selected=[]
    for record,label in zip(search['coefficients'],frame['labels']):
        candidates=[row for residue,row in record['residue_rows'].items()
                    if int(residue)&((1 << alias_bits)-1)==label
                    and row['certified_raw_phase_margin_turns']>=search['required_raw_margin_turns']]
        if not candidates:
            raise AssertionError('An affine label has no certified mathematical row.')
        row=min(candidates,key=lambda r:(-r['certified_raw_phase_margin_turns'],
                                         r['worst_relative_to_tolerance'],
                                         r['a'],r['b'],r['c'],r['high_anchor']))
        selected.append(copy.deepcopy(row))
    model.update(coefficients=selected,low_alias_bits=alias_bits,
                 shared_L={i:i for i in range(alias_bits)},
                 address_affine_rows=list(frame['plan']['rows']),
                 address_frame_constants=list(frame['plan']['constants']),
                 numerical_address_indexing='original_mantissa_address',
                 coefficient_alias_raw_margin_turns=search['required_raw_margin_turns'],
                 worst_relative_to_tolerance=max(row['worst_relative_to_tolerance'] for row in selected),
                 r_storage_width=max(row['r_max'] for row in selected).bit_length(),
                 r_full_width=max(row['r_prefix_max'] for row in selected).bit_length(),
                 c_storage_width=(max(row['c'] for row in selected) >> model['c_storage_shift']).bit_length(),
                 nearest_anchor_pass=dict(changed_addresses=[],physical_high_frame='H-1',
                                          initial_output_top_xor_bits=[18,19],
                                          initial_output_top_xor_constant=1,
                                          selection='chosen during coefficient residue search'))
    for row,label in zip(selected,frame['labels']):
        if row['a']&((1 << alias_bits)-1)!=label:
            raise AssertionError('The selected A residue does not match the address frame.')
        unsigned=row['low_constant']+(1 << model['high_shift'])
        if ((unsigned >> 18)^(unsigned >> 19))&1!=1:
            raise AssertionError('The nearest initial top-bit relation was lost.')
    model['physical_table_words']=balanced_table_words(model)
    model['physical_table_words_unsigned_cyclic']=balanced_table_words(model,unsigned_cyclic=True)
    return model


def minimum_normalization_shift(address, q, p):
    exponent, index=divmod(address,1 << p.segment_bits)
    normalized=(((1 << p.segment_bits)+index) << p.residual_bits)+q
    normalized=normalized >> (1-exponent)
    candidate=normalized.copy()
    shifts=np.zeros_like(q)
    while np.any(candidate>p.max_x):
        excessive=candidate>p.max_x
        if np.any(excessive & ((candidate & 3)!=0)):
            raise AssertionError('A residual marked reachable cannot normalize to a legal x.')
        candidate=np.where(excessive,candidate >> 2,candidate)
        shifts+=excessive.astype(np.int64)
    return shifts


def search_residue_rows(*, radius_b=12, radius_c=32,
                         curvature_storage_shift=3,
                         required_margin_turns=1e-12, verbose=True,
                         label_mode='a3'):
    if label_mode not in ('a3','a2c1'):
        raise ValueError('Unknown mathematical residue label.')
    p=Parameters(output_fraction_bits=26,derivative_fraction_bits=25,
                 address_sharing=False)
    cstep=1 << curvature_storage_shift
    main_shift=p.second_row_fraction_bits-2
    records=[]
    search_floor=-3e-12
    for address in range(p.num_segments):
        q=segment_inputs(address,p)
        if not len(q):
            raise AssertionError('The fine benchmark should reach every segment.')
        minimum_k=minimum_normalization_shift(address,q,p)
        phase_scale=np.ldexp(np.ones_like(q,dtype=float),minimum_k-p.phase_fraction_bits)
        target=target_values(address,q,p)*2.0**p.output_fraction_bits
        tolerance=np.ldexp(target,-p.precision_bits)
        allowance=tolerance-search_floor/phase_scale
        _,bseed,cseed=coefficient_seed(address,p)
        first_c=max(0,round(cseed)-radius_c)
        first_c+=-first_c%cstep
        best={}
        for c in range(first_c,round(cseed)+radius_c+1,cstep):
            curvature=signed_row_sum(c,q,p.first_row_fraction_bits,p.residual_bits)
            first_b=round(bseed)-radius_b
            first_b+=(-c//2-first_b)%2
            for b in range(first_b,round(bseed)+radius_b+1,2):
                full=b-curvature
                if int(full.min())<0:
                    continue
                r=full >> 1
                correction=signed_row_sum(r,q,main_shift,p.residual_bits) >> 1
                required=target+correction
                lower=math.ceil(float(np.max(required-allowance))+1e-7)
                upper=math.floor(float(np.min(required+allowance))-1e-7)
                if lower>upper:
                    continue
                cmin,cmax=int(correction.min()),int(correction.max())
                for a in range(lower,upper+1):
                    high=(a+(1 << (p.high_shift-1))) >> p.high_shift
                    if not 1<=high<=(1 << p.high_width):
                        continue
                    low_min=a-cmax-(high << p.high_shift)
                    low_max=a-cmin-(high << p.high_shift)
                    if not -(1 << p.high_shift)<=low_min<=low_max<(1 << p.high_shift):
                        continue
                    remaining=(tolerance-np.abs(a-required))*phase_scale
                    margin=float(remaining.min())
                    residue=(a&7 if label_mode=='a3' else
                             (a&3)|(((c >> curvature_storage_shift)&1)<<2))
                    ratio=float((np.abs(a-required)/tolerance).max())
                    key=(-margin,ratio,a,b,c,high)
                    if residue not in best or key<best[residue][0]:
                        at=int(remaining.argmin())
                        row=dict(address=address,a=a,b=b,c=c,high_anchor=high,
                                 low_constant=a-(high << p.high_shift),r_initial=b >> 1,
                                 r_full_min=int(full.min()),r_full_max=int(full.max()),
                                 r_prefix_min=b-c//2,r_prefix_max=b+c//2,
                                 r_min=int(r.min()),r_max=int(r.max()),
                                 y_min=a-cmax,y_max=a-cmin,low_min=low_min,low_max=low_max,
                                 worst_relative_to_tolerance=ratio,at_q=int(q[at]),
                                 certified_raw_phase_margin_turns=margin,
                                 margin_minimum_k=int(minimum_k[at]))
                        best[residue]=(key,row)
        mask=sum(1 << residue for residue,(_,row) in best.items()
                 if row['certified_raw_phase_margin_turns']>=required_margin_turns)
        record=dict(address=address,feasible_residue_mask=mask,
                    residue_rows={str(residue):value[1] for residue,value in sorted(best.items())})
        records.append(record)
        if verbose and (address%16==0 or not mask):
            print(dict(address=address,mask=mask,feasible_labels=mask.bit_count()),flush=True)
    result=dict(schema='balanced-A-only-residue-search-v1',parameters=asdict(p),
                c_storage_shift=curvature_storage_shift,r_storage_shift=1,
                required_raw_margin_turns=required_margin_turns,
                radius_b=radius_b,radius_c=radius_c,guard_bits=1,
                masks=[r['feasible_residue_mask'] for r in records],
                coefficients=records)
    result['mod4_masks']=[sum(1 << bit for bit in range(4)
                             if mask & ((1 << bit)|(1 << (bit+4))))
                          for mask in result['masks']]
    if label_mode!='a3':
        result['label_mode']=label_mode
    return result


