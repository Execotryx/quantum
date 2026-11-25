# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Bounded main Horner groups with their result LSB represented by source parity.

The result's omitted low bit is a known affine function of preserved source
bits. Signed row additions update that parity independently of their signs.
The physical target contains only the quotient by two. This interface tracks
the parity through any order of complete bounded row groups.
"""
from __future__ import annotations

from dataclasses import dataclass,replace
import kickmix as km

from paired_arithmetic import release_saved_bit,repay_saved_bit
from split_bounded import SplitBoundedToken,_digit_count,_row_controls
from variable_lsb_main import row_parity_mask
from virtual_lsb import SourceParity,forward_virtual_row,inverse_virtual_row


def virtual_main_plan(logical_plan):
    """Turn a certified full-result bound into a bound on its quotient update.

    If Delta is the full signed update and p is the old omitted bit, the
    physical update is floor((p+Delta)/2), whose magnitude is at most
    ceil(maximum_absolute_sum/2). Its sign is either Delta's sign or zero,
    so the existing last-digit sign certificate remains valid.
    """
    if logical_plan.signed_source:
        raise ValueError('The virtual main source must be unsigned.')
    maximum=(logical_plan.maximum_absolute_sum+1)//2
    width=maximum.bit_length()+1 if maximum else 0
    return replace(logical_plan,window=width,maximum_absolute_sum=maximum)


@dataclass
class VirtualMainToken(SplitBoundedToken):
    parity_before:int=0
    parity_after:int=0
    row_parities:object=None
    external_lsb:object=False
    parity_constant:bool=False


def _row_seed(parity,source_width,shift,external_lsb=False,parity_constant=False):
    cut=-shift
    return SourceParity(parity ^ ((1 << cut) if 0<=cut<source_width else 0),
                        constant=parity_constant,
                        extra_wires=(external_lsb,) if isinstance(external_lsb,km.q) else ())


def forward_virtual_main_low(builder,digits,source,low,plan,*,parity_before=1,
                              saved_bit=None,external_lsb=False,parity_constant=False):
    """Add one group, retaining only a parity description of its logical LSB.

    `plan` is returned by virtual_main_plan; `low` has its physical window
    width. The initial omitted result bit equals XOR(source[i] for bits in
    parity_before). The next group's parity_before is token.parity_after.
    Existing bounded high-correction routines accept the returned token.
    """
    source,low=list(source),list(low)
    if _digit_count(digits)!=plan.digits or len(low)!=plan.window or not low:
        raise ValueError('Virtual-main widths must match a nonempty physical window.')
    if parity_before<0 or parity_before >> len(source):
        raise ValueError('The omitted result bit must be a parity on source wires.')
    if external_lsb is not False and (not isinstance(external_lsb,km.q) or external_lsb in source+low):
        raise ValueError('External original LSB must be a separate preserved quantum wire.')
    saved=saved_bit
    if saved is None:
        saved=builder.alloc_qubits(1)[0];builder.cx(low[-1],saved)
    elif not isinstance(saved,km.q) or saved in source+low:
        raise ValueError('Saved original window MSB must be a separate quantum wire.')
    token=VirtualMainToken(plan,saved,len(low),[],parity_before=parity_before,
                           row_parities=[],external_lsb=external_lsb,
                           parity_constant=bool(parity_constant))
    parity=parity_before
    rows=list(zip(range(plan.first,plan.last),plan.shifts))
    for index,shift,sign in _row_controls(digits,rows):
        seed=_row_seed(parity,len(source),shift,external_lsb,parity_constant)
        token.row_parities.append(seed)
        token.row_debts.append(forward_virtual_row(builder,source,low,shift=shift,sign=sign,
                                                   initial_lsb=seed))
        parity^=row_parity_mask(len(source),shift)
    token.parity_after=parity
    return token


def inverse_virtual_main_low(builder,digits,source,low,token,*,carry_budget=None):
    """Reverse a physical quotient group and repay all measured carry phases."""
    source,low=list(source),list(low)
    plan=token.plan
    if token.stage!='high_undone' or len(low)!=token.window or _digit_count(digits)!=plan.digits:
        raise ValueError('Virtual inverse low rows must follow their matching inverse high correction.')
    if token.saved_bit is not None:
        token.saved_measurement=release_saved_bit(builder,token.saved_bit)
        token.saved_bit=None
    rows=list(reversed(list(zip(range(plan.first,plan.last),plan.shifts))))
    for index,shift,sign in _row_controls(digits,rows):
        offset=index-plan.first
        inverse_virtual_row(builder,source,low,token.row_debts[offset],shift=shift,sign=sign,
                              initial_lsb=token.row_parities[offset],carry_budget=carry_budget)
    if token.saved_measurement is None:
        raise ValueError('Missing original physical window-MSB phase record.')
    repay_saved_bit(builder,low[-1],token.saved_measurement)
    token.saved_measurement=None
    token.stage='consumed'
