# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Reuse the final C5 route's masked second bit for threshold four.

For encoded bits a,b,c,d, the existing threshold-four helper is
1 + b + a*b + b*d = 1 + b*(1+a+d).  The forward route already owns
v=u*b.  Keeping v until this threshold costs no new route product and lets
g4=u + v*(1+a+d) use one product instead of two.  Every route measurement
is repaid immediately.  The same threshold-four outcome belongs to the
same original threshold ledger; the shared-u owner is also unchanged.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction

import reencoded_c20_phase as original
from cyclic_phase import _pow2
from reencode_synthesis import synthesize
from threshold_phase_ledger import PackedThresholdPhasePass


ORIGINAL_LOW = original.low_phase_reencoded


def open_forward_c5(builder, value, packed, u, candidate, *, negative=None):
    """Emit the same swaps, retaining the already computed final plane."""
    operations = candidate['c5_network']
    spaces = [tuple(space) for space in candidate['C5_flag_schedule']['chosen_subspaces']]
    final_plane = tuple(sorted((1, 2, 1 ^ 2)))
    last_second_bit = max(index for index, space in enumerate(spaces) if 2 in space)
    if (spaces[last_second_bit] != final_plane or
            any(not set(space).issubset(final_plane) for space in spaces[last_second_bit:])):
        raise AssertionError('The selected C5 route no longer finishes in its certified retained-bit plane.')
    spaces[last_second_bit:] = [final_plane] * (len(spaces) - last_second_bit)
    flags = original.LinearFlagSpace(builder, list(packed.residual[:4]) + [packed.t, u],
        original.encoded_flag_terms, omit_repayment=negative == 'missing_route_repayment')
    swaps = 0
    for operation, space in zip(operations, spaces):
        flags.move_to(space)
        with flags.control(operation['control_mask']) as control:
            left, right = operation['swap']
            for cycle in range(4):
                a, b = (5 * cycle + 16 * left) % 20, (5 * cycle + 16 * right) % 20
                if not (negative == 'missing_route_swap' and swaps == 0):
                    builder.cswap(control, value[a], value[b])
                swaps += 1
    if flags.space != final_plane or swaps != 28 or flags.products != 4:
        raise AssertionError('Keeping the final flag changed the native C5 route budget.')
    return flags, swaps


@contextmanager
def handed_threshold_four(builder, packed, u, flags, plan, phase_pass, *, negative=None):
    """One new product; consume the retained route flag before phase AND."""
    expected = {0, 1 << 1, (1 << 0) | (1 << 1), (1 << 1) | (1 << 3)}
    if int(plan['threshold']) != 4 or set(plan['terms']) != expected:
        raise AssertionError('The source-derived threshold no longer has the certified factorization.')
    before = flags.products
    flags.move_to((2,))
    if flags.products != before or flags.masks != [2]:
        raise AssertionError('The threshold handoff recomputed its supposedly retained product.')
    q = list(packed.residual[:4])
    control = builder.alloc_qubits(1)[0]
    builder.cx(u, control)
    # Temporarily expose 1+a+d on d; restore it before measuring u*b.
    builder.cx(q[0], q[3])
    builder.x(q[3])
    builder.ccx(flags.wires[0], q[3], control)
    builder.x(q[3])
    builder.cx(q[0], q[3])
    if negative == 'missing_retained_flag_repayment':
        flags.omit_repayment = True
    flags.close()
    if flags.measurements != flags.products:
        raise AssertionError('The handoff left an unowned route measurement.')
    try:
        yield control
    finally:
        if negative == 'missing_threshold_ledger':
            outcome = builder.alloc_bits(1)[0]
            builder.hmr(control, outcome)
            builder.free(control)
            builder.free(outcome)
        else:
            phase_pass.ledger(packed).erase(builder, control, 4)


def _feature(builder, control, data, angle):
    temporary = builder.alloc_qubits(1)[0]
    builder.ccx(control, data, temporary)
    builder.z_pow(temporary, angle)
    builder.del_and(control, data, temporary)
    builder.free(temporary)


