# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Bounded Horner rows whose low and high words need not coexist with C.

The source is required only for the low rows. After those rows, it can be
erased and the high target word decoded into the same physical storage.
The high correction uses the saved old low MSB, the new low MSB, and the
sign of the bounded update. Its inverse can run before restoring the source.

The optional digit-provider interface accepts PackedShift directly. Inactive
rows are removed before asking for a logical digit, so mathematically zero
rows never allocate packed-control helpers.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from itertools import groupby

import kickmix as km
from paired_arithmetic import (
    CarryDebt, _row_inputs, _deferred_overflow,
    forward_signed_row, inverse_signed_row,
    release_saved_bit, repay_saved_bit,
)


@contextmanager
def _digit(provider, index):
    if hasattr(provider, "digit"):
        with provider.digit(index) as wire:
            yield wire
    else:
        yield provider[index]


def _digit_count(provider):
    return len(provider.residual) if hasattr(provider, "digit") else len(provider)


def _row_controls(provider, rows):
    """Borrow consecutive packed[2]/packed[3] controls with one shared u predicate."""
    for early, run in groupby(rows, key=lambda row: row[0] in (2,3)):
        run = list(run)
        share = (early and len(run) > 1 and hasattr(provider, "higher_nonzero")
                 and not getattr(provider, "compact_digits", False))
        context = provider.higher_nonzero() if share else nullcontext()
        with context:
            for index, amount in run:
                with _digit(provider, index) as control:
                    yield index, amount, control


@dataclass
class SplitBoundedToken:
    plan: object
    saved_bit: object
    window: int
    row_debts: list
    overflow_debt: object = None
    high_width: int | None = None
    stage: str = "low_done"
    saved_measurement: object = None


def forward_bounded_low(builder, digits, source, low, plan, *, saved_bit=None):
    """Compute all low rows and retain their original top bit and phase debts.

    `low` must have exactly the certified signed-window width. Its initial
    value is arbitrary. It is updated modulo that width. The source and all
    logical digits are preserved. Call forward_bounded_high when the high
    target word has become available.

    If `saved_bit` is supplied, it must already contain an exact copy of
    the original low MSB. Otherwise this function allocates and copies it.
    """
    low, source = list(low), list(source)
    if _digit_count(digits) != plan.digits or len(low) != plan.window or not low:
        raise ValueError("Digit count and nonempty low width must match the bounded plan.")
    saved = saved_bit
    if saved is None:
        saved = builder.alloc_qubits(1)[0]
        builder.cx(low[-1], saved)
    elif not isinstance(saved, km.q) or saved in low+source:
        raise ValueError("An external saved bit must be a distinct quantum wire.")
    token = SplitBoundedToken(plan, saved, len(low), [None]*(plan.last-plan.first))
    rows = []
    for index, amount in zip(range(plan.first, plan.last), plan.shifts):
        _, active, _ = _row_inputs(source, low, shift=amount, nearest=True,
                                    signed_source=plan.signed_source)
        if not active:
            token.row_debts[index-plan.first] = CarryDebt({}, 0)
            continue
        rows.append((index,amount))
    for index, amount, control in _row_controls(digits, rows):
        token.row_debts[index-plan.first] = forward_signed_row(
            builder, source, low, shift=amount, sign=control,
            signed_source=plan.signed_source)
    return token


def _high(builder, digits, low, high, token, *, inverse, source_sign,
            carry_budget, overflow_phase=None, allow_dirty_overflow=False):
    low, high = list(low), list(high)
    if len(low) != token.window or not high:
        raise ValueError("The low width must match its token, and high must be nonempty.")
    if token.saved_bit is None:
        raise ValueError("The original low MSB must be available for the high correction.")
    if token.plan.signed_source:
        if not isinstance(source_sign, km.q):
            raise ValueError("A signed-source block needs its preserved sign wire.")
        source = [source_sign]
    else:
        if source_sign is not False:
            raise ValueError("An unsigned-source block has constant zero source sign.")
        source = []
    if _digit_count(digits) != token.plan.digits:
        raise ValueError("Digit count does not match the bounded plan.")
    with _digit(digits, token.plan.last-1) as control:
        # The overflow kernel consults only the group's last logical digit.
        controls = [False]*token.plan.digits
        controls[token.plan.last-1] = control
        _deferred_overflow(builder, controls, source, low+high, token,
                           inverse=inverse, carry_budget=carry_budget,
                           overflow_phase=overflow_phase,allow_dirty_overflow=allow_dirty_overflow)


def forward_bounded_high(builder, digits, low, high, token, *, source_sign=False):
    """Apply the single high-word correction without requiring the source word."""
    if token.stage != "low_done":
        raise ValueError("Forward high correction must follow the low rows exactly once.")
    _high(builder, digits, low, high, token, inverse=False,
          source_sign=source_sign, carry_budget=None)
    token.high_width = len(high)
    token.stage = "high_done"


def inverse_bounded_high(builder, digits, low, high, token, *, source_sign=False,
                          carry_budget=None, release_saved=True,
                          overflow_phase=None, allow_dirty_overflow=False):
    """Undo high correction, optionally releasing the saved low bit immediately.

    A caller may previously measure/free the saved bit into its table-phase
    ledger and reload its identical logical value into a new wire. Assign
    that new wire to token.saved_bit before this call. The table ledger's
    phase repayment remains the caller's responsibility.
    """
    if token.stage != "high_done" or len(high) != token.high_width:
        raise ValueError("Inverse high correction must match the completed forward one.")
    _high(builder, digits, low, high, token, inverse=True,
          source_sign=source_sign, carry_budget=carry_budget,
          overflow_phase=overflow_phase,allow_dirty_overflow=allow_dirty_overflow)
    token.stage = "high_undone"
    if release_saved:
        token.saved_measurement = release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None


def inverse_bounded_low(builder, digits, source, low, token, *, carry_budget=None):
    """Reverse low rows and repay their carries plus the saved-MSB measurement."""
    low, source = list(low), list(source)
    if token.stage != "high_undone" or len(low) != token.window:
        raise ValueError("Inverse low rows must follow the matching inverse high correction.")
    if _digit_count(digits) != token.plan.digits:
        raise ValueError("Digit count does not match the bounded plan.")
    if token.saved_bit is not None:
        token.saved_measurement = release_saved_bit(builder, token.saved_bit)
        token.saved_bit = None
    rows = []
    for offset in reversed(range(token.plan.last-token.plan.first)):
        index = token.plan.first+offset
        amount = token.plan.shifts[offset]
        debt = token.row_debts[offset]
        _, active, _ = _row_inputs(source, low, shift=amount, nearest=True,
                                    signed_source=token.plan.signed_source)
        if not active:
            if debt.width or debt.measurements or debt.consumed:
                raise ValueError("Inactive row does not match its forward debt.")
            debt.consumed = True
            continue
        rows.append((index,amount))
    for index, amount, control in _row_controls(digits, rows):
        inverse_signed_row(builder, source, low, token.row_debts[index-token.plan.first],
                            shift=amount, sign=control,
                            signed_source=token.plan.signed_source,
                            carry_budget=carry_budget)
    if token.saved_measurement is None:
        raise ValueError("Missing saved-MSB phase record.")
    repay_saved_bit(builder, low[-1], token.saved_measurement)
    token.saved_measurement = None
    token.stage = "consumed"
