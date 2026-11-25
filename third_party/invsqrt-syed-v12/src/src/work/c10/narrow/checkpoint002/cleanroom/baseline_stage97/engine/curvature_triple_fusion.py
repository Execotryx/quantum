# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Fuse three curvature rows with streamed source erasure at width57.

The first three rounded rows produce a signed two-bit physical update.  Its
magnitude uses five products.  The first magnitude bit is quadratic in the
preserved coefficient/digits and is erased immediately after its source use.
The second is measured after its source use, transferring one private phase
owner to this paired arithmetic token.  The matching inverse reconstructs
that magnitude and repays the owner before subtracting.  It never enters the
table ledger or any region outside the curvature child.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass

import kickmix as km
from codebook import emit_erase, emit_xor, factor_polynomial
from curvature_pair_fusion import _selected
from fusion.arithmetic import _compute_carry, _sum_keep_carry
from paired_arithmetic import (CarryDebt, _finish_top, inverse_signed_row,
                               release_saved_bit, repay_saved_bit)
from split_bounded import _digit, _digit_count, _row_controls
from variable_lsb_main import row_parity_mask
from virtual_lsb import SourceParity, VirtualRowDebt, forward_virtual_row, inverse_virtual_row
from virtual_main import VirtualMainToken, _row_seed


@dataclass
class TripleDebt:
    carry: CarryDebt
    source_phase: object
    consumed: bool = False


def magnitude_plans():
    """Original variable order is C[7],C[6],C[5],digit4,digit5,digit6."""
    temporary = factor_polynomial(6, False, 0, [(2, 5)])
    low = factor_polynomial(7, False, (1 << 1)|(1 << 6),
                            [(0, 3), (0, 4), (1, 4), (1, 5)])
    high = factor_polynomial(8, False, (1 << 0)|(1 << 6),
        [(0, 3), (0, 5), (6, 7), (4, 7), (5, 7), (4, 6), (5, 6)])
    low_original = factor_polynomial(6, False, 1 << 1,
        [(2, 5), (0, 3), (0, 4), (1, 4), (1, 5)])
    if [plan.and_count for plan in (temporary, low, high)] != [1, 2, 2]:
        raise AssertionError('The streamed two-bit magnitude lost its five-product factorization.')
    return temporary, low, high, low_original


def certify_identity(minimum=24, maximum=190):
    if not 0 <= minimum <= maximum < 192:
        raise ValueError('The two high coefficient bits must never both be one.')
    temporary_plan, low_plan, high_plan, low_original = magnitude_plans()
    checked = 0
    for curvature in range(minimum, maximum+1):
        for digits in range(8):
            original = ((curvature >> 7) & 1) | (((curvature >> 6) & 1) << 1)
            original |= ((curvature >> 5) & 1) << 2
            original |= digits << 3
            temporary = temporary_plan.evaluate_bits(original)
            low = low_plan.evaluate_bits(original | (temporary << 6))
            high = high_plan.evaluate_bits(original | (temporary << 6) | (low << 7))
            logical = sum((1-2*((digits >> index) & 1))*((curvature+(1 << (cut-1))) >> cut)
                          for index, cut in enumerate((8, 7, 6)))
            if ((1-2*((digits >> 2) & 1))*(low+2*high) != logical//2
                    or logical % 2 != (curvature >> 5) & 1
                    or low != low_original.evaluate_bits(original)):
                raise AssertionError('The three-row magnitude or omitted parity is not exact.')
            checked += 1
    return dict(curvature_interval=[minimum, maximum], digit_words=8, cases=checked,
                exact_signed_two_bit_magnitude=True, omitted_parity='stored curvature bit5',
                magnitude_low_is_quadratic_in_original_coordinates=True)


def _magnitude(builder, source, digits):
    source, digits = list(source), list(digits)
    if len(source) != 8 or len(digits) != 3 or len(set(source+digits)) != 11:
        raise ValueError('The triple fusion requires C8 and three distinct digit wires.')
    variables = [source[7], source[6], source[5], *digits]
    temporary_plan, low_plan, high_plan, low_original = magnitude_plans()
    temporary = builder.alloc_qubits(1)[0]
    emit_xor(builder, variables, temporary, temporary_plan)
    low = builder.alloc_qubits(1)[0]
    emit_xor(builder, variables+[temporary], low, low_plan)
    high = builder.alloc_qubits(1)[0]
    emit_xor(builder, variables+[temporary, low], high, high_plan)
    return variables, temporary, low, high, (temporary_plan, low_plan, high_plan, low_original)


