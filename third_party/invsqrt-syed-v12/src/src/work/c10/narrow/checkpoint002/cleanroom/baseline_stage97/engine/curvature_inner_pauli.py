# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Undo the selected curvature child through its measured top bit.

The decoded original inner snapshot remains quantum after its high correction.
We measure the current inner top bit and reverse the three paired updates on
four physical bits.  Their outgoing carries need only conditional quadratic
phases.  At the end the remaining sign is repaid on the original snapshot,
which is transferred into the reset top wire.  All phase owners stay inside
this child; the outer Blo9 character and the table ledger are unchanged.

The forward triple implementation is deliberately not modified.  This scope
must be installed inside its existing installed() context.
"""
from __future__ import annotations

from contextlib import contextmanager

import kickmix as km
from blo9_pauli import pauli_character
from codebook import emit_erase
from curvature_pair_fusion import _selected
from curvature_triple_fusion import _magnitude
from fourier_suffix_inverse import (FourierSuffixDebt, _final_segment,
                                    inverse_add_truncated)
from paired_arithmetic import inverse_signed_row
from split_bounded import _digit, _digit_count, _row_controls
from virtual_lsb import SourceParity, inverse_virtual_row


def _inverse_add_single_pauli(builder, source, target, debt, *, sign, suffix,
                             carry_in=False, signed_source=False, carry_budget=None,
                             dirty_wires=(), carry_lifecycle=None,
                             overflow_phase=None, allow_dirty_overflow=False):
    """Use one complete shortened segment when its clean carries fit.

    The generic Fourier partitioner may tie a full segment with several
    length-one boundaries. Those boundaries introduce conditional X frames
    and more HMR outcomes, although they have the same AND cost. At this
    selected cut all three full-segment carries fit. Keeping them through
    the phase-only final majority removes the unnecessary boundaries and
    keeps quantum data independent of outcomes at every instruction.
    """
    import paired_arithmetic
    if (signed_source or overflow_phase is not None or dirty_wires
            or not isinstance(suffix, FourierSuffixDebt) or suffix.consumed
            or not getattr(suffix, '_inner_pauli_zero_odd', False)):
        raise ValueError('The selected single segment requires its local Pauli character.')
    a, b, preserve = paired_arithmetic._inputs(source, target, carry_in, False)
    needed = len(b)-1
    available = builder.max_qubits-builder.num_allocated_qubits
    if (preserve is not None or debt.consumed or debt.width != len(b)+1 or not b
            or needed > available or (carry_budget is not None and carry_budget < needed)):
        raise ValueError('The full shortened carry segment must fit without releasing its input.')
    debt.consumed = True
    builder.x(km.array(b))
    _final_segment(builder, a, b, carry_in, start=0, debt=debt, sign=sign, suffix=suffix)
    builder.x(km.array(b))
    if debt.measurements:
        raise AssertionError('The full shortened segment left an original carry phase unpaid.')
    return False  # the unchanged virtual-row caller erases its incoming carry


@contextmanager
def _single_pauli_row_adder(sign, suffix):
    import paired_arithmetic
    import virtual_lsb
    previous_paired, previous_virtual = paired_arithmetic.inverse_add, virtual_lsb.inverse_add

    def replacement(builder, source, target, debt, **options):
        return _inverse_add_single_pauli(builder, source, target, debt,
                                         sign=sign, suffix=suffix, **options)

    paired_arithmetic.inverse_add = virtual_lsb.inverse_add = replacement
    try:
        yield
    finally:
        paired_arithmetic.inverse_add, virtual_lsb.inverse_add = previous_paired, previous_virtual


def inverse_high_retaining_snapshot(builder, digits, low, high, token, suffix):
    """Emit the existing high inverse while keeping its original snapshot.

    This is the existing one-bit-suffix high inverse through its final stage
    assignment.  Its former HMR/free of the saved bit is postponed into the
    inner low inverse, where the saved value repays a different local outcome.
    """
    low, high = list(low), list(high)
    if (builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != 47
            or not getattr(token, 'curvature_triple_fusion', None)
            or not isinstance(suffix, FourierSuffixDebt) or suffix.consumed
            or token.stage != 'high_done' or token.window != 5
            or len(low) != 5 or len(high) != 4 or token.high_width != 5
            or not isinstance(token.saved_bit, km.q) or token.saved_measurement is not None
            or token.plan.signed_source or token.overflow_debt is None
            or token.overflow_debt.consumed):
        raise ValueError('Require the selected 47-live inner5/high4 inverse and quantum snapshot.')
    with _digit(digits, token.plan.last-1) as sign:
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
    if builder.num_allocated_qubits != 47:
        raise AssertionError('The high correction must retain exactly its original snapshot.')


def inverse_triple_shortened(builder, source, target, digits, debt, suffix,
                             *, carry_budget=None):
    """Consume the unchanged fused carry and private source owners on four bits."""
    target, digits = list(target), list(digits)
    if (debt.consumed or debt.source_phase is None or len(target) != 4
            or debt.carry.width != 5 or debt.carry.consumed
            or not isinstance(suffix, FourierSuffixDebt) or suffix.consumed):
        raise ValueError('The unchanged width-five fused debts and a fresh Pauli suffix are required.')
    variables, temporary, low, high, plans = _magnitude(builder, source, digits)
    temporary_plan, low_plan, high_plan, _ = plans
    builder.push_condition(debt.source_phase)
    builder.z(high)
    builder.pop_condition()
    builder.free(debt.source_phase)
    debt.source_phase = None
    with _single_pauli_row_adder(digits[-1], suffix):
        inverse_signed_row(builder, [low, high], target, debt.carry,
                           shift=0, sign=digits[-1], nearest=False,
                           signed_source=False, carry_budget=carry_budget)
    emit_erase(builder, variables+[temporary, low], [high], [high_plan])
    builder.free(high)
    emit_erase(builder, variables+[temporary], [low], [low_plan])
    builder.free(low)
    emit_erase(builder, variables, [temporary], [temporary_plan])
    builder.free(temporary)
    debt.consumed = True
    if not debt.carry.consumed or debt.carry.measurements:
        raise AssertionError('The shortened fused update left an original carry phase unpaid.')


def inverse_child(builder, digits, source, low, token, *, carry_budget=None,
                  omit_snapshot_repayment=False):
    """Restore the exact five-bit child, including its measured top wire."""
    source, low = list(source), list(low)
    if (builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != 47
            or not getattr(token, 'curvature_triple_fusion', None)
            or not _selected(source, low, token.plan) or token.stage != 'high_undone'
            or _digit_count(digits) != 14 or len(token.row_debts) != 5
            or not isinstance(token.saved_bit, km.q) or token.saved_measurement is not None
            or token.saved_bit in source+low):
        raise ValueError('Require the selected 47-live fused child with its original quantum snapshot.')
    if (token.parity_before != 0 or token.parity_after != 8
            or any(seed != SourceParity(0) for seed in token.row_parities)):
        raise ValueError('The original omitted-parity interface must be unchanged.')
    placeholders = [token.row_debts[index].carry_debt for index in (1, 2)]
    if any(debt.consumed or debt.measurements or debt.width != 5 for debt in placeholders):
        raise ValueError('The two unchanged compatibility carry debts must be fresh and empty.')
    if token.curvature_triple_debt.carry is not token.row_debts[0].carry_debt:
        raise ValueError('The first row lost the private fused carry owner.')
    if token.overflow_debt is not None and (not token.overflow_debt.consumed
                                           or token.overflow_debt.measurements):
        raise ValueError('The original inner high correction must already be completely undone.')
    saved, top = token.saved_bit, low[-1]
    measured = builder.alloc_bits(1)[0]
    builder.hmr(top, measured)
    # Keep the reset physical top wire allocated; its identity is part of the
    # caller's unchanged Blo word and it receives the original value below.
    suffix = pauli_character(builder, measured)
    suffix._inner_pauli_zero_odd = True
    retained = low[:-1]
    rows = list(reversed(list(zip(range(7, token.plan.last), token.plan.shifts[3:]))))
    for index, shift, sign in _row_controls(digits, rows):
        offset = index-token.plan.first
        if len(source[-shift+1:]) > len(retained):
            raise AssertionError('A direct source contribution would enter the measured top bit.')
        with _single_pauli_row_adder(sign, suffix):
            inverse_virtual_row(builder, source, retained, token.row_debts[offset],
                                shift=shift, sign=sign, carry_budget=carry_budget,
                                initial_lsb=token.row_parities[offset])
    with _digit(digits, 4) as first, _digit(digits, 5) as second, _digit(digits, 6) as third:
        inverse_triple_shortened(builder, source, retained, [first, second, third],
                                 token.curvature_triple_debt, suffix,
                                 carry_budget=carry_budget)
    for debt in placeholders:
        debt.consumed = True
    # The arithmetic has transported this character back to the initial top
    # value.  That value is still quantum in the exact original snapshot.
    if not omit_snapshot_repayment:
        builder.push_condition(measured)
        builder.z(saved)
        builder.pop_condition()
    builder.free(suffix.odd)
    builder.free(measured)
    suffix.consumed = True
    builder.cx(saved, top)
    builder.cx(top, saved)
    builder.free(saved)
    token.saved_bit = None
    token.stage = 'consumed'
    if (not token.curvature_triple_debt.consumed
            or token.curvature_triple_debt.source_phase is not None
            or any(not row.carry_debt.consumed or row.carry_debt.measurements
                   for row in token.row_debts)
            or builder.num_allocated_qubits != 46):
        raise AssertionError('The shortened child did not consume every local owner at the original exit.')


@contextmanager
def installed():
    import blo9_pauli
    import curvature_triple_fusion
    import nested_virtual
    if not getattr(nested_virtual.forward_virtual_main_low, '_curvature_triple_fusion', False):
        raise RuntimeError('Install the inner Pauli inverse inside the frozen triple fusion scope.')
    previous_high = blo9_pauli.inverse_high_truncated
    previous_child = curvature_triple_fusion.inverse_child
    report = dict(high_calls=0, child_calls=0, expected_mean_AND_saving=3,
                  region='backward_curvature_low', entry_live=47, exit_live=46,
                  original_forward_triple_unchanged=True,
                  full_shortened_segments_avoid_unnecessary_conditional_data_frames=True,
                  original_physical_top_restored_from_quantum_snapshot=True,
                  original_carry_and_private_source_owners_consumed=True,
                  outer_Blo9_character_and_table_ledger_unchanged=True)

    def high(builder, digits, low, upper, token, suffix):
        if not getattr(token, 'curvature_triple_fusion', None):
            return previous_high(builder, digits, low, upper, token, suffix)
        inverse_high_retaining_snapshot(builder, digits, low, upper, token, suffix)
        report['high_calls'] += 1

    def child(builder, digits, source, low, token, **options):
        if not getattr(token, 'curvature_triple_fusion', None):
            return previous_child(builder, digits, source, low, token, **options)
        inverse_child(builder, digits, source, low, token, **options)
        report['child_calls'] += 1

    blo9_pauli.inverse_high_truncated = high
    # Preserve the existing triple wrapper's paired-call accounting by
    # replacing the binding that it delegates to, not the wrapper itself.
    curvature_triple_fusion.inverse_child = child
    try:
        yield report
        if (report['high_calls'], report['child_calls']) != (1, 1):
            raise AssertionError('Exactly one high correction and one selected child must be shortened.')
    finally:
        blo9_pauli.inverse_high_truncated = previous_high
        curvature_triple_fusion.inverse_child = previous_child
