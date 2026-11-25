# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Nested bounded updates with a source-parity representation of the low bit.

The final child always updates the whole outer physical window. Earlier
children use their certified smaller windows and a single high correction.
With two children, the only inner saved bit is a literal original table bit.
The caller may measure it into its table-phase ledger after the forward low
rows, and reconstruct it before the matching inverse child.
"""
from __future__ import annotations

from dataclasses import dataclass,field
import kickmix as km

from paired_arithmetic import release_saved_bit,repay_saved_bit
from split_bounded import (_digit_count,_row_controls,
                           forward_bounded_high,inverse_bounded_high)
from variable_lsb_main import row_parity_mask
from virtual_lsb import VirtualRowDebt,forward_virtual_row,inverse_virtual_row
from virtual_main import (VirtualMainToken,_row_seed,
                          forward_virtual_main_low,inverse_virtual_main_low)


@dataclass
class NestedVirtualToken(VirtualMainToken):
    children:list=field(default_factory=list)


def _full_virtual_rows(builder,digits,source,low,plan,*,parity_before=1,
                       inverse=False,token=None,carry_budget=None):
    """An entire physical word needs no separate high overflow correction."""
    if not inverse:
        token=VirtualMainToken(plan,None,len(low),[None]*(plan.last-plan.first),
                               stage='full_low_done',parity_before=parity_before,
                               row_parities=[None]*(plan.last-plan.first))
        parity=parity_before
        rows=[]
        for index,shift in zip(range(plan.first,plan.last),plan.shifts):
            offset=index-plan.first
            token.row_parities[offset]=_row_seed(parity,len(source),shift)
            parity^=row_parity_mask(len(source),shift)
            if shift<=0 and -shift>len(source):
                token.row_debts[offset]=VirtualRowDebt(shift,False,True,None)
            else:
                rows.append((index,shift))
        token.parity_after=parity
    else:
        rows=[(index,plan.shifts[index-plan.first])
              for index in reversed(range(plan.first,plan.last))
              if not token.row_debts[index-plan.first].inactive]
    for index,shift,sign in _row_controls(digits,rows):
        offset=index-plan.first
        if inverse:
            inverse_virtual_row(builder,source,low,token.row_debts[offset],
                                  shift=shift,sign=sign,
                                  initial_lsb=token.row_parities[offset],
                                  carry_budget=carry_budget)
        else:
            token.row_debts[offset]=forward_virtual_row(
                builder,source,low,shift=shift,sign=sign,
                initial_lsb=token.row_parities[offset])
    if inverse:token.stage='consumed'
    return token


def forward_nested_virtual_low(builder,digits,source,low,outer_plan,child_plans,
                                *,parity_before=1,saved_bit=None,
                                defer_outer_saved=False):
    """Compute child groups and retain original window-MSB phase witnesses.

    Every plan is a physical quotient plan from ``virtual_main_plan``. The
    caller's omitted initial low bit is the XOR of source bits selected by
    parity_before. ``defer_outer_saved`` leaves token.saved_bit unset; the
    caller must decode the original outer MSB before its high correction.
    """
    source,low,plans=list(source),list(low),list(child_plans)
    if _digit_count(digits)!=outer_plan.digits or len(low)!=outer_plan.window:
        raise ValueError('Outer physical word does not match its quotient plan.')
    if not plans or plans[0].first!=outer_plan.first or plans[-1].last!=outer_plan.last:
        raise ValueError('Children must cover the complete outer row interval.')
    if any(left.last!=right.first for left,right in zip(plans,plans[1:])):
        raise ValueError('Child intervals must be consecutive and disjoint.')
    if any(plan.window>len(low) or plan.signed_source for plan in plans):
        raise ValueError('Children must be unsigned-source updates inside the outer window.')
    if parity_before<0 or parity_before >> len(source):
        raise ValueError('Initial virtual low bit must be a source parity.')
    if defer_outer_saved and saved_bit is not None:
        raise ValueError('Supply a saved outer bit or defer its decode, not both.')
    if saved_bit is None and not defer_outer_saved:
        saved_bit=builder.alloc_qubits(1)[0]
        builder.cx(low[-1],saved_bit)
    elif saved_bit is not None and (not isinstance(saved_bit,km.q) or saved_bit in low+source):
        raise ValueError('The saved original outer bit must be a separate quantum wire.')
    token=NestedVirtualToken(outer_plan,saved_bit,len(low),[],
                              parity_before=parity_before,row_parities=[])
    parity=parity_before
    for position,plan in enumerate(plans):
        if position+1<len(plans) and plan.window<len(low):
            child=forward_virtual_main_low(builder,digits,source,low[:plan.window],plan,
                                            parity_before=parity)
            forward_bounded_high(builder,digits,low[:plan.window],low[plan.window:],child)
        else:
            child=_full_virtual_rows(builder,digits,source,low,plan,parity_before=parity)
        parity=child.parity_after
        token.children.append(child)
    token.parity_after=parity
    return token


def inverse_nested_virtual_low(builder,digits,source,low,token,*,carry_budget=None):
    """Undo all child groups after the separately performed outer high inverse."""
    source,low=list(source),list(low)
    if token.stage!='high_undone' or len(low)!=token.window:
        raise ValueError('Nested inverse low must follow its outer high correction.')
    if token.saved_bit is not None:
        token.saved_measurement=release_saved_bit(builder,token.saved_bit)
        token.saved_bit=None
    for child in reversed(token.children):
        if child.stage=='high_done':
            inverse_bounded_high(builder,digits,low[:child.window],low[child.window:],child,
                                   carry_budget=carry_budget)
            inverse_virtual_main_low(builder,digits,source,low[:child.window],child,
                                       carry_budget=carry_budget)
        elif child.stage=='full_low_done':
            _full_virtual_rows(builder,digits,source,low,child.plan,inverse=True,
                                token=child,carry_budget=carry_budget)
        else:
            raise ValueError('Nested child has already been consumed or has an invalid stage.')
    if token.saved_measurement is None:
        raise ValueError('Missing original outer-MSB measurement record.')
    repay_saved_bit(builder,low[-1],token.saved_measurement)
    token.saved_measurement=None
    token.stage='consumed'
