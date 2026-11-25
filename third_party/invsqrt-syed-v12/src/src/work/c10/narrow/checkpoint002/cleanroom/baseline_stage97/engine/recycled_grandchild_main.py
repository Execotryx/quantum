# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Reuse one nested snapshot slot across seven- and nine-bit main windows.

The first two rows use a seven-bit grandchild before rows two and three
run on their nine-bit child.  The grandchild's low rows do not touch the
child's top bit.  Compute its wrap first, measure its original-top snapshot,
then copy the still-original child top into the released slot before the
grandchild's two high bits change.

The measured wrap has a private phase owner.  Its value is the XOR of the
two full-parent row carries at the grandchild boundary: each signed row
restores its complement frame, and both source bits at that boundary are
zero.  Distinct classical copies of that outcome are paid by those already
computed inverse carries.  No new owner survives the main inverse.
"""
from __future__ import annotations

from contextlib import contextmanager

import kickmix as km
import asymmetric_nested_main as asymmetric
import nested_main_window as nested_main
import paired_arithmetic as paired
import split_bounded
from variable_lsb_main import row_parity_mask
import virtual_lsb
import virtual_main


def transfer_snapshot_and_high(builder, low, high, grandchild, child, sign):
    """Run the two-bit grandchild high update while transferring one saved slot."""
    low, high = list(low), list(high)
    if (grandchild.stage != 'low_done' or child.saved_bit is not None
            or grandchild.saved_bit is None or len(high) != 2
            or len(low) != grandchild.window or child.window != len(low)+2):
        raise ValueError('Snapshot transfer needs one held grandchild snapshot and two untouched high bits.')
    saved, top = grandchild.saved_bit, low[-1]
    builder.cx(sign, saved)
    builder.cx(sign, top)
    builder.x(top)
    wrap = builder.alloc_qubits(1)[0]
    builder.ccx(saved, top, wrap)
    # The wrap is now held.  Return both controls to their original frames
    # before measuring the old top; its phase is paid on that original bit.
    builder.x(top)
    builder.cx(sign, top)
    builder.cx(sign, saved)
    grandchild.saved_measurement = paired.release_saved_bit(builder, saved)
    grandchild.saved_bit = None

    child.saved_bit = builder.alloc_qubits(1)[0]
    builder.cx(high[-1], child.saved_bit)
    for wire in high:
        builder.cx(sign, wire)
    pending = []

    def release_wrap():
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(wrap, outcome)
        builder.free(wrap)
        # A CarryDebt owns and frees its record.  Allocate distinct copies,
        # never share one record between the two consuming inverse rows.
        for _ in grandchild.row_debts:
            owned = builder.alloc_bits(1)[0]
            builder.bit_store(owned, False)
            builder.cx(outcome, owned)
            pending.append({grandchild.window: owned})
        builder.free(outcome)

    grandchild.overflow_debt = virtual_lsb._add_disposable_carry(
        builder, [], high, wrap, release_wrap)
    for wire in high:
        builder.cx(sign, wire)
    if grandchild.overflow_debt.measurements:
        raise AssertionError('The two-bit grandchild high update created a carry debt.')
    owners = [record[grandchild.window] for record in pending]
    if len(owners) != 2 or len(set(owners)) != 2:
        raise AssertionError('Each grandchild row must own a distinct copy of the wrap phase.')
    grandchild.private_carry_debts = pending
    grandchild.high_width = 2
    grandchild.stage = 'high_done'


def forward_recycled_child(builder, digits, source, low, plan, grandplan, *, parity_before,
                           finish_high=None):
    """Compute a bounded child, preserving only one inner snapshot at a time."""
    source, low = list(source), list(low)
    if (plan.first != grandplan.first or grandplan.last-grandplan.first != 2
            or plan.last-grandplan.last != 2 or len(low) != plan.window
            or plan.window-grandplan.window != 2 or not all(shift <= 0 for shift in plan.shifts)
            or split_bounded._digit_count(digits) != plan.digits):
        raise ValueError('The recycled child requires two early and two late unsigned virtual rows.')
    if any(len(source[-shift+1:]) > grandplan.window for shift in grandplan.shifts):
        raise ValueError('A grandchild source has a nonzero bit at the promoted carry boundary.')
    child = virtual_main.VirtualMainToken(plan, None, plan.window,
        [None]*(plan.last-plan.first), parity_before=parity_before,
        row_parities=[None]*(plan.last-plan.first))
    grandlow, grandhigh = low[:grandplan.window], low[grandplan.window:]
    saved = builder.alloc_qubits(1)[0]
    builder.cx(grandlow[-1], saved)
    grand = virtual_main.VirtualMainToken(grandplan, saved, grandplan.window, [],
        parity_before=parity_before, row_parities=[])
    parity = parity_before
    rows = list(zip(range(grandplan.first, grandplan.last), grandplan.shifts))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        seed = virtual_main._row_seed(parity, len(source), shift)
        debt = virtual_lsb.forward_virtual_row(builder, source, grandlow,
            shift=shift, sign=sign, initial_lsb=seed)
        if debt.inactive or debt.ordinary:
            raise ValueError('The two promoted carries require active unsigned virtual rows.')
        grand.row_debts.append(debt)
        grand.row_parities.append(seed)
        child.row_debts[index-plan.first] = debt
        child.row_parities[index-plan.first] = seed
        parity ^= row_parity_mask(len(source), shift)
        if index+1 == grandplan.last:
            transfer_snapshot_and_high(builder, grandlow, grandhigh, grand, child, sign)
    grand.parity_after = parity
    later = [(index, plan.shifts[index-plan.first]) for index in range(grandplan.last, plan.last)]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        seed = virtual_main._row_seed(parity, len(source), shift)
        child.row_parities[index-plan.first] = seed
        child.row_debts[index-plan.first] = virtual_lsb.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)
        if index+1 == plan.last:
            # Keep this packed last digit exposed for the caller's high
            # correction, just as the proved nine-bit child does.
            if finish_high is not None:
                finish_high(child, sign)
    child.parity_after = parity
    child.recycled_grandchild = grand
    return child


def forward_nested_recycled(builder, digits, source, low, plan, child_plan, *, parity_before):
    """Selected eleven-bit parent with a seven-to-nine snapshot transfer."""
    source, low = list(source), list(low)
    if (len(low) != plan.window or (len(source), plan.digits, plan.first, plan.last, plan.window,
            child_plan.first, child_plan.last, child_plan.window) != (17, 14, 0, 6, 11, 0, 4, 9)):
        raise ValueError('The selected recycled main geometry changed.')
    grandplan = nested_main.child_plan(child_plan, 2)
    if grandplan.window != 7:
        raise AssertionError('The first-two-row mathematical bound is no longer seven bits.')
    saved = builder.alloc_qubits(1)[0]
    builder.cx(low[-1], saved)
    token = virtual_main.VirtualMainToken(plan, saved, plan.window,
        [None]*(plan.last-plan.first), parity_before=parity_before,
        row_parities=[None]*(plan.last-plan.first))
    parity = parity_before
    later = [(index, plan.shifts[index-plan.first]) for index in range(child_plan.last, plan.last)]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        seed = virtual_main._row_seed(parity, len(source), shift)
        offset = index-plan.first
        token.row_parities[offset] = seed
        token.row_debts[offset] = virtual_lsb.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)

    def finish_high(child, sign):
        split_bounded.forward_bounded_high(builder, nested_main.single_control(child_plan, sign),
            low[:child_plan.window], low[child_plan.window:], child)

    child = forward_recycled_child(builder, digits, source, low[:child_plan.window],
        child_plan, grandplan, parity_before=parity, finish_high=finish_high)
    for offset, debt in enumerate(child.row_debts):
        index = child.plan.first+offset-plan.first
        token.row_debts[index] = debt
        token.row_parities[index] = child.row_parities[offset]
    token.parity_after = child.parity_after
    token.nested_child = child
    return token


def inverse_promoted_row(builder, source, target, row, private, *, narrow_width,
                         shift, sign, initial_lsb, carry_budget=None):
    """Repay lower forward carries and private copies of one promoted carry."""
    original = row.carry_debt
    if (row.shift != shift or row.ordinary or row.inactive or shift > 0
            or original.width != narrow_width or original.consumed
            or any(not 1 <= position <= narrow_width-2 for position in original.measurements)
            or any(position != narrow_width or position > len(target)-2 for position in private)
            or set(original.measurements).intersection(private)):
        raise ValueError('The promoted row has mismatched carry positions or owners.')
    measurements = dict(original.measurements)
    measurements.update(private)
    widened = paired.CarryDebt(measurements, len(target))
    view = virtual_lsb.VirtualRowDebt(row.shift, False, False, widened)
    virtual_lsb.inverse_virtual_row(builder, source, target, view, shift=shift, sign=sign,
        initial_lsb=initial_lsb, carry_budget=carry_budget)
    if widened.measurements or not widened.consumed:
        raise AssertionError('A promoted private carry phase was not repaid.')
    original.measurements.clear()
    original.consumed = True
    private.clear()


def inverse_recycled_child(builder, digits, source, target, child, *, carry_budget=None):
    """Undo all child rows on the parent and consume both private snapshots."""
    source, target = list(source), list(target)
    grand = child.recycled_grandchild
    if (child.stage != 'high_done' or child.saved_bit is not None
            or child.saved_measurement is None
            or not getattr(child, 'asymmetric_snapshot_retired', False)
            or len(target) != child.window+2 or child.high_width != 2
            or child.overflow_debt.width != 2 or child.overflow_debt.measurements
            or child.overflow_debt.consumed
            or grand.stage != 'high_done' or grand.saved_bit is not None
            or grand.saved_measurement is None or grand.high_width != 2
            or grand.overflow_debt.width != 2 or grand.overflow_debt.measurements
            or grand.overflow_debt.consumed):
        raise ValueError('The recycled child must own two classical snapshots and empty high ledgers.')
    private = grand.private_carry_debts
    if len(private) != 2 or any(set(record) != {grand.window} for record in private):
        raise ValueError('Each grandchild row needs its one promoted wrap phase owner.')
    owners = [record[grand.window] for record in private]
    if len(set(owners)) != 2 or not all(isinstance(owner, km.b) for owner in owners):
        raise ValueError('The promoted wrap records must be distinct classical owners.')

    rows = list(reversed(list(zip(range(child.plan.first, child.plan.last), child.plan.shifts))))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        offset = index-child.plan.first
        if index < grand.plan.last:
            inner = index-grand.plan.first
            if child.row_debts[offset] is not grand.row_debts[inner]:
                raise AssertionError('The child lost its original grandchild row-debt identity.')
            inverse_promoted_row(builder, source, target, grand.row_debts[inner], private[inner],
                narrow_width=grand.window, shift=shift, sign=sign,
                initial_lsb=grand.row_parities[inner], carry_budget=carry_budget)
        else:
            asymmetric.inverse_widened_row(builder, source, target, child.row_debts[offset],
                narrow_width=child.window, shift=shift, sign=sign,
                initial_lsb=child.row_parities[offset], carry_budget=carry_budget)
    if any(private):
        raise AssertionError('A private promoted carry outcome remains owned.')
    paired.repay_saved_bit(builder, target[grand.window-1], grand.saved_measurement)
    grand.saved_measurement = None
    grand.overflow_debt.consumed = True
    grand.stage = 'consumed'
    paired.repay_saved_bit(builder, target[child.window-1], child.saved_measurement)
    child.saved_measurement = None
    child.overflow_debt.consumed = True
    child.stage = 'consumed'


def inverse_nested_recycled(builder, digits, source, low, token, *, carry_budget=None):
    source, low = list(source), list(low)
    if token.stage != 'high_undone' or len(low) != token.window:
        raise ValueError('The original parent high correction must be reversed first.')
    if token.saved_bit is not None:
        token.saved_measurement = paired.release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    child = token.nested_child
    inverse_recycled_child(builder, digits, source, low, child, carry_budget=carry_budget)
    later = [(index, token.plan.shifts[index-token.plan.first])
             for index in reversed(range(child.plan.last, token.plan.last))]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        offset = index-token.plan.first
        virtual_lsb.inverse_virtual_row(builder, source, low, token.row_debts[offset],
            shift=shift, sign=sign, initial_lsb=token.row_parities[offset],
            carry_budget=carry_budget)
    if token.saved_measurement is None:
        raise AssertionError('The restored parent snapshot has no phase owner.')
    paired.repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = 'consumed'


@contextmanager
def installed():
    """Unselected Stage 91 scope; preserve every existing external main boundary."""
    import fourier_main
    import scheduled_generator
    report = dict(asymmetric_main_audit=[], recycled_grandchild_calls=0,
                  extra_snapshot_through_phase=0, external_phase_ledger_changes=False)
    with asymmetric.installed(audit=report['asymmetric_main_audit']):
        old_forward = nested_main.forward_nested
        bindings = [(virtual_main, 'inverse_virtual_main_low'),
                    (scheduled_generator, 'inverse_virtual_main_low'),
                    (fourier_main, 'inverse_virtual_main_low')]
        previous = [(module, name, getattr(module, name)) for module, name in bindings]
        old_inverse = virtual_main.inverse_virtual_main_low

        def forward(*args, **kwargs):
            token = forward_nested_recycled(*args, **kwargs)
            report['recycled_grandchild_calls'] += 1
            report['grandchild_width'] = token.nested_child.recycled_grandchild.window
            report['child_width'] = token.nested_child.window
            report['private_wrap_outcomes'] = 1
            report['distinct_private_carry_owners'] = 2
            return token

        def inverse(builder, digits, source, low, token, **kwargs):
            if hasattr(getattr(token, 'nested_child', None), 'recycled_grandchild'):
                return inverse_nested_recycled(builder, digits, source, low, token, **kwargs)
            return old_inverse(builder, digits, source, low, token, **kwargs)

        nested_main.forward_nested = forward
        for module, name in bindings:
            setattr(module, name, inverse)
        try:
            yield report
            if report['recycled_grandchild_calls'] != 1:
                raise AssertionError('Exactly one selected recycled main child must be emitted.')
        finally:
            nested_main.forward_nested = old_forward
            for module, name, function in reversed(previous):
                setattr(module, name, function)
