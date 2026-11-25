# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Share the final packed decoder with the complete thermometer cleanup basis.

This is an opt-in source component.  Install its adapter outside the existing
PackedThresholdPhasePass scope.  It is intended for the selected schedule's
single final unpack, followed by inverse normalization with thermometer
cleanup.  No model, compiled circuit, saved plan, or numerical table is read.

The packed state retains t=[k>0] and four residual positions.  For k>=2 those
positions contain (f1, f2 XOR f3, f0, f3); k=0/1 may have residual data in the
positions where the packing contract permits it.  Nine exact products expose
a complete ten-dimensional basis of functions of k in 0..10.  A freshly
derived Clifford frame makes these the monomials with masks 1..10.  Four of
the wires serve as ordinary flags during inverse routing, and all ten are
later reused by the existing thermometer erasure.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache

import kickmix as km
from codebook import BinarySpan, parity_function
from fusion.normalization import ShiftFlags
from packed_shift import PackedShift, _phase_u
import thermometer_cleanup
from threshold_phase_ledger import ThresholdPhaseLedger


@lru_cache(maxsize=1)
def monomial_frame():
    """Derive, and certify, the invertible ten-function output frame."""
    truths = [0 for _ in range(10)]
    for count in range(11):
        first, second, third, fourth = [(count >> bit) & 1 for bit in range(4)]
        high_pair = third ^ fourth
        values = (int(count > 0), second, high_pair, second & high_pair,
                  fourth, first & int(count >= 2), first & second,
                  first & third, first & fourth, second & fourth)
        for index, value in enumerate(values):
            truths[index] |= value << count
    span = BinarySpan(truths)
    if len(span.pivots) != 10:
        raise AssertionError('The direct packed decoder lost a required function of the count.')
    rows = []
    for mask in range(1, 11):
        truth = sum(int(count & mask == mask) << count for count in range(11))
        expression = span.solve(truth)
        if expression is None or parity_function(expression, truths) != truth:
            raise AssertionError('A count monomial has no exact direct-decoder representation.')
        rows.append(expression)
    # This call also proves full row rank.  No numerical synthesis is used.
    operations = thermometer_cleanup.linear_frame(rows)
    return tuple(rows), tuple(operations)


@dataclass
class PreparedCleanup:
    builder: object
    packed: object
    wires: list
    flags: list
    helper_wires: list

    @property
    def monomials(self):
        return {mask: self.wires[mask - 1] for mask in range(1, 11)}


def decode_to_monomials(packed):
    """Restore residual data and flags, retaining the six later cleanup terms.

    The caller must eventually consume the returned basis through the exact
    thermometer erasure.  Keeping the original t wire in this basis avoids
    measuring t and subsequently recreating the same nonlinear information.
    Existing flag/u measurement debts are repaid and released exactly once.
    """
    packed._require_no_borrowed_controls()
    if not packed.is_packed or packed.max_k != 10:
        raise ValueError('Direct final cleanup requires the packed k<=10 geometry.')
    if len(packed._flag_debts) not in (0, 4):
        raise AssertionError('The packed flag ledger has an unexpected width.')
    builder = packed.builder
    residual = list(packed.residual[:4])
    retained = packed.t
    products = list(builder.alloc_qubits(9))
    second, high_pair, cross, fourth, odd_high, first_second, first_third, first_fourth, second_fourth = products

    builder.ccx(retained, residual[0], second)
    builder.ccx(retained, residual[1], high_pair)
    builder.ccx(second, residual[1], cross)
    builder.ccx(high_pair, residual[3], fourth)

    # cross temporarily holds u = second OR high_pair.
    builder.cx(second, cross)
    builder.cx(high_pair, cross)
    builder.ccx(cross, residual[2], odd_high)
    builder.cx(high_pair, cross)
    builder.cx(second, cross)

    builder.ccx(second, residual[2], first_second)
    # high_pair XOR fourth is the original third binary flag.
    builder.cx(fourth, high_pair)
    builder.ccx(high_pair, residual[2], first_third)
    builder.cx(fourth, high_pair)
    builder.ccx(fourth, residual[2], first_fourth)
    builder.ccx(fourth, residual[0], second_fourth)

    for source, target in zip((second, high_pair, odd_high, fourth), residual):
        builder.cx(source, target)

    wires = [retained] + products
    _, operations = monomial_frame()
    for operation, left, right in operations:
        if operation == 'cx':
            builder.cx(wires[left], wires[right])
        else:
            builder.swap(wires[left], wires[right])
    flags = [wires[(1 << bit) - 1] for bit in range(4)]
    flag_set = set(flags)
    helpers = [wire for wire in wires if wire not in flag_set]

    for outcome in packed._u_debts:
        _phase_u(builder, flags, outcome)
        builder.free(outcome)
    packed._u_debts.clear()
    for flag, outcome in zip(flags, packed._flag_debts):
        builder.push_condition(outcome)
        builder.z(flag)
        builder.pop_condition()
        builder.free(outcome)
    packed._flag_debts.clear()
    packed._flags = flags
    packed._t = None
    return PreparedCleanup(builder, packed, wires, flags, helpers)


