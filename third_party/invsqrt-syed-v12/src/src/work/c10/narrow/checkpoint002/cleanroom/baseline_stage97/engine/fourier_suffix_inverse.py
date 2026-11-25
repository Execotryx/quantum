# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""An isolated inverse after Fourier-measuring the two highest result bits.

This research module does not change the selected generator.  Measuring
top first, applying S**m1 to the next bit, and then measuring that bit
contributes i**((m1+2*m0)*suffix).  The remaining inverse needs a signed
quarter-turn phase on each carry out of its shorter word.

The signed S of a majority is four T gates, with no auxiliary quantum wire:

  2*(2*q-1)*Maj(a,b,c)
    = 2*q-(q^a)-(q^b)-(q^c)+(q^a^b^c) (mod 8).

Every expression on the right is an affine parity.  A classically selected
Z of a majority is quadratic and uses CZ gates only.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from fractions import Fraction

import kickmix as km
import paired_arithmetic as paired
from fusion.arithmetic import _compute_carry, _erase_carry, _phase_borrow
from fusion.compiler import phase_quadratic, MAJORITY_TRUTH


@dataclass
class FourierSuffixDebt:
    odd: object
    twice: object
    consumed: bool = False


@dataclass
class FourierSuffixDebt3:
    odd: object
    twice: object
    four_times: object
    consumed: bool = False
    # Physical result wires above the retained word in each forward adder:
    # two beside a reconstructed top, or all three of a literal top.
    physical: int = 2


def measure_suffix2(builder, low_bit, high_bit):
    """Reset the suffix, retaining its exact Fourier phase as classical data."""
    if low_bit == high_bit:
        raise ValueError('The two suffix wires must be distinct.')
    odd, twice = builder.alloc_bits(2)
    builder.hmr(high_bit, odd)
    builder.free(high_bit)
    builder.push_condition(odd)
    builder.z_pow(low_bit, Fraction(1, 2))
    builder.pop_condition()
    builder.hmr(low_bit, twice)
    builder.free(low_bit)
    return FourierSuffixDebt(odd, twice)


def measure_suffix3(builder, low_bit, middle_bit, high_bit):
    """Measure three high bits; the only T gate is conditioned on one HMR bit."""
    if len({low_bit, middle_bit, high_bit}) != 3:
        raise ValueError('The three suffix wires must be distinct.')
    odd, twice, four_times = builder.alloc_bits(3)
    builder.hmr(high_bit, odd)
    builder.free(high_bit)
    builder.push_condition(odd)
    builder.z_pow(middle_bit, Fraction(1, 2))
    builder.z_pow(low_bit, Fraction(1, 4))
    builder.pop_condition()
    builder.hmr(middle_bit, twice)
    builder.free(middle_bit)
    builder.push_condition(twice)
    builder.z_pow(low_bit, Fraction(1, 2))
    builder.pop_condition()
    builder.hmr(low_bit, four_times)
    builder.free(low_bit)
    return FourierSuffixDebt3(odd, twice, four_times)


def signed_s_majority(builder, sign, a, b, incoming):
    """Apply i**((2*sign-1)*Maj(a,b,incoming)), preserving every input."""
    if not isinstance(sign, km.q):
        raise ValueError('The arithmetic sign must be a quantum wire.')
    values = [wire for wire in (a, b, incoming) if isinstance(wire, km.q)]
    if sign in values or len(values) != len(set(values)):
        raise ValueError('The sign and nonconstant majority inputs must be distinct.')
    # All five parities contain sign, which is borrowed as their pivot.
    terms = {frozenset(): 2}
    for wire in (a, b, incoming):
        key = frozenset((wire,)) if isinstance(wire, km.q) else frozenset()
        terms[key] = terms.get(key, 0) - 1
    key = frozenset(values)
    terms[key] = terms.get(key, 0) + 1
    for controls, coefficient in terms.items():
        coefficient %= 8
        if not coefficient:
            continue
        ordered = sorted(controls, key=str)
        for wire in ordered:
            builder.cx(wire, sign)
        builder.z_pow(sign, Fraction(coefficient, 4))
        for wire in reversed(ordered):
            builder.cx(wire, sign)


def repay_signed_carry(builder, a, b, incoming, sign, suffix):
    """Phase the inverse signed carry by i**(j*(2*sign-1)*carry)."""
    three = isinstance(suffix, FourierSuffixDebt3)
    builder.push_condition(suffix.four_times if three else suffix.twice)
    phase_quadratic(builder, [a, b, incoming], MAJORITY_TRUTH)
    builder.pop_condition()
    builder.push_condition(suffix.twice if three else suffix.odd)
    signed_s_majority(builder, sign, a, b, incoming)
    builder.pop_condition()
    if three:
        builder.push_condition(suffix.odd)
        frame = _compute_carry(builder, a, b, incoming)
        if frame.outgoing is not False:
            # (2*q-1)*c = q-(q XOR c): two T gates after one AND.
            builder.z_pow(sign, Fraction(1, 4))
            builder.cx(frame.outgoing, sign)
            builder.z_pow(sign, Fraction(-1, 4))
            builder.cx(frame.outgoing, sign)
        _erase_carry(builder, frame, write_sum=False)
        builder.pop_condition()