def forward_triple(builder, source, target, digits, *, omit_low_repayment=False):
    """Emit a width-five signed update, releasing each used source bit."""
    target, digits = list(target), list(digits)
    if len(target) != 5:
        raise ValueError('The selected curvature child has five physical target bits.')
    variables, temporary, low, high, plans = _magnitude(builder, source, digits)
    temporary_plan, _, _, low_original = plans
    emit_erase(builder, variables, [temporary], [temporary_plan])
    builder.free(temporary)
    a = [low, high]+[False]*(len(target)-2)
    for wire in target:
        builder.cx(digits[-1], wire)
    carry, measurements, source_phase = False, {}, None
    for index, (aa, bb) in enumerate(zip(a[:-2], target[:-2])):
        frame = _compute_carry(builder, aa, bb, carry)
        _sum_keep_carry(builder, frame)
        if index == 0:
            if omit_low_repayment:
                outcome = builder.alloc_bits(1)[0]
                builder.hmr(low, outcome)
                builder.free(outcome)
            else:
                emit_erase(builder, variables, [low], [low_original])
            builder.free(low)
        elif index == 1:
            source_phase = builder.alloc_bits(1)[0]
            builder.hmr(high, source_phase)
            builder.free(high)
        if index:
            outcome = builder.alloc_bits(1)[0]
            builder.hmr(carry, outcome)
            builder.free(carry)
            measurements[index] = outcome
        carry = frame.outgoing
    _finish_top(builder, a, target, carry, None)
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(carry, outcome)
    builder.free(carry)
    measurements[len(target)-2] = outcome
    for wire in target:
        builder.cx(digits[-1], wire)
    if source_phase is None:
        raise AssertionError('The measured high magnitude bit has no private phase owner.')
    return TripleDebt(CarryDebt(measurements, len(target)), source_phase)


def inverse_triple(builder, source, target, digits, debt, *, carry_budget=None,
                    omit_source_repayment=False):
    """Repay the measured source bit locally, then undo the paired addition."""
    target, digits = list(target), list(digits)
    if debt.consumed or debt.source_phase is None or len(target) != 5 or debt.carry.width != 5:
        raise ValueError('The fresh private source/carry phase owner is required.')
    variables, temporary, low, high, plans = _magnitude(builder, source, digits)
    temporary_plan, low_plan, high_plan, _ = plans
    if not omit_source_repayment:
        builder.push_condition(debt.source_phase)
        builder.z(high)
        builder.pop_condition()
    builder.free(debt.source_phase)
    debt.source_phase = None
    inverse_signed_row(builder, [low, high], target, debt.carry, shift=0, sign=digits[-1],
                       nearest=False, signed_source=False, carry_budget=carry_budget)
    emit_erase(builder, variables+[temporary, low], [high], [high_plan])
    builder.free(high)
    emit_erase(builder, variables+[temporary], [low], [low_plan])
    builder.free(low)
    emit_erase(builder, variables, [temporary], [temporary_plan])
    builder.free(temporary)
    debt.consumed = True
    if not debt.carry.consumed or debt.carry.measurements:
        raise AssertionError('The reconstructed magnitude left an original carry phase unpaid.')


def forward_child(builder, digits, source, low, plan, *, parity_before=0,
                  saved_bit=None, external_lsb=False, parity_constant=False):
    source, low = list(source), list(low)
    if (not _selected(source, low, plan) or _digit_count(digits) != 14
            or parity_before != 0 or external_lsb is not False or parity_constant):
        raise ValueError('The triple fusion requires the unchanged first curvature child.')
    identity = certify_identity(plan.source_min, plan.source_max)
    saved = saved_bit
    if saved is None:
        saved = builder.alloc_qubits(1)[0]
        builder.cx(low[-1], saved)
    elif not isinstance(saved, km.q) or saved in source+low:
        raise ValueError('The original inner snapshot must be a distinct held wire.')
    token = VirtualMainToken(plan, saved, len(low), [], parity_before=0,
                             row_parities=[], external_lsb=False, parity_constant=False)
    parity = 0
    for shift in plan.shifts:
        token.row_parities.append(_row_seed(parity, len(source), shift))
        parity ^= row_parity_mask(len(source), shift)
    if any(seed != SourceParity(0) for seed in token.row_parities):
        raise AssertionError('The ascending row parity seeds changed.')
    with _digit(digits, 4) as first, _digit(digits, 5) as second, _digit(digits, 6) as third:
        fused = forward_triple(builder, source, low, [first, second, third])
    token.row_debts.append(VirtualRowDebt(-8, False, False, fused.carry))
    for shift in (-7, -6):
        token.row_debts.append(VirtualRowDebt(shift, False, False, CarryDebt({}, len(low))))
    for index, shift, sign in _row_controls(digits, list(zip(range(7, plan.last), plan.shifts[3:]))):
        token.row_debts.append(forward_virtual_row(
            builder, source, low, shift=shift, sign=sign,
            initial_lsb=token.row_parities[index-plan.first]))
    token.parity_after = parity
    token.curvature_triple_debt = fused
    token.curvature_triple_fusion = dict(
        identity_certificate=identity, digits=[4, 5, 6], shifts=[-8, -7, -6],
        magnitude_polynomials=[asdict(plan) for plan in magnitude_plans()[:3]],
        combined_forward_ANDs=9, combined_inverse_ANDs=9,
        original_forward_ANDs=15, original_inverse_ANDs=15,
        source_high_phase_owner='private child token; repaid before inverse addition',
        source_low_and_temporary_phases_repaid_immediately=True,
        original_inner_snapshot_preserved=True, two_empty_compatibility_debts=True,
        table_ledger_unchanged=True)
    return token


