# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Width-bounded high-word increments for sparse-tail phase fusion.

These routines preserve the packed shift and all tail bits. A paired
increment uses a temporary AND as its incoming carry, releases that carry
after its first forward use, and keeps only classical carry-phase debts
through the phase pass. The inverse recomputes and repays every debt.
No coefficient value or gate sequence is embedded in this module.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass

import kickmix as km
from paired_arithmetic import inverse_add
from virtual_lsb import _add_disposable_carry
from packed_phase import packed_threshold_plan,_phase_masked_polynomial
from quadratic_terms import xor_polynomial
from cyclic_phase import _erase_polynomial


@dataclass
class PackedThreshold:
    threshold:int
    control:object
    t:object
    q:tuple
    consumed:bool=False


def _and(builder,a,b):
    out=builder.alloc_qubits(1)[0]
    builder.ccx(a,b,out)
    return out


def _clear_and(builder,a,b,out):
    builder.del_and(a,b,out);builder.free(out)


def make_threshold(builder,packed,threshold=7,*,u=None):
    """Compute k>=threshold with2/3 ANDs on the certified packed domain.

    k>=7: t*packed[1]*(packed[3] XOR packed[0]*packed[2])
    k>=8: t*packed[1]*packed[3]
    k>=9: t*packed[1]*packed[3]*(packed[0] XOR packed[2])
    k>=10: t*packed[0]*packed[3]

    The formulas vanish for k=0 (t=0) and k=1 (packed[0]=packed[1]=0), including
    arbitrary packed[2]/packed[3] in those cases. They are checked on every
    fixed code for k=2..10 by the independent proof fixture.
    """
    if not packed.is_packed or packed.max_k!=10 or threshold not in (7,8,9,10):
        raise ValueError('Sparse-tail thresholds require packed k in0..10.')
    q=tuple(packed.residual[:4]);t=packed.t
    if u is not None:
        if not isinstance(u,km.q) or u in q+(t,):
            raise ValueError('A shared k>=2 wire must be a distinct preserved qubit.')
        plan=packed_threshold_plan(threshold)
        if threshold==8:
            out=_and(builder,u,q[3])
        else:
            helper=builder.alloc_qubits(1)[0]
            xor_polynomial(builder,list(q),helper,plan.terms)
            out=_and(builder,u,helper)
            _erase_polynomial(builder,helper,list(q),plan.terms)
        return PackedThreshold(threshold,out,t,q)
    a=_and(builder,t,q[0] if threshold==10 else q[1])
    if threshold in (8,10):
        out=_and(builder,a,q[3])
    elif threshold==7:
        b=_and(builder,q[0],q[2]);builder.cx(q[3],b)
        out=_and(builder,a,b)
        builder.cx(q[3],b);_clear_and(builder,q[0],q[2],b)
    else:
        builder.cx(q[2],q[0])
        b=_and(builder,q[0],q[3])
        out=_and(builder,a,b)
        _clear_and(builder,q[0],q[3],b)
        builder.cx(q[2],q[0])
    _clear_and(builder,t,q[0] if threshold==10 else q[1],a)
    return PackedThreshold(threshold,out,t,q)


def erase_threshold(builder,token,*,u=None,ledger=None):
    """Repay every threshold-HMR outcome on the still-live packed inputs."""
    if token.consumed:raise ValueError('Threshold token was already consumed.')
    token.consumed=True
    measured=builder.alloc_bits(1)[0]
    builder.hmr(token.control,measured);builder.free(token.control)
    if ledger is not None:
        ledger.record(token.threshold,measured)
        return
    t,q=token.t,token.q
    if u is not None:
        plan=packed_threshold_plan(token.threshold)
        _phase_masked_polynomial(builder,u,list(q),plan.terms,measured)
        builder.free(measured)
        return
    builder.push_condition(measured)
    if token.threshold in (8,10):
        builder.ccz(t,q[0] if token.threshold==10 else q[1],q[3])
    else:
        a=_and(builder,t,q[1])
        if token.threshold==7:
            builder.cz(a,q[3]);builder.ccz(a,q[0],q[2])
        else:
            builder.cx(q[2],q[0]);builder.ccz(a,q[0],q[3]);builder.cx(q[2],q[0])
        _clear_and(builder,t,q[1],a)
    builder.pop_condition();builder.free(measured)


@contextmanager
def threshold_control(builder,packed,threshold=7,*,u=None):
    token=make_threshold(builder,packed,threshold,u=u)
    try:
        yield token.control
    finally:
        erase_threshold(builder,token,u=u)


@dataclass
class IncrementToken:
    debt:object
    control:object
    tail:object
    width:int
    consumed:bool=False


def forward_increment(builder,word,control,tail):
    """word += control*tail modulo2**width; no quantum carry survives."""
    word=list(word)
    if not word or len(set(word+[control,tail]))!=len(word)+2:
        raise ValueError('Increment word and its two factors must be nonempty/disjoint.')
    carry=_and(builder,control,tail)
    debt=_add_disposable_carry(builder,[],word,carry,
        lambda:_clear_and(builder,control,tail,carry))
    return IncrementToken(debt,control,tail,len(word))


def inverse_increment(builder,word,token,*,carry_budget=None):
    """Undo the matching increment, including every deferred carry sign."""
    word=list(word)
    if token.consumed or len(word)!=token.width:
        raise ValueError('Missing matching unconsumed high increment.')
    token.consumed=True
    def make():return _and(builder,token.control,token.tail)
    def erase(carry):_clear_and(builder,token.control,token.tail,carry)
    carry=make()
    released=inverse_add(builder,[],word,token.debt,carry_in=carry,
        carry_budget=carry_budget,carry_lifecycle=(erase,make))
    if not released:erase(carry)
