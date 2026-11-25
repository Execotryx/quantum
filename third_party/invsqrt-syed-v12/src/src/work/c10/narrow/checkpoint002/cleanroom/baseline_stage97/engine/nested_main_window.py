# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""A bounded child window for the first four main-result rows.

The selected eleven-bit parent performs its last two rows first, then a
nine-bit child for the first four rows, followed by the child's one high
correction.  The original parent high correction and all external result
interfaces are retained.  One additional saved bit lives through the phase
pass; a caller must separately provide a phase kernel accepting that bit.

Only two tight packed-digit lifetimes borrow existing packed wires.  Their
control frame is phase free, restores every packed bit, and uses no new
measurement owner.  Bounded forward wraps are erased after their first
use, which preserves the 57-qubit main-arithmetic limit.
"""
from __future__ import annotations

from contextlib import contextmanager

import kickmix as km
import paired_arithmetic as paired
from packed_shift import PackedShift
import split_bounded
from staged_arithmetic import bounded_rows_plan
from variable_lsb_main import row_parity_mask
import virtual_lsb
import virtual_main


def child_plan(parent, last):
    logical = bounded_rows_plan(
        digits=parent.digits, source_min=parent.source_min, source_max=parent.source_max,
        source_fraction=0, target_fraction=0, first=parent.first, last=last,
        first_shift=parent.shifts[0] - parent.first)
    plan = virtual_main.virtual_main_plan(logical)
    if not 0 < plan.window < parent.window:
        raise ValueError('The child must leave a nonempty parent high word.')
    return plan


def single_control(plan, sign):
    controls = [False] * plan.digits
    controls[plan.last - 1] = sign
    return controls


def forward_nested(builder, digits, source, low, plan, child, *, parity_before):
    """Compute an independently bounded child, then the rest of its parent."""
    source, low = list(source), list(low)
    if (plan.first != child.first or not plan.first < child.last < plan.last
            or len(low) != plan.window or child.window >= len(low)):
        raise ValueError('Mismatched nested row bounds or low-word ownership.')
    saved = builder.alloc_qubits(1)[0]
    builder.cx(low[-1], saved)
    token = virtual_main.VirtualMainToken(plan, saved, len(low),
        [None] * (plan.last - plan.first), parity_before=parity_before,
        row_parities=[None] * (plan.last - plan.first))
    parity = parity_before
    later = [(index, plan.shifts[index - plan.first]) for index in range(child.last, plan.last)]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        seed = virtual_main._row_seed(parity, len(source), shift)
        offset = index - plan.first
        token.row_parities[offset] = seed
        token.row_debts[offset] = virtual_lsb.forward_virtual_row(
            builder, source, low, shift=shift, sign=sign, initial_lsb=seed)
        parity ^= row_parity_mask(len(source), shift)

    child_low, child_high = low[:child.window], low[child.window:]
    saved_child = builder.alloc_qubits(1)[0]
    builder.cx(child_low[-1], saved_child)
    nested = virtual_main.VirtualMainToken(child, saved_child, child.window, [],
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
            # This correction only reads the already exposed sign.  It does
            # not consult any other packed bit while the borrowed frame runs.
            split_bounded.forward_bounded_high(builder, single_control(child, sign),
                                               child_low, child_high, nested)
    token.parity_after = nested.parity_after = parity
    token.nested_child = nested
    return token


def inverse_nested(builder, digits, source, low, token, *, carry_budget=None):
    """Consume every original and child snapshot within the main inverse."""
    source, low = list(source), list(low)
    if token.stage != 'high_undone' or len(low) != token.window:
        raise ValueError('The original parent high correction must be reversed first.')
    if token.saved_bit is not None:
        token.saved_measurement = paired.release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    nested = token.nested_child
    child = nested.plan
    child_low, child_high = low[:child.window], low[child.window:]
    rows = list(reversed(list(zip(range(child.first, child.last), child.shifts))))
    for index, shift, sign in split_bounded._row_controls(digits, rows):
        if index + 1 == child.last:
            split_bounded.inverse_bounded_high(builder, single_control(child, sign),
                child_low, child_high, nested, carry_budget=carry_budget)
        offset = index - child.first
        virtual_lsb.inverse_virtual_row(builder, source, child_low, nested.row_debts[offset],
            shift=shift, sign=sign, initial_lsb=nested.row_parities[offset], carry_budget=carry_budget)
    if nested.saved_bit is not None or nested.saved_measurement is None:
        raise AssertionError('The child snapshot did not transfer to its phase owner.')
    paired.repay_saved_bit(builder, child_low[-1], nested.saved_measurement)
    nested.saved_measurement = None
    nested.stage = 'consumed'

    later = [(index, token.plan.shifts[index - token.plan.first])
             for index in reversed(range(child.last, token.plan.last))]
    for index, shift, sign in split_bounded._row_controls(digits, later):
        offset = index - token.plan.first
        virtual_lsb.inverse_virtual_row(builder, source, low, token.row_debts[offset],
            shift=shift, sign=sign, initial_lsb=token.row_parities[offset], carry_budget=carry_budget)
    if token.saved_measurement is None:
        raise AssertionError('The parent snapshot has no phase owner.')
    paired.repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = 'consumed'


def forward_disposable_wrap(builder, residual, source, target, token, **kwargs):
    """The existing forward high correction, releasing its quadratic wrap early."""
    if kwargs.get('inverse') or token.plan.signed_source or token.saved_bit is None:
        raise ValueError('The disposable wrap is only an unsigned forward correction.')
    sign = residual[token.plan.last - 1]
    saved, top = token.saved_bit, target[token.window - 1]
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

    token.overflow_debt = virtual_lsb._add_disposable_carry(builder, [], high, wrap, release)
    for wire in high:
        builder.cx(sign, wire)
    builder.x(top)
    builder.cx(sign, top)
    builder.cx(sign, saved)


@contextmanager
def borrowed_digit(packed, index, mask):
    """Expose a zero-on-u logical digit using an exact phase-free frame."""
    if (index not in (2, 3) or not packed.is_packed or packed.max_k != 10
            or packed._cached_u != mask or packed._active_digits != 1):
        raise ValueError('The tight digit needs exactly one active owner and its cached u.')
    builder = packed.builder
    position, retained = packed.residual[index], packed.t
    if len({mask, position, retained}) != 3:
        raise ValueError('The borrowed packed wires must be distinct.')
    builder.cx(mask, retained)
    builder.cswap(mask, position, retained)
    try:
        yield position
    finally:
        builder.cswap(mask, position, retained)
        builder.cx(mask, retained)


@contextmanager
def installed(*, audit=None):
    """Select the nested main window without touching any other region.