def _partition(width, clean, *, release_input, three=False):
    """Choose segmented carries with a phase-only final majority.

    A final segment uses length-1 carry wires.  The signed S-majority
    needs no extra wire.  Its expected four-T cost is one half equivalent.
    Nonfinal boundary signs retain the existing conditioned comparator.
    """
    if width < 1 or clean < 0:
        raise ValueError('A nonempty word and nonnegative carry budget are required.')
    states = {(0, 0): (0.0, ())}
    candidates = []
    for used in range(clean + 1 + int(release_input)):
        for (start, count), (cost, sizes) in list(states.items()):
            if count != used:
                continue
            capacity = clean - used + int(release_input and used > 0)
            remaining = width - start
            if remaining <= capacity + 1 - int(three):
                correction = 0.5 if release_input and used > 0 else 0.0
                phase_cost = 1.25 if three else 0.5
                candidates.append((cost + remaining - 1 + phase_cost + correction,
                                   sizes + (remaining,)))
            if used == clean + int(release_input):
                continue
            for length in range(1, min(capacity, remaining - 1) + 1):
                key = (start + length, used + 1)
                candidate = (cost + length + 0.5 * (length - 1), sizes + (length,))
                if key not in states or candidate < states[key]:
                    states[key] = candidate
    if not candidates:
        raise ValueError(f'No {width}-bit Fourier inverse with {clean} carry wires.')
    return list(min(candidates)[1])


def _final_segment(builder, a, b, incoming, *, start, debt, sign, suffix):
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
    repay_signed_carry(builder, a[-1], b[-1], carry, sign, suffix)
    measured = debt.measurements.pop(start + len(b), None)
    if measured is not None:
        # Dropping two physical bits exposes the final forward-measured
        # carry as this phase-only majority, so its Z debt costs no AND.
        builder.push_condition(measured)
        phase_quadratic(builder, [a[-1], b[-1], carry], MAJORITY_TRUTH)
        builder.pop_condition()
        builder.free(measured)
    builder.cx(a[-1], b[-1])
    builder.cx(carry, b[-1])
    for frame in reversed(frames):
        _erase_carry(builder, frame, write_sum=True)


def inverse_add_truncated(builder, source, target, debt, *, sign, suffix,
                          carry_in=False, signed_source=False, carry_budget=None,
                          dirty_wires=(), carry_lifecycle=None,
                          overflow_phase=None, allow_dirty_overflow=False):
    """Undo low bits after measuring one or two highest physical result bits.

    The matching forward add had one more target bit for a two-bit suffix,
    or two more for a three-bit suffix. Its last measured carry is either
    an ordinary incoming carry or the final phase-only majority. Both
    are repaid explicitly by this shortened inverse.
    """
    if signed_source or overflow_phase is not None:
        raise ValueError('This prototype accepts unsigned sources and its own phase debt.')
    a, b, preserve = paired._inputs(source, target, carry_in, False)
    three = isinstance(suffix, FourierSuffixDebt3)
    removed = suffix.physical if three else 1
    if preserve is not None or debt.consumed or debt.width != len(b) + removed:
        raise ValueError('The forward debt width does not match the measured suffix.')
    if any(position > len(b) for position in debt.measurements):
        raise ValueError('A forward carry owner lies above the retained inverse boundary.')
    if not b:
        raise ValueError('A completely measured target needs a separate constant-add phase.')
    debt.consumed = True
    available = builder.max_qubits - builder.num_allocated_qubits
    desired = len(b) - 1 + int(three) if carry_budget is None else carry_budget
    clean = int(min(available, desired, len(b) - 1 + int(three)))
    sizes = _partition(len(b), clean, release_input=carry_lifecycle is not None, three=three)
    builder.x(km.array(b))
    boundaries = []
    start, carry = 0, carry_in
    released = False
    for number, length in enumerate(sizes):
        aa, bb = a[start:start + length], b[start:start + length]
        if number + 1 == len(sizes):
            _final_segment(builder, aa, bb, carry, start=start, debt=debt,
                           sign=sign, suffix=suffix)
        else:
            outgoing = paired._segment_repay(builder, aa, bb, carry,
                retain_outgoing=True, preserve=None, start=start, debt=debt)
            recorded = carry
            if number == 0 and carry_lifecycle is not None:
                carry_lifecycle[0](carry_in)
                recorded = None
                released = True
            boundaries.append((aa, bb, recorded, outgoing))
            carry = outgoing
        start += length
    for aa, bb, incoming, outgoing in reversed(boundaries):
        if outgoing is False:
            continue
        measured = builder.alloc_bits(1)[0]
        builder.hmr(outgoing, measured)
        builder.free(outgoing)
        builder.push_condition(measured)
        recreated = incoming is None
        if recreated:
            incoming = carry_lifecycle[1]()
        _phase_borrow(builder, aa, bb, incoming)
        if recreated:
            carry_lifecycle[0](incoming)
        builder.pop_condition()
        builder.free(measured)
    builder.x(km.array(b))
    if debt.measurements:
        raise AssertionError(f'Unpaid forward carry phases: {sorted(debt.measurements)}')
    return released