def inverse_child(builder, digits, source, low, token, *, carry_budget=None):
    source, low = list(source), list(low)
    if (not getattr(token, 'curvature_triple_fusion', None)
            or not _selected(source, low, token.plan) or token.stage != 'high_undone'
            or _digit_count(digits) != 14):
        raise ValueError('The fused curvature child is absent or at the wrong lifetime cut.')
    placeholders = [token.row_debts[index].carry_debt for index in (1, 2)]
    if any(debt.consumed or debt.measurements or debt.width != len(low) for debt in placeholders):
        raise ValueError('The two compatibility carry debts must be empty and fresh.')
    if token.curvature_triple_debt.carry is not token.row_debts[0].carry_debt:
        raise ValueError('The first row lost the private fused carry owner.')
    if token.saved_bit is not None:
        token.saved_measurement = release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    rows = list(reversed(list(zip(range(7, token.plan.last), token.plan.shifts[3:]))))
    for index, shift, sign in _row_controls(digits, rows):
        offset = index-token.plan.first
        inverse_virtual_row(builder, source, low, token.row_debts[offset],
                            shift=shift, sign=sign, carry_budget=carry_budget,
                            initial_lsb=token.row_parities[offset])
    with _digit(digits, 4) as first, _digit(digits, 5) as second, _digit(digits, 6) as third:
        inverse_triple(builder, source, low, [first, second, third],
                       token.curvature_triple_debt, carry_budget=carry_budget)
    for debt in placeholders:
        debt.consumed = True
    if token.saved_measurement is None:
        raise ValueError('The original inner snapshot lost its phase owner.')
    repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = 'consumed'
    if (not token.curvature_triple_debt.consumed or token.curvature_triple_debt.source_phase is not None
            or any(not row.carry_debt.consumed or row.carry_debt.measurements for row in token.row_debts)):
        raise AssertionError('The private source/carry phase owner was not completely consumed.')


@contextmanager
def installed():
    import nested_virtual
    import blo9_pauli
    previous_forward = nested_virtual.forward_virtual_main_low
    previous_inverse = blo9_pauli.inverse_virtual_main_low
    if (getattr(previous_forward, '_curvature_pair_fusion', False)
            or getattr(previous_forward, '_curvature_triple_fusion', False)):
        raise RuntimeError('Choose one curvature first-row fusion in a build scope.')
    report = dict(forward_calls=0, inverse_calls=0, expected_AND_saving=12,
                  regions=['forward_curvature_low', 'backward_curvature_low'],
                  original_snapshot_and_table_ledger_unchanged=True)

    def forward(builder, digits, source, low, plan, **options):
        if not _selected(source, low, plan):
            return previous_forward(builder, digits, source, low, plan, **options)
        token = forward_child(builder, digits, source, low, plan, **options)
        report['forward_calls'] += 1
        report['fusion'] = token.curvature_triple_fusion
        return token

    def inverse(builder, digits, source, low, token, **options):
        if not getattr(token, 'curvature_triple_fusion', None):
            return previous_inverse(builder, digits, source, low, token, **options)
        inverse_child(builder, digits, source, low, token, **options)
        report['inverse_calls'] += 1

    forward._curvature_triple_fusion = True
    nested_virtual.forward_virtual_main_low = forward
    blo9_pauli.inverse_virtual_main_low = inverse
    try:
        yield report
        if (report['forward_calls'], report['inverse_calls']) != (1, 1):
            raise AssertionError('Exactly one fused curvature child must be generated and consumed.')
    finally:
        nested_virtual.forward_virtual_main_low = previous_forward
        blo9_pauli.inverse_virtual_main_low = previous_inverse
