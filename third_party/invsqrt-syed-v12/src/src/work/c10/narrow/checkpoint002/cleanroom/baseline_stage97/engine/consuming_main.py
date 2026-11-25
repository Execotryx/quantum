# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""A-even consuming main arithmetic on a literal twenty-bit result word.

The refitted coefficient table has an even low word, so its bit zero is not
stored.  The last signed row uses the odd operand 2R+1 and runs first:

    U = A + R + 1 - q*(2R + 1),   R = 2v + r,
    U0 = q XOR r XOR 1,           floor(U/2) = A/2 + (1 - 2q)*(v + r).

The upper word is complemented under q, the unsigned source R[1:] is added
with carry-in R0, the complement is undone, and CX(R0, q), X(q) turn the
consumed sign wire into result bit zero.  The remaining rows are the
existing virtual-bottom rows with initial virtual bit zero.

The result is a literal word, so no original-top snapshot and no
reconstructed top exist.  Every forward adder which reaches the three
Fourier-measured high bits uses a three-bit carry-clean terminal: with
incoming carry c and lowest terminal bit b it computes d = c AND b, updates
b, runs the ordinary two-bit terminal with carry d, and erases d from
c AND NOT b' before c itself is released.  Forward carry debts therefore
exist only at positions up to the retained inverse width, exactly the
interface of the shortened Fourier inverse.

