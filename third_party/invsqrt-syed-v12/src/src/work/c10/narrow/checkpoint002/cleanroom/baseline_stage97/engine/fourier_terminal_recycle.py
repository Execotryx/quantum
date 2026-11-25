# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""An exact Fourier terminal which conditionally recycles two carry frames.

The existing signed-T carry phase needs one extra clean wire.  When its odd
classical outcome is one, the last two ordinary carry frames can instead be
consumed early and one cleared allocation reused for that phase.  Measuring
the remaining old carry introduces the composition of two borrow majorities;
its only cubic term is repaid by one conditioned CCZ.  Thus this alternative
uses one less clean wire and costs one quarter of a Toffoli more in mean.
The partition selector chooses it only when saved boundary recomputation is
strictly larger.  No measurement debt leaves the enclosing inverse adder.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction

import kickmix as km
from conditioned_terminal import _erase_without_free, _phase_two_borrows
import fourier_suffix_inverse as original
from fusion.arithmetic import _Frame, _compute_carry, _erase_carry, _sum_keep_carry
from fusion.compiler import MAJORITY_TRUTH, phase_quadratic


def _carry_into(builder, a, b, incoming, outgoing):
    """The unsigned majority frame, using a caller-certified clean wire."""
    if a is False and incoming is False:
        raise ValueError('A recycled terminal requires its nonconstant incoming carry.')
    if a is False:
        builder.ccx(incoming, b, outgoing)
    else:
        builder.cx(incoming, a)
        builder.cx(incoming, b)
        builder.ccx(a, b, outgoing)
        builder.cx(incoming, outgoing)
    return _Frame(a, b, incoming, outgoing)


def final_segment(builder, a, b, incoming, *, start, debt, sign, suffix,
                  drop_borrow_cubic=False):
    """Add a terminal and apply its signed Fourier carry phase exactly.

This has the same data and debt contract as the selected final segment.
There must be at least three target bits and two nonconstant final carry
frames.  The caller reserves length-1 clean wires, with no extra phase wire.
"""
    if not isinstance(suffix, original.FourierSuffixDebt3) or len(b) < 3:
        raise ValueError('The recycled terminal needs a three-outcome suffix and at least three bits.')
    frames = []
    carry = incoming
    for index, (aa, bb) in enumerate(zip(a[:-1], b[:-1])):
        frame = _compute_carry(builder, aa, bb, carry)
        measured = debt.measurements.pop(start + index + 1, None)
        if measured is not None:
            if frame.outgoing is not False:
                builder.push_condition(measured)
                builder.z(frame.outgoing)
                builder.pop_condition()
            builder.free(measured)
        frames.append(frame)
        carry = frame.outgoing
    previous, last = frames[-2:]
    if not all(isinstance(frame.outgoing, km.q) for frame in (previous, last)):
        raise ValueError('The last two carries must occupy quantum allocations.')
    if last.incoming != previous.outgoing or last.outgoing != carry:
        raise AssertionError('The two recycled carry frames are not adjacent.')

    # Both these signs are quadratic in live wires before the frames change.
    builder.push_condition(suffix.four_times)
    phase_quadratic(builder, [a[-1], b[-1], carry], MAJORITY_TRUTH)
    builder.pop_condition()
    measured = debt.measurements.pop(start + len(b), None)
    if measured is not None:
        builder.push_condition(measured)
        phase_quadratic(builder, [a[-1], b[-1], carry], MAJORITY_TRUTH)
        builder.pop_condition()
        builder.free(measured)

    recycled = previous.outgoing
    builder.push_condition(suffix.odd)
    _sum_keep_carry(builder, last)
    _erase_without_free(builder, previous, write_sum=True)
    phase_frame = _carry_into(builder, a[-1], b[-1], carry, recycled)
    builder.z_pow(sign, Fraction(1, 4))
    builder.cx(recycled, sign)
    builder.z_pow(sign, Fraction(-1, 4))
    builder.cx(recycled, sign)
    builder.push_condition(suffix.twice)
    builder.z_pow(recycled, Fraction(-1, 2))
    builder.cz(sign, recycled)
    builder.pop_condition()
    _erase_without_free(builder, phase_frame, write_sum=True)
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(carry, outcome)
    builder.push_condition(outcome)
    _phase_two_borrows(builder, previous, last, drop_cubic=drop_borrow_cubic)
    builder.pop_condition()
    builder.free(outcome)
    builder.pop_condition()

    builder.x(suffix.odd)
    builder.push_condition(suffix.odd)
    builder.push_condition(suffix.twice)
    original.signed_s_majority(builder, sign, a[-1], b[-1], carry)
    builder.pop_condition()
    builder.cx(a[-1], b[-1])
    builder.cx(carry, b[-1])
    _erase_without_free(builder, last, write_sum=True)
    _erase_without_free(builder, previous, write_sum=True)
    builder.pop_condition()
    builder.x(suffix.odd)
    # Both branches have exactly these two allocations cleared.
    builder.free(carry)
    builder.free(recycled)
    for frame in reversed(frames[:-2]):
        _erase_carry(builder, frame, write_sum=True)


