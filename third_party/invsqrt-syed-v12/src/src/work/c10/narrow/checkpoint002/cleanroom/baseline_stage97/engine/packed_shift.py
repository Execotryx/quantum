# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Store k<=10 in normalized residual zeros and one external quantum bit.

The valid domain is k in [0,max_k], max_k<=10, with the residual's low
min(2*k,4) bits zero.  Normalization provides the stronger condition that
all low 2*k input bits are zero.  This module consumes no compiled circuit.

Packing and logical-digit helpers may retain explicitly recorded measurement
phase debts.  `unpack()` reconstructs the binary flags and repays every debt
for every outcome.  All intervening uses must preserve the packed residual
and the represented k, apart from exact temporary changes that are restored.
"""
from __future__ import annotations

from contextlib import contextmanager
import kickmix as km
from fusion.normalization import ShiftFlags


def _or_into(builder, a, b, target):
    builder.cx(a, target)
    builder.cx(b, target)
    builder.ccx(a, b, target)


def _erase_or(builder, a, b, target):
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(target, outcome)
    builder.push_condition(outcome)
    builder.z(a)
    builder.z(b)
    builder.cz(a, b)
    builder.pop_condition()
    builder.free(outcome)
    builder.free(target)


def _compute_u_from_flags(builder, flags):
    """u = f1 OR f2 OR f3 on k<=10, using one shared product."""
    _, f1, f2, f3 = flags
    u = builder.alloc_qubits(1)[0]
    for flag in (f1, f2, f3):
        builder.cx(flag, u)
    builder.cx(f2, f3)
    builder.ccx(f1, f3, u)
    builder.cx(f2, f3)
    return u


def _phase_u(builder, flags, outcome):
    _, f1, f2, f3 = flags
    builder.push_condition(outcome)
    for flag in (f1, f2, f3):
        builder.z(flag)
    builder.cz(f1, f2)
    builder.cz(f1, f3)
    builder.pop_condition()


def _erase_u_from_flags(builder, flags, u, pending=()):
    """Repay this u measurement and any earlier debts for the same k."""
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(u, outcome)
    builder.free(u)
    for earlier in pending:
        builder.cx(earlier, outcome)
        builder.free(earlier)
    _phase_u(builder, flags, outcome)
    builder.free(outcome)


def _erase_t_from_flags(builder, flags, t):
    """Exact OR-of-flags phase on k<=10: five CZs and one conditioned CCZ."""
    outcome = builder.alloc_bits(1)[0]
    builder.hmr(t, outcome)
    builder.free(t)
    builder.push_condition(outcome)
    for flag in flags:
        builder.z(flag)
    for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3)):
        builder.cz(flags[i], flags[j])
    builder.ccz(flags[0], flags[1], flags[2])
    builder.pop_condition()
    builder.free(outcome)


class PackedShift:
    """A reversible shift register with three fewer persistent qubits.

    Start with four allocated binary flag wires and a normalized residual:

        shift = PackedShift(builder, residual, flags)
        shift.pack()
        with shift.digit(i) as logical_digit:
            ...  # Preserve the digit; use it as an arithmetic control.
        with shift.unpacked() as ordinary_flags:
            ...  # Optional phase pass; preserve flags and residual.
        final_flags = shift.unpack()

    The last line leaves no pending measurement phases.  `ordinary_flags`
    and `final_flags` are ShiftFlags lists with max_k preserved.  The context
    manager repacks after its body and records the new flag measurements.

    While packed, indices0/1 need one temporary logical digit. Indices2/3
    need one temporary u indicator plus one digit; their OR helper is freed
    before entering the body. Indices>=4 use the residual wire directly.
    A `higher_nonzero()` context can share u across multiple digit contexts.
    """

    def __init__(self, builder, residual, flags, *, max_k=None):
        self.builder = builder
        self.residual = list(residual)
        given_max = getattr(flags, "max_k", None)
        self.max_k = given_max if max_k is None and given_max is not None else (
            10 if max_k is None else int(max_k))
        self._flags = list(flags)
        if len(self._flags) != 4 or len(self.residual) < 4:
            raise ValueError("PackedShift requires four binary flags and at least four residual bits.")
        if not 0 <= self.max_k <= 10:
            raise ValueError("This certified packing supports only k<=10.")
        if len(set(self.residual+self._flags)) != len(self.residual)+4:
            raise ValueError("Residual and shift flags must use disjoint distinct wires.")
        self._t = None
        self._flag_debts = []
        self._u_debts = []
        self._cached_u = None
        self._active_digits = 0

    @property
    def is_packed(self):
        return self._t is not None

    @property
    def t(self):
        if not self.is_packed:
            raise ValueError("The external t indicator exists only while packed.")
        return self._t

    @property
    def flags(self):
        if self.is_packed:
            raise ValueError("Binary shift flags are not live while packed.")
        return ShiftFlags(self._flags, self.max_k)

    @property
    def pending_measurements(self):
        return len(self._flag_debts)+len(self._u_debts)

    def _require_no_borrowed_controls(self):
        if self._active_digits or self._cached_u is not None:
            raise ValueError("Finish logical-digit/u contexts before packing or unpacking.")

    def _xor_residual_code(self, flags, u, t):
        q0, q1, q2, q3 = self.residual[:4]
        f0, f1, f2, f3 = flags
        self.builder.cx(f1, q0)
        self.builder.cx(f2, q1)
        self.builder.cx(f3, q1)
        # f0*u = t XOR f0 XOR u because t=f0 OR u. Reuse that
        # product instead of emitting another Toffoli.
        self.builder.cx(t, q2)
        self.builder.cx(f0, q2)
        self.builder.cx(u, q2)
        self.builder.cx(f3, q3)

    def pack(self):
        """Encode flags into residual zeros; retain their exact phase ledger."""
        self._require_no_borrowed_controls()
        if self.is_packed:
            return self
        if self._flag_debts or self._u_debts:
            raise AssertionError("An unpacked register cannot have outstanding phase debts.")
        flags = self._flags
        u = _compute_u_from_flags(self.builder, flags)
        t = self.builder.alloc_qubits(1)[0]
        _or_into(self.builder, flags[0], u, t)
        self._xor_residual_code(flags, u, t)
        _erase_u_from_flags(self.builder, flags, u)
        outcomes = self.builder.alloc_bits(4)
        self.builder.hmr(km.array(flags), outcomes)
        self.builder.free(km.array(flags))
        self._flag_debts = list(outcomes)
        self._flags = None
        self._t = t
        return self

    def _compute_u_from_packed(self):
        q0, q1 = self.residual[:2]
        either = self.builder.alloc_qubits(1)[0]
        _or_into(self.builder, q0, q1, either)
        u = self.builder.alloc_qubits(1)[0]
        self.builder.ccx(self._t, either, u)
        _erase_or(self.builder, q0, q1, either)
        return u

    def unpack(self):
        """Restore binary flags and the original residual; repay every phase."""
        self._require_no_borrowed_controls()
        if not self.is_packed:
            return self.flags
        q0, q1, q2, q3 = self.residual[:4]
        t = self._t
        u = self._compute_u_from_packed()
        flags = list(self.builder.alloc_qubits(4))
        f0, f1, f2, f3 = flags
        self.builder.ccx(t, q0, f1)
        self.builder.ccx(u, q3, f3)
        self.builder.cx(q3, q1)
        self.builder.ccx(u, q1, f2)
        self.builder.cx(q3, q1)
        self.builder.cx(t, f0)
        self.builder.cx(u, f0)
        self.builder.ccx(u, q2, f0)
        self._xor_residual_code(flags, u, t)
        _erase_u_from_flags(self.builder, flags, u, self._u_debts)
        self._u_debts.clear()
        _erase_t_from_flags(self.builder, flags, t)
        for flag, outcome in zip(flags, self._flag_debts):
            self.builder.push_condition(outcome)
            self.builder.z(flag)
            self.builder.pop_condition()
            self.builder.free(outcome)
        self._flag_debts.clear()
        self._flags = flags
        self._t = None
        return self.flags

    @contextmanager
    def unpacked(self):
        """Temporarily materialize binary flags, then repack with a new ledger."""
        was_packed = self.is_packed
        flags = self.unpack()
        try:
            yield flags
        finally:
            if was_packed:
                self.pack()

    @contextmanager
    def higher_nonzero(self):
        """Temporarily expose u=[k>=2], sharing it across nested digit uses."""
        if self._cached_u is not None:
            yield self._cached_u
            return
        if self.is_packed:
            u = self._compute_u_from_packed()
        else:
            u = _compute_u_from_flags(self.builder, self._flags)
        self._cached_u = u
        try:
            yield u
        finally:
            self._cached_u = None
            if self.is_packed:
                # This is a function solely of the same logical k. Defer
                # its sign to unpack, where u has the quadratic flag form.
                outcome = self.builder.alloc_bits(1)[0]
                self.builder.hmr(u, outcome)
                self.builder.free(u)
                self._u_debts.append(outcome)
            else:
                _erase_u_from_flags(self.builder, self._flags, u)

    @contextmanager
    def _masked_digit(self, index, mask):
        digit = self.builder.alloc_qubits(1)[0]
        self.builder.x(mask)
        self.builder.ccx(mask, self.residual[index], digit)
        self.builder.x(mask)
        try:
            yield digit
        finally:
            self.builder.x(mask)
            self.builder.del_and(mask, self.residual[index], digit)
            self.builder.x(mask)
            self.builder.free(digit)

    @contextmanager
    def digit(self, index):
        """Expose the original normalized residual bit, with exact cleanup."""
        if not 0 <= index < len(self.residual):
            raise IndexError(index)
        self._active_digits += 1
        try:
            if not self.is_packed or index >= 4:
                yield self.residual[index]
            elif index < 2:
                with self._masked_digit(index, self._t) as digit:
                    yield digit
            else:
                with self.higher_nonzero() as u:
                    with self._masked_digit(index, u) as digit:
                        yield digit
        finally:
            self._active_digits -= 1
