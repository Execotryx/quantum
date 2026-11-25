# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Narrow forward main rows with full-parent inverse rows.

The first four main rows may be computed modulo nine bits and followed by
one bounded two-bit high correction.  Their inverse instead subtracts each
row modulo the eleven-bit parent.  Forward carry phases only concern lower
positions, so the original nine-bit measurement ledger is also a valid
partial ledger for each eleven-bit inverse.  No high-correction carry phase
exists for its two-bit adder.

This removes the child's saved quantum bit before low phase.  Its private
X-measurement phase is repaid on the restored old child MSB after the four
full-width inverse rows.  No new debt escapes the main-result region.
"""
from __future__ import annotations

from contextlib import contextmanager

import nested_main_window as nested_main
import paired_arithmetic as paired
import split_bounded
import virtual_lsb
import virtual_main


def retire_child_snapshot(builder, token):
    """Retain only a classical phase owner after a debt-free high correction."""
    child = token.nested_child
    high = child.overflow_debt
    if (child.stage != 'high_done' or child.high_width != 2
            or token.window - child.window != 2
            or not isinstance(high, paired.CarryDebt) or high.width != 2
            or high.measurements or high.consumed
            or child.saved_bit is None or child.saved_measurement is not None):
        raise ValueError('Snapshot retirement needs an unconsumed, phase-free two-bit child high update.')
    child.saved_measurement = paired.release_saved_bit(builder, child.saved_bit)
    child.saved_bit = None
    child.asymmetric_snapshot_retired = True


def inverse_widened_row(builder, source, target, token, *, narrow_width,
                        shift, sign, initial_lsb, carry_budget=None):
    """Invert a virtual row while repaying its unchanged lower carry functions.

For a right-shifted unsigned virtual row, carry at position j depends only
on incoming carry and source/target bits strictly below j.  The low bits of
modular additions are independent of their selected modulus.  Accordingly
every measured carry from the narrow forward row equals its counterpart
in this wider inverse.  The newly exposed high positions have zero debt.
The source-parity seed and complemented sign frame are identical.
"""
    if (token.shift != shift or shift > 0 or token.ordinary
            or len(target) <= narrow_width):
        raise ValueError('Widening is restricted to the same unsigned virtual row and a larger target.')
    if token.inactive:
        if token.carry_debt is not None:
            raise ValueError('An inactive virtual row unexpectedly owns a carry debt.')
        return
    original = token.carry_debt
    if (not isinstance(original, paired.CarryDebt)
            or original.width != narrow_width or original.consumed
            or any(not isinstance(position, int) or not 1 <= position <= narrow_width - 2
                   for position in original.measurements)):
        raise ValueError('The narrow carry ledger has an invalid or already consumed owner.')
    widened = paired.CarryDebt(original.measurements, len(target))
    view = virtual_lsb.VirtualRowDebt(token.shift, False, False, widened)
    virtual_lsb.inverse_virtual_row(builder, source, target, view,
        shift=shift, sign=sign, initial_lsb=initial_lsb, carry_budget=carry_budget)
    if not widened.consumed or widened.measurements:
        raise AssertionError('A widened inverse failed to repay the original lower carry ledger.')
    original.consumed = True


def inverse_asymmetric(builder, digits, source, low, token, *, carry_budget=None):
    """Reverse the bounded child through full-parent rows and repay its snapshot."""
    source, low = list(source), list(low)
    if (token.stage != 'high_undone' or len(low) != token.window
            or split_bounded._digit_count(digits) != token.plan.digits):
        raise ValueError('The parent high correction must be reversed before its rows.')
    if token.saved_bit is not None:
        token.saved_measurement = paired.release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    child = token.nested_child
    high = child.overflow_debt
    if (child.stage != 'high_done' or child.high_width != 2
            or not getattr(child, 'asymmetric_snapshot_retired', False)
            or child.saved_bit is not None or child.saved_measurement is None
            or not isinstance(high, paired.CarryDebt) or high.width != 2
            or high.measurements or high.consumed):
        raise ValueError('The child must own exactly its retired snapshot and empty high ledger.')

    rows = list(reversed(list(zip(range(child.plan.first, child.plan.last), child.plan.shifts))))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        offset = index - child.plan.first
        if token.row_debts[index - token.plan.first] is not child.row_debts[offset]:
            raise AssertionError('Parent and child lost their shared original row-debt owner.')
        inverse_widened_row(builder, source, low, child.row_debts[offset],
            narrow_width=child.window, shift=shift, sign=sign,
            initial_lsb=child.row_parities[offset], carry_budget=carry_budget)

    # The complete full-width row subtraction has now undone both the child
    # low update and its one net high correction.  That high adder had no
    # measured carries, so there is no extra phase polynomial to reconstruct.
    high.consumed = True
    paired.repay_saved_bit(builder, low[child.window - 1], child.saved_measurement)
    child.saved_measurement = None
    child.stage = 'consumed'

    later = [(index, token.plan.shifts[index - token.plan.first])
             for index in reversed(range(child.plan.last, token.plan.last))]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        offset = index - token.plan.first
        virtual_lsb.inverse_virtual_row(builder, source, low, token.row_debts[offset],
            shift=shift, sign=sign, initial_lsb=token.row_parities[offset],
            carry_budget=carry_budget)
    if token.saved_measurement is None:
        raise AssertionError('The restored parent MSB has no matching phase owner.')
    paired.repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = 'consumed'


@contextmanager
def installed(*, audit=None):
    """Select only the main 9-to-11 child while preserving the 54-live phase entry."""
    import fourier_main
    import scheduled_generator
    records = [] if audit is None else audit
    with nested_main.installed(audit=records):
        original_forward = virtual_main.forward_virtual_main_low
        original_inverse = virtual_main.inverse_virtual_main_low
        bindings = [(virtual_main, 'forward_virtual_main_low'),
                    (scheduled_generator, 'forward_virtual_main_low'),
                    (virtual_main, 'inverse_virtual_main_low'),
                    (scheduled_generator, 'inverse_virtual_main_low'),
                    (fourier_main, 'inverse_virtual_main_low')]
        previous = [(module, name, getattr(module, name)) for module, name in bindings]

        def forward(builder, digits, source, low, plan, **kwargs):
            token = original_forward(builder, digits, source, low, plan, **kwargs)
            if hasattr(token, 'nested_child'):
                retire_child_snapshot(builder, token)
                record = records[-1]
                if record.get('component') != 'nested_main_child':
                    raise AssertionError('The selected nested child lost its source audit record.')
                record.update(persistent_extra_snapshot=0,
                              backward_child_row_width=plan.window,
                              child_high_forward_carry_debts=0,
                              child_snapshot_repayment='private conditional Z after inverse child rows')
            return token

        def inverse(builder, digits, source, low, token, **kwargs):
            if hasattr(token, 'nested_child'):
                return inverse_asymmetric(builder, digits, source, low, token, **kwargs)
            return original_inverse(builder, digits, source, low, token, **kwargs)

        for module, name in bindings:
            setattr(module, name, forward if name == 'forward_virtual_main_low' else inverse)
        try:
            yield records
        finally:
            for module, name, function in reversed(previous):
                setattr(module, name, function)
