# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Explicit callback ownership for the independently proved early-H7f hook.

The mathematical hook in early_high.py is copied unchanged when this adapter
is integrated. Its experimental converter monkeypatch is not used here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from early_high import (AllocatedHighZeros as ProvedAllocatedHighZeros,
                        EarlyHigh7fHook as ProvedEarlyHigh7fHook,
                        RETIRE_BITS)


@dataclass
class AllocatedHighZeros:
    """Single-use callback return carrying seven owned zero allocations.

    The underlying proved token owns the quantum allocations until consume().
    Its seven classical HMR results belong exclusively to the table ledger.
    This adapter emits no measurement and creates no additional phase debt.
    """
    contract: ProvedAllocatedHighZeros
    phase_metadata: dict
    consumed: bool = field(default=False, init=False)
    extra_control_owner: object | None = None
    reloaded_seeds: dict = field(default_factory=dict)

    def consume(self, builder, high_items, debts):
        if self.consumed or self.contract.released:
            raise ValueError('The allocated-high-zero token has already been consumed.')
        if self.extra_control_owner is not None:
            self.extra_control_owner.check_callback_transition(builder, 55, 53)
        high_items = list(high_items)
        if len(high_items) != 8 or [item.name for item in high_items] != [f'high{i}' for i in range(8)]:
            raise ValueError('The token requires the original ordered high8 codeword.')
        if len({item.wire for item in high_items}) != 8:
            raise ValueError('The original high-word wire ownership is not unique.')
        if builder.num_allocated_qubits != 53:
            raise ValueError('Early-H ownership must pass directly from the 53-live callback.')
        if (self.contract.zero_bits != RETIRE_BITS
                or self.phase_metadata.get('allocated_high_zero_bits') != list(RETIRE_BITS)
                or self.phase_metadata.get('original_high_restored_bits') != [7]
                or self.phase_metadata.get('callback_live_qubits') != 53):
            raise ValueError('The callback token does not describe the selected early-H7f lifetime.')
        # Check exclusive classical ownership, not merely presence in a set.
        # The original token also checks the exact builder, ledger and wires.
        occurrences = {bit: 0 for bit in self.contract.table_measurements}
        for _coefficients, outcomes in debts.pending:
            for bit in outcomes:
                if bit in occurrences:
                    occurrences[bit] += 1
        if len(occurrences) != 7 or any(count != 1 for count in occurrences.values()):
            raise ValueError('Each early-H outcome must have exactly one pending ledger owner.')
        before = builder.num_allocated_qubits
        pending_before = tuple((tuple(coefficients), tuple(outcomes))
                               for coefficients, outcomes in debts.pending)
        kept = self.contract.release(builder, high_items, debts)
        if (builder.num_allocated_qubits != 46 or len(kept) != 1
                or kept[0] is not high_items[7]):
            raise AssertionError('Consuming early-H zeros must retain only the original H7.')
        pending_after = tuple((tuple(coefficients), tuple(outcomes))
                              for coefficients, outcomes in debts.pending)
        if pending_after != pending_before:
            raise AssertionError('Releasing zero allocations changed the table phase ledger.')
        self.consumed = True
        return kept, dict(live_before=before, live_after=46,
                          freed_zero_bits=list(RETIRE_BITS), kept_original_bits=[7],
                          retained_code_coordinates=31, repeated_hmr=False,
                          repeated_phase_debt=False, single_use_token_consumed=True)


class EarlyHigh7fHook:
    """Preserve the existing five-argument factory and bind the ledger once."""
    def __init__(self, model, angles, packed, address, address_frame, *, phase_pass):
        self._arguments = (model, angles, packed, address, address_frame)
        self._phase_pass = phase_pass
        self._core = None
        self._issued = None
        self.last_metadata = None

    def bind_table_ledger(self, debts):
        if self._core is not None or self._issued is not None:
            raise ValueError('The early-H table ledger may be bound only once.')
        if debts.address_bits != 8:
            raise ValueError('The early-H table ledger requires the original eight-bit address.')
        self._core = ProvedEarlyHigh7fHook(*self._arguments, phase_pass=self._phase_pass,
                                         debts=debts)

    def seed_factory(self, factory=None):
        if self._core is None:
            raise ValueError('Bind the table ledger before capturing initializer seeds.')
        return self._core.seed_factory(factory)

    def __call__(self, builder, high, *, owned_controls=None):
        if self._core is None or self._issued is not None:
            raise ValueError('A bound early-H hook can be called exactly once.')
        expected_entry = 53 if owned_controls is None else 55
        if builder.num_allocated_qubits != expected_entry:
            raise ValueError('The selected early-H callback does not match its explicit allocation owner.')
        metadata = self._core(builder, high, owned_controls=owned_controls)
        contract = self._core.retirement.contract
        if (not isinstance(contract, ProvedAllocatedHighZeros)
                or contract.released or builder.num_allocated_qubits != 53):
            raise AssertionError('The proved callback did not return seven owned zero allocations.')
        self.last_metadata = dict(metadata)
        self._issued = AllocatedHighZeros(contract, self.last_metadata, extra_control_owner=owned_controls,
                                          reloaded_seeds=dict(getattr(self._core, 'reloaded_seeds', {})))
        return self._issued


def bind_high_table_ledger(hook, debts):
    """The existing restored-high hook has no external table-ledger binding."""
    if isinstance(hook, EarlyHigh7fHook):
        hook.bind_table_ledger(debts)


def split_high_callback_result(result):
    """Separate JSON metadata from the explicit lifetime ownership return."""
    if isinstance(result, AllocatedHighZeros):
        return result.phase_metadata, result
    if isinstance(result, dict):
        return result, None
    raise TypeError('A high hook must return metadata or an allocated-zero ownership token.')


def assert_high_callback_transition(builder, before, result):
    """Check either an unchanged callback or the exact declared u and g9 consumption."""
    after = builder.num_allocated_qubits
    if isinstance(result, AllocatedHighZeros) and result.extra_control_owner is not None:
        result.extra_control_owner.check_callback_transition(builder, before, after)
    elif after != before:
        raise ValueError('High phase did not restore its temporary workspace.')


def consume_high_callback_result(builder, high_items, debts, result):
    """Called once by the initializer, immediately before coefficient conversion."""
    if result is None:
        return list(high_items), None
    if not isinstance(result, AllocatedHighZeros):
        raise TypeError('The initializer received an unknown high-word ownership contract.')
    return result.consume(builder, high_items, debts)
