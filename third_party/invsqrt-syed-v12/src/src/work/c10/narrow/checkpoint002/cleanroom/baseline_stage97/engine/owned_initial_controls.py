# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Retain captured u and g9 through high decoding and consume both once.

This isolated adapter requires the explicit optional-owner interfaces in
tooling/owned_initial_controls_interfaces.patch.  It does not edit production files.
Install it inside SharedNormalizationCleanupPass and outside refined build.

The original prefix supplies g9=[k>=9] by one additional CNOT copy.  Captured
u=[k>=2] is retained coherently at pack.  The high callback borrows both exact
wires; its existing threshold erasure and outer higher_nonzero cleanup own
their HMR outcomes in the original two ledgers.  Final unpack repays both.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import inspect

import kickmix as km
from packed_shift import PackedShift
from high_increment import PackedThreshold
from threshold_phase_ledger import threshold_terms
import prefix_normalization
import shared_normalization_controls


@dataclass
class InitialHighOwners:
    builder: object
    packed: object
    wire: object
    original_flags: tuple
    g9: object
    stage: str = 'prefix_copied'
    outcome: object = None
    callback_entry: int | None = None
    callback_exit: int | None = None
    debts_before: tuple = field(default_factory=tuple)
    decode_entries: int = 0
    borrow_count: int = 0
    threshold_token: object = None
    threshold_ledger: object = None
    threshold_outcome: object = None
    threshold_borrows: int = 0
    # Seeds deleted for the duration of the high callback (0, or 1 under cap 56).
    absent_seeds: int = 0

    def _builder(self, builder):
        if builder is not self.builder or self.packed.builder is not builder:
            raise ValueError('The retained u belongs to a different builder or packed state.')
        if not isinstance(self.wire, km.q):
            raise ValueError('The retained u must be one allocated quantum wire.')
        if not isinstance(self.g9, km.q) or self.g9 == self.wire:
            raise ValueError('The retained g9 must be a second distinct allocated quantum wire.')

    def finish_pack(self):
        self._builder(self.builder)
        if self.stage != 'prefix_copied' or not self.packed.is_packed:
            raise ValueError('Retained-u packing ownership was not transferred exactly once.')
        if self.builder.num_allocated_qubits != 25:
            raise AssertionError('The retained-u packed entry must contain exactly twenty-five live wires.')
        if {self.wire, self.g9} & (set(self.packed.residual) | {self.packed.t}):
            raise AssertionError('A retained control aliases a packed data wire.')
        if self.packed.max_k != 10 or self.packed._cached_u is not None:
            raise AssertionError('The retained u has a different packed-count contract.')
        self.stage = 'packed_live'

    def begin_decode(self, builder, source):
        self._builder(builder)
        if self.stage != 'packed_live' or self.decode_entries:
            raise ValueError('Retained-u high decoding may start exactly once.')
        if builder.num_allocated_qubits != 47:
            raise AssertionError('High decoding needs the original forty-five wires plus these two owners.')
        if len(source) != 30 or {self.wire, self.g9} & {item.wire for item in source}:
            raise AssertionError('Both extra controls must be outside the unchanged thirty-coordinate decoder.')
        self.decode_entries += 1
        self.stage = 'decoding'

    def check_decode_live(self, builder, expected):
        self._builder(builder)
        if self.stage != 'decoding' or expected not in (47, 55):
            raise ValueError('Invalid retained-u decoder allocation contract.')
        if builder.num_allocated_qubits != expected:
            raise AssertionError('The declared retained-u decoder allocation count changed.')

    def finish_decode(self, builder, high):
        self.check_decode_live(builder, 55)
        if len(high) != 8 or {self.wire, self.g9} & set(high):
            raise AssertionError('Both retained controls must remain separate from all eight high outputs.')
        self.stage = 'decoded'

    def begin_callback(self, builder, packed, entry):
        self._builder(builder)
        if packed is not self.packed or self.stage != 'decoded' or entry != 55:
            raise ValueError('The declared two-owner high callback must enter at fifty-five live wires.')
        if builder.num_allocated_qubits != entry or packed._cached_u is not None:
            raise AssertionError('The high callback did not enter at the declared u lifetime boundary.')
        if self.threshold_ledger is None:
            raise AssertionError('The matching threshold ledger must be bound before the two-owner callback.')
        self.debts_before = tuple(packed._u_debts)
        self.callback_entry = entry
        self.stage = 'callback_active'

    def borrow(self, packed):
        self._builder(packed.builder)
        if packed is not self.packed or self.stage != 'callback_active' or self.borrow_count:
            raise ValueError('Only the matching first outer high-phase scope may consume the retained u.')
        if packed._cached_u is not None or tuple(packed._u_debts) != self.debts_before:
            raise AssertionError('The retained u was requested through a different cached/debt interface.')
        self.borrow_count += 1
        self.stage = 'borrowed'
        return self.wire

    def borrow_g9(self, builder, packed, u):
        self._builder(builder)
        if (packed is not self.packed or self.stage != 'borrowed' or u != self.wire
                or self.threshold_token is not None or self.threshold_borrows):
            raise ValueError('Only the matching high callback may borrow the retained g9 once.')
        if self.absent_seeds not in (0, 1) or builder.num_allocated_qubits != 55-self.absent_seeds:
            raise AssertionError('The supplied g9 must require no extra callback allocation.')
        self.threshold_token = PackedThreshold(9, self.g9, packed.t, tuple(packed.residual[:4]))
        self.threshold_borrows += 1
        return self.threshold_token

    def finish_g9_erasure(self, builder, token, ledger, before):
        self._builder(builder)
        if token is not self.threshold_token or ledger is not self.threshold_ledger:
            raise ValueError('The retained g9 was erased through a different token or phase owner.')
        if not token.consumed or builder.num_allocated_qubits != 54-self.absent_seeds:
            raise AssertionError('The original g9 erasure must free one of the callback allocations.')
        after = tuple(ledger.pending)
        if len(after) != len(before) + 1 or after[:-1] != before:
            raise AssertionError('The original g9 erasure did not append exactly one threshold debt.')
        terms, outcome, conditions = after[-1]
        if terms != threshold_terms(9) or conditions or outcome not in ledger._owned:
            raise AssertionError('The new phase record is not the original unguarded g9 debt.')
        self.threshold_outcome = outcome

    def finish_callback(self, builder, packed, entry):
        self._builder(builder)
        if packed is not self.packed or self.stage != 'borrowed' or self.borrow_count != 1:
            raise ValueError('The retained u was not consumed once by the actual high callback.')
        if entry != 55 or builder.num_allocated_qubits != 53 or packed._cached_u is not None:
            raise AssertionError('The high callback must consume precisely both extra owners, fifty-five to fifty-three.')
        if (self.threshold_borrows != 1 or self.threshold_token is None
                or not self.threshold_token.consumed or self.threshold_outcome is None):
            raise AssertionError('The g9 owner did not transfer through its original threshold erasure.')
        after = tuple(packed._u_debts)
        if len(after) != len(self.debts_before) + 1 or after[:-1] != self.debts_before:
            raise AssertionError('The existing outer u erasure did not append exactly one owned phase debt.')
        self.outcome = after[-1]
        self.callback_exit = 53
        self.stage = 'both_ledgers_owned'

    def check_callback_transition(self, builder, before, after):
        self._builder(builder)
        if (self.stage != 'both_ledgers_owned' or before != 55 or after != 53
                or self.callback_entry != before or self.callback_exit != after
                or builder.num_allocated_qubits != after):
            raise AssertionError('The initializer lacks the exact two-owner callback consumption certificate.')
        if self.packed._u_debts.count(self.outcome) != 1:
            raise AssertionError('The transferred u measurement has lost its unique packed-ledger owner.')
        if (sum(outcome == self.threshold_outcome for _, outcome, _ in self.threshold_ledger.pending) != 1
                or self.threshold_outcome not in self.threshold_ledger._owned):
            raise AssertionError('The transferred g9 measurement has lost its unique threshold-ledger owner.')

    def check_final(self):
        self._builder(self.builder)
        if self.stage != 'both_ledgers_owned' or self.borrow_count != 1 or self.decode_entries != 1:
            raise AssertionError('The retained-u lifecycle did not reach its unique ledger owner.')
        if self.packed.is_packed or self.packed.pending_measurements or self.packed._cached_u is not None:
            raise AssertionError('The retained-u lifecycle did not reach final unpack and phase repayment.')
        if self.threshold_ledger.pending or self.threshold_ledger._owned:
            raise AssertionError('The retained g9 phase did not reach final threshold repayment.')
        self.stage = 'repaid'