def repay_initial_complement_suffix(builder, initial_bit, suffix, *, original_snapshot=None):
    """Repay the initial suffix 2-initial_bit after its table reconstruction."""
    if suffix.consumed:
        raise ValueError('The Fourier suffix debt has already been repaid.')
    if isinstance(suffix, FourierSuffixDebt3):
        lower, initial_bit = list(initial_bit)
        builder.push_condition(suffix.odd)
        builder.z_pow(lower, Fraction(-1, 4))
        builder.pop_condition()
        builder.push_condition(suffix.twice)
        builder.z_pow(lower, Fraction(-1, 2))
        builder.pop_condition()
        builder.push_condition(suffix.four_times)
        builder.z(lower)
        builder.pop_condition()
        builder.free(suffix.four_times)
    builder.z(suffix.odd)
    builder.push_condition(suffix.odd)
    builder.z_pow(initial_bit, Fraction(1, 2))
    builder.pop_condition()
    builder.push_condition(suffix.twice)
    builder.z(initial_bit)
    builder.pop_condition()
    builder.free(suffix.odd)
    builder.free(suffix.twice)
    suffix.consumed = True
    if original_snapshot is not None:
        paired.repay_saved_bit(builder, initial_bit, original_snapshot)


@contextmanager
def shortened_row_adder(sign, suffix):
    """Bind the existing virtual-bottom row to the shortened inverse only."""
    import virtual_lsb
    old_paired, old_virtual = paired.inverse_add, virtual_lsb.inverse_add
    def replacement(builder, source, target, debt, **kwargs):
        return inverse_add_truncated(builder, source, target, debt,
                                     sign=sign, suffix=suffix, **kwargs)
    paired.inverse_add = virtual_lsb.inverse_add = replacement
    try:
        yield
    finally:
        paired.inverse_add, virtual_lsb.inverse_add = old_paired, old_virtual


def inverse_high_truncated(builder, digits, low, high, token, suffix):
    """Undo a bounded high increment after removing its top result wire."""
    from split_bounded import _digit
    removed = suffix.physical if isinstance(suffix, FourierSuffixDebt3) else 1
    if token.stage != 'high_done' or len(high) + removed != token.high_width:
        raise ValueError('The high correction width does not match the measured suffix.')
    if token.saved_bit is None or token.plan.signed_source or not high:
        raise ValueError('This prototype needs its saved boundary and a nonempty high word.')
    with _digit(digits, token.plan.last - 1) as sign:
        saved, top = token.saved_bit, low[-1]
        builder.cx(sign, saved)
        builder.cx(sign, top)
        builder.x(top)
        wrap = builder.alloc_qubits(1)[0]
        builder.ccx(saved, top, wrap)
        for wire in high:
            builder.cx(sign, wire)
        inverse_add_truncated(builder, [], high, token.overflow_debt,
            sign=sign, suffix=suffix, carry_in=wrap)
        for wire in high:
            builder.cx(sign, wire)
        builder.del_and(saved, top, wrap)
        builder.free(wrap)
        builder.x(top)
        builder.cx(sign, top)
        builder.cx(sign, saved)
    token.stage = 'high_undone'
    token.saved_measurement = paired.release_saved_bit(builder, token.saved_bit)
    token.saved_bit = None


def inverse_full_group_truncated(builder, digits, source, target, token, suffix):
    """Shorten a full modular group; proper smaller windows stay unchanged."""
    from split_bounded import _row_controls
    from virtual_lsb import inverse_virtual_row
    removed = suffix.physical if isinstance(suffix, FourierSuffixDebt3) else 1
    if token.consumed or len(target) + removed != token.width:
        raise ValueError('The full-group width does not match the measured suffix.')
    token.consumed = True
    rows = list(reversed(list(zip(range(token.plan.first, token.plan.last),
                                  token.plan.shifts))))
    for index, shift, sign in _row_controls(digits, rows):
        offset = index - token.plan.first
        with shortened_row_adder(sign, suffix):
            inverse_virtual_row(builder, source, target, token.row_debts[offset],
                shift=shift, sign=sign, initial_lsb=token.row_parities[offset])
