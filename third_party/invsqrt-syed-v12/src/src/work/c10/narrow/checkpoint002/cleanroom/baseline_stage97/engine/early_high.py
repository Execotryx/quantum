# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Consume H0..6 before inverse tail-delta, retaining an exact phase ledger.

The production generator is never rewritten. This module changes one lifetime:
HMR acts on H_j XOR g9*D_j, the mixed sign is repaid on the preserved static
bank, and the remaining H_j sign transfers to DeferredTablePhases. The seven
zero allocations remain owned until the initializer converter consumes their
explicit single-use contract. H7 and the entire static bank are restored.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import kickmix as km
import initial_retained as initial_module
import merged_phase
from affine_labels import emit_address_frame
from codebook import bits, parity_function
from controlled_table_delta import apply_delta
from high_increment import make_threshold, erase_threshold
from r17_lookup import table_words
from retained_products import convert_retained_products as original_converter
from tail43_hook import Tail43HighPhaseHook, borrow_affine

RETIRE_MASK = 0x7f
RETIRE_BITS = tuple(range(7))


@dataclass
class AllocatedHighZeros:
    """Seven allocated zero wires whose measurement bits already have an owner."""
    high_wires: tuple
    zero_bits: tuple
    ledger: object
    builder: object
    table_measurements: tuple
    released: bool = False

    def release(self, builder, high_items, ledger):
        if self.released or builder is not self.builder or ledger is not self.ledger:
            raise ValueError('The precleared-H contract is stale or belongs to another lifecycle.')
        if tuple(item.wire for item in high_items) != self.high_wires:
            raise ValueError('The initializer changed the contracted high-word wires.')
        if self.zero_bits != RETIRE_BITS:
            raise ValueError('The contract does not clear exactly H0..6.')
        owned = {bit for _, word in ledger.pending for bit in word}
        if not set(self.table_measurements) <= owned:
            raise ValueError('The table ledger no longer owns every early-H measurement.')
        before = builder.num_allocated_qubits
        builder.free(km.array([self.high_wires[i] for i in self.zero_bits]))
        if builder.num_allocated_qubits != before-7:
            raise AssertionError('Releasing precleared H did not free seven allocations.')
        self.released = True
        return [item for i, item in enumerate(high_items) if i not in self.zero_bits]


