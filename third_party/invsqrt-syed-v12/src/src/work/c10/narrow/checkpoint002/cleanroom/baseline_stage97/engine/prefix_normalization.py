# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Pair normalization with one shared zero-prefix chain and exact flag cleanup.

For positive even-width input x, t_j=[the top 2*j bits are zero]. The binary
shift bit f_i is XOR(t_j for j divisible by 2**i). This compiles k directly
from the input and uses the usual binary controlled-swap shift network.

Inverse cleanup may measure f and pay its exact prefix phase. Branch
specialization depends only on the measured classical flags. Every branch
has a complete phase correction, including outcomes never seen in a seed.
"""
from __future__ import annotations

from contextlib import contextmanager
import kickmix as km


def _shape(x, flags):
    x, flags = list(x), list(flags)
    if len(x) < 4 or len(x) % 2:
        raise ValueError('Pair normalization expects an even input width of at least four.')
    maximum = (len(x)-2)//2
    if len(flags) != maximum.bit_length():
        raise ValueError('Binary flag width does not match the possible pair count.')
    if len(set(x+flags)) != len(x)+len(flags):
        raise ValueError('Input and flags must use distinct quantum wires.')
    return x, flags, maximum


@contextmanager
def _prefixes(builder, zero_bits, length, *, affine_first_pair=False):
    """Expose all prefix ANDs, with exact measured-AND cleanup on exit."""
    if not 1 <= length <= len(zero_bits):
        raise ValueError('Invalid zero-prefix length.')
    prefixes = {1:zero_bits[0]}
    steps = []
    for index in range(1,length):
        previous, bit = prefixes[index], zero_bits[index]
        target = builder.alloc_qubits(1)[0]
        affine = affine_first_pair and index == 1
        if affine:
            # For original top bits a*b=0, their complemented bits obey
            # (1-a)*(1-b) = 1 XOR (1-a) XOR (1-b).
            builder.x(target)
            builder.cx(previous,target)
            builder.cx(bit,target)
        else:
            builder.ccx(previous,bit,target)
        prefixes[index+1] = target
        steps.append((previous,bit,target,affine))
    try:
        yield prefixes
    finally:
        for previous,bit,target,affine in reversed(steps):
            if affine:
                builder.cx(bit,target)
                builder.cx(previous,target)
                builder.x(target)
            else:
                builder.del_and(previous,bit,target)
            builder.free(target)


def xor_pair_count(builder, x, flags, *, original_input_max=None):
    """XOR the mathematical pair count into flags, using 2*max_k-1 ANDs."""
    x, flags, maximum = _shape(x,flags)
    exclusive_top_pair = original_input_max is not None
    if exclusive_top_pair and not (
            isinstance(original_input_max,int)
            and 0 < original_input_max < 3*(1 << (len(x)-2))):
        raise ValueError('The original-input bound must exclude simultaneous top ones.')
    zero_bits = list(reversed(x[2:]))
    builder.x(km.array(zero_bits))
    with _prefixes(builder,zero_bits,len(zero_bits),
                   affine_first_pair=exclusive_top_pair) as prefixes:
        for bit,flag in enumerate(flags):
            for j in range(1 << bit,maximum+1,1 << bit):
                builder.cx(prefixes[2*j],flag)
    builder.x(km.array(zero_bits))


def _shift(builder,x,flags,*,inverse):
    indices = list(reversed(range(len(flags))))
    if inverse:
        indices.reverse()
    for bit in indices:
        distance = 2 << bit
        pairs = [(x[i],x[i-distance]) for i in range(len(x)-1,distance-1,-1)]
        if inverse:
            pairs.reverse()
        for left,right in pairs:
            builder.cswap(flags[bit],left,right)


def _selected_prefixes(pattern, maximum, flag_width):
    return tuple(j for j in range(1,maximum+1)
                 if sum(((pattern >> bit)&1) for bit in range(flag_width)
                        if j % (1 << bit) == 0)&1)


def _constant_prefix_phase(builder,zero_bits,selected):
    """Pay one fixed XOR of thermometer bits, omitting its final two ANDs."""
    if not selected:
        return
    last=selected[-1]
    if last==1:
        builder.cz(zero_bits[0],zero_bits[1])
        return
    length=2*last-2
    with _prefixes(builder,zero_bits,length) as prefixes:
        for j in selected[:-1]:
            builder.z(prefixes[2*j])
        builder.ccz(prefixes[length],zero_bits[length],zero_bits[length+1])


def erase_pair_count(builder,x,flags,*,branched=True):
    """Reset flags by HMR and repay their full phase on the restored input.

    With branched=True, every possible flag-measurement pattern has a
    separately certified prefix-phase circuit. With branched=False, one
    shared chain is computed unconditionally and its final sign is applied
    only when the appropriate parity of measured flags is one.
    """
    x,flags,maximum=_shape(x,flags)
    outcomes=list(builder.alloc_bits(len(flags)))
    for flag,outcome in zip(flags,outcomes):
        builder.hmr(flag,outcome)
    zero_bits=list(reversed(x[2:]))
    builder.x(km.array(zero_bits))
    if branched:
        for pattern in range(1 << len(flags)):
            selected=_selected_prefixes(pattern,maximum,len(flags))
            if not selected:
                continue
            zeros=[outcome for bit,outcome in enumerate(outcomes) if not (pattern >> bit)&1]
            for outcome in zeros:
                builder.x(outcome)
            for outcome in outcomes:
                builder.push_condition(outcome)
            _constant_prefix_phase(builder,zero_bits,selected)
            for _ in outcomes:
                builder.pop_condition()
            for outcome in zeros:
                builder.x(outcome)
    elif maximum==1:
        builder.push_condition(outcomes[0])
        builder.cz(zero_bits[0],zero_bits[1])
        builder.pop_condition()
    else:
        length=2*maximum-2
        with _prefixes(builder,zero_bits,length) as prefixes:
            for j in range(1,maximum):
                for bit,outcome in enumerate(outcomes):
                    if j % (1 << bit)==0:
                        builder.push_condition(outcome)
                        builder.z(prefixes[2*j])
                        builder.pop_condition()
            parity=builder.alloc_bits(1)[0]
            for bit,outcome in enumerate(outcomes):
                if maximum % (1 << bit)==0:
                    builder.cx(outcome,parity)
            builder.push_condition(parity)
            builder.ccz(prefixes[length],zero_bits[length],zero_bits[length+1])
            builder.pop_condition()
            builder.free(parity)
    builder.x(km.array(zero_bits))
    builder.free(km.array(outcomes))


def normalize(builder,x,flags,*,inverse=False,cleanup='branched',original_input_max=None):
    """Normalize positive x by pairs, or restore it and clear binary flags.

    cleanup='coherent' uses the same shared-chain XOR in each direction.
    cleanup='phase' uses the single-chain measured phase cleanup.
    cleanup='branched' specializes prefix cleanup to every outcome pattern.
    cleanup='thermometer' first changes the binary count into a minimal
    monomial/threshold basis, then measures the thresholds top-down.
    original_input_max is an explicit promise on the original input before
    the shift, or after restoration; it is never applied to normalized bits.
    """
    x,flags,_=_shape(x,flags)
    if cleanup not in ('coherent','phase','branched','thermometer'):
        raise ValueError('Unknown pair-count cleanup mode.')
    if inverse:
        _shift(builder,x,flags,inverse=True)
        if cleanup=='coherent':
            xor_pair_count(builder,x,flags,original_input_max=original_input_max)
        elif cleanup=='thermometer':
            from thermometer_cleanup import erase_pair_count_thermometer
            erase_pair_count_thermometer(builder,x,flags)
        else:
            erase_pair_count(builder,x,flags,branched=cleanup=='branched')
    else:
        xor_pair_count(builder,x,flags,original_input_max=original_input_max)
        _shift(builder,x,flags,inverse=False)
