# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Defer packed-threshold measurement phases to reconstructed binary k.

For k in0..10 every threshold [k>=j] has an exact ANF containing only
linear/quadratic terms and, possibly, the common cubic f0*f1*f2. Combining
the measured coefficients therefore needs at most one conditioned CCZ in
total, regardless of the number of compact threshold erasures.
"""
from __future__ import annotations
from contextlib import contextmanager
from functools import lru_cache

import kickmix as km
import packed_phase
import packed_shift
from packed_shift import PackedShift
from codebook import BinarySpan
from quadratic_terms import xor_polynomial
from cyclic_phase import _erase_polynomial


@lru_cache(maxsize=10)
def threshold_terms(threshold):
    """Derive the common-cubic extension from exact k<=10 truth tables."""
    if not 1<=threshold<=10:raise ValueError('Threshold must be in1..10.')
    monomials=tuple(mask for mask in range(16) if mask.bit_count()<=2 or mask==7)
    columns=[sum(int(k&mask==mask) << k for k in range(11)) for mask in monomials]
    target=sum(int(k>=threshold) << k for k in range(11))
    span=BinarySpan(columns);solution=span.solve(target)
    if solution is None:raise AssertionError('The threshold has no common-cubic extension.')
    choices=[]
    for select in range(1 << len(span.nullspace)):
        candidate=solution
        for i,relation in enumerate(span.nullspace):
            if select >> i&1:candidate^=relation
        terms=tuple(monomials[i] for i in range(len(monomials)) if candidate >> i&1)
        choices.append(((7 in terms,len(terms),terms),terms))
    terms=min(choices)[1]
    for k in range(11):
        if (sum(int(k&mask==mask) for mask in terms)&1)!=int(k>=threshold):
            raise AssertionError('Threshold ANF certificate failed.')
    return terms


class ThresholdPhaseLedger:
    """Own threshold HMR outcomes until a binary-k register is available.

    ``conditions`` records any surrounding classical measurement guards.
    Those guard bits are borrowed and must keep their values until repayment;
    the measured output is owned by this ledger and must not be freed/reused.
    Multiplying by the recorded guards also handles stale output bits from
    inactive HMR instructions. Ordinary packed-phase erasures are unconditional.
    """
    def __init__(self):
        self.pending=[]
        self._owned=set()

    def record(self,threshold,outcome,*,conditions=()):
        terms=threshold_terms(int(threshold))
        if outcome in self._owned:raise ValueError('A threshold outcome already has an owner.')
        conditions=tuple(conditions)
        if any(not isinstance(bit,km.b) for bit in (outcome,)+conditions):
            raise ValueError('Threshold debts and their guards must be classical bits.')
        self._owned.add(outcome)
        self.pending.append((terms,outcome,conditions))

    def erase(self,builder,wire,threshold,*,conditions=()):
        outcome=builder.alloc_bits(1)[0]
        builder.hmr(wire,outcome);builder.free(wire)
        self.record(threshold,outcome,conditions=conditions)
        return outcome

    def repay(self,builder,flags):
        flags=list(flags)
        if len(flags)!=4:raise ValueError('Threshold repayment needs four reconstructed binary flags.')
        if not self.pending:return dict(outcomes=0,cubic_corrections=0)
        by_term={}
        for terms,outcome,conditions in self.pending:
            for term in terms:by_term.setdefault(term,[]).append((outcome,conditions))
        for term,records in sorted(by_term.items()):
            parity=builder.alloc_bits(1)[0]
            builder.bit_store(parity,False)
            for outcome,conditions in records:
                for guard in conditions:builder.push_condition(guard)
                builder.cx(outcome,parity)
                for _ in conditions:builder.pop_condition()
            builder.push_condition(parity)
            wires=[flags[i] for i in range(4) if term >> i&1]
            if len(wires)==1:builder.z(wires[0])
            elif len(wires)==2:builder.cz(*wires)
            elif len(wires)==3:builder.ccz(*wires)
            elif wires:raise AssertionError('Unexpected high-degree threshold phase.')
            else:builder.z(True)
            builder.pop_condition();builder.free(parity)
        count=len(self.pending)
        for _,outcome,_ in self.pending:builder.free(outcome)
        self.pending.clear();self._owned.clear()
        return dict(outcomes=count,cubic_corrections=int(7 in by_term),
            common_cubic='f0*f1*f2',quantum_workspace=0)


class PackedThresholdPhasePass:
    """Opt-in in-memory adapter; its threshold function can patch root aliases.

    Use ``with phase_pass.install():`` while building. It replaces compact
    packed thresholds and repays each ledger immediately after the matching
    PackedShift.unpack has reconstructed binary flags. Modules that imported
    ``_threshold`` by name should use ``phase_pass.threshold`` explicitly.
    """
    def __init__(self,*,merge_external_t=True):
        self.ledgers={};self.repayments=[]
        self.original_threshold=packed_phase._threshold
        self.merge_external_t=bool(merge_external_t)
        self._provided={}

    def ledger(self,packed):
        return self.ledgers.setdefault(packed,ThresholdPhaseLedger())

    @contextmanager
    def reuse_threshold(self,packed,threshold,control):
        """Borrow an already certified [k>=threshold] wire, preserving it.

        The provider owns the wire and its eventual erasure. In particular,
        a retained g9 also makes g10=g9*packed[0] on every valid packed state.
        """
        threshold=int(threshold)
        threshold_terms(threshold)
        if not isinstance(control,km.q):raise ValueError('A reused threshold must be a quantum wire.')
        key=(packed,threshold)
        if key in self._provided:raise ValueError('This threshold already has an active provider.')
        self._provided[key]=control
        try:yield control
        finally:del self._provided[key]

    @contextmanager
    def threshold(self,builder,packed,u,threshold,*,phase_conditions=()):
        supplied=self._provided.get((packed,threshold))
        if supplied is not None:
            yield supplied,0,0
            return
        nine=self._provided.get((packed,9))
        if threshold==10 and nine is not None:
            # For k9/10, packed q0=f1 distinguishes the two. Else g9=0,
            # including the arbitrary residual bits allowed when k0/1.
            q0=packed.residual[0]
            control=builder.alloc_qubits(1)[0]
            builder.ccx(nine,q0,control)
            try:yield control,1,0
            finally:
                builder.del_and(nine,q0,control);builder.free(control)
            return
        available=builder.max_qubits-builder.num_allocated_qubits
        plan=packed_phase.packed_threshold_plan(threshold) if threshold>=3 else None
        if plan is None or not plan.products or available>=3:
            with self.original_threshold(builder,packed,u,threshold) as value:
                yield value
            return
        q=list(packed.residual[:4])
        helper=builder.alloc_qubits(1)[0]
        xor_polynomial(builder,q,helper,plan.terms)
        control=builder.alloc_qubits(1)[0]
        builder.ccx(u,helper,control)
        _erase_polynomial(builder,helper,q,plan.terms)
        try:
            yield control,plan.products+1,0
        finally:
            self.ledger(packed).erase(builder,control,threshold,conditions=phase_conditions)

    @contextmanager
    def install(self):
        old_threshold=packed_phase._threshold
        old_unpack=PackedShift.unpack
        old_erase_t=packed_shift._erase_t_from_flags
        self.original_threshold=old_threshold
        active=[]
        def erase_t(builder,flags,t):
            if not active or not self.merge_external_t:
                return old_erase_t(builder,flags,t)
            self.ledger(active[-1]).erase(builder,t,1)
        def unpack(packed):
            active.append(packed)
            try:
                flags=old_unpack(packed)
            finally:
                active.pop()
            ledger=self.ledgers.get(packed)
            if ledger is not None and ledger.pending:
                self.repayments.append(ledger.repay(packed.builder,flags))
            return flags
        packed_phase._threshold=self.threshold
        packed_shift._erase_t_from_flags=erase_t
        PackedShift.unpack=unpack
        try:
            yield self
        finally:
            packed_phase._threshold=old_threshold
            packed_shift._erase_t_from_flags=old_erase_t
            PackedShift.unpack=old_unpack
