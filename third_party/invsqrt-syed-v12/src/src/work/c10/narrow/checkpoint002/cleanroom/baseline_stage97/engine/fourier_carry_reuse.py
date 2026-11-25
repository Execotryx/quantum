# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Reuse a conditionally computed Fourier carry for its simultaneous S phase.

When the odd suffix outcome is one, the existing signed-T correction already
computes the majority into a temporary wire.  In that branch its signed-S
correction is S^-1(carry) CZ(sign, carry), which costs no T gates.  The original
four-T majority formula is needed only when twice is one and odd is zero.

The public installation scope changes only this local phase-repayment helper.
All adders, carry ownership, measurements, and constant terms remain exact.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction

import fourier_suffix_inverse as original
from fusion.arithmetic import _compute_carry, _erase_carry
from fusion.compiler import MAJORITY_TRUTH, phase_quadratic


def repay_signed_carry(builder, a, b, incoming, sign, suffix):
    """Apply the original signed Fourier carry phase with a shared majority."""
    three = isinstance(suffix, original.FourierSuffixDebt3)
    builder.push_condition(suffix.four_times if three else suffix.twice)
    phase_quadratic(builder, [a, b, incoming], MAJORITY_TRUTH)
    builder.pop_condition()
    if not three:
        builder.push_condition(suffix.odd)
        original.signed_s_majority(builder, sign, a, b, incoming)
        builder.pop_condition()
        return

    # The two S implementations occupy disjoint classical branches.  Restore
    # the odd outcome before any other owner can read or release it.
    builder.x(suffix.odd)
    builder.push_condition(suffix.odd)
    builder.push_condition(suffix.twice)
    original.signed_s_majority(builder, sign, a, b, incoming)
    builder.pop_condition()
    builder.pop_condition()
    builder.x(suffix.odd)

    builder.push_condition(suffix.odd)
    frame = _compute_carry(builder, a, b, incoming)
    if frame.outgoing is not False:
        builder.z_pow(sign, Fraction(1, 4))
        builder.cx(frame.outgoing, sign)
        builder.z_pow(sign, Fraction(-1, 4))
        builder.cx(frame.outgoing, sign)
        builder.push_condition(suffix.twice)
        builder.z_pow(frame.outgoing, Fraction(-1, 2))
        builder.cz(sign, frame.outgoing)
        builder.pop_condition()
    _erase_carry(builder, frame, write_sum=False)
    builder.pop_condition()


@contextmanager
def installed():
    """Install the exact carry reuse for one source-emission scope."""
    previous = original.repay_signed_carry
    if previous is repay_signed_carry:
        raise RuntimeError('Fourier carry reuse is already installed.')
    original.repay_signed_carry = repay_signed_carry
    try:
        yield
    finally:
        original.repay_signed_carry = previous