The inverse reverses the bounded groups and the early pair as before, then
the full row, restores the sign wire, and finally reverses the consuming
row on the retained upper word with the same signed Fourier carry phases.
"""
from __future__ import annotations

from contextlib import contextmanager

import kickmix as km
from cyclic_phase import _erase_polynomial
import fourier_suffix_inverse as fourier
from fusion.arithmetic import _compute_carry, _sum_keep_carry
import nested_main_window as nested_main
import paired_arithmetic as paired
from quadratic_terms import xor_polynomial
import split_bounded
import top_virtual_main as top_main
from variable_lsb_main import row_parity_mask
import virtual_lsb
import virtual_main

SUFFIX_BITS = 3


def forward_add_clean_terminal(builder, source, target, *, carry_in, release=None):
    """target += source + carry_in, exposing carry debts only below the top three bits.

    The three high source bits must be literal zero.  Carries into positions
    1..width-3 are measured into the returned debt, as in the paired adder.
    The carry into position width-2 lives only inside the terminal and is
    erased there for both measurement outcomes.  With `release`, the incoming
    carry is disposable and is released by that callback as soon as its last
    reader has run; otherwise it is a preserved source wire.
    """
    a, b, _ = paired._inputs(source, target, carry_in, False)
    width = len(b)
    if width < SUFFIX_BITS or any(wire is not False for wire in a[-SUFFIX_BITS:]):
        raise ValueError('The carry-clean terminal needs three literal-zero high source bits.')
    if not isinstance(carry_in, km.q):
        raise ValueError('The carry-clean terminal needs a quantum incoming carry.')
    debts = {}

    def measure(carry, position):
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(carry, outcome)
        builder.free(carry)
        debts[position] = outcome

    incoming = carry_in
    for index, (aa, bb) in enumerate(zip(a[:-SUFFIX_BITS], b[:-SUFFIX_BITS])):
        frame = _compute_carry(builder, aa, bb, incoming)
        _sum_keep_carry(builder, frame)
        if index:
            measure(incoming, index)
        elif release is not None:
            release()
        incoming = frame.outgoing
    low, middle, top = b[-SUFFIX_BITS:]
    inner = builder.alloc_qubits(1)[0]
    builder.ccx(incoming, low, inner)
    builder.cx(incoming, low)
    builder.ccx(inner, middle, top)
    builder.cx(inner, middle)
    # The inner carry is incoming AND NOT the updated low terminal bit.
    builder.x(low)
    builder.del_and(incoming, low, inner)
    builder.x(low)
    builder.free(inner)
    if width > SUFFIX_BITS:
        measure(incoming, width-SUFFIX_BITS)
    elif release is not None:
        release()
    return paired.CarryDebt(debts, width)


def forward_consuming_row(builder, source, upper, sign):
    """Add the odd last row to an even word; the sign wire becomes result bit zero."""
    source, upper = list(source), list(upper)
    if (len(source) < 2 or len(upper) < len(source)+2 or not isinstance(sign, km.q)
            or sign in source+upper):
        raise ValueError('The consuming row needs R, a wider disjoint upper word and its sign wire.')
    for wire in upper:
        builder.cx(sign, wire)
    debt = forward_add_clean_terminal(builder, source[1:], upper, carry_in=source[0])
    for wire in upper:
        builder.cx(sign, wire)
    builder.cx(source[0], sign)
    builder.x(sign)
    return debt


def inverse_consuming_row_truncated(builder, source, upper, low_bit, debt, suffix, *,
                                    carry_budget=None):
    """Restore the sign wire, then reverse the consuming row on the retained upper word."""
    source, upper = list(source), list(upper)
    if len(upper) != len(source)-1 or low_bit in source+upper:
        raise ValueError('The retained upper word must hold exactly the shifted source.')
    builder.x(low_bit)
    builder.cx(source[0], low_bit)
    for wire in upper:
        builder.cx(low_bit, wire)
    fourier.inverse_add_truncated(builder, source[1:], upper, debt, sign=low_bit,
        suffix=suffix, carry_in=source[0], carry_budget=carry_budget)
    for wire in upper:
        builder.cx(low_bit, wire)


def forward_virtual_row_clean(builder, source, target, *, shift, sign, initial_lsb):
    """A virtual-bottom row on the whole literal word, with the carry-clean terminal."""
    source, target = list(source), list(target)
    if shift > 0:
        raise ValueError('The literal full row is a right-shifted or unshifted virtual row.')
    cut = -shift
    variables, terms = virtual_lsb._carry_terms(source, sign, cut, initial_lsb)
    if not terms:
        raise ValueError('The literal full row must own an active source-parity carry.')
    carry = builder.alloc_qubits(1)[0]
    xor_polynomial(builder, variables, carry, terms)
    for wire in target:
        builder.cx(sign, wire)
    debt = forward_add_clean_terminal(builder, source[cut+1:], target, carry_in=carry,
        release=lambda: _erase_polynomial(builder, carry, variables, terms))
    for wire in target:
        builder.cx(sign, wire)
    return virtual_lsb.VirtualRowDebt(shift, False, False, debt)


def forward_clean_wrap(builder, residual, source, target, token, **kwargs):
    """A bounded forward high correction which reaches the literal top bits."""
    if kwargs.get('inverse') or token.plan.signed_source or token.saved_bit is None:
        raise ValueError('The carry-clean wrap is only an unsigned forward correction.')
    sign = residual[token.plan.last-1]
    saved, top = token.saved_bit, target[token.window-1]
    high = list(target[token.window:])
    builder.cx(sign, saved)
    builder.cx(sign, top)
    builder.x(top)
    wrap = builder.alloc_qubits(1)[0]
    builder.ccx(saved, top, wrap)
    for wire in high:
        builder.cx(sign, wire)

    def release():
        builder.del_and(saved, top, wrap)
        builder.free(wrap)

    token.overflow_debt = forward_add_clean_terminal(builder, [], high, carry_in=wrap,
                                                     release=release)
    for wire in high:
        builder.cx(sign, wire)
    builder.x(top)
    builder.cx(sign, top)
    builder.cx(sign, saved)


def _sign_wire(digits, index):
    """The physical wire of a logical digit which is stored without packing."""
    if hasattr(digits, 'digit'):
        if index < 4:
            raise ValueError('The consumed digit must be a directly stored residual wire.')
        return digits.residual[index]
    return digits[index]


def forward_consuming_full(builder, digits, source, upper, plan, child, *, parity_before):
    """Consume the last row, then the full row and the early bounded pair.

    `upper` is the stored even word without its zero bit; the returned
    token carries the literal word, whose bit zero is the consumed sign wire.
    """
    source, upper = list(source), list(upper)
    if (plan.signed_source or child.signed_source or len(upper) != plan.window
            or split_bounded._digit_count(digits) != plan.digits
            or plan.first != child.first or child.last-child.first != 2
            or plan.last-child.last != 2 or plan.window-child.window != 2
            or tuple(plan.shifts[:2]) != tuple(child.shifts)
            or tuple(plan.shifts[2:]) != (0, 1)
            or any(shift > 0 for shift in child.shifts)
            or not 0 <= parity_before < 1 << len(source)):
        raise ValueError('The consuming full window requires two early virtual rows and the final pair.')
    if len(source) > child.window:
        raise ValueError('A source contribution would extend into the measured Fourier suffix.')
    last = plan.last-1
    low_bit = _sign_wire(digits, last)
    consumed = forward_consuming_row(builder, source, upper, low_bit)
    target = [low_bit]+upper
    rows = plan.last-plan.first
    token = top_main.FullVirtualToken(plan, len(target), [None]*rows, [None]*rows,
                                      parity_before, parity_before)
    token.row_debts[last-plan.first] = virtual_lsb.VirtualRowDebt(plan.shifts[-1], True, False, consumed)
    parity = parity_before
    full = [(child.last, plan.shifts[child.last-plan.first])]
    for index, shift, sign in split_bounded._row_controls(digits, full):
        seed = virtual_main._row_seed(parity, len(source), shift)
        offset = index-plan.first
        token.row_parities[offset] = seed
        token.row_debts[offset] = forward_virtual_row_clean(
            builder, source, target, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)

    low, high = target[:child.window], target[child.window:]
    if len(high) != SUFFIX_BITS:
        raise AssertionError('The early pair must leave exactly the Fourier suffix above it.')
    saved = builder.alloc_qubits(1)[0]
    builder.cx(low[-1], saved)
    narrow = virtual_main.VirtualMainToken(child, saved, child.window, [],
        parity_before=parity, row_parities=[])
    early = list(zip(range(child.first, child.last), child.shifts))
    for index, shift, sign in split_bounded._row_controls(digits, early):
        seed = virtual_main._row_seed(parity, len(source), shift)
        row = virtual_lsb.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        if row.inactive or row.ordinary:
            raise ValueError('The selected early pair must use active virtual-bottom rows.')
        narrow.row_debts.append(row)
        narrow.row_parities.append(seed)
        token.row_debts[index-plan.first] = row
        token.row_parities[index-plan.first] = seed
        parity ^= row_parity_mask(len(source), shift)
        if index+1 == child.last:
            forward_clean_wrap(builder, nested_main.single_control(child, sign), [],
                               low+high, narrow, inverse=False)
            narrow.high_width = len(high)
            narrow.stage = 'high_done'
    if (narrow.overflow_debt.width != SUFFIX_BITS or narrow.overflow_debt.measurements
            or narrow.overflow_debt.consumed):
        raise AssertionError('The private three-bit high correction must have no forward carry phase.')
    narrow.saved_measurement = paired.release_saved_bit(builder, narrow.saved_bit)
    narrow.saved_bit = None
    narrow.full_snapshot_retired = True
    token.parity_after = narrow.parity_after = parity
    token.asymmetric_full_child = narrow
    token.literal_target = target
    token.consumed_low_bit = low_bit
    return token


def inverse_narrow_literal_row(builder, source, target, row, *, narrow_width, full_width,
                               shift, sign, initial_lsb, suffix, carry_budget=None):
    """Repay an early narrow row through the literal-width Fourier inverse."""
    original = row.carry_debt
    if (row.shift != shift or shift > 0 or row.ordinary or row.inactive
            or original.consumed or original.width != narrow_width
            or len(target) != narrow_width or full_width != narrow_width+SUFFIX_BITS
            or any(not 1 <= position <= narrow_width-2 for position in original.measurements)):
        raise ValueError('The early row has mismatched lower carry positions or target widths.')
    widened = paired.CarryDebt(original.measurements, full_width)
    view = virtual_lsb.VirtualRowDebt(row.shift, False, False, widened)
    with fourier.shortened_row_adder(sign, suffix):
        virtual_lsb.inverse_virtual_row(builder, source, target, view,
            shift=shift, sign=sign, initial_lsb=initial_lsb, carry_budget=carry_budget)
    if widened.measurements or not widened.consumed:
        raise AssertionError('The Fourier inverse left a private lower carry phase unpaid.')
    original.consumed = True


def inverse_consuming_full_truncated(builder, digits, source, target, token, suffix, *,
                                     carry_budget=None):
    """Reverse the early pair, the full row, and finally the consuming row."""
    source, target = list(source), list(target)
    narrow = token.asymmetric_full_child
    if (token.consumed or not isinstance(suffix, fourier.FourierSuffixDebt3)
            or suffix.consumed or suffix.physical != SUFFIX_BITS
            or token.width != len(target)+SUFFIX_BITS
            or target != token.literal_target[:len(target)]
            or narrow.window != len(target) or narrow.stage != 'high_done'
            or narrow.high_width != SUFFIX_BITS or narrow.saved_bit is not None
            or narrow.saved_measurement is None
            or not getattr(narrow, 'full_snapshot_retired', False)
            or narrow.overflow_debt.consumed or narrow.overflow_debt.measurements
            or narrow.overflow_debt.width != SUFFIX_BITS
            or split_bounded._digit_count(digits) != token.plan.digits):
        raise ValueError('The consuming inverse requires its retired snapshot and the literal three-bit suffix.')
    external = (suffix.odd, suffix.twice, suffix.four_times)
    private = [narrow.saved_measurement]
    for row in token.row_debts:
        private.extend(row.carry_debt.measurements.values())
    if len(set(private+list(external))) != len(private)+len(external):
        raise ValueError('The private full-group and external suffix owners must be distinct.')
    token.consumed = True
    plan = token.plan
    early = list(reversed(list(zip(range(narrow.plan.first, narrow.plan.last), narrow.plan.shifts))))
    for index, shift, sign in split_bounded._row_controls(digits, early):
        offset = index-plan.first
        row = token.row_debts[offset]
        if row is not narrow.row_debts[index-narrow.plan.first]:
            raise AssertionError('The full and narrow views no longer own the same forward row.')
        inverse_narrow_literal_row(builder, source, target, row,
            narrow_width=narrow.window, full_width=token.width, shift=shift, sign=sign,
            initial_lsb=token.row_parities[offset], suffix=suffix, carry_budget=carry_budget)
    narrow.overflow_debt.consumed = True
    paired.repay_saved_bit(builder, target[narrow.window-1], narrow.saved_measurement)
    narrow.saved_measurement = None
    narrow.stage = 'consumed'

    full = [(narrow.plan.last, plan.shifts[narrow.plan.last-plan.first])]
    for index, shift, sign in split_bounded._row_controls(digits, full):
        offset = index-plan.first
        with fourier.shortened_row_adder(sign, suffix):
            virtual_lsb.inverse_virtual_row(builder, source, target, token.row_debts[offset],
                shift=shift, sign=sign, initial_lsb=token.row_parities[offset],
                carry_budget=carry_budget)
    consumed = token.row_debts[plan.last-1-plan.first]
    if target[0] != token.consumed_low_bit or not consumed.ordinary:
        raise AssertionError('The consumed sign wire left result position zero.')
    inverse_consuming_row_truncated(builder, source, target[1:], target[0],
        consumed.carry_debt, suffix, carry_budget=carry_budget)
    if (suffix.odd, suffix.twice, suffix.four_times) != external or suffix.consumed:
        raise AssertionError('The consuming inverse changed the external Fourier owners.')


@contextmanager
def installed(*, audit=None):
    """Select the consuming first group and the literal-top bounded corrections."""
    import fourier_main
    import scheduled_generator
    records = [] if audit is None else audit
    old_forward = top_main.forward_full_virtual_rows
    old_inverse = fourier.inverse_full_group_truncated
    old_full_inverse = top_main.inverse_full_virtual_rows
    old_wrap = nested_main.forward_disposable_wrap
    bindings = [(top_main, 'forward_full_virtual_rows'),
                (scheduled_generator, 'forward_full_virtual_rows'),
                (fourier, 'inverse_full_group_truncated'),
                (fourier_main, 'inverse_full_group_truncated'),
                (top_main, 'inverse_full_virtual_rows'),
                (scheduled_generator, 'inverse_full_virtual_rows'),
                (nested_main, 'forward_disposable_wrap')]
    previous = [(module, name, getattr(module, name)) for module, name in bindings]
    literal = {'suffix': None, 'clean_wraps': []}

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
        token = forward_consuming_full(builder, digits, source, target, plan, child, **kwargs)
        if builder.num_allocated_qubits != before:
            raise AssertionError('The private full-group snapshot survived through the phase boundary.')
        literal['suffix'] = tuple(token.literal_target[-SUFFIX_BITS:])
        records.append({'component': 'consuming_full_main',
            'group_rows': [plan.first, plan.last], 'early_rows': [child.first, child.last],
            'forward_order': [plan.last-1, child.last]+list(range(child.first, child.last)),
            'literal_width': len(token.literal_target), 'narrow_width': child.window,
            'consumed_sign_digit': plan.last-1, 'original_top_snapshot': 0,
            'private_high_forward_carry_debts': 0, 'persistent_extra_snapshot': 0,
            'snapshot_repayment': 'conditional Z after early inverse, before the full row inverse',
            'external_fourier_owner_changes': False})
        return token

    def inverse(builder, digits, source, target, token, suffix):
        if hasattr(token, 'consumed_low_bit'):
            return inverse_consuming_full_truncated(builder, digits, source, target, token, suffix)
        return old_inverse(builder, digits, source, target, token, suffix)

    def full_inverse(builder, digits, source, target, token, **kwargs):
        if hasattr(token, 'consumed_low_bit'):
            raise ValueError('The consuming full group requires the three-outcome Fourier inverse.')
        return old_full_inverse(builder, digits, source, target, token, **kwargs)

    def wrap(builder, residual, source, target, token, **kwargs):
        high = tuple(target[token.window:])
        if literal['suffix'] is not None and high[-SUFFIX_BITS:] == literal['suffix']:
            forward_clean_wrap(builder, residual, source, target, token, **kwargs)
            literal['clean_wraps'].append(len(high))
            return None
        return old_wrap(builder, residual, source, target, token, **kwargs)

    top_main.forward_full_virtual_rows = scheduled_generator.forward_full_virtual_rows = forward
    fourier.inverse_full_group_truncated = fourier_main.inverse_full_group_truncated = inverse
    top_main.inverse_full_virtual_rows = scheduled_generator.inverse_full_virtual_rows = full_inverse
    nested_main.forward_disposable_wrap = wrap
    try:
        yield records
        if records:
            records[-1]['literal_bounded_high_widths'] = list(literal['clean_wraps'])
    finally:
        for module, name, value in reversed(previous):
            setattr(module, name, value)
