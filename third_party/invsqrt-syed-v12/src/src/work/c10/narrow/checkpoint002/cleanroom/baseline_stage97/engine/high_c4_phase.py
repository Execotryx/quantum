# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""An isolated joint-C4 replacement for the selected eight-bit high route.

The four-state controlled permutation is synthesized from cyclic rotations,
not loaded from a gate file or saved search result. The existing tail43 phase
features, threshold provider and early-H ownership hook are left unchanged.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction
import merged_phase
from cyclic_phase import _erase_polynomial, _pow2, rotation_pairs
from quadratic_terms import compile_polynomial, xor_polynomial
from c4_routing_math import c4_synthesis, flag_terms


@contextmanager
def linear_flags(builder, packed, u, masks, *, omit_repayment=False):
    """Compute at most two linear functions of k, then repay every HMR sign.

    The nonlinear part of each exact packed formula has common factor u;
    therefore one AND suffices. Its erasure is only Z/CZ, for all64 values of
    packed[0]..packed[3],t,u, including values outside the packed promise.
    """
    masks = tuple(map(int, masks))
    if not 1 <= len(masks) <= 2 or len(set(masks)) != len(masks):
        raise ValueError('This route holds one or two distinct linear flags.')
    variables = list(packed.residual[:4])+[packed.t, u]
    if len(set(variables)) != 6:
        raise ValueError('The six packed variables must be distinct.')
    if builder.max_qubits-builder.num_allocated_qubits < len(masks):
        raise ValueError('The joint route lacks its declared two-flag workspace.')
    words = []
    for mask in masks:
        terms = flag_terms(mask)
        plan = compile_polynomial(6, terms)
        if len(plan.products) != 1 or any(term.bit_count() > 2 for term in terms):
            raise AssertionError('A linear shift flag ceased to be one quadratic product.')
        target = builder.alloc_qubits(1)[0]
        xor_polynomial(builder, variables, target, terms)
        words.append((target, terms))
    try:
        yield tuple(wire for wire, _ in words)
    finally:
        for wire, terms in reversed(words):
            if omit_repayment:
                # Deliberately incorrect, available only to falsify the proof.
                outcome = builder.alloc_bits(1)[0]
                builder.hmr(wire, outcome)
                builder.free(outcome)
                builder.free(wire)
            else:
                _erase_polynomial(builder, wire, variables, terms)


def route_high(builder, value, packed, u, *, inverse=False, omit_repayment=False):
    """Rotate high8 by k mod8 with15 CSWAPs and three temporary ANDs."""
    value = list(value)
    if len(value) != 8 or len(set(value)) != 8:
        raise ValueError('The selected joint route requires exactly eight distinct value wires.')
    path, synthesis = c4_synthesis()
    if len(path) != 4:
        raise AssertionError('The deterministic C4 synthesis changed its complete length.')

    def even_route():
        with linear_flags(builder, packed, u, (2, 4),
                          omit_repayment=omit_repayment) as (a, b):
            for action in reversed(path) if inverse else path:
                mask = int(action['control_mask'])
                if mask == 1:
                    control = a
                elif mask == 2:
                    control = b
                elif mask == 3:
                    builder.cx(a, b)
                    control = b
                else:
                    raise AssertionError('The C4 search returned a non-linear control.')
                left, right = action['swap']
                # The two parity classes are independent C4 cycles.
                for offset in (0, 1):
                    builder.cswap(control, value[offset+2*left], value[offset+2*right])
                if mask == 3:
                    builder.cx(a, b)

    def odd_route():
        pairs = rotation_pairs(8, 1)
        if len(pairs) != 7:
            raise AssertionError('The one-step eight-cycle decomposition changed.')
        with linear_flags(builder, packed, u, (1,),
                          omit_repayment=omit_repayment) as (odd,):
            for left, right in reversed(pairs) if inverse else pairs:
                builder.cswap(odd, value[left], value[right])

    if inverse:
        odd_route(); even_route()
    else:
        even_route(); odd_route()
    return dict(cswaps=15, and_products=3, maximum_live_flags=2,
                inverse=bool(inverse), mathematical_synthesis=synthesis)


