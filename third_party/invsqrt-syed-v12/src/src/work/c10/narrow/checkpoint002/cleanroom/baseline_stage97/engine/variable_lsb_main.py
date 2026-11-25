# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Grouped main Horner rows for derivative 2*R+B0, with B0=original L0.

Only the final two rounded rows depend on the omitted derivative bit. They
must be consecutive within one group. A temporary B0 is reconstructed from
the current result LSB and the known source-row parity immediately before
the pair, then cleared immediately afterward. It is absent during all other
rows and during phase application. No measurement is used to erase it.
"""
from __future__ import annotations

from dataclasses import dataclass,replace
import kickmix as km

from paired_arithmetic import (CarryDebt,forward_add,inverse_add,
                               forward_signed_row,inverse_signed_row,
                               release_saved_bit,repay_saved_bit)
from split_bounded import SplitBoundedToken,_digit_count,_row_controls


@dataclass
class VariableLsbToken(SplitBoundedToken):
    parity_before:int=0
    parity_after:int=0


def row_parity_mask(source_width,shift):
    """Source-only parity of RN(R*2**shift), with signs immaterial mod2."""
    if shift>0:
        return 0
    if shift==0:
        return int(source_width>0)
    cut=-shift
    return ((1 << cut) if cut<source_width else 0) ^ \
           ((1 << (cut-1)) if cut-1<source_width else 0)


def _frame_alias(builder,helper,low_bit,source,mask):
    builder.cx(low_bit,helper)
    for index,wire in enumerate(source):
        if mask >> index&1:
            builder.cx(wire,helper)


def _check_plan(plan,source_width):
    if plan.signed_source or not plan.shifts or plan.shifts[0]-plan.first!=2-plan.digits:
        raise ValueError('Expected unsigned stored R with final ordinary shifts0 and1.')
    pair=range(plan.digits-2,plan.digits)
    included=sum(plan.first<=index<plan.last for index in pair)
    if included==1:
        raise ValueError('Both omitted-bit-dependent rows must belong to the same group.')
    if included:
        bound=plan.maximum_absolute_sum+2
        if bound >= 1 << (plan.window-1):
            raise ValueError('The original signed window does not cover both extra B0 terms.')
        # The largest and next-largest rows both gain B0; the certificate
        # that the last term dominates the others is therefore unchanged.
        plan=replace(plan,maximum_absolute_sum=bound)
    return plan


def _special_row(builder,source,low,lsb,sign,kind,*,inverse=False,debt=None,
                  carry_budget=None):
    if kind=='word':
        function=inverse_signed_row if inverse else forward_signed_row
        arguments=dict(shift=0,sign=sign)
        if inverse:
            arguments['carry_budget']=carry_budget
            return function(builder,[lsb]+source,low,debt,**arguments)
        return function(builder,[lsb]+source,low,**arguments)
    for wire in low:
        builder.cx(sign,wire)
    if inverse:
        result=inverse_add(builder,source,low,debt,carry_in=lsb,
                           carry_budget=carry_budget)
    else:
        result=forward_add(builder,source,low,carry_in=lsb)
    for wire in low:
        builder.cx(sign,wire)
    return result


def forward_variable_low(builder,digits,source,low,plan,*,parity_before=0,
                          saved_bit=None):
    """Compatible low-group entry, returning a normal high-correction token.

    Start the complete main stage with parity_before=0. For each subsequent
    group, pass the preceding token.parity_after, including when groups are
    reordered. The initial full result LSB must equal the original omitted
    derivative bit B0. Source and digits are preserved. Existing
    forward_bounded_high/inverse_bounded_high operate on this token.
    """
    source,low=list(source),list(low)
    plan=_check_plan(plan,len(source))
    if _digit_count(digits)!=plan.digits or len(low)!=plan.window or not low:
        raise ValueError('Digit count and nonempty low width must match the plan.')
    if parity_before<0 or parity_before >> len(source):
        raise ValueError('The row parity must be a mask on the stored source bits.')
    saved=saved_bit
    if saved is None:
        saved=builder.alloc_qubits(1)[0];builder.cx(low[-1],saved)
    elif not isinstance(saved,km.q) or saved in source+low:
        raise ValueError('Saved original MSB must be a separate quantum wire.')
    token=VariableLsbToken(plan,saved,len(low),[],parity_before=parity_before)
    parity=parity_before
    lsb=None
    rows=list(zip(range(plan.first,plan.last),plan.shifts))
    for index,shift,sign in _row_controls(digits,rows):
        if index==plan.digits-2:
            lsb=builder.alloc_qubits(1)[0]
            _frame_alias(builder,lsb,low[0],source,parity)
            debt=_special_row(builder,source,low,lsb,sign,'carry')
        elif index==plan.digits-1:
            if lsb is None:
                raise AssertionError('The omitted-bit pair was separated.')
            debt=_special_row(builder,source,low,lsb,sign,'word')
            parity^=1  # The pair contributes R0; the two B0 terms cancel.
            _frame_alias(builder,lsb,low[0],source,parity)
            builder.free(lsb);lsb=None
        else:
            debt=forward_signed_row(builder,source,low,shift=shift,sign=sign)
            parity^=row_parity_mask(len(source),shift)
        token.row_debts.append(debt)
    if lsb is not None:
        raise AssertionError('Unfinished omitted-bit pair.')
    token.parity_after=parity
    return token


def inverse_variable_low(builder,digits,source,low,token,*,carry_budget=None):
    """Undo one matching variable-LSB group after its high correction."""
    source,low=list(source),list(low)
    plan=token.plan
    if token.stage!='high_undone' or len(low)!=token.window:
        raise ValueError('Inverse low rows must follow their matching inverse high correction.')
    if _digit_count(digits)!=plan.digits:
        raise ValueError('Digit count does not match the plan.')
    if token.saved_bit is not None:
        token.saved_measurement=release_saved_bit(builder,token.saved_bit)
        token.saved_bit=None
    parity=token.parity_after
    lsb=None
    rows=list(reversed(list(zip(range(plan.first,plan.last),plan.shifts))))
    for index,shift,sign in _row_controls(digits,rows):
        debt=token.row_debts[index-plan.first]
        if index==plan.digits-1:
            lsb=builder.alloc_qubits(1)[0]
            _frame_alias(builder,lsb,low[0],source,parity)
            _special_row(builder,source,low,lsb,sign,'word',inverse=True,
                         debt=debt,carry_budget=carry_budget)
        elif index==plan.digits-2:
            if lsb is None:
                raise AssertionError('The omitted-bit pair was separated.')
            _special_row(builder,source,low,lsb,sign,'carry',inverse=True,
                         debt=debt,carry_budget=carry_budget)
            parity^=1
            _frame_alias(builder,lsb,low[0],source,parity)
            builder.free(lsb);lsb=None
        else:
            inverse_signed_row(builder,source,low,debt,shift=shift,sign=sign,
                                carry_budget=carry_budget)
            parity^=row_parity_mask(len(source),shift)
    if lsb is not None or parity!=token.parity_before:
        raise AssertionError('Variable-LSB row parity failed to reverse.')
    if token.saved_measurement is None:
        raise ValueError('Missing saved-MSB measurement record.')
    repay_saved_bit(builder,low[-1],token.saved_measurement)
    token.saved_measurement=None
    token.stage='consumed'