This is intentionally uninstalled by default.  Its main arithmetic enters
the low phase with one additional snapshot; whole-generator use requires an
explicitly compatible low-phase kernel.
"""
    import fourier_main
    import scheduled_generator
    records = [] if audit is None else audit
    original_forward = virtual_main.forward_virtual_main_low
    original_inverse = virtual_main.inverse_virtual_main_low
    original_overflow = split_bounded._deferred_overflow
    original_masked = PackedShift._masked_digit
    bindings = [(virtual_main, 'forward_virtual_main_low'),
                (scheduled_generator, 'forward_virtual_main_low'),
                (virtual_main, 'inverse_virtual_main_low'),
                (scheduled_generator, 'inverse_virtual_main_low'),
                (fourier_main, 'inverse_virtual_main_low'),
                (split_bounded, '_deferred_overflow'),
                (PackedShift, '_masked_digit')]
    previous = [(module, name, getattr(module, name)) for module, name in bindings]
    main_tokens = set()
    active = {'nested_forward': False}

    def forward(builder, digits, source, low, plan, **kwargs):
        main = len(source) == 17 and plan.digits == 14
        selected = main and (plan.first, plan.last, plan.window) == (0, 6, 11)
        if not selected:
            token = original_forward(builder, digits, source, low, plan, **kwargs)
        else:
            if set(kwargs) != {'parity_before'}:
                raise ValueError('The nested selected main requires its unmodified parity-only interface.')
            child = child_plan(plan, 4)
            if child.window != 9:
                raise AssertionError('The selected first-four-row bound ceased to be nine bits.')
            active['nested_forward'] = True
            try:
                token = forward_nested(builder, digits, source, low, plan, child, **kwargs)
            finally:
                active['nested_forward'] = False
            main_tokens.add(id(token.nested_child))
            records.append({'component': 'nested_main_child', 'rows': [child.first, child.last],
                            'child_width': child.window, 'parent_width': plan.window,
                            'persistent_extra_snapshot': 1})
        if main:
            main_tokens.add(id(token))
        return token

    def inverse(builder, digits, source, low, token, **kwargs):
        if hasattr(token, 'nested_child'):
            return inverse_nested(builder, digits, source, low, token, **kwargs)
        return original_inverse(builder, digits, source, low, token, **kwargs)

    def overflow(builder, residual, source, target, token, **kwargs):
        if not kwargs.get('inverse') and (id(token) in main_tokens or active['nested_forward']):
            return forward_disposable_wrap(builder, residual, source, target, token, **kwargs)
        return original_overflow(builder, residual, source, target, token, **kwargs)

    @contextmanager
    def masked(packed, index, mask):
        builder = packed.builder
        free = builder.max_qubits - builder.num_allocated_qubits
        if active['nested_forward'] and index in (2, 3) and free == 2:
            entry = builder.num_allocated_qubits
            with borrowed_digit(packed, index, mask) as control:
                yield control
            if builder.num_allocated_qubits != entry:
                raise AssertionError('A tight row changed its persistent allocations.')
            records.append({'component': 'borrowed_packed_digit', 'digit': index,
                            'entry_live': entry, 'added_Toffoli_equivalents': 1})
        else:
            with original_masked(packed, index, mask) as control:
                yield control

    for module, name in bindings:
        replacement = (forward if name == 'forward_virtual_main_low' else
                       inverse if name == 'inverse_virtual_main_low' else
                       overflow if name == '_deferred_overflow' else masked)
        setattr(module, name, replacement)
    try:
        yield records
    finally:
        for module, name, function in reversed(previous):
            setattr(module, name, function)