def high_phase_c4(builder, value, packed, fractional_bits, *, beta=1,
                  turn_offsets=None, complement_overflow=False,
                  or_features=None, skip_overflow=(), tail_bits=None,
                  tail_first_removed=None, omit_flag_repayment=False):
    """Emit the unchanged selected tail43 high feature family with C4 routing.

    This deliberately accepts only the proved high8/F18/complement/tail18
    geometry. It resolves merged_phase._threshold at call time so that the
    existing early-H hook retains g9 and the threshold ledger owns every
    compact erasure exactly as in production.
    """
    value = list(value)
    if (len(value) != 8 or fractional_bits != 18 or Fraction(beta) != 1
            or not complement_overflow or or_features or tuple(skip_overflow)
            or tail_first_removed != 8 or sorted(tail_bits or {}) != [18]):
        raise ValueError('Only the selected tail43 high8/F18 geometry is certified here.')
    if not packed.is_packed or packed.max_k != 10:
        raise ValueError('The high route requires the existing packed k in0..10 promise.')
    if len(set(value+list(packed.residual)+[packed.t])) != 8+len(packed.residual)+1:
        raise ValueError('The high word and packed shift must have distinct physical ownership.')
    offsets = [Fraction(0)]*18 if turn_offsets is None else list(map(Fraction, turn_offsets))
    if len(offsets) != 18:
        raise ValueError('The selected high phase has exactly18 ordered features.')
    tail18 = tail_bits[18]
    if tail18 in value or tail18 in packed.residual or tail18 == packed.t:
        raise ValueError('The borrowed tail bit must be outside the high/packed words.')
    base = [_pow2(i-17) for i in range(8)]
    overflow = [255*_pow2(j-17) for j in range(10)]
    for j, angle in enumerate(overflow):
        base[j % 8] += angle
    angles, records = [], []
    products = conditional = 0
    with packed.higher_nonzero() as u:
        forward = route_high(builder, value, packed, u,
                             omit_repayment=omit_flag_repayment)
        products += forward['and_products']
        for i, wire in enumerate(value):
            angle = base[i]+2*offsets[i]
            builder.z_pow(wire, angle)
            angles.append(angle); records.append(('base', i))
        for j in range(10):
            with merged_phase._threshold(builder, packed, u, j+1) as (control, cost, ccz):
                products += cost; conditional += ccz
                angle = -overflow[j]+2*offsets[8+j]
                if j == 9:
                    merged_phase._mux_phase(builder, value[1], tail18, control, angle)
                    builder.cz(control, tail18)
                else:
                    builder.x(control)
                    temporary = builder.alloc_qubits(1)[0]
                    builder.ccx(control, value[j % 8], temporary)
                    builder.z_pow(temporary, angle)
                    builder.del_and(control, value[j % 8], temporary)
                    builder.free(temporary)
                    builder.x(control)
                products += 1
                angles.append(angle); records.append(('overflow', j))
        backward = route_high(builder, value, packed, u, inverse=True,
                              omit_repayment=omit_flag_repayment)
        products += backward['and_products']
    return dict(width=8, max_k=10, direct_packed=True, complement_overflow=True,
        cswaps=forward['cswaps']+backward['cswaps'], and_products=products+2,
        hmr_conditioned_ccz=conditional,
        expected_toffolis=forward['cswaps']+backward['cswaps']+products+2+conditional/2,
        z_pow_calls=len(angles), half_turn_angles=list(map(str, angles)),
        turn_offsets=list(map(str, offsets)), or_features={}, skipped_overflow=[],
        feature_order=records, tail_first_removed=8, tail_bits=[18],
        joint_c4_high=True, routing_math=forward['mathematical_synthesis'],
        maximum_live_route_flags=2, negative_control_omits_flag_repayment=bool(omit_flag_repayment))


@contextmanager
def install_high_c4(*, omit_flag_repayment=False):
    """Isolated fixture adapter; no frozen module on disk is modified."""
    previous = merged_phase.merged_packed_cyclic_scale_phase
    if previous is high_phase_c4:
        raise ValueError('The C4 fixture adapter is already installed.')

    def emit(*args, **kwargs):
        return high_phase_c4(*args, **kwargs,
                             omit_flag_repayment=omit_flag_repayment)
    merged_phase.merged_packed_cyclic_scale_phase = emit
    try:
        yield
    finally:
        merged_phase.merged_packed_cyclic_scale_phase = previous
