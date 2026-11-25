# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Single-use ownership for shortened main inversion and static phase return."""
from __future__ import annotations
from dataclasses import dataclass

from fourier_suffix_inverse import (
    FourierSuffixDebt3, measure_suffix2, measure_suffix3,
    inverse_high_truncated, inverse_full_group_truncated,
)
from fourier_suffix_return import fixed_code, synthesize, repay_at_fixed_code
from virtual_main import inverse_virtual_main_low


@dataclass
class FourierResultDebt:
    removed: int
    suffix: object
    original_snapshot: object
    original_width: int
    stage: str = 'measured'

    @property
    def low_width(self):
        return self.original_width-self.removed


def measure_result_suffix(builder, result, phase_top, original_snapshot, *, removed):
    """Release the measured high result wires, transferring their exact debt."""
    result = list(result)
    if removed not in (1, 2) or len(result) != 19 or phase_top in result:
        raise ValueError('The selected Fourier interface is L19 plus its reconstructed top.')
    if removed == 2:
        suffix = measure_suffix3(builder, result[-2], result[-1], phase_top)
    else:
        suffix = measure_suffix2(builder, result[-1], phase_top)
    return result[:-removed], FourierResultDebt(removed, suffix, original_snapshot, len(result))


def measure_literal_suffix(builder, result, original_snapshot):
    """Measure the three literal top wires of a consuming twenty-bit result.

    There is no reconstructed top and no original-top snapshot here; the
    caller passes a stored-zero classical placeholder for the latter so that
    the unchanged fixed-code repayment keeps its one ledger coordinate.
    """
    result = list(result)
    if len(result) != 20 or len(set(result)) != 20:
        raise ValueError('The literal Fourier interface is a distinct twenty-bit result word.')
    suffix = measure_suffix3(builder, result[-3], result[-2], result[-1])
    suffix.physical = 3
    return result[:-3], FourierResultDebt(3, suffix, original_snapshot, len(result))


def inverse_main_groups(builder, digits, source, retained, groups, debt):
    """Reverse the selected rows while preserving the complete suffix phase."""
    retained = list(retained)
    if debt.stage != 'measured' or len(retained) != debt.low_width or debt.suffix.consumed:
        raise ValueError('Missing matching single-use Fourier main debt.')
    expected = [(10, 14), (0, 6), (6, 10)]
    if [(token.plan.first, token.plan.last) for _, _, token in groups] != expected:
        raise ValueError('The bounded Fourier composition requires the selected three groups.')
    for low, high, token in reversed(groups):
        original=list(low)+list(high)
        if (len(original)!=debt.original_width or original[:debt.low_width]!=retained
                or len(set(original))!=len(original)):
            raise ValueError('The saved group wires are not the exact original result prefix.')
        if high:
            if len(low)+len(high) != debt.original_width or len(high) <= debt.removed:
                raise ValueError('A shortened high correction has the wrong ownership cut.')
            inverse_high_truncated(builder, digits, low, list(high)[:-debt.removed], token, debt.suffix)
            inverse_virtual_main_low(builder, digits, source, low, token)
        else:
            # paired._inputs truncates excess source wires. Such truncation
            # would lose a direct contribution to the measured suffix, so it
            # is forbidden in this composition, even though the old generic
            # adder accepts it. R17 fits each selected retained17/18 row.
            for amount in token.plan.shifts:
                actual_source=len(source) if amount>0 else max(0,len(source)+amount-1)
                actual_target=len(retained)-max(0,amount-1)
                if actual_source>actual_target:
                    raise ValueError('A shortened row would silently discard unsigned source bits.')
            inverse_full_group_truncated(builder, digits, source, retained, token, debt.suffix)
        for row in token.row_debts:
            carry=getattr(row,'carry_debt',row)
            if carry is not None and (not carry.consumed or carry.measurements):
                raise AssertionError('A shortened group left a forward carry phase unpaid.')
        if high:
            if (token.stage!='consumed' or token.saved_bit is not None
                    or token.saved_measurement is not None or token.overflow_debt is None
                    or not token.overflow_debt.consumed or token.overflow_debt.measurements):
                raise AssertionError('A shortened bounded-high/snapshot debt remains owned.')
        elif not token.consumed:
            raise AssertionError('The shortened full-group token was not consumed.')
    debt.stage = 'main_reversed'
    return dict(removed=debt.removed, retained_low_bits=list(range(debt.low_width)),
                omitted_physical_low_bits=list(range(debt.low_width, debt.original_width)),
                original_phase_top=19, non_Pauli_initial_suffix_pending=True,
                original_snapshot_pending=True, all_row_tokens_consumed=True)


def repay_result_at_fixed_code(builder, data, variables, functions, debt, table_debts):
    """Consume the remaining table-only Fourier phase exactly once."""
    if debt.stage != 'main_reversed' or debt.suffix.consumed:
        raise ValueError('The Fourier phase debt is missing, premature or already consumed.')
    three=isinstance(debt.suffix,FourierSuffixDebt3)
    if three != (debt.removed==debt.suffix.physical if three else debt.removed==1):
        raise ValueError('The measured suffix shape does not match the retained low word.')
    decoded=2 if three else 1
    incoming=[debt.suffix.odd,debt.suffix.twice,debt.original_snapshot]
    if three:incoming.append(debt.suffix.four_times)
    existing={bit for _,word in table_debts.pending for bit in word}
    if len(set(incoming))!=len(incoming) or existing.intersection(incoming):
        raise ValueError('A Fourier/snapshot outcome already belongs to another ledger owner.')
    _, expected, _ = fixed_code(data)
    if list(functions) != expected:
        raise AssertionError('The Fourier repayment and mandatory inverse use different fixed codes.')
    plans, synthesis = synthesize(data, decoded)
    metadata = repay_at_fixed_code(
        builder, data, variables, plans, odd=debt.suffix.odd, twice=debt.suffix.twice,
        original_snapshot=debt.original_snapshot, debts=table_debts,
        four_times=debt.suffix.four_times if three else None)
    debt.suffix.consumed = True
    debt.stage = 'consumed'
    return dict(metadata, decoder_synthesis=synthesis,
                debt_consumed_once=True, source_function_order_verified=True,
                replaces_missing_retirement_bits=list(range(debt.low_width, 19)))
