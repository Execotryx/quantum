# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""A private narrow forward window inside the first full main-result group.

The last two rows update the full physical word first.  The first two rows
then use a window two bits narrower and one debt-free high correction.  Its
original top-bit snapshot is measured before phase application.  The three-
outcome Fourier inverse absorbs that correction while reversing the first
two rows on the retained word; its existing signed carry phases account for
both measured high bits.  The private snapshot is repaid before reversing
the last two rows, when its precise original value has returned.

Only the recorded lower carries belong to the narrow forward operation.
Their values depend on the identical lower input prefix, independent of
the containing modulus.  A full-width debt view therefore changes only the
width certificate; it neither invents high measurement owners nor transfers
any private owner to the external Fourier/table ledger.
"""
from __future__ import annotations

from contextlib import contextmanager

import fourier_suffix_inverse as fourier
import nested_main_window as nested_main
import paired_arithmetic as paired
import split_bounded
import top_virtual_main as top_main
from variable_lsb_main import row_parity_mask
import virtual_lsb
import virtual_main


def forward_asymmetric_full(builder, digits, source, target, plan, child, *, parity_before):
    """Emit later full rows, then the early bounded pair and its high update."""
    source, target = list(source), list(target)
    if (plan.signed_source or child.signed_source or len(target) != plan.window
            or split_bounded._digit_count(digits) != plan.digits
            or plan.first != child.first or child.last-child.first != 2
            or plan.last-child.last != 2 or plan.window-child.window != 2
            or tuple(plan.shifts[:2]) != tuple(child.shifts)
            or tuple(plan.shifts[2:]) != (0, 1)
            or any(shift > 0 for shift in child.shifts)
            or not 0 <= parity_before < 1 << len(source)):
        raise ValueError('The full asymmetric window requires two early virtual rows and the final ordinary pair.')
    if len(source) > child.window:
        raise ValueError('A source contribution would extend into the measured Fourier suffix.')
    token = top_main.FullVirtualToken(plan, len(target),
        [None]*(plan.last-plan.first), [None]*(plan.last-plan.first),
        parity_before, parity_before)
    parity = parity_before
    later = [(index, plan.shifts[index-plan.first]) for index in range(child.last, plan.last)]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        seed = virtual_main._row_seed(parity, len(source), shift)
        offset = index-plan.first
        token.row_parities[offset] = seed
        token.row_debts[offset] = top_main.forward_virtual_row(
            builder, source, target, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)

    low, high = target[:child.window], target[child.window:]
    saved = builder.alloc_qubits(1)[0]
    builder.cx(low[-1], saved)
    narrow = virtual_main.VirtualMainToken(child, saved, child.window, [],
        parity_before=parity, row_parities=[])
    rows = list(zip(range(child.first, child.last), child.shifts))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        seed = virtual_main._row_seed(parity, len(source), shift)
        row = top_main.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        if row.inactive or row.ordinary:
            raise ValueError('The selected early pair must use active virtual-bottom rows.')
        narrow.row_debts.append(row)
        narrow.row_parities.append(seed)
        token.row_debts[index-plan.first] = row
        token.row_parities[index-plan.first] = seed
        parity ^= row_parity_mask(len(source), shift)
        if index+1 == child.last:
            # Reuse the already exposed last digit.  The direct disposable
            # kernel has no measured carry for a two-bit high word.
            nested_main.forward_disposable_wrap(builder,
                nested_main.single_control(child, sign), [], low+high, narrow,
                inverse=False)
            narrow.high_width = len(high)
            narrow.stage = 'high_done'
    if (narrow.overflow_debt.width != 2 or narrow.overflow_debt.measurements
            or narrow.overflow_debt.consumed):
        raise AssertionError('The private two-bit high correction must have no forward carry phase.')
    narrow.saved_measurement = paired.release_saved_bit(builder, narrow.saved_bit)
    narrow.saved_bit = None
    narrow.full_snapshot_retired = True
    token.parity_after = narrow.parity_after = parity
    token.asymmetric_full_child = narrow
    return token


def inverse_narrow_fourier_row(builder, source, target, row, *, narrow_width,
                               full_width, shift, sign, initial_lsb, suffix, carry_budget=None):
    """Repay a narrow row through the existing full-width Fourier inverse."""
    original = row.carry_debt
    if (row.shift != shift or shift > 0 or row.ordinary or row.inactive
            or original.consumed or original.width != narrow_width
            or len(target) != narrow_width or full_width != narrow_width+2
            or any(not 1 <= position <= narrow_width-2 for position in original.measurements)):
        raise ValueError('The early row has mismatched lower carry positions or target widths.')
    # Sharing the dictionary makes consumption visible to the original row
    # token.  The upper two positions deliberately have no forward owner.
    widened = paired.CarryDebt(original.measurements, full_width)
    view = virtual_lsb.VirtualRowDebt(row.shift, False, False, widened)
    with fourier.shortened_row_adder(sign, suffix):
        virtual_lsb.inverse_virtual_row(builder, source, target, view,
            shift=shift, sign=sign, initial_lsb=initial_lsb, carry_budget=carry_budget)
    if widened.measurements or not widened.consumed:
        raise AssertionError('The Fourier inverse left a private lower carry phase unpaid.')
    original.consumed = True


def inverse_asymmetric_full_truncated(builder, digits, source, target, token, suffix, *, carry_budget=None):
    """Reverse the early pair, repay its private snapshot, then the later pair."""
    source, target = list(source), list(target)
    narrow = token.asymmetric_full_child
    if (token.consumed or not isinstance(suffix, fourier.FourierSuffixDebt3)
            or suffix.consumed or token.width != len(target)+2
            or narrow.window != len(target) or narrow.stage != 'high_done'
            or narrow.high_width != 2 or narrow.saved_bit is not None
            or narrow.saved_measurement is None
            or not getattr(narrow, 'full_snapshot_retired', False)
            or narrow.overflow_debt.consumed or narrow.overflow_debt.measurements
            or narrow.overflow_debt.width != 2
            or split_bounded._digit_count(digits) != token.plan.digits):
        raise ValueError('The full inverse requires its private retired snapshot and unchanged three-outcome suffix.')
    external = (suffix.odd, suffix.twice, suffix.four_times)
    private = [narrow.saved_measurement]
    for row in token.row_debts:
        private.extend(row.carry_debt.measurements.values())
    if len(set(private+list(external))) != len(private)+len(external):
        raise ValueError('The private full-group and external suffix owners must be distinct.')
    token.consumed = True
    rows = list(reversed(list(zip(range(narrow.plan.first, narrow.plan.last), narrow.plan.shifts))))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        offset = index-token.plan.first
        row = token.row_debts[offset]
        if row is not narrow.row_debts[index-narrow.plan.first]:
            raise AssertionError('The full and narrow views no longer own the same forward row.')
        inverse_narrow_fourier_row(builder, source, target, row,
            narrow_width=narrow.window, full_width=token.width, shift=shift, sign=sign,
            initial_lsb=token.row_parities[offset], suffix=suffix, carry_budget=carry_budget)
    narrow.overflow_debt.consumed = True
    paired.repay_saved_bit(builder, target[narrow.window-1], narrow.saved_measurement)
    narrow.saved_measurement = None
    narrow.stage = 'consumed'

    later = [(index, token.plan.shifts[index-token.plan.first])
             for index in reversed(range(narrow.plan.last, token.plan.last))]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        offset = index-token.plan.first
        with fourier.shortened_row_adder(sign, suffix):
            virtual_lsb.inverse_virtual_row(builder, source, target, token.row_debts[offset],
                shift=shift, sign=sign, initial_lsb=token.row_parities[offset], carry_budget=carry_budget)
    if (suffix.odd, suffix.twice, suffix.four_times) != external or suffix.consumed:
        raise AssertionError('A private full inverse changed the external Fourier owners.')


@contextmanager
def installed(*, audit=None):
    """Select only the first full main group; leave bounded groups untouched."""
    import fourier_main
    import scheduled_generator
    records = [] if audit is None else audit
    old_forward = top_main.forward_full_virtual_rows
    old_inverse = fourier.inverse_full_group_truncated
    old_full_inverse = top_main.inverse_full_virtual_rows
    bindings = [(top_main, 'forward_full_virtual_rows'),
                (scheduled_generator, 'forward_full_virtual_rows'),
                (fourier, 'inverse_full_group_truncated'),
                (fourier_main, 'inverse_full_group_truncated'),
                (top_main, 'inverse_full_virtual_rows'),
                (scheduled_generator, 'inverse_full_virtual_rows')]
    previous = [(module, name, getattr(module, name)) for module, name in bindings]

    def forward(builder, digits, source, target, plan, **kwargs):
        selected = (len(source), plan.digits, plan.first, plan.last, plan.window) == (17, 14, 10, 14, 19)
        if not selected:
            return old_forward(builder, digits, source, target, plan, **kwargs)
        if set(kwargs) != {'parity_before'}:
            raise ValueError('The selected full window requires the unchanged source-parity interface.')
        child = nested_main.child_plan(plan, plan.first+2)
        if child.window != 17:
            raise AssertionError('The early full-group pair ceased to have a seventeen-bit bound.')
        before = builder.num_allocated_qubits
        token = forward_asymmetric_full(builder, digits, source, target, plan, child, **kwargs)
        if builder.num_allocated_qubits != before:
            raise AssertionError('The private full-group snapshot survived through the phase boundary.')
        records.append({'component': 'asymmetric_full_main',
            'group_rows': [plan.first, plan.last], 'early_rows': [child.first, child.last],
            'forward_order': list(range(child.last, plan.last))+list(range(child.first, child.last)),
            'full_width': plan.window, 'narrow_width': child.window,
            'private_high_forward_carry_debts': 0, 'persistent_extra_snapshot': 0,
            'snapshot_repayment': 'conditional Z after early inverse, before later inverse',
            'external_fourier_owner_changes': False})
        return token

    def inverse(builder, digits, source, target, token, suffix):
        if hasattr(token, 'asymmetric_full_child'):
            return inverse_asymmetric_full_truncated(builder, digits, source, target, token, suffix)
        return old_inverse(builder, digits, source, target, token, suffix)

    def full_inverse(builder, digits, source, target, token, **kwargs):
        if hasattr(token, 'asymmetric_full_child'):
            raise ValueError('The asymmetric full group requires the selected three-outcome Fourier inverse.')
        return old_full_inverse(builder, digits, source, target, token, **kwargs)

    top_main.forward_full_virtual_rows = scheduled_generator.forward_full_virtual_rows = forward
    fourier.inverse_full_group_truncated = fourier_main.inverse_full_group_truncated = inverse
    top_main.inverse_full_virtual_rows = scheduled_generator.inverse_full_virtual_rows = full_inverse
    try:
        yield records
    finally:
        for module, name, value in reversed(previous):
            setattr(module, name, value)
