# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Narrow arithmetic stages for the from-source inverse-square-root generator.

This module constructs gates from word widths and arithmetic identities.  It
does not load a circuit, either ours or a third party's.
"""
from __future__ import annotations

from dataclasses import dataclass
import kickmix as km

from fusion.arithmetic import add, signed_row
from quadratic_terms import xor_polynomial


@dataclass(frozen=True)
class ProductPlan:
    """Certified bounds for accumulating centered signed binary digits."""

    shifts: tuple[int, ...]
    widths: tuple[int, ...]
    bounds: tuple[int, ...]
    nearest: bool
    signed_source: bool
    initial_width: int = 0


@dataclass(frozen=True)
class BoundedRowsPlan:
    """All-source certificate for a consecutive block of centered rows."""

    digits: int
    first: int
    last: int
    shifts: tuple[int, ...]
    window: int
    maximum_absolute_sum: int
    source_min: int
    source_max: int
    signed_source: bool


@dataclass(frozen=True)
class BoundedRowsToken:
    plan: BoundedRowsPlan
    saved_bit: object
    window: int


def product_plan(*, digits: int, source_min: int, source_max: int,
                 source_fraction: int, target_fraction: int,
                 nearest: bool = True, signed_source: bool = False,
                 initial_min: int = 0, initial_max: int = 0,
                 first_shift: int | None = None) -> ProductPlan:
    """Bound every partial sum independently of the input/coeff correlation.

    For source s, row i adds (1-2*q_i)*round(s*2**shift_i).  Each bound
    encloses both signs of every permitted source, so copying the old sign
    into newly allocated high bits is an exact integer sign extension.
    """
    if source_min > source_max:
        raise ValueError("The source interval is empty.")
    if not signed_source and source_min < 0:
        raise ValueError("A negative source needs signed_source=True.")
    shifts, widths, bounds = [], [], []
    if initial_min > initial_max:
        raise ValueError("The initial accumulator interval is empty.")
    bound = max(abs(initial_min), abs(initial_max))
    initial_width = bound.bit_length()+1 if bound else 0
    for index in range(digits):
        shift = index+(first_shift if first_shift is not None else
                       -digits-1+target_fraction-source_fraction)
        def scale(value):
            if shift >= 0:
                return value << shift
            cut = -shift
            return (value + ((1 << (cut-1)) if nearest else 0)) >> cut
        row_bound = max(abs(scale(source_min)), abs(scale(source_max)))
        bound += row_bound
        shifts.append(shift)
        # The positive endpoint +bound, as well as -bound, must fit.
        widths.append(bound.bit_length()+1 if bound else 0)
        bounds.append(bound)
    return ProductPlan(tuple(shifts), tuple(widths), tuple(bounds), nearest,
                       signed_source, initial_width)


def bounded_rows_plan(*, digits: int, source_min: int, source_max: int,
                      source_fraction: int, target_fraction: int,
                      signed_source: bool = False, first: int = 0,
                      last: int | None = None,
                      first_shift: int | None = None) -> BoundedRowsPlan:
    """Certify a short modular row window and the sign of its net update.

    Every value in the source interval is checked, with exact integers.
    All rounded operands have the source's sign, and the last operand's
    magnitude must dominate the sum of earlier magnitudes.  Therefore the
    net update has sign (source_sign XOR q[last-1]), with zero harmless.
    The magnitude bound covers all 2**(last-first) digit assignments.
    """
    last = digits if last is None else last
    if not 0 <= first < last <= digits or source_min > source_max:
        raise ValueError("Invalid row or source interval.")
    if not signed_source and source_min < 0:
        raise ValueError("A negative source needs signed_source=True.")
    shifts = tuple(i+(first_shift if first_shift is not None else
                      -digits-1+target_fraction-source_fraction)
                   for i in range(first, last))
    maximum = 0
    for value in range(source_min, source_max+1):
        operands = [(value << shift) if shift >= 0 else
                    ((value+(1 << (-shift-1))) >> -shift) for shift in shifts]
        if any(operand*value < 0 for operand in operands):
            raise AssertionError("Rounded operand changes source sign.")
        magnitude = sum(abs(operand) for operand in operands)
        if 2*abs(operands[-1]) < magnitude:
            raise ValueError("The last row does not determine the net sign.")
        maximum = max(maximum, magnitude)
    window = maximum.bit_length()+1 if maximum else 0
    return BoundedRowsPlan(digits, first, last, shifts, window, maximum,
                           source_min, source_max, signed_source)


def _bounded_row_sequence(builder, residual, source, target, plan, *,
                          inverse, carry_budget):
    sequence = list(zip(range(plan.first, plan.last), plan.shifts))
    if inverse:
        sequence.reverse()
    for index, shift in sequence:
        signed_row(builder, source, target, shift=shift, sign=residual[index],
                   inverse=inverse, nearest=True,
                   signed_source=plan.signed_source, carry_budget=carry_budget)


def _pay_window_overflow(builder, residual, source, target, token, *,
                         inverse, carry_budget):
    """Apply the one possible signed carry into the high target slice."""
    plan, saved, width = token.plan, token.saved_bit, token.window
    if saved is None:
        return
    sigma = residual[plan.last-1]
    if plan.signed_source:
        builder.cx(source[-1], sigma)
    top = target[width-1]
    builder.cx(sigma, saved)
    builder.cx(sigma, top)
    builder.x(top)
    wrap = builder.alloc_qubits(1)[0]
    builder.ccx(saved, top, wrap)
    high = target[width:]
    for wire in high:
        builder.cx(sigma, wire)
    add(builder, [], high, carry_in=wrap, subtract=inverse,
        carry_budget=carry_budget)
    for wire in high:
        builder.cx(sigma, wire)
    builder.del_and(saved, top, wrap)
    builder.free(wrap)
    builder.x(top)
    builder.cx(sigma, top)
    builder.cx(sigma, saved)
    if plan.signed_source:
        builder.cx(source[-1], sigma)


def bounded_horner_rows(builder, residual, source, target,
                        plan: BoundedRowsPlan, *, carry_budget=None):
    """Apply rows only to their bounded low window and pay high carry once.

    One saved bit remembers the initial most significant bit of that window.
    It must survive until `undo_bounded_horner_rows` after the phase pass.
    The high word is incremented or decremented only once for the whole
    group, rather than propagating every row's carry through it.
    """
    residual, source, target = list(residual), list(source), list(target)
    if len(residual) != plan.digits:
        raise ValueError("Residual width does not match the block plan.")
    width = min(plan.window, len(target))
    saved = None
    if 0 < width < len(target):
        saved = builder.alloc_qubits(1)[0]
        builder.cx(target[width-1], saved)
    token = BoundedRowsToken(plan, saved, width)
    if width:
        _bounded_row_sequence(builder, residual, source, target[:width], plan,
                              inverse=False, carry_budget=carry_budget)
        _pay_window_overflow(builder, residual, source, target, token,
                             inverse=False, carry_budget=carry_budget)
    return token


def undo_bounded_horner_rows(builder, residual, source, target,
                             token: BoundedRowsToken, *, carry_budget=None):
    """Undo the paid carry, reverse the low rows, and clear the saved bit."""
    residual, source, target = list(residual), list(source), list(target)
    saved_debt = None
    if token.window:
        _pay_window_overflow(builder, residual, source, target, token,
                             inverse=True, carry_budget=carry_budget)
        if token.saved_bit is not None:
            saved_debt = builder.alloc_bits(1)[0]
            builder.hmr(token.saved_bit, saved_debt)
            builder.free(token.saved_bit)
        _bounded_row_sequence(builder, residual, source, target[:token.window],
                              token.plan, inverse=True, carry_budget=carry_budget)
    if saved_debt is not None:
        builder.push_condition(saved_debt)
        builder.z(target[token.window-1])
        builder.pop_condition()
        builder.free(saved_debt)


def growing_product(builder, residual, source, plan: ProductPlan, *,
                    carry_budget=None, initial=()):
    """Compute a centered product into an initially zero, growing word.

    The returned accumulator is a signed two's-complement integer.  Unlike a
    preloaded full-width constant, its upper bits are known sign extensions
    until a row needs them.  This avoids propagating every early carry through
    the full final word.  `erase_growing_product` is its exact inverse.
    """
    residual, source = list(residual), list(source)
    if len(residual) != len(plan.shifts):
        raise ValueError("Residual width does not match the product plan.")
    accumulator = list(initial)
    if len(accumulator) != plan.initial_width:
        raise ValueError("Initial accumulator width does not match the plan.")
    for sign, shift, width in zip(residual, plan.shifts, plan.widths):
        if width > len(accumulator):
            more = list(builder.alloc_qubits(width-len(accumulator)))
            if accumulator:
                for wire in more:
                    builder.cx(accumulator[-1], wire)
            accumulator.extend(more)
        if not width:
            continue
        signed_row(builder, source, accumulator, shift=shift, sign=sign,
                   nearest=plan.nearest, signed_source=plan.signed_source,
                   carry_budget=carry_budget)
    return km.array(accumulator)


def erase_growing_product(builder, residual, source, accumulator,
                          plan: ProductPlan, *, carry_budget=None):
    """Undo the rows, remove sign-extension copies, and release the word."""
    residual, source, accumulator = (list(residual), list(source),
                                      list(accumulator))
    if len(accumulator) != (plan.widths[-1] if plan.widths else 0):
        raise ValueError("Accumulator width does not match the product plan.")
    for index in reversed(range(len(residual))):
        width = plan.widths[index]
        if not width:
            continue
        signed_row(builder, source, accumulator, shift=plan.shifts[index],
                   sign=residual[index], inverse=True, nearest=plan.nearest,
                   signed_source=plan.signed_source, carry_budget=carry_budget)
        previous = plan.widths[index-1] if index else plan.initial_width
        if previous < width:
            dead = accumulator[previous:]
            if previous:
                for wire in dead:
                    builder.cx(accumulator[previous-1], wire)
            builder.free(km.array(dead))
            accumulator = accumulator[:previous]


def merge_signed_overlap(builder, high, low, anchor_low, *, split: int,
                         carry_budget=None):
    """Merge a signed two-bit overlap and erase its duplicate exactly.

    Initially high=H, low=S (signed), and anchor_low=H mod 4.  The latter
    must be supplied by the table's live coding basis.  We form

        high' = H + floor(S/2**split)
        R = (S mod 2**split) + 2**split * high'.

    The two duplicate high bits of S can then be measured away using only
    Z/CZ repayment.  Both possible values of each measurement are exact.
    This function preserves anchor_low; its eventual table cleanup belongs
    to the coefficient decoder, rather than to the arithmetic stage.
    """
    high, low, anchor_low = list(high), list(low), list(anchor_low)
    if len(low) != split+2 or len(anchor_low) != 2 or len(high) < 2:
        raise ValueError("The merge requires exactly two overlapping bits.")
    if len(set(high+low+anchor_low)) != len(high)+len(low)+2:
        raise ValueError("Merge inputs must use distinct physical wires.")
    add(builder, low[split:], high, signed_source=True,
        carry_budget=carry_budget)
    outcomes = builder.alloc_bits(2)
    for wire, outcome in zip(low[split:], outcomes):
        builder.hmr(wire, outcome)
        builder.free(wire)
    # S_hi = high' - H (mod 4).  Its bits are
    # s0 = high'[0] XOR H[0]
    # s1 = high'[1] XOR H[1] XOR H[0] XOR H[0]*high'[0].
    builder.push_condition(outcomes[0])
    builder.z(high[0])
    builder.z(anchor_low[0])
    builder.pop_condition()
    builder.push_condition(outcomes[1])
    builder.z(high[1])
    builder.z(anchor_low[1])
    builder.z(anchor_low[0])
    builder.cz(anchor_low[0], high[0])
    builder.pop_condition()
    builder.free(outcomes)
    return km.array([*low[:split], *high])


def unmerge_signed_overlap(builder, merged, anchor_low, *, split: int,
                           carry_budget=None):
    """Reverse `merge_signed_overlap`, reconstructing the two overlap bits."""
    merged, anchor_low = list(merged), list(anchor_low)
    high = merged[split:]
    if len(anchor_low) != 2 or len(high) < 2:
        raise ValueError("The merge requires exactly two overlapping bits.")
    overlap = list(builder.alloc_qubits(2))
    builder.cx(high[0], overlap[0])
    builder.cx(anchor_low[0], overlap[0])
    builder.cx(high[1], overlap[1])
    builder.cx(anchor_low[1], overlap[1])
    builder.cx(anchor_low[0], overlap[1])
    builder.ccx(anchor_low[0], high[0], overlap[1])
    add(builder, overlap, high, signed_source=True, subtract=True,
        carry_budget=carry_budget)
    return km.array(high), km.array([*merged[:split], *overlap])


def erase_two_low_bits(builder, word, residual, curvature, *,
                       curvature_storage_shift: int, cut_at_first_row: int):
    """Drop two low bits after an exactly certified centered curvature sum.

    Preconditions are checked by the mathematical table generator:

      S = B + sum_i (1-2*q_i) * RN(C / 2**(cut_at_first_row-i))
      B + sum_i RN(C / 2**(cut_at_first_row-i)) == 0 (mod 4).

    A table-dependent anchor divisible by four may be subtracted from B.
    C is represented as curvature * 2**curvature_storage_shift.  On this
    domain S[0] is exactly zero and S[1] is a quadratic polynomial whose
    products are individual residual and curvature bits.  Consequently its
    X-measurement needs only CZ repayments, for every outcome.
    """
    word, residual, curvature = list(word), list(residual), list(curvature)
    if len(word) < 3:
        raise ValueError("The derivative word must contain two removable bits.")
    for index in range(len(residual)):
        if cut_at_first_row-index <= 0:
            raise ValueError("This form expects strictly positive right shifts.")
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(word[1], outcome)
    builder.push_condition(outcome)
    for index, digit in enumerate(residual):
        cut = cut_at_first_row-index
        for source_index in (cut, cut-1):
            physical = source_index-curvature_storage_shift
            if 0 <= physical < len(curvature):
                builder.cz(digit, curvature[physical])
    builder.pop_condition()
    builder.free(outcome)
    builder.free(km.array(word[:2]))
    return km.array(word[2:])


def restore_two_low_bits(builder, compressed, residual, curvature, *,
                         curvature_storage_shift: int, cut_at_first_row: int):
    """Reconstruct the exact zero/quadratic low bits before reversing rows."""
    residual, curvature = list(residual), list(curvature)
    low = list(builder.alloc_qubits(2))
    terms = []
    for index, digit in enumerate(residual):
        cut = cut_at_first_row-index
        if cut <= 0:
            raise ValueError("This form expects strictly positive right shifts.")
        for source_index in (cut, cut-1):
            physical = source_index-curvature_storage_shift
            if 0 <= physical < len(curvature):
                terms.append((1 << index)|(1 << (len(residual)+physical)))
    xor_polynomial(builder, residual+curvature, low[1], terms)
    return km.array([*low, *compressed])
