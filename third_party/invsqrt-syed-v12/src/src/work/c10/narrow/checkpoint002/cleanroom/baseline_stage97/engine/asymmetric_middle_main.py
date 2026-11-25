# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""A two-row child for the middle bounded main-result group.

Rows eight and nine run first on the original fifteen-bit parent.  Rows
six and seven then run on their certified thirteen-bit child, followed by
one two-bit high correction.  The child's saved bit is measured and freed
before the original parent high correction and before the low phase.

The unchanged partial-ledger inverse subtracts the two early rows on all
fifteen parent bits, repays the private child snapshot, and then subtracts
the later rows.  Its original parent snapshot and Fourier high interface
keep exactly their existing owners.  The child needs two carry slots while
its snapshot is live; these digits have no packed-control helper.

This scope composes inside recycled_grandchild_main.installed().  It does
not call or replace that scope's selected first-group forward function.
"""
from __future__ import annotations

from contextlib import contextmanager

import asymmetric_nested_main as asymmetric
import nested_main_window as nested_main
import split_bounded
from variable_lsb_main import row_parity_mask
import virtual_lsb
import virtual_main


def forward_middle(builder, digits, source, low, plan, child, *, parity_before):
    """Add a two-row child after its two later parent rows, with exact parity.

The nonzero row offset is retained throughout, so small native fixtures can
check the same ownership arithmetic without introducing unused input wires.
The caller supplies the existing disposable forward-wrap scope.  Unlike
the first group's patched forward function, this entry point is stable
while the recycled-grandchild scope is active.
"""
    source, low = list(source), list(low)
    if (plan.signed_source or child.signed_source
            or split_bounded._digit_count(digits) != plan.digits
            or child.digits != plan.digits or plan.first != child.first
            or child.last - child.first != 2 or plan.last - child.last != 2
            or len(low) != plan.window or plan.window - child.window != 2
            or child.shifts != plan.shifts[:child.last - child.first]
            or any(shift > 0 for shift in plan.shifts)
            or not isinstance(parity_before, int) or parity_before < 0
            or parity_before >> len(source)):
        raise ValueError('The middle child needs two unsigned virtual rows and a two-bit parent high word.')
    if builder.max_qubits - builder.num_allocated_qubits < 4:
        raise ValueError('Two snapshots and two streaming carry slots must fit before the middle group.')

    saved = builder.alloc_qubits(1)[0]
    builder.cx(low[-1], saved)
    token = virtual_main.VirtualMainToken(plan, saved, len(low),
        [None] * (plan.last - plan.first), parity_before=parity_before,
        row_parities=[None] * (plan.last - plan.first))
    parity = parity_before
    later = [(index, plan.shifts[index - plan.first])
             for index in range(child.last, plan.last)]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        seed = virtual_main._row_seed(parity, len(source), shift)
        offset = index - plan.first
        token.row_parities[offset] = seed
        token.row_debts[offset] = virtual_lsb.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)

    child_low, child_high = low[:child.window], low[child.window:]
    snapshot = builder.alloc_qubits(1)[0]
    builder.cx(child_low[-1], snapshot)
    nested = virtual_main.VirtualMainToken(child, snapshot, child.window, [],
        parity_before=parity, row_parities=[])
    rows = list(zip(range(child.first, child.last), child.shifts))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        seed = virtual_main._row_seed(parity, len(source), shift)
        debt = virtual_lsb.forward_virtual_row(
            builder, source, child_low, shift=shift, sign=sign, initial_lsb=seed)
        nested.row_parities.append(seed)
        nested.row_debts.append(debt)
        token.row_parities[index - plan.first] = seed
        token.row_debts[index - plan.first] = debt
        parity ^= row_parity_mask(len(source), shift)
        if index + 1 == child.last:
            split_bounded.forward_bounded_high(builder,
                nested_main.single_control(child, sign), child_low, child_high, nested)
    token.parity_after = nested.parity_after = parity
    token.nested_child = nested
    token.asymmetric_middle_selected = True
    asymmetric.retire_child_snapshot(builder, token)
    return token


@contextmanager
def installed():
    """Select only rows six through nine, preserving every external owner."""
    import fourier_main
    import scheduled_generator

    report = dict(middle_child_calls=0, middle_inverse_calls=0,
                  extra_snapshot_through_phase=0, external_phase_ledger_changes=False)
    old_forward = virtual_main.forward_virtual_main_low
    old_inverse = virtual_main.inverse_virtual_main_low
    old_overflow = split_bounded._deferred_overflow
    bindings = [(virtual_main, 'forward_virtual_main_low'),
                (scheduled_generator, 'forward_virtual_main_low'),
                (virtual_main, 'inverse_virtual_main_low'),
                (scheduled_generator, 'inverse_virtual_main_low'),
                (fourier_main, 'inverse_virtual_main_low'),
                (split_bounded, '_deferred_overflow')]
    previous = [(module, name, getattr(module, name)) for module, name in bindings]
    owned_tokens = set()
    active = [False]

    def forward(builder, digits, source, low, plan, **kwargs):
        selected = (len(source), plan.digits, plan.first, plan.last, plan.window) == (17, 14, 6, 10, 15)
        if not selected:
            return old_forward(builder, digits, source, low, plan, **kwargs)
        if set(kwargs) != {'parity_before'}:
            raise ValueError('The selected middle group requires its unchanged source-parity interface.')
        child = nested_main.child_plan(plan, plan.first + 2)
        if child.window != 13:
            raise AssertionError('The selected two-row child ceased to be thirteen bits.')
        entry = builder.num_allocated_qubits
        active[0] = True
        try:
            token = forward_middle(builder, digits, source, low, plan, child, **kwargs)
        finally:
            active[0] = False
        owned_tokens.update((id(token), id(token.nested_child)))
        if builder.num_allocated_qubits != entry + 1:
            raise AssertionError('Only the original parent snapshot may survive the middle low rows.')
        report['middle_child_calls'] += 1
        report.update(rows=[child.first, child.last], later_rows=[child.last, plan.last],
            child_width=child.window, parent_width=plan.window,
            child_high_width=token.nested_child.high_width,
            child_high_forward_carry_debts=len(token.nested_child.overflow_debt.measurements),
            entry_live=entry, after_low_live=builder.num_allocated_qubits,
            private_child_snapshot_retired=True, packed_digit_helpers=0,
            parity_before=token.parity_before, parity_after=token.parity_after,
            backward_child_row_width=plan.window,
            child_snapshot_repayment='private conditional Z after inverse child rows')
        return token

    def inverse(builder, digits, source, low, token, **kwargs):
        if not getattr(token, 'asymmetric_middle_selected', False):
            return old_inverse(builder, digits, source, low, token, **kwargs)
        if (id(token) not in owned_tokens or token.high_width not in (4, 5)
                or token.stage != 'high_undone' or not token.overflow_debt.consumed
                or token.overflow_debt.measurements):
            raise ValueError('The original middle Fourier high correction must be consumed first.')
        asymmetric.inverse_asymmetric(builder, digits, source, low, token, **kwargs)
        child = token.nested_child
        if (child.stage != 'consumed' or child.saved_bit is not None
                or child.saved_measurement is not None or child.overflow_debt.measurements
                or not child.overflow_debt.consumed):
            raise AssertionError('The private middle child left a snapshot or carry owner.')
        report['middle_inverse_calls'] += 1
        report['all_private_owners_consumed'] = True

    def overflow(builder, digits, source, target, token, **kwargs):
        if not kwargs.get('inverse') and (active[0] or id(token) in owned_tokens):
            return nested_main.forward_disposable_wrap(builder, digits, source, target, token, **kwargs)
        return old_overflow(builder, digits, source, target, token, **kwargs)

    for module, name in bindings:
        replacement = (forward if name == 'forward_virtual_main_low' else
                       inverse if name == 'inverse_virtual_main_low' else overflow)
        setattr(module, name, replacement)
    try:
        yield report
        if report['middle_child_calls'] != 1 or report['middle_inverse_calls'] != 1:
            raise AssertionError('Exactly one selected middle child and matching inverse must be emitted.')
    finally:
        for module, name, function in reversed(previous):
            setattr(module, name, function)