def low_phase_reencoded(builder, value, packed, fractional_bits, *, turn_offsets,
                        threshold, beta=1, negative=None):
    """The original 28 phase features with one less threshold product."""
    if negative not in (None, 'missing_route_repayment', 'missing_route_swap',
            'missing_threshold_helper_repayment', 'missing_threshold_ledger',
            'missing_encoding_Toffoli', 'missing_retained_flag_repayment'):
        raise ValueError('Unknown deliberately incorrect component-proof control.')
    value = list(value)
    offsets, beta = tuple(map(Fraction, turn_offsets)), Fraction(beta)
    if (len(value) != 20 or fractional_bits != 37 or len(offsets) != 30 or
            packed.max_k != 10 or not packed.is_packed):
        raise ValueError('Require the selected packed word20/F37/k0..10 geometry.')
    if len(set(value + list(packed.residual) + [packed.t])) != 21 + len(packed.residual):
        raise ValueError('Phase data and packed residual variables must be disjoint.')
    phase_pass = getattr(threshold, '__self__', None)
    if not isinstance(phase_pass, PackedThresholdPhasePass) or not phase_pass.merge_external_t:
        raise ValueError('Require the original bound threshold owner with merged external-t repayment.')
    import packed_phase
    unpack = type(packed).unpack
    closure = {name: cell.cell_contents for name, cell in
               zip(unpack.__code__.co_freevars, unpack.__closure__ or ())}
    if (getattr(packed_phase._threshold, '__self__', None) is not phase_pass or
            closure.get('self') is not phase_pass):
        raise ValueError('The bound threshold owner must own the installed unpack scope.')
    if packed._cached_u is not None:
        raise ValueError('The low kernel requires its original fresh shared-u lifecycle.')
    entry_live = builder.num_allocated_qubits
    if entry_live != 54 or builder.max_qubits != 57:
        raise ValueError('The selected handoff requires the established54-live/57-limit cut.')
    candidate, certificate = synthesize()
    q = list(packed.residual[:4])
    plans = {int(plan['threshold']): plan for plan in candidate['threshold_plans']}
    base_angles = [beta * _pow2(bit - fractional_bits + 1) + 2 * offsets[bit]
                   for bit in range(20)]
    overflow_angles = [beta * ((1 << 20) - 1) * _pow2(bit - fractional_bits + 1)
                       + 2 * offsets[20 + bit] for bit in range(8)]
    routes, encoding, threshold_products = [], [], 0
    with packed.higher_nonzero() as u:
        routes.append(original.emit_route(builder, value, packed, u, candidate,
                                           kind='c4', negative=negative))
        encoding.append(original.emit_encoding(builder, q, candidate['encode_program'],
                                                negative=negative == 'missing_encoding_Toffoli'))
        flags, swaps = open_forward_c5(builder, value, packed, u, candidate, negative=negative)
        for wire, angle in zip(value, base_angles):
            builder.z_pow(wire, angle)
        with handed_threshold_four(builder, packed, u, flags, plans[4], phase_pass,
                                   negative=negative) as control:
            _feature(builder, control, value[3], overflow_angles[3])
            threshold_products += 1
        routes.append(dict(kind='c5', inverse=False, cswaps=swaps,
            flag_products=flags.products, flag_measurements=flags.measurements,
            flag_transitions=flags.transitions, final_mask_reused_for_threshold=2))
        for bit in range(8):
            if bit == 3:
                continue
            with original.encoded_threshold(builder, packed, u, bit + 1,
                    plans.get(bit + 1), phase_pass, negative=negative) as (control, cost):
                threshold_products += cost
                _feature(builder, control, value[bit], overflow_angles[bit])
        routes.append(original.emit_route(builder, value, packed, u, candidate,
                                           kind='c5', inverse=True, negative=negative))
        encoding.append(original.emit_encoding(builder, q, candidate['encode_program'], inverse=True))
        routes.append(original.emit_route(builder, value, packed, u, candidate,
                                           kind='c4', inverse=True, negative=negative))
    swaps = sum(item['cswaps'] for item in routes)
    products = (sum(item['flag_products'] for item in routes) +
                sum(item['Toffolis'] for item in encoding) + threshold_products + 8 + 2)
    if threshold_products != 10 or swaps != 96 or products != 38:
        raise AssertionError('The handoff low kernel differs from134 E.')
    if builder.num_allocated_qubits != entry_live:
        raise AssertionError('The handoff changed the original low-phase allocation boundary.')
    return dict(width=20, max_k=10, reencoded_C20=True, cswaps=swaps, and_products=products,
        expected_toffolis=swaps + products, expected_extra_T=0, expected_generic_rotations=28,
        z_pow_calls=28, half_turn_angles=list(map(str, base_angles + overflow_angles)),
        turn_offsets=list(map(str, offsets)), skipped_overflow=[8, 9], route_controllers=routes,
        encoding=encoding, threshold_compute_ANDs=threshold_products, encoded_thresholds_deferred=6,
        shared_u_and_external_t_ledger_contract_preserved=True, source_synthesis=certificate,
        negative_control=negative, complete_generator_and_official_verification_pending=True,
        stage93_retained_threshold_handoff=dict(threshold=4, retained_encoded_linear_mask=2,
            identity='u*(1+b+b*a+b*d) = u + (u*b)*(1+a+d)',
            threshold_compute_ANDs_before=2, threshold_compute_ANDs_after=1,
            low_kernel_E_before=135, low_kernel_E_after=134,
            existing_route_products_unchanged=True, every_route_phase_repaid_immediately=True,
            external_threshold_owner_and_truth_unchanged=True, shared_u_owner_unchanged=True,
            no_table_measurement_owner_touched=True, numerical_angles_unchanged=True,
            entry_live=entry_live, peak_limit=57,
            live_cut_sequence=[54, 55, 57, 56, 57, 56, 57, 56, 55, 54],
            overflow_emission_order=[3] + [bit for bit in range(8) if bit != 3]))


@contextmanager
def installed(*, audit=None):
    """Install only the low-phase emitter at its existing dynamic-import hook."""
    previous = original.low_phase_reencoded
    if previous is not ORIGINAL_LOW:
        raise RuntimeError('Another low-phase replacement is active.')
    records = [] if audit is None else audit
    def emit(*args, **kwargs):
        metadata = low_phase_reencoded(*args, **kwargs)
        records.append(metadata['stage93_retained_threshold_handoff'])
        return metadata
    original.low_phase_reencoded = emit
    try:
        yield records
    finally:
        original.low_phase_reencoded = previous
