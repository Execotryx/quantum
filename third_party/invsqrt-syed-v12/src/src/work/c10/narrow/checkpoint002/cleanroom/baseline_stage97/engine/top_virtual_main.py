# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Main arithmetic with a nearest-anchor top bit reconstructed only for phase.

Initially the omitted top bit is NOT a, where a is the highest retained
result bit.  For total update P with |P| < 2**(n-1) and sign sigma, save a
and update the n retained bits modulo 2**n.  If their final high bit is b,
the omitted final bit is

    1 XOR sigma XOR ((a XOR sigma) AND (b XOR sigma)).

The saved bit can be measured immediately after the phase pass, because
its original value reappears after inverse arithmetic.  Its conditional Z
repayment therefore needs no quantum storage during that inverse.
"""
from __future__ import annotations

from dataclasses import dataclass
import kickmix as km

from split_bounded import _digit_count, _row_controls
from virtual_main import _row_seed
from variable_lsb_main import row_parity_mask
from virtual_lsb import forward_virtual_row, inverse_virtual_row


@dataclass
class FullVirtualToken:
    plan: object
    width: int
    row_debts: list
    row_parities: list
    parity_before: int
    parity_after: int
    consumed: bool = False


def omit_complement_top(builder, full_target):
    """Reuse a certified initial complemented top bit as the global snapshot.

    The caller must certify full_target[-1] == NOT full_target[-2] from
    its mathematical coefficient table.  This X turns the former high wire
    into an exact copy of the highest retained bit, with no allocation.
    """
    full_target = list(full_target)
    if len(full_target) < 2 or len(set(full_target)) != len(full_target):
        raise ValueError('Expected a distinct target word of at least two bits.')
    builder.x(full_target[-1])
    return full_target[:-1], full_target[-1]


def restore_complement_top(builder, target):
    """After inverse rows, re-create the original top for the table decoder."""
    target = list(target)
    if not target:
        raise ValueError('The restored lower target word must be nonempty.')
    high = builder.alloc_qubits(1)[0]
    builder.cx(target[-1], high)
    builder.x(high)
    return target+[high]


def forward_full_virtual_rows(builder, digits, source, target, plan, *,
                              parity_before=0):
    """Virtual-bottom rows modulo the entire physical target word.

    No old-window bit or high correction is needed because this operation
    intentionally updates the whole modular word.  The enclosing caller
    owns the one global top-reconstruction certificate and saved bit.
    """
    source, target = list(source), list(target)
    if len(target) != plan.window or _digit_count(digits) != plan.digits:
        raise ValueError('Full virtual-row dimensions must match the plan.')
    token = FullVirtualToken(plan, len(target), [], [], parity_before, parity_before)
    rows = list(zip(range(plan.first, plan.last), plan.shifts))
    for _, shift, sign in _row_controls(digits, rows):
        seed = _row_seed(token.parity_after, len(source), shift)
        token.row_parities.append(seed)
        token.row_debts.append(forward_virtual_row(builder, source, target,
            shift=shift, sign=sign, initial_lsb=seed))
        token.parity_after ^= row_parity_mask(len(source), shift)
    return token


def inverse_full_virtual_rows(builder, digits, source, target, token, *,
                              carry_budget=None, overflow_phase=None,
                              allow_dirty_overflow=False):
    """Undo a whole-word virtual row group, repaying its measured carries."""
    source, target = list(source), list(target)
    if token.consumed or len(target) != token.width:
        raise ValueError('Missing matching, unconsumed full virtual-row token.')
    if _digit_count(digits) != token.plan.digits:
        raise ValueError('Digit count differs from the matching forward rows.')
    token.consumed = True
    rows = list(reversed(list(zip(range(token.plan.first, token.plan.last),
                                  token.plan.shifts))))
    for index, shift, sign in _row_controls(digits, rows):
        offset = index-token.plan.first
        inverse_virtual_row(builder, source, target, token.row_debts[offset],
            shift=shift, sign=sign, initial_lsb=token.row_parities[offset],
            carry_budget=carry_budget, overflow_phase=overflow_phase,
            allow_dirty_overflow=allow_dirty_overflow)


def reconstruct_top(builder, saved_original, current_top, sign):
    """Allocate the omitted result top bit using one AND and affine gates."""
    if len({saved_original, current_top, sign}) != 3:
        raise ValueError('Top reconstruction requires three distinct source wires.')
    top = builder.alloc_qubits(1)[0]
    builder.cx(sign, saved_original)
    builder.cx(sign, current_top)
    builder.ccx(saved_original, current_top, top)
    builder.cx(sign, current_top)
    builder.cx(sign, saved_original)
    builder.cx(sign, top)
    builder.x(top)
    return top


def erase_reconstructed_top(builder, top, saved_original, current_top, sign):
    """Erase the temporary top exactly for both X-measurement outcomes.

    Undoing the affine part first leaves the pure AND.  Measuring that AND
    contributes (-1)**(m*(a XOR sign)*(b XOR sign)); the conditioned CZ in
    del_and applies the same sign, including all affine framing effects.
    """
    builder.x(top)
    builder.cx(sign, top)
    builder.cx(sign, saved_original)
    builder.cx(sign, current_top)
    builder.del_and(saved_original, current_top, top)
    builder.free(top)
    builder.cx(sign, current_top)
    builder.cx(sign, saved_original)
