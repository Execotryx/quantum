# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Fuse the first two curvature rows into one exact signed unit update.

Stored curvature is below192, so its two high bits are never both one.
For digits u,v and high bits a=C[7], b=C[6], the first two virtual rows
change the physical quotient by a*(1-u)-(a+b)*v.  This is (1-2*v)*m,
where m=a XOR (a*u) XOR ((a XOR b)*v).  The two-product quadratic m
therefore replaces two width-five additions by one.  Its HMR sign is
repaid immediately with Z/CZ; only the ordinary paired carry debt remains.

The bounded child retains its original snapshot, five row positions and
omitted-parity description.  Its first debt owns the fused row, and its
second is an explicitly empty compatibility record consumed with that row.
No table-ledger function or final word is changed.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict

import kickmix as km
from codebook import emit_erase, emit_xor, factor_polynomial
from paired_arithmetic import (CarryDebt, forward_signed_row, inverse_signed_row,
                               release_saved_bit, repay_saved_bit)
from split_bounded import _digit, _digit_count, _row_controls
from variable_lsb_main import row_parity_mask
from virtual_lsb import SourceParity, VirtualRowDebt, forward_virtual_row, inverse_virtual_row
from virtual_main import VirtualMainToken, _row_seed


def magnitude_plan():
    """Variable order: high curvature bit, next curvature bit, first, second."""
    plan = factor_polynomial(4, False, 1, [(0, 2), (0, 3), (1, 3)])
    if plan.and_count != 2:
        raise AssertionError('The fused signed-unit magnitude must use exactly two products.')
    return plan


def certify_identity(minimum=24, maximum=190):
    """Certify the exact quotient and omitted parity before any emission."""
    if not 0 <= minimum <= maximum < 192:
        raise ValueError('The two high curvature bits must never both be one.')
    checked = 0
    for curvature in range(minimum, maximum+1):
        high, next_high = (curvature >> 7) & 1, (curvature >> 6) & 1
        for first in range(2):
            for second in range(2):
                logical = (1-2*first)*((curvature+128) >> 8)
                logical += (1-2*second)*((curvature+64) >> 7)
                magnitude = high ^ (high & first) ^ ((high ^ next_high) & second)
                delta = (1-2*second)*magnitude
                if logical//2 != delta or logical % 2 != next_high:
                    raise AssertionError('The signed-unit fusion changed a quotient or omitted parity.')
                checked += 1
    return dict(curvature_interval=[minimum, maximum], digit_words=4, cases=checked,
                exact_physical_quotient=True, omitted_parity='stored curvature bit6',
                high_curvature_bits_mutually_exclusive=True)


def _magnitude(builder, source, first, second):
    source = list(source)
    if len(source) != 8 or first == second or first in source or second in source:
        raise ValueError('The fused row requires C8 and two distinct preserved digit wires.')
    variables = [source[7], source[6], first, second]
    plan = magnitude_plan()
    target = builder.alloc_qubits(1)[0]
    emit_xor(builder, variables, target, plan)
    return target, variables, plan


def _clear_magnitude(builder, magnitude, variables, plan, *, omit_repayment=False):
    if omit_repayment:
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(magnitude, outcome)
        builder.free(outcome)
    else:
        emit_erase(builder, variables, [magnitude], [plan])
    builder.free(magnitude)


def forward_pair(builder, source, target, first, second, *, omit_repayment=False):
    if len(target) != 5:
        raise ValueError('The fused curvature child has exactly five physical target bits.')
    magnitude, variables, plan = _magnitude(builder, source, first, second)
    debt = forward_signed_row(builder, [magnitude], target, shift=0, sign=second,
                              nearest=False, signed_source=False)
    _clear_magnitude(builder, magnitude, variables, plan, omit_repayment=omit_repayment)
    return debt


def inverse_pair(builder, source, target, first, second, debt, *, carry_budget=None):
    if len(target) != 5 or debt.width != 5:
        raise ValueError('The inverse fused row needs its original five-bit paired debt.')
    magnitude, variables, plan = _magnitude(builder, source, first, second)
    inverse_signed_row(builder, [magnitude], target, debt, shift=0, sign=second,
                       nearest=False, signed_source=False, carry_budget=carry_budget)
    _clear_magnitude(builder, magnitude, variables, plan)


def _selected(source, low, plan):
    return (len(source) == 8 and len(low) == 5 and plan.first == 4 and plan.last == 9
            and tuple(plan.shifts) == tuple(range(-8, -3)) and plan.window == 5
            and not plan.signed_source)