class RecycledSeed:
    """One seed monomial that is absent while the high callback runs.

    The high route needs two temporary wires above the callback entry. Under
    a cap that leaves only one, a two-factor seed which no delta mask reads
    is deleted in the raw address frame by DEL_AND on its two address
    factors (the measurement sign is repaid at once), and it is recomputed
    by one AND on a new wire after the callback. The callback receives the
    projected live bank and projected masks, never the freed wire.
    """
    def __init__(self, builder, hook, variables):
        factors = None
        groups = [m for m in range(1, 16) if m.bit_count() >= 2]
        for number, item in enumerate(hook.seeds):
            index = len(hook.address)+number
            mask = groups[number % len(groups)]
            if mask.bit_count() != 2 or any(m >> (index+1) & 1 for m in hook.delta.masks):
                continue
            start = 4*(number//len(groups))
            factors = [start+bit for bit in range(4) if mask >> bit & 1]
            break
        if factors is None:
            raise ValueError('No two-factor seed is unread by the high callback.')
        truth = hook.functions[factors[0]] & hook.functions[factors[1]]
        if hook.functions[index] != truth or variables[index] != item.wire:
            raise AssertionError('The selected seed is not the product of its two raw address factors.')
        self.name, self.index, self.factors = item.name, index, tuple(factors)
        self.controls = (hook.address[factors[0]], hook.address[factors[1]])
        low = (1 << (index+1))-1
        masks = tuple((m & low) | ((m >> (index+2)) << (index+1)) for m in hook.delta.masks)
        functions = hook.functions[:index]+hook.functions[index+1:]
        for old, new in zip(hook.delta.masks, masks):
            if ((old ^ new) & 1 or parity_function(old >> 1, hook.functions)
                    != parity_function(new >> 1, functions)):
                raise AssertionError('Projecting the static bank changed an affine delta truth.')
        self.delta = replace(hook.delta, masks=masks, function_count=len(functions))
        self.variables = variables[:index]+variables[index+1:]
        self.entry = builder.num_allocated_qubits
        builder.del_and(self.controls[0], self.controls[1], item.wire)
        builder.free(item.wire)
        self.wire = None

    def reload(self, builder):
        if self.wire is not None or builder.num_allocated_qubits != self.entry-3:
            raise AssertionError('The absent seed is reloaded once, after both retained controls are consumed.')
        self.wire = builder.alloc_qubits(1)[0]
        builder.ccx(self.controls[0], self.controls[1], self.wire)
        return self.wire


class EarlyHighRetirement:
    """Local exact replacement, also usable without the large phase network."""
    def __init__(self, model, frame, delta, debts):
        self.delta = delta
        self.debts = debts
        if len(delta.masks) != 8 or delta.masks[7] != 0 or delta.and_count != 3:
            raise ValueError('This bounded experiment requires the selected three-product low delta.')
        raw_high = table_words(model)['high']
        self.high_table = [0]*256
        for address, high in enumerate(raw_high):
            self.high_table[frame.transform(address) if frame else address] = high & RETIRE_MASK
        self.contract = None
        self.metadata = None

    def consume_shifted(self, builder, high, threshold, variables, *, omit_mixed=False,
                        delta=None):
        """Called in RAW address frame, after the phase restored H XOR g9*D.

        For outcome m, HMR contributes (-1)^(m*(H XOR gD)). Applying
        (-1)^(m*gD) leaves precisely (-1)^(m*H), owned by the framed ledger.
        The affine D is expanded as conditional Z/CZ, without quantum ANDs.
        ``omit_mixed`` is a deliberately incorrect negative-control option.
        """
        if self.contract is not None:
            raise ValueError('Early high retirement may occur only once per initializer.')
        high, variables = list(high), list(variables)
        delta = self.delta if delta is None else delta
        if len(delta.masks) != 8 or delta.masks[7] != 0 or delta.and_count != self.delta.and_count:
            raise ValueError('A projected delta must keep the selected three-product shape.')
        if len(high) != 8 or len(variables) != delta.function_count:
            raise ValueError('The early-H word/static-bank dimensions changed.')
        if len(set(high+variables+[threshold])) != len(high)+len(variables)+1:
            raise ValueError('The high word, static bank, and threshold must be disjoint.')
        outcomes = tuple(builder.alloc_bits(7))
        builder.hmr(km.array(high[:7]), km.array(outcomes))
        z_count = cz_count = 0
        if not omit_mixed:
            for outcome, mask in zip(outcomes, delta.masks[:7]):
                builder.push_condition(outcome)
                if mask & 1:
                    builder.z(threshold)
                    z_count += 1
                for index in bits(mask >> 1):
                    builder.cz(threshold, variables[index])
                    cz_count += 1
                builder.pop_condition()
        recorded = self.debts.record_measurements(self.high_table, outcomes)
        self.contract = AllocatedHighZeros(tuple(high), RETIRE_BITS, self.debts,
                                          builder, outcomes)
        self.metadata = dict(recorded, retirement_mask=RETIRE_MASK,
            zero_bits=list(RETIRE_BITS), kept_original_high_bits=[7],
            mixed_sign_conditional_z=z_count, mixed_sign_conditional_cz=cz_count,
            mixed_sign_and_count=0, inverse_delta_ands_omitted=delta.and_count,
            zero_allocations_retained_until_conversion=True,
            negative_control_omits_mixed_sign=bool(omit_mixed))
        return self.metadata


class EarlyHigh7fHook(Tail43HighPhaseHook):
    def __init__(self, model, angles, packed, address, address_frame, *, phase_pass, debts):
        super().__init__(model, angles, packed, address, address_frame, phase_pass=phase_pass)
        self.retirement = EarlyHighRetirement(model, address_frame, self.delta, debts)

    def __call__(self, builder, high, *, owned_controls=None):
        high = list(high)
        if self.seeds is None or len(high) != 8:
            raise ValueError('Capture the original 22 seed helpers and provide H8 first.')
        entry = builder.num_allocated_qubits
        if owned_controls is not None:
            from owned_initial_controls import require_owners
            require_owners(owned_controls).begin_callback(builder, self.packed, entry)
        variables = self.address+[item.wire for item in self.seeds]
        delta, recycled = self.delta, None
        self.reloaded_seeds = {}
        if self.frame is not None:
            emit_address_frame(builder, self.address, self.frame, inverse=True)
        try:
            if owned_controls is not None and builder.max_qubits-entry < 2:
                # Cap 56: the route's two temporary wires need one absent seed.
                if builder.max_qubits-entry != 1:
                    raise ValueError('The high callback can recycle exactly one seed.')
                recycled = RecycledSeed(builder, self, variables)
                variables, delta = recycled.variables, recycled.delta
                owned_controls.absent_seeds = 1
            with self.packed.higher_nonzero() as u:
                threshold = make_threshold(builder, self.packed, 9, u=u)
                apply_delta(builder, high, threshold.control, variables, delta)
                with borrow_affine(builder, self.address, self.tail_mask) as tail18:
                    with self.phase_pass.reuse_threshold(self.packed, 9, threshold.control):
                        previous = merged_phase._threshold
                        merged_phase._threshold = self.phase_pass.threshold
                        try:
                            phase = merged_phase.merged_packed_cyclic_scale_phase(
                                builder, high, self.packed, 18, turn_offsets=self.offsets,
                                complement_overflow=True, tail_bits={18: tail18},
                                tail_first_removed=8)
                        finally:
                            merged_phase._threshold = previous
                self.retirement.consume_shifted(builder, high, threshold.control, variables,
                                                delta=delta)
                # D7=0 was certified above. The retained H7 already has its
                # original value; H0..6 must stay zero, so no inverse delta.
                erase_threshold(builder, threshold, u=u,
                                ledger=self.phase_pass.ledger(self.packed))
            if recycled is not None:
                self.reloaded_seeds = {recycled.name: recycled.reload(builder)}
        finally:
            if self.frame is not None:
                emit_address_frame(builder, self.address, self.frame)
        if owned_controls is None:
            if builder.num_allocated_qubits != entry:
                raise AssertionError('The phase callback changed allocation ownership.')
        else:
            owned_controls.finish_callback(builder, self.packed, entry)
        callback_exit = builder.num_allocated_qubits
        avoided_u_setup = 2 if owned_controls is not None else 0
        avoided_threshold_setup = 2 if owned_controls is not None else 0
        extra = self.delta.and_count+2-avoided_threshold_setup+int(recycled is not None)
        self.last_metadata = dict(phase, tail43_hook=True, early_high_7f=True,
            certificate=self.certificate, and_products=phase['and_products']+extra-avoided_u_setup,
            expected_toffolis=phase['expected_toffolis']+extra-avoided_u_setup,
            hook_extra_ands=extra, shared_u_setup_ands=2-avoided_u_setup,
            shared_g9_setup_ands=2-avoided_threshold_setup,
            threshold_phases_deferred=True, static_bank_restored=True,
            affine_address_frame_restored=True, callback_live_qubits=callback_exit,
            callback_entry_live_qubits=entry, retained_initial_controls_consumed=owned_controls is not None,
            original_high_restored_bits=[7], allocated_high_zero_bits=list(RETIRE_BITS),
            early_retirement=self.retirement.metadata,
            recycled_seed=None if recycled is None else dict(
                name=recycled.name, bank_index=recycled.index, raw_address_factors=list(recycled.factors),
                deleted_by='DEL_AND on its two raw address factors', reload_ands=1,
                projected_delta_masks=list(recycled.delta.masks), callback_live_during_route=entry-1))
        return self.last_metadata


def make_initializer(retirement, *, progress=None):
    """Use the selected initializer, replacing only its consumed-H contract."""
    def initialize(builder, data, address, debts, high_phase, **options):
        if debts is not retirement.debts:
            raise ValueError('Hook and initializer must share the same table-phase ledger.')
        if options.get('decoder_trials', 80) != 80 or options.get('rank_rounds', 0):
            raise ValueError('Keep the selected deterministic decoder settings.')
        if options.get('direction_limit', 4) != 4 or options.get('retained_helpers', 1) != 1:
            raise ValueError('Only the early high lifetime changes in this experiment.')
        previous = initial_module.convert_retained_products
        if previous is not original_converter:
            raise RuntimeError('Another initializer-converter experiment is active.')
        calls = 0
        released = None

        def converter(b, consumed, desired, ledger, **settings):
            nonlocal calls, released
            calls += 1
            if calls != 1 or settings.get('seed') != 2026110609:
                raise AssertionError('The selected initializer conversion contract changed.')
            if settings.get('basis_trials') != 256 or settings.get('retained_helpers') != 1:
                raise AssertionError('The selected product search settings changed.')
            consumed = list(consumed)
            if len(consumed) != 38 or len({item.wire for item in consumed}) != 38:
                raise AssertionError('Expected address8 + seed22 + high8 with unique ownership.')
            bank, high = consumed[:-8], consumed[-8:]
            if [item.name for item in high] != [f'high{i}' for i in range(8)]:
                raise AssertionError('The selected high codeword ordering changed.')
            if retirement.contract is None:
                raise AssertionError('The callback did not produce an allocated-zero contract.')
            before = b.num_allocated_qubits
            kept = retirement.contract.release(b, high, ledger)
            released = dict(live_before=before, live_after=b.num_allocated_qubits,
                            freed_zero_bits=list(RETIRE_BITS), repeated_hmr=False,
                            repeated_phase_debt=False, kept_original_bits=[7])
            settings['progress'] = progress
            return previous(b, bank+kept, desired, ledger, **settings)

        initial_module.convert_retained_products = converter
        try:
            words, metadata = initial_module.initial_retained(
                builder, data, address, debts, high_phase, **options)
        finally:
            initial_module.convert_retained_products = previous
        if calls != 1 or not retirement.contract.released:
            raise AssertionError('The zero-wire contract was not consumed exactly once.')
        if metadata['seed_ands'] != 22 or metadata['high_decode']['and_count'] != 35:
            raise AssertionError('The unchanged seed/high decoder budget changed.')
        return words, dict(metadata, early_high_zero_release=released,
                           selected_conversion_seed=2026110609,
                           selected_direction_limit=4)
    return initialize