def choose_partition(width, clean, *, release_input, three):
    """Choose exact quarter-unit expected cost and deterministic segment sizes."""
    if width < 1 or clean < 0:
        raise ValueError('A nonempty word and nonnegative carry budget are required.')
    states = {(0, 0): (0, ())}
    candidates = []
    for used in range(clean + 1 + int(release_input)):
        for (start, count), (cost, sizes) in list(states.items()):
            if count != used:
                continue
            capacity = clean - used + int(release_input and used > 0)
            remaining = width - start
            recreation = 2 if release_input and used > 0 else 0
            if remaining <= capacity + 1 - int(three):
                phase = 4 if three else 2
                candidates.append((cost + 4 * (remaining - 1) + phase + recreation,
                                   False, sizes + (remaining,)))
            if three and 3 <= remaining <= capacity + 1:
                candidates.append((cost + 4 * (remaining - 1) + 5 + recreation,
                                   True, sizes + (remaining,)))
            if used == clean + int(release_input):
                continue
            for length in range(1, min(capacity, remaining - 1) + 1):
                key = (start + length, used + 1)
                trial = (cost + 4 * length + 2 * (length - 1), sizes + (length,))
                if key not in states or trial < states[key]:
                    states[key] = trial
    if not candidates:
        raise ValueError(f'No {width}-bit Fourier inverse with {clean} carry wires.')
    score, recycled, sizes = min(candidates)
    return list(sizes), recycled, score


@contextmanager
def installed(*, audit=None):
    """Install only inside a caller-owned main-result inverse emission scope."""
    old_inverse = original.inverse_add_truncated
    old_partition = original._partition
    old_final = original._final_segment
    active = []
    records = [] if audit is None else audit

    def inverse(builder, source, target, debt, **kwargs):
        state = {'recycled': False,
                 'eligible': isinstance(kwargs.get('suffix'), original.FourierSuffixDebt3)
                             and (bool(source) or isinstance(kwargs.get('carry_in'), km.q))}
        active.append(state)
        try:
            return old_inverse(builder, source, target, debt, **kwargs)
        finally:
            if active.pop() is not state:
                raise AssertionError('Fourier terminal ownership scopes were not nested.')

    def partition(width, clean, *, release_input, three=False):
        if not active or not active[-1]['eligible']:
            return old_partition(width, clean, release_input=release_input, three=three)
        sizes, recycle, score = choose_partition(width, clean, release_input=release_input, three=three)
        active[-1]['recycled'] = recycle
        records.append({'width': width, 'clean': clean, 'release_input': release_input,
                        'three': three, 'sizes': sizes, 'recycled_terminal': recycle,
                        'modeled_quarter_equivalents': score})
        return sizes

    def final(builder, a, b, incoming, **kwargs):
        if active and active[-1]['recycled']:
            return final_segment(builder, a, b, incoming, **kwargs)
        return old_final(builder, a, b, incoming, **kwargs)

    original.inverse_add_truncated = inverse
    original._partition = partition
    original._final_segment = final
    try:
        yield records
    finally:
        original.inverse_add_truncated = old_inverse
        original._partition = old_partition
        original._final_segment = old_final


@contextmanager
def installed_main_only(*, audit=None):
    """Scope all replacements to the existing main-result inverse call.

The separate Blo9 curvature inverse also imports the Fourier arithmetic
module.  Wrapping the main owner here ensures that no curvature or excluded
region sees an installed arithmetic binding, even one that would be inert.
"""
    import fourier_main
    previous = fourier_main.inverse_main_groups
    records = [] if audit is None else audit

    def inverse_main(*args, **kwargs):
        with installed(audit=records):
            return previous(*args, **kwargs)

    fourier_main.inverse_main_groups = inverse_main
    try:
        yield records
    finally:
        fourier_main.inverse_main_groups = previous