def forward_child(builder, digits, source, low, plan, *, parity_before=0,
                  saved_bit=None, external_lsb=False, parity_constant=False):
    """Emit the selected bounded child with the first two rows fused."""
    source, low = list(source), list(low)
    if (not _selected(source, low, plan) or _digit_count(digits) != 14
            or parity_before != 0 or external_lsb is not False or parity_constant):
        raise ValueError('The fusion requires the unchanged first curvature child and zero original LSB.')
    identity = certify_identity(plan.source_min, plan.source_max)
    saved = saved_bit
    if saved is None:
        saved = builder.alloc_qubits(1)[0]
        builder.cx(low[-1], saved)
    elif not isinstance(saved, km.q) or saved in source+low:
        raise ValueError('The original child snapshot must be a distinct held quantum wire.')
    token = VirtualMainToken(plan, saved, len(low), [], parity_before=0,
                             row_parities=[], external_lsb=False, parity_constant=False)
    parity = 0
    for shift in plan.shifts:
        token.row_parities.append(_row_seed(parity, len(source), shift))
        parity ^= row_parity_mask(len(source), shift)
    if any(seed != SourceParity(0) for seed in token.row_parities):
        raise AssertionError('The selected ascending curvature row seeds changed.')
    with _digit(digits, 4) as first, _digit(digits, 5) as second:
        fused = forward_pair(builder, source, low, first, second)
    token.row_debts.append(VirtualRowDebt(-8, False, False, fused))
    token.row_debts.append(VirtualRowDebt(-7, False, False, CarryDebt({}, len(low))))
    rows = list(zip(range(6, plan.last), plan.shifts[2:]))
    for index, shift, sign in _row_controls(digits, rows):
        token.row_debts.append(forward_virtual_row(
            builder, source, low, shift=shift, sign=sign,
            initial_lsb=token.row_parities[index-plan.first]))
    token.parity_after = parity
    token.curvature_pair_fusion = dict(
        identity_certificate=identity, digits=[4, 5], shifts=[-8, -7],
        magnitude_polynomial=asdict(magnitude_plan()),
        combined_forward_ANDs=6, combined_inverse_ANDs=6,
        original_forward_ANDs=10, original_inverse_ANDs=10,
        immediately_repaid_magnitude=True, original_inner_snapshot_preserved=True,
        second_carry_record_explicitly_empty=True, table_ledger_unchanged=True)
    return token


def inverse_child(builder, digits, source, low, token, *, carry_budget=None):
    """Consume the fused first debt and every unchanged later row/snapshot."""
    source, low = list(source), list(low)
    if (not getattr(token, 'curvature_pair_fusion', None)
            or not _selected(source, low, token.plan) or token.stage != 'high_undone'
            or _digit_count(digits) != 14):
        raise ValueError('The selected fused child is missing or at the wrong lifetime cut.')
    placeholder = token.row_debts[1].carry_debt
    if placeholder.consumed or placeholder.measurements or placeholder.width != len(low):
        raise ValueError('The fused second-row compatibility debt is not empty and fresh.')
    if token.saved_bit is not None:
        token.saved_measurement = release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    rows = list(reversed(list(zip(range(6, token.plan.last), token.plan.shifts[2:]))))
    for index, shift, sign in _row_controls(digits, rows):
        offset = index-token.plan.first
        inverse_virtual_row(builder, source, low, token.row_debts[offset],
                            shift=shift, sign=sign, carry_budget=carry_budget,
                            initial_lsb=token.row_parities[offset])
    with _digit(digits, 4) as first, _digit(digits, 5) as second:
        inverse_pair(builder, source, low, first, second,
                     token.row_debts[0].carry_debt, carry_budget=carry_budget)
    placeholder.consumed = True
    if token.saved_measurement is None:
        raise ValueError('The unchanged original child snapshot lost its phase owner.')
    repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = 'consumed'
    if any(not row.carry_debt.consumed or row.carry_debt.measurements for row in token.row_debts):
        raise AssertionError('The fused child left a forward carry phase unpaid.')


@contextmanager
def installed():
    """Install only the nested curvature forward and Blo9 child inverse hooks."""
    import nested_virtual
    import blo9_pauli
    previous_forward = nested_virtual.forward_virtual_main_low
    previous_inverse = blo9_pauli.inverse_virtual_main_low
    if getattr(previous_forward, '_curvature_pair_fusion', False):
        raise RuntimeError('Curvature first-pair fusion is already installed.')
    report = dict(forward_calls=0, inverse_calls=0,
                  regions=['forward_curvature_low', 'backward_curvature_low'],
                  expected_AND_saving=8, original_snapshot_and_table_ledger_unchanged=True)

    def forward(builder, digits, source, low, plan, **options):
        if not _selected(source, low, plan):
            return previous_forward(builder, digits, source, low, plan, **options)
        token = forward_child(builder, digits, source, low, plan, **options)
        report['forward_calls'] += 1
        report['fusion'] = token.curvature_pair_fusion
        return token

    def inverse(builder, digits, source, low, token, **options):
        if not getattr(token, 'curvature_pair_fusion', None):
            return previous_inverse(builder, digits, source, low, token, **options)
        inverse_child(builder, digits, source, low, token, **options)
        report['inverse_calls'] += 1

    forward._curvature_pair_fusion = True
    nested_virtual.forward_virtual_main_low = forward
    blo9_pauli.inverse_virtual_main_low = inverse
    try:
        yield report
        if (report['forward_calls'], report['inverse_calls']) != (1, 1):
            raise AssertionError('The selected schedule must consume exactly one paired curvature fusion.')
    finally:
        nested_virtual.forward_virtual_main_low = previous_forward
        blo9_pauli.inverse_virtual_main_low = previous_inverse
