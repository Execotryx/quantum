# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Reversible normalization derived from zero tests and controlled shifts.

No circuit input or gate template is read by this module.  For an input of
width 2*n_p+2 the output is in [2**(width-2), 2**width).  The four flags for
n_p=10 encode the number of zero pairs, rather than its unary expansion.
"""
from __future__ import annotations
import kickmix as km


def zero_flag(builder, data, flag, *, inverse=False):
    """Create/erase flag = AND_i NOT data[i], with exact X-measurement repair."""
    data = list(data)
    if not data:
        builder.x(flag)
        return
    builder.x(km.array(data))
    if len(data) == 1:
        builder.cx(data[0], flag)
    else:
        scratch = list(builder.alloc_qubits(max(0, len(data)-2)))
        left = data[0]
        steps = []
        for q, target in zip(data[1:-1], scratch):
            builder.ccx(left, q, target)
            steps.append((left, q, target))
            left = target
        if inverse:
            builder.del_and(left, data[-1], flag)
        else:
            builder.ccx(left, data[-1], flag)
        for a, b, c in reversed(steps):
            builder.del_and(a, b, c)
        builder.free(km.array(scratch))
    builder.x(km.array(data))


def normalize(builder, x, flags, *, inverse=False):
    """x *= 4**k with a binary k in flags; undo if inverse.

    For each power-of-two pair count, test the top 2*count bits and shift
    only when they are all zero.  Descending swaps implement a left shift
    because the target range is zero in the enabled branch.  The opposite
    order restores the input exactly.  Tests are erased only AFTER restoration.
    """
    indices = list(reversed(range(len(flags))))
    if inverse:
        indices.reverse()
    for j in indices:
        shift = 2 << j
        if shift >= len(x):
            continue
        flag = flags[j]
        pairs = [(x[i], x[i-shift]) for i in range(len(x)-1, shift-1, -1)]
        if inverse:
            for a, b in reversed(pairs):
                builder.cswap(flag, a, b)
            zero_flag(builder, x[-shift:], flag, inverse=True)
        else:
            zero_flag(builder, x[-shift:], flag)
            for a, b in pairs:
                builder.cswap(flag, a, b)


def semilog_align(builder, x, *, inverse=False):
    """Turn a normalized word into 8-bit semi-log index and 14-bit residual.

    Low-half inputs have (top,second)=(0,1).  Removing that known leading
    one and shifting the remaining 21-bit lane left once gives the same
    residual scale as high-half inputs.  The branch bit stays at the top.
    This permutation is reversible on every normalized input.
    """
    branch = x[-1]
    builder.x(branch)
    if inverse:
        builder.right_rotate(x[:-1], 1, control=branch)
        builder.cx(branch, x[-2])
    else:
        builder.cx(branch, x[-2])
        builder.left_rotate(x[:-1], 1, control=branch)
    builder.x(branch)


def scale_phase(builder, value, flags, fractional_bits, *, signed=False, beta=1):
    """Apply beta*value*2**k/2**fractional_bits turns, preserving all wires.

    Pad to the largest POSSIBLE normalized shift (n_p, not 2**len(flags)-1).
    Controlled rotations on the padded word are shifts on the valid domain.
    Signed words are sign-extended first, and their final top bit has negative
    phase weight.  Padding is uncomputed and freed after the inverse shifts.
    """
    from fractions import Fraction
    value = list(value)
    # The caller stores the maximum reachable k on the optional list wrapper;
    # for benchmark width22 the exact maximum is10.
    max_k = getattr(flags, 'max_k', None)
    if max_k is None:
        max_k = (1 << len(flags)) - 1
    padding = list(builder.alloc_qubits(max_k))
    if signed:
        for q in padding:
            builder.cx(value[-1], q)
    word = km.array(value + padding)
    def clear_wrap(flag, amount):
        if not signed:
            return
        if builder.num_free_qubits < 1:
            for i in range(amount):
                builder.ccx(flag, word[-1], word[i])
            return
        helper = builder.alloc_qubits(1)
        builder.ccx(flag, word[-1], helper[0])
        for i in range(amount):
            builder.cx(helper[0], word[i])
        builder.del_and(flag, word[-1], helper[0])
        builder.free(helper)
    shifts = []
    for j in reversed(range(len(flags))):
        flag, amount = flags[j], 1 << j
        # If this flag is enabled, the earlier (larger) shifts can total at
        # most the largest multiple of 2*amount that still leaves room for
        # this shift in k <= max_k.  All higher bits are zero/sign padding.
        prior = ((max_k-amount) // (2*amount)) * (2*amount)
        length = len(value)+max(0, prior)
        pairs = [(word[i],word[i-amount]) for i in range(length+amount-1,amount-1,-1)]
        for a,b in pairs:
            builder.cswap(flag,a,b)
        clear_wrap(flag, amount)
        shifts.append((flag,amount,pairs))
    for i, q in enumerate(word):
        sign = -1 if signed and i == len(word)-1 else 1
        builder.z_pow(q, Fraction(beta) * sign * Fraction(2) ** (i-fractional_bits+1))
    for flag,amount,pairs in reversed(shifts):
        clear_wrap(flag,amount)
        for a,b in reversed(pairs):
            builder.cswap(flag,a,b)
    if signed:
        for q in padding:
            builder.cx(value[-1], q)
    builder.free(km.array(padding))


class ShiftFlags(list):
    """Wire list carrying a known mathematical range bound."""
    def __init__(self, wires, max_k):
        super().__init__(wires)
        self.max_k = max_k