def require_owners(owner):
    if not isinstance(owner, InitialHighOwners):
        raise TypeError('Explicit InitialHighOwners are required for both additional high-decoder allocations.')
    return owner


class RetainedInitialControlsScope:
    """Replace only initial-u erasure/recomputation under explicit contracts."""
    def __init__(self):
        self.owners = {}
        self.by_builder = {}
        self._packing = None
        self.prefix_thresholds = {}
        self.prefix_captures = 0

    @contextmanager
    def install(self):
        import early_high
        import high_ownership
        import high_product_share
        if any('owned_controls' not in inspect.signature(function).parameters for function in (
                high_product_share.convert_shared_high, high_product_share.emit_variant,
                high_ownership.EarlyHigh7fHook.__call__, early_high.EarlyHigh7fHook.__call__)):
            raise RuntimeError('Apply the explicit owned-u interface patch in an isolated candidate first.')
        old_pack = PackedShift.pack
        old_erase = shared_normalization_controls._erase_u_from_flags
        old_compute = PackedShift._compute_u_from_packed
        old_convert = high_product_share.convert_shared_high
        old_hook = high_ownership.EarlyHigh7fHook.__call__
        old_prefixes = prefix_normalization._prefixes
        old_make_threshold = early_high.make_threshold
        old_erase_threshold = early_high.erase_threshold

        @contextmanager
        def prefixes(builder, zero_bits, length, **options):
            if length != 20 or len(zero_bits) != 20 or id(builder) in self.prefix_thresholds:
                raise AssertionError('Retained g9 requires the one original twenty-bit zero-prefix scope.')
            with old_prefixes(builder, zero_bits, length, **options) as values:
                wire = builder.alloc_qubits(1)[0]
                builder.cx(values[18], wire)
                self.prefix_thresholds[id(builder)] = wire
                self.prefix_captures += 1
                yield values

        def erase(builder, flags, wire, pending=()):
            packed = self._packing
            if packed is None:
                return old_erase(builder, flags, wire, pending)
            if pending or builder is not packed.builder or tuple(flags) != tuple(packed._flags):
                raise AssertionError('The captured initial u erasure has a different owner or flag frame.')
            if packed in self.owners or id(builder) in self.by_builder:
                raise AssertionError('The initial u already has a retained owner.')
            g9 = self.prefix_thresholds.pop(id(builder), None)
            if g9 is None:
                raise AssertionError('The initial pack has no captured original-prefix g9 owner.')
            owner = InitialHighOwners(builder, packed, wire, tuple(flags), g9)
            self.owners[packed] = owner
            self.by_builder[id(builder)] = owner
            # Coherent retention intentionally creates no HMR or phase debt.

        def pack(packed):
            if packed.is_packed:
                return old_pack(packed)
            if self._packing is not None:
                raise RuntimeError('Nested initial pack ownership is not supported.')
            self._packing = packed
            try:
                result = old_pack(packed)
            finally:
                self._packing = None
            owner = self.owners.get(packed)
            if owner is None:
                raise AssertionError('The initial packing did not supply its already captured u wire.')
            owner.finish_pack()
            return result

        def compute(packed):
            owner = self.owners.get(packed)
            if owner is None or owner.stage in ('both_ledgers_owned', 'repaid'):
                return old_compute(packed)
            return owner.borrow(packed)

        def convert(builder, retained, consumed, desired, phase_debts, **settings):
            owner = self.by_builder.get(id(builder))
            if owner is None:
                return old_convert(builder, retained, consumed, desired, phase_debts, **settings)
            return old_convert(builder, retained, consumed, desired, phase_debts,
                               owned_controls=owner, **settings)

        def hook(instance, builder, high):
            owner = self.owners.get(instance._arguments[2])
            if owner is None:
                return old_hook(instance, builder, high)
            if owner.threshold_ledger is not None:
                raise AssertionError('The retained g9 threshold ledger was bound twice.')
            owner.threshold_ledger = instance._phase_pass.ledger(owner.packed)
            return old_hook(instance, builder, high, owned_controls=owner)

        def make_threshold(builder, packed, threshold=7, *, u=None):
            owner = self.owners.get(packed)
            if owner is None or threshold != 9:
                return old_make_threshold(builder, packed, threshold, u=u)
            return owner.borrow_g9(builder, packed, u)

        def erase_threshold(builder, token, *, u=None, ledger=None):
            owner = self.by_builder.get(id(builder))
            if owner is None or token is not owner.threshold_token:
                return old_erase_threshold(builder, token, u=u, ledger=ledger)
            if u != owner.wire or ledger is not owner.threshold_ledger:
                raise AssertionError('The retained g9 must use its original u and threshold ledger.')
            before = tuple(ledger.pending)
            old_erase_threshold(builder, token, u=u, ledger=ledger)
            owner.finish_g9_erasure(builder, token, ledger, before)

        shared_normalization_controls._erase_u_from_flags = erase
        PackedShift.pack = pack
        PackedShift._compute_u_from_packed = compute
        high_product_share.convert_shared_high = convert
        high_ownership.EarlyHigh7fHook.__call__ = hook
        prefix_normalization._prefixes = prefixes
        early_high.make_threshold = make_threshold
        early_high.erase_threshold = erase_threshold
        try:
            yield self
        finally:
            shared_normalization_controls._erase_u_from_flags = old_erase
            PackedShift.pack = old_pack
            PackedShift._compute_u_from_packed = old_compute
            high_product_share.convert_shared_high = old_convert
            high_ownership.EarlyHigh7fHook.__call__ = old_hook
            prefix_normalization._prefixes = old_prefixes
            early_high.make_threshold = old_make_threshold
            early_high.erase_threshold = old_erase_threshold
        if len(self.owners) != 1 or self.prefix_thresholds or self.prefix_captures != 1:
            raise AssertionError('The selected two-owner scope must consume one initial packed state and one g9 copy.')
        for owner in self.owners.values():
            owner.check_final()

    def metadata(self):
        if len(self.owners) != 1:
            raise AssertionError('The initial-u ownership record is incomplete.')
        owner = next(iter(self.owners.values()))
        if owner.stage != 'repaid':
            raise AssertionError('The initial-u phase debt has not completed final repayment.')
        return dict(status='EXPLICIT_INITIAL_U_G9_LIFECYCLE_COMPLETED',
                    packed_live=25, high_decode_entry=47, high_decode_exit=55,
                    high_callback_entry=55, high_callback_exit=53,
                    unchanged_early_high_release=[53, 46],
                    initial_owner_count=2, outer_u_borrows=owner.borrow_count,
                    g9_token_borrows=owner.threshold_borrows,
                    original_prefix_g9_copies=self.prefix_captures,
                    initial_u_measurement_omitted=True,
                    existing_later_HMR_and_ledger_repayment_preserved=True,
                    expected_saved_E_vs_stage86=4,
                    complete_generator_official_verification_required=True)
