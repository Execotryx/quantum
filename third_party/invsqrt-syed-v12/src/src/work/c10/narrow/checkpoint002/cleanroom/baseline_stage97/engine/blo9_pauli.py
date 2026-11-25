# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Isolated one-real-bit Pauli specialization of the proved Fourier inverse.

This module is not installed into a frozen generator. The selected interface
is the actual C8/Blo10 nested curvature inverse after the unchanged joint
lookup. It returns Blo0..8 and an explicit original-Blo9 phase owner. The
final-address wrapper consumes that owner using the caller's mathematical
coefficient table in its existing physical address frame.
"""
from __future__ import annotations
from dataclasses import dataclass

import kickmix as km
from fourier_suffix_inverse import (FourierSuffixDebt, inverse_high_truncated,
                                    shortened_row_adder)
from split_bounded import _digit_count, _row_controls
from virtual_lsb import inverse_virtual_row, SourceParity
from virtual_main import inverse_virtual_main_low
from r17_lookup import table_words
from retained_address import restore_address_retained


@dataclass
class Blo9PhaseDebt:
    outcome: object
    stage: str = 'low_reversed'
    removed_physical_bits: tuple = (9,)
    character: str = 'Pauli one-real-bit suffix'
    outer_snapshot_record_merged: bool = True


def pauli_character(builder, outcome):
    """Return i**(2*m*S), explicitly fixing the unused character bit to zero.

    The zero bit is a classical constant, not another HMR outcome. This uses
    the unchanged removed=1 debt-width contract of inverse_add_truncated.
    Its S-majority branches have a false guard and therefore zero mean cost.
    """
    if not isinstance(outcome, km.b):
        raise ValueError('The Pauli character must own a classical HMR result.')
    zero = builder.alloc_bits(1)[0]
    builder.bit_store(zero, False)
    return FourierSuffixDebt(odd=zero, twice=outcome)


def _require_unused_row(row, width):
    if row.inactive or row.carry_debt is None:
        raise ValueError('The selected ten curvature rows are active.')
    carry = row.carry_debt
    if carry.width != width or carry.consumed:
        raise ValueError('A curvature row has another width or already-consumed carries.')


def require_selected_cut(builder, digits, source, low, token):
    """Fail before measuring anything if the selected lifetime differs."""
    if (builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != 48
            or _digit_count(digits) != 14 or len(source) != 8 or len(low) != 10
            or len(set(source + low)) != 18):
        raise ValueError('Require the selected 48-live C8/Blo10/14-digit cut at width57.')
    p = token.plan
    if (token.stage != 'high_undone' or token.window != 10
            or token.high_width != 7 or token.saved_bit is not None
            or not isinstance(token.saved_measurement, km.b)
            or token.overflow_debt is None or not token.overflow_debt.consumed
            or token.overflow_debt.measurements
            or (p.digits, p.first, p.last, p.window, p.signed_source) != (14, 4, 14, 10, False)
            or tuple(p.shifts) != tuple(range(-8, 2))
            or (p.source_min, p.source_max) != (24, 190)
            or token.parity_before != 0 or token.parity_after != 0
            or len(token.children) != 2):
        raise ValueError('The outer curvature/high/snapshot ownership contract differs.')
    inner, full = token.children
    if (inner.stage != 'high_done' or inner.window != 5 or inner.high_width != 5
            or inner.saved_bit is None or inner.saved_measurement is not None
            or inner.overflow_debt is None or inner.overflow_debt.consumed
            or (inner.plan.first, inner.plan.last) != (4, 9)
            or tuple(inner.plan.shifts) != tuple(range(-8, -3))
            or inner.parity_before != 0 or inner.parity_after != 8):
        raise ValueError('The original inner5/high5 carry and snapshot cut differs.')
    if (full.stage != 'full_low_done' or full.window != 10
            or full.saved_bit is not None or full.saved_measurement is not None
            or (full.plan.first, full.plan.last) != (9, 14)
            or tuple(full.plan.shifts) != tuple(range(-3, 2))
            or full.parity_before != 8 or full.parity_after != 0):
        raise ValueError('The final five full-width curvature rows differ.')
    for child, width in ((inner, 5), (full, 10)):
        if len(child.row_debts) != 5 or len(child.row_parities) != 5:
            raise ValueError('The selected child does not own exactly five row debts.')
        for row, seed in zip(child.row_debts, child.row_parities):
            _require_unused_row(row, width)
            if (not isinstance(seed, SourceParity) or seed.mask != 0
                    or seed.constant or seed.extra_wires):
                raise ValueError('The selected ascending curvature rows have zero row seeds.')


def _require_consumed(child):
    if child.stage != 'consumed' or child.saved_bit is not None or child.saved_measurement is not None:
        raise AssertionError('A child snapshot or stage remains owned.')
    for row in child.row_debts:
        if row.carry_debt is None or not row.carry_debt.consumed or row.carry_debt.measurements:
            raise AssertionError('An original curvature carry phase remains unpaid.')
    if child.overflow_debt is not None and (
            not child.overflow_debt.consumed or child.overflow_debt.measurements):
        raise AssertionError('An original high-correction carry phase remains unpaid.')


def inverse_nested_blo9(builder, digits, source, low, token):
    """Return retained Blo9 and one exact original-table phase owner.

    The outer high correction is already undone. The unchanged inner high
    correction and five final rows use the measured-top inverse with odd=0.
    The initial outer snapshot need not have outcome zero: its phase is
    merged into the new suffix owner only after every arithmetic correction.
    """
    source, low = list(source), list(low)
    require_selected_cut(builder, digits, source, low, token)
    outer = token.saved_measurement
    measured = builder.alloc_bits(1)[0]
    builder.hmr(low[-1], measured)
    builder.free(low[-1])
    retained = low[:-1]
    suffix = pauli_character(builder, measured)
    inner, full = token.children
    rows = list(reversed(list(zip(range(full.plan.first, full.plan.last), full.plan.shifts))))
    for index, amount, sign in _row_controls(digits, rows):
        offset = index - full.plan.first
        actual_source = len(source) if amount > 0 else max(0, len(source) + amount - 1)
        actual_target = len(retained) - max(0, amount - 1)
        if actual_source > actual_target:
            raise AssertionError('A direct source contribution would enter the measured suffix.')
        with shortened_row_adder(sign, suffix):
            inverse_virtual_row(builder, source, retained, full.row_debts[offset],
                shift=amount, sign=sign, initial_lsb=full.row_parities[offset])
    full.stage = 'consumed'
    inverse_high_truncated(builder, digits, retained[:5], retained[5:], inner, suffix)
    inverse_virtual_main_low(builder, digits, source, retained[:5], inner)
    _require_consumed(full)
    _require_consumed(inner)
    # Both signs now multiply the SAME original Blo9 table function. Mutating
    # the suffix owner earlier would corrupt its already-needed carry phases.
    if outer == measured or outer == suffix.odd:
        raise AssertionError('The outer and newly allocated phase owners alias.')
    builder.cx(outer, measured)
    builder.free(outer)
    token.saved_measurement = None
    builder.free(suffix.odd)
    suffix.consumed = True  # ownership of twice transfers to Blo9PhaseDebt
    token.stage = 'consumed'
    if builder.num_allocated_qubits != 46:
        raise AssertionError('The shortened nested inverse did not release exactly two quantum wires.')
    return retained, Blo9PhaseDebt(measured)


def record_initial_blo9(data, debt, table_ledger):
    """Transfer the sole remaining Pauli sign to the existing address ledger."""
    if (not isinstance(debt, Blo9PhaseDebt) or debt.stage != 'low_reversed'
            or debt.removed_physical_bits != (9,) or not debt.outer_snapshot_record_merged
            or not isinstance(debt.outcome, km.b) or table_ledger.address_bits != 8
            or data.get('lookup_view_only') is not True):
        raise ValueError('A fresh original-Blo9 owner and the actual physical table frame are required.')
    values = table_words(data)
    metadata = table_ledger.record_measurements([(value >> 9) & 1 for value in values['blo']], [debt.outcome])
    debt.stage = 'table_owned'
    return dict(metadata, original_physical_Blo_bit=9,
        current_address_frame_preserved=True, outer_snapshot_XOR_merged=True,
        no_non_Pauli_table_phase=True)


def restore_address_blo9(builder, data, low, blo, curvature, table_ledger, debt,
                         **options):
    """Use the same deterministic retained-product decoder on the shorter code.

    Complete lookup lifecycle cost must include the caller's later ledger
    repayment. This wrapper deliberately reports no projected circuit score.
    """
    if (len(low) != 14 or len(blo) != 9 or len(curvature) != 8
            or list(options.get('low_bits', range(14))) != (
                list(range(1, 15)) if data.get('consuming_odd_last_row') else list(range(14)))
            or builder.num_allocated_qubits != 46 or builder.max_qubits not in (56, 57)):
        raise ValueError('The shorter address-return cut must be L14/Blo9/C8 at46 live qubits.')
    phase = record_initial_blo9(data, debt, table_ledger)
    returned, metadata = restore_address_retained(builder, data, low, blo, curvature,
        table_ledger, **options)
    return returned, dict(metadata, Blo9_Pauli_suffix=phase,
        final_table_phase_repayment_still_required=True)