def repay_thresholds_on_monomials(ledger, builder, prepared):
    """Consume all threshold owners using the already retained count basis."""
    if not ledger.pending:
        return dict(outcomes=0, cubic_corrections=0)
    by_term = {}
    for terms, outcome, conditions in ledger.pending:
        for term in terms:
            by_term.setdefault(term, []).append((outcome, conditions))
    monomials = prepared.monomials
    for term, records in sorted(by_term.items()):
        # Terms outside the ten nonconstant basis masks vanish on k<=10.
        if term and term not in monomials:
            if any(count & term == term for count in range(11)):
                raise AssertionError('An unrepresented threshold monomial is not identically zero.')
            continue
        parity = builder.alloc_bits(1)[0]
        builder.bit_store(parity, False)
        for outcome, conditions in records:
            for guard in conditions:
                builder.push_condition(guard)
            builder.cx(outcome, parity)
            for _ in conditions:
                builder.pop_condition()
        builder.push_condition(parity)
        builder.z(monomials[term] if term else True)
        builder.pop_condition()
        builder.free(parity)
    count = len(ledger.pending)
    for _, outcome, _ in ledger.pending:
        builder.free(outcome)
    ledger.pending.clear()
    ledger._owned.clear()
    return dict(outcomes=count, cubic_corrections=0,
                reused_count_monomials=True, common_cubic_already_available=True,
                quantum_workspace=0, threshold_owners_released_once=True)


class LatePackedCleanupPass:
    """Scoped final-unpack adapter; it never changes an active release by itself."""
    def __init__(self):
        self.prepared = {}
        self.decodings = 0
        self.consumptions = 0
        self.threshold_repayments = []

    @staticmethod
    def _key(builder, flags):
        return id(builder), tuple(flags)

    @contextmanager
    def install(self):
        old_unpack = PackedShift.unpack
        old_basis = thermometer_cleanup.binary_to_thermometer
        old_repay = ThresholdPhaseLedger.repay
        if old_unpack.__qualname__ != 'PackedShift.unpack':
            raise RuntimeError('Install late cleanup outside the packed-threshold adapter.')

        def unpack(packed):
            if not packed.is_packed:
                return old_unpack(packed)
            prepared = decode_to_monomials(packed)
            key = self._key(packed.builder, prepared.flags)
            if key in self.prepared:
                raise AssertionError('A final cleanup basis already has an owner.')
            self.prepared[key] = prepared
            self.decodings += 1
            return ShiftFlags(prepared.flags, packed.max_k)

        def repay(ledger, builder, flags):
            prepared = self.prepared.get(self._key(builder, flags))
            if prepared is None:
                return old_repay(ledger, builder, flags)
            metadata = repay_thresholds_on_monomials(ledger, builder, prepared)
            self.threshold_repayments.append(metadata)
            return metadata

        def basis(builder, flags, maximum):
            key = self._key(builder, flags)
            prepared = self.prepared.pop(key, None)
            if prepared is None:
                return old_basis(builder, flags, maximum)
            if maximum != 10:
                raise ValueError('A retained count basis has the wrong thermometer width.')
            rows = thermometer_cleanup.thermometer_matrix(maximum)
            for operation, left, right in thermometer_cleanup.linear_frame(rows):
                if operation == 'cx':
                    builder.cx(prepared.wires[left], prepared.wires[right])
                else:
                    builder.swap(prepared.wires[left], prepared.wires[right])
            self.consumptions += 1
            return prepared.wires, prepared.helper_wires

        PackedShift.unpack = unpack
        ThresholdPhaseLedger.repay = repay
        thermometer_cleanup.binary_to_thermometer = basis
        try:
            yield self
        finally:
            PackedShift.unpack = old_unpack
            ThresholdPhaseLedger.repay = old_repay
            thermometer_cleanup.binary_to_thermometer = old_basis
        if self.prepared or self.decodings != self.consumptions:
            raise AssertionError('A final packed cleanup basis was not consumed exactly once.')
