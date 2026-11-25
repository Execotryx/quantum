# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Exact branch-local terminal carry reuse for the paired inverse adder.

This opt-in pass acts on an inverse terminal whose two high source bits
are zero and whose overflow sign is controlled by an HMR outcome. The
ordinary terminal costs one data CCX plus one conditioned CCZ: 1.5 mean
Toffolis. Its measurement-one branch instead consumes two earlier carry
frames, reuses one cleared wire for the terminal product, and phases that
product by CZ. One new HMR debt is a composition of two borrow majorities;
its cubic part has one product and needs one conditioned CCZ. Thus the
branch costs 1.5, the zero branch costs 1, and the mean is 1.25.

All live data and both recycled carry wires have the same final state in
both branches. No quantum wire is allocated by the replacement. This is a
generator pass, not a gate sequence extracted from a compiled circuit.
"""
from __future__ import annotations

from contextlib import contextmanager
import kickmix as km

import paired_arithmetic as paired
from fusion.arithmetic import _compute_carry, _erase_carry, _sum_keep_carry


def _erase_without_free(builder, frame, *, write_sum):
    """The ordinary exact erasure, keeping the cleared allocation reusable."""
    a,b,incoming,outgoing=frame.a,frame.b,frame.incoming,frame.outgoing
    if outgoing is False:
        return
    if frame.preserve_sign:
        raise ValueError('The conditioned terminal currently requires unsigned source frames.')
    if a is False:
        builder.del_and(incoming,b,outgoing)
        if write_sum:builder.cx(incoming,b)
    else:
        builder.cx(incoming,outgoing)
        builder.del_and(a,b,outgoing)
        builder.cx(incoming,a)
        builder.cx(a if write_sum else incoming,b)


def _phase_two_borrows(builder, first, second, *, drop_cubic=False):
    """Phase Maj(a1,!s1,Maj(a0,!s0,c)) using at most one CCZ.

    All source and sum wires are restored. The first majority is either
    one product, or c XOR (a0 XOR c)*(!s0 XOR c). Its product multiplied
    by a1 XOR !s1 is the sole cubic factor. Constants are handled exactly.
    """
    a0,s0,c=first.a,first.b,first.incoming
    a1,s1=second.a,second.b
    if first.preserve_sign or second.preserve_sign:
        raise ValueError('Two-borrow phase needs distinct unsigned source bits.')
    builder.x(s0);builder.x(s1)
    builder.cz(a1,s1)
    general=a0 is not False and c is not False
    if general:
        builder.cz(c,a1);builder.cz(c,s1)
        builder.cx(c,a0);builder.cx(c,s0)
        left,right=a0,s0
    elif a0 is False:
        left,right=c,s0
    else:
        left,right=a0,s0
    builder.cx(a1,s1)
    if not drop_cubic:
        builder.ccz(left,right,s1)
    builder.cx(a1,s1)
    if general:
        builder.cx(c,s0);builder.cx(c,a0)
    builder.x(s1);builder.x(s0)


def _terminal(builder,a,b,incoming,frames,phase,*,drop_cubic=False):
    """Consume the last two carry frames with no additional allocation."""
    previous,last=frames[-2:]
    recycled=previous.outgoing
    if last.incoming!=recycled or last.outgoing!=incoming:
        raise AssertionError('Terminal carry frames do not form the expected chain.')
    if a[-2] is not False or a[-1] is not False:
        raise ValueError('The terminal source suffix must be zero.')

    builder.push_condition(phase)
    # Finish the preceding sum before erasing its incoming chain wire.
    _sum_keep_carry(builder,last)
    _erase_without_free(builder,previous,write_sum=True)
    builder.ccx(incoming,b[-2],recycled)
    builder.cz(recycled,b[-1])
    builder.cx(recycled,b[-1])
    builder.cx(incoming,b[-2])
    # The old product is incoming AND NOT the now-updated sum bit.
    builder.x(b[-2])
    builder.del_and(incoming,b[-2],recycled)
    builder.x(b[-2])
    measured=builder.alloc_bits(1)[0]
    builder.hmr(incoming,measured)
    builder.push_condition(measured)
    _phase_two_borrows(builder,previous,last,drop_cubic=drop_cubic)
    builder.pop_condition()
    builder.free(measured)
    builder.pop_condition()

    # The outcome-zero branch is the original arithmetic without a sign.
    builder.x(phase)
    builder.push_condition(phase)
    paired._finish_top(builder,a,b,incoming,None)
    _erase_without_free(builder,last,write_sum=True)
    _erase_without_free(builder,previous,write_sum=True)
    builder.pop_condition()
    builder.x(phase)
    # Both branch exits have these two allocations exactly zero.
    builder.free(incoming);builder.free(recycled)


@contextmanager
def use_conditioned_terminals(*,audit=None,drop_cubic=False):
    """Temporarily install the pass in the selected task-written arithmetic.

    This only changes the in-memory generator used inside the context. The
    selected package and its default source files remain untouched.
    ``drop_cubic`` exists solely for a failing negative-control proof.
    """
    original=paired._segment_repay
    records=[] if audit is None else audit
    def replacement(builder,a,b,incoming,*,retain_outgoing,preserve,start,debt,
                    overflow_phase=None):
        eligible=(not retain_outgoing and overflow_phase is not None and
                  preserve is None and len(b)>=4 and
                  a[-2] is False and a[-1] is False and
                  (incoming is not False or any(w is not False for w in a[:-3])))
        if not eligible:
            return original(builder,a,b,incoming,retain_outgoing=retain_outgoing,
                preserve=preserve,start=start,debt=debt,overflow_phase=overflow_phase)
        frames=[];carry=incoming
        for index,(aa,bb) in enumerate(zip(a[:-2],b[:-2])):
            frame=_compute_carry(builder,aa,bb,carry,preserve=preserve)
            measured=debt.measurements.pop(start+index+1,None)
            if measured is not None:
                if frame.outgoing is not False:
                    builder.push_condition(measured);builder.z(frame.outgoing)
                    builder.pop_condition()
                builder.free(measured)
            frames.append(frame);carry=frame.outgoing
        if not all(isinstance(f.outgoing,km.q) for f in frames[-2:]):
            raise AssertionError('Eligibility predicted a missing carry allocation.')
        records.append(dict(terminal_width=len(b),start=start,
            live_qubits=builder.num_allocated_qubits,expected_toffoli_saving=0.25))
        _terminal(builder,a,b,carry,frames,overflow_phase,drop_cubic=drop_cubic)
        for frame in reversed(frames[:-2]):
            _erase_carry(builder,frame,write_sum=True)
        return False
    paired._segment_repay=replacement
    try:
        yield records
    finally:
        paired._segment_repay=original
