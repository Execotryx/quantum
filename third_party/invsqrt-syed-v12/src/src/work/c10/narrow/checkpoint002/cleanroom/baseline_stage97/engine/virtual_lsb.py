# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Horner rows with an omitted, mathematically known low coefficient bit.

For a coefficient with a preserved original low bit B0, ascending rounded
rows of unsigned C give virtual low bit B0 XOR C[cut] immediately before
RN(C/2**cut), and B0 XOR C[cut-1] immediately afterward. At cut0 the output
bit is B0. The stored word is the quotient by two. In the complemented
target frame its carry is the one-product mux
C[cut] XOR (sign XOR B0)*(C[cut] XOR C[cut-1]), with absent C bits zero.

The mux is measured and repaid after the first physical forward bit, so it
shares the two-carry allocation budget. In the inverse it remains until
the exact segmented carry cleanup finishes. Final table decoding must make
enough inverse carry space available; this module does not hide that cost.
"""
from __future__ import annotations
from dataclasses import dataclass

import kickmix as km
from fusion.arithmetic import _compute_carry,_sum_keep_carry
from paired_arithmetic import (CarryDebt,_inputs,_finish_top,forward_signed_row,
                               inverse_signed_row,inverse_add,
                               release_saved_bit,repay_saved_bit)
from staged_arithmetic import BoundedRowsPlan
from split_bounded import SplitBoundedToken,_digit,_digit_count
from quadratic_terms import xor_polynomial
from cyclic_phase import _erase_polynomial


@dataclass
class VirtualRowDebt:
    shift:int
    ordinary:bool
    inactive:bool
    carry_debt:object


@dataclass(frozen=True)
class SourceParity:
    """A preserved affine parity of source bits, requiring no physical helper."""
    mask:int
    constant:bool=False
    extra_wires:tuple=()


def virtual_rows_plan(*,digits,source_min,source_max,first_shift):
    """Certify every source and all digit choices for the final quotient."""
    if source_min<0 or source_min>source_max or first_shift>=0:
        raise ValueError('Expected an unsigned source and an initial right shift.')
    shifts=tuple(first_shift+i for i in range(digits))
    maximum=0
    for value in range(source_min,source_max+1):
        if value >> -first_shift:
            raise ValueError('The initial omitted bit must be zero for the whole source interval.')
        operands=[(value << s) if s>=0 else (value+(1 << (-s-1))) >> -s for s in shifts]
        total=sum(operands)
        if total&1:
            raise ValueError('The final omitted bit is not identically zero.')
        if 2*operands[-1]<total:
            raise ValueError('The final digit does not determine the total update sign.')
        maximum=max(maximum,total//2)
    window=maximum.bit_length()+1 if maximum else 0
    return BoundedRowsPlan(digits,0,digits,shifts,window,maximum,
                           source_min,source_max,False)


def _carry_terms(source,sign,cut,initial_lsb=False):
    variables=list(source)+[sign]
    q=1 << len(source)
    originals=[]
    constant=False
    if isinstance(initial_lsb,SourceParity):
        if initial_lsb.mask<0 or initial_lsb.mask >> len(source):
            raise ValueError('Source parity mask exceeds the coefficient width.')
        originals=[1 << index for index in range(len(source)) if initial_lsb.mask >> index&1]
        constant=initial_lsb.constant
        for wire in initial_lsb.extra_wires:
            if not isinstance(wire,km.q) or wire in variables:
                raise ValueError('Extra parity wires must be distinct from source and sign.')
            originals.append(1 << len(variables))
            variables.append(wire)
    elif isinstance(initial_lsb,km.q):
        if initial_lsb in variables:
            raise ValueError('Original coefficient LSB must be a separate preserved wire.')
        originals=[1 << len(variables)]
        variables.append(initial_lsb)
    elif initial_lsb not in (False,True):
        raise ValueError('Original coefficient LSB must be a wire or Boolean constant.')
    else:
        constant=bool(initial_lsb)
    terms=[]
    if cut<len(source):
        a=1 << cut
        terms.extend((a,a|q))
        terms.extend(a|original for original in originals)
        if constant:terms.append(a)
    if cut>=1 and cut-1<len(source):
        c=1 << (cut-1)
        terms.append(c|q)
        terms.extend(c|original for original in originals)
        if constant:terms.append(c)
    return variables,tuple(terms)


def _add_disposable_carry(builder,source,target,carry,release):
    """Forward paired adder releasing its source-derived first carry early."""
    a,b,preserve=_inputs(source,target,carry,False)
    width=len(b)
    debts={}
    if not width:
        release()
        return CarryDebt(debts,width)
    if width==1:
        builder.cx(a[0],b[0]);builder.cx(carry,b[0])
        release()
        return CarryDebt(debts,width)
    incoming=carry
    released=False
    for index,(aa,bb) in enumerate(zip(a[:-2],b[:-2])):
        frame=_compute_carry(builder,aa,bb,incoming,preserve=preserve)
        _sum_keep_carry(builder,frame)
        if index==0:
            release();released=True
        else:
            outcome=builder.alloc_bits(1)[0]
            builder.hmr(incoming,outcome);builder.free(incoming)
            debts[index]=outcome
        incoming=frame.outgoing
    _finish_top(builder,a,b,incoming,preserve)
    if not released:
        release()
    if width>2:
        outcome=builder.alloc_bits(1)[0]
        builder.hmr(incoming,outcome);builder.free(incoming)
        debts[width-2]=outcome
    return CarryDebt(debts,width)


def forward_virtual_row(builder,source,target,*,shift,sign,initial_lsb=False):
    source,target=list(source),list(target)
    if shift>0:
        debt=forward_signed_row(builder,source,target,shift=shift-1,sign=sign)
        return VirtualRowDebt(shift,True,False,debt)
    cut=-shift
    variables,terms=_carry_terms(source,sign,cut,initial_lsb)
    high_source=source[cut+1:]
    if not terms and not high_source:
        return VirtualRowDebt(shift,False,True,None)
    carry=builder.alloc_qubits(1)[0]
    xor_polynomial(builder,variables,carry,terms)
    for wire in target:
        builder.cx(sign,wire)
    debt=_add_disposable_carry(builder,high_source,target,carry,
        lambda:_erase_polynomial(builder,carry,variables,terms))
    for wire in target:
        builder.cx(sign,wire)
    return VirtualRowDebt(shift,False,False,debt)


def inverse_virtual_row(builder,source,target,token,*,shift,sign,carry_budget=None,
                         initial_lsb=False,release_carry=True,overflow_phase=None,
                         allow_dirty_overflow=False):
    if shift!=token.shift:
        raise ValueError('Virtual row token belongs to another shift.')
    source,target=list(source),list(target)
    if token.inactive:
        return
    if token.ordinary:
        inverse_signed_row(builder,source,target,token.carry_debt,
                            shift=shift-1,sign=sign,carry_budget=carry_budget,
                            overflow_phase=overflow_phase,allow_dirty_overflow=allow_dirty_overflow)
        return
    cut=-shift
    variables,terms=_carry_terms(source,sign,cut,initial_lsb)
    def make_carry():
        wire=builder.alloc_qubits(1)[0]
        xor_polynomial(builder,variables,wire,terms)
        return wire
    def erase_carry(wire):
        _erase_polynomial(builder,wire,variables,terms)
    carry=make_carry()
    for wire in target:
        builder.cx(sign,wire)
    released=inverse_add(builder,source[cut+1:],target,token.carry_debt,
                         carry_in=carry,carry_budget=carry_budget,
                         carry_lifecycle=(erase_carry,make_carry) if release_carry else None,
                         overflow_phase=overflow_phase,allow_dirty_overflow=allow_dirty_overflow)
    for wire in target:
        builder.cx(sign,wire)
    if not released:
        erase_carry(carry)


@dataclass
class VirtualBlockToken(SplitBoundedToken):
    initial_lsb:object=False


def forward_virtual_low(builder,digits,source,low,plan,*,saved_bit=None,initial_lsb=False):
    """All ascending virtual-LSB rows, without allocating a saved old MSB.

    The original old MSB may be decoded from static coefficient information
    after these rows and assigned to token.saved_bit. It must be assigned
    before the existing forward_bounded_high operation is called.
    """
    low,source=list(low),list(source)
    if _digit_count(digits)!=plan.digits or len(low)!=plan.window:
        raise ValueError('Virtual-low data widths do not match the plan.')
    token=VirtualBlockToken(plan,saved_bit,len(low),[],initial_lsb=initial_lsb)
    for index,shift in enumerate(plan.shifts):
        if shift<=0 and -shift>len(source):
            token.row_debts.append(VirtualRowDebt(shift,False,True,None))
            continue
        with _digit(digits,index) as sign:
            token.row_debts.append(forward_virtual_row(builder,source,low,shift=shift,sign=sign,
                                                       initial_lsb=initial_lsb))
    return token


def inverse_virtual_low(builder,digits,source,low,token,*,carry_budget=None,initial_lsb=None):
    """Reverse virtual rows after inverse high correction and phase repay."""
    low,source=list(low),list(source)
    if token.stage!='high_undone' or len(low)!=token.window:
        raise ValueError('Virtual inverse low must follow its inverse high correction.')
    if token.saved_bit is not None:
        token.saved_measurement=release_saved_bit(builder,token.saved_bit)
        token.saved_bit=None
    if initial_lsb is None:
        initial_lsb=token.initial_lsb
    for index in reversed(range(len(token.plan.shifts))):
        debt=token.row_debts[index]
        if debt.inactive:
            continue
        with _digit(digits,index) as sign:
            inverse_virtual_row(builder,source,low,debt,shift=token.plan.shifts[index],
                                  sign=sign,carry_budget=carry_budget,initial_lsb=initial_lsb)
    if token.saved_measurement is None:
        raise ValueError('Missing saved original top-bit measurement.')
    repay_saved_bit(builder,low[-1],token.saved_measurement)
    token.saved_measurement=None
    token.stage='consumed'
