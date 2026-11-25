# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Restore the original word through a complete raw leading-prefix frame.

The final packed decoder already retains all ten count monomials for k in
zero through ten.  Copying the semilog odd-leading-zero bit E and computing
E*T_j for ten count thresholds gives twenty-one independent functions of
ell=2*k+E.  A freshly derived invertible CNOT/SWAP frame turns those wires
into P_j=[ell>=j], without numerical or circuit inputs.

These prefixes clear the semilog branch, reverse the source-derived binary
butterfly, and reinsert the original leading one.  Prefixes are then measured
from longest to shortest.  P_j=P_(j-1)*(1-original_bit) repays each outcome
using only Z/CZ gates on its retained parent and the restored input bit.
The original four allocated flag wires finish at zero for their caller.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

import kickmix as km
from codebook import BinarySpan, bits, parity_function
from stage94_bit_routing_math import (
    operations, leading_indicator_terms, certificate as bit_route_certificate,
)
from thermometer_cleanup import linear_frame, thermometer_matrix


@lru_cache(maxsize=1)
def raw_prefix_frame():
    """Derive and certify the full twenty-one-function leading-prefix frame."""
    count_functions = [sum(int((leading//2) & mask == mask) << leading
                           for leading in range(22)) for mask in range(1, 11)]
    odd_function = sum((leading & 1) << leading for leading in range(22))
    mixed_functions = [sum(int((leading & 1) and leading//2 >= threshold) << leading
                           for leading in range(22)) for threshold in range(1, 11)]
    functions = count_functions+[odd_function]+mixed_functions
    span = BinarySpan(functions)
    if len(span.pivots) != 21 or any(function & 1 for function in functions):
        raise AssertionError('The full leading-function basis lost its zero-basepoint rank.')
    rows = []
    for length in range(1, 22):
        truth = sum(int(leading >= length) << leading for leading in range(22))
        expression = span.solve(truth)
        if expression is None or parity_function(expression, functions) != truth:
            raise AssertionError('A raw leading prefix has no exact retained-basis expression.')
        rows.append(expression)
    frame = tuple(linear_frame(rows))
    return dict(rows=tuple(rows), operations=frame,
                function_count=21, all_leading_zero_contexts=22,
                basis_rank=21, extra_ANDs=10,
                all_functions_zero_at_leading_count_zero=True,
                exact_threshold_truths_certified=True,
                invertible_linear_frame_certified=True)


@contextmanager
def _borrow_count_parity(builder, wires, expression):
    """Borrow a homogeneous count parity while preserving every source."""
    positions = list(bits(expression))
    if not positions:
        raise ValueError('A nonzero count threshold needs a nonempty parity.')
    pivot = wires[positions[0]]
    others = [wires[position] for position in positions[1:]]
    for source in others:
        builder.cx(source, pivot)
    try:
        yield pivot
    finally:
        for source in reversed(others):
            builder.cx(source, pivot)


@contextmanager
def _borrow_prefix_selector(builder, prefixes, terms):
    """Borrow a freshly derived zero-false butterfly selector parity."""
    terms = tuple(terms)
    if not terms or 0 in terms or any(not 1 <= term <= len(prefixes) for term in terms):
        raise ValueError('The selected butterfly requires a nonempty zero-false prefix selector.')
    if len(set(terms)) != len(terms):
        raise ValueError('A prefix selector cannot repeat a source wire.')
    pivot = prefixes[terms[0]-1]
    others = [prefixes[term-1] for term in terms[1:]]
    for source in others:
        builder.cx(source, pivot)
    try:
        yield pivot
    finally:
        for source in reversed(others):
            builder.cx(source, pivot)


def repay_prefix_phase(builder, outcome, wire_parent, data_bit):
    """Repay m*parent*(1-data_bit) for either X-measurement outcome."""
    builder.push_condition(outcome)
    builder.z(wire_parent)
    builder.cz(wire_parent, data_bit)
    builder.pop_condition()


def restore_with_bit_prefixes(builder, inputs, flags, late, certificate=None):
    """Consume the final monomial owner and restore the input with raw prefixes.

    Start at the existing aligned-word/final-unpack boundary.  The explicit
    inverse semilog call and the later thermometer-erasure call must be
    matched no-ops owned by the enclosing Stage94 normalization adapter.
    Every pending packed/threshold phase must have been paid before entry.
    """
    inputs, flags = list(inputs), list(flags)
    if certificate is None:
        certificate = bit_route_certificate(21)
    if len(inputs) != 22 or len(flags) != 4 or len(set(inputs+flags)) != 26:
        raise ValueError('Bit-prefix restoration requires the original input and flag geometry.')
    if (certificate.get('status') != 'EXACT_ZERO_SUPPORTED_BINARY_BUTTERFLY'
            or certificate.get('payload_width') != 21
            or certificate.get('controlled_swaps') != 42
            or not certificate.get('forward_and_inverse_proved')
            or certificate.get('virtual_nonzero_uses') != 0):
        raise AssertionError('The inverse butterfly lacks its fresh complete mathematical certificate.')
    key = id(builder), tuple(flags)
    prepared = late.prepared.pop(key, None)
    if prepared is None or list(prepared.flags) != flags:
        raise AssertionError('The bit-prefix inverse has no matched final monomial owner.')
    monomials = [prepared.monomials[mask] for mask in range(1, 11)]
    if (len(set(monomials)) != 10 or set(flags) - set(monomials)
            or set(monomials) & set(inputs)):
        raise AssertionError('The final count basis has an invalid quantum interface.')
    entry = builder.num_allocated_qubits
    auxiliary = list(builder.alloc_qubits(11))
    odd, products = auxiliary[0], auxiliary[1:]
    builder.x(odd)
    builder.cx(inputs[-1], odd)
    count_rows = thermometer_matrix(10)
    for expression, target in zip(count_rows, products):
        with _borrow_count_parity(builder, monomials, expression) as threshold:
            builder.ccx(odd, threshold, target)

    prefixes = monomials+[odd]+products
    frame = raw_prefix_frame()
    for operation, first, second in frame['operations']:
        if operation == 'cx':
            builder.cx(prefixes[first], prefixes[second])
        elif operation == 'swap':
            builder.swap(prefixes[first], prefixes[second])
        else:
            raise AssertionError('The exact prefix frame contains an unsupported linear operation.')

    # The branch is h=1 XOR E, and E is the parity of all raw thresholds.
    # Its original wire is the zero padding above the twenty-one-bit payload.
    builder.x(inputs[-1])
    for prefix in prefixes:
        builder.cx(prefix, inputs[-1])

    route = operations(21)
    swaps = 0
    for operation in reversed(route):
        with _borrow_prefix_selector(builder, prefixes, operation['prefix_terms']) as control:
            builder.cswap(control, inputs[operation['first']], inputs[operation['second']])
            swaps += 1
    if swaps != certificate['controlled_swaps']:
        raise AssertionError('The inverse payload emission differs from the certified butterfly.')

    for position, target in enumerate(inputs):
        for term in leading_indicator_terms(position, len(inputs)):
            if term == 0:
                builder.x(target)
            else:
                builder.cx(prefixes[term-1], target)

    for length in reversed(range(1, len(prefixes)+1)):
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(prefixes[length-1], outcome)
        data_bit = inputs[len(inputs)-length]
        if length == 1:
            # P_1=1 XOR original_highest.  Preserve its outcome-dependent
            # constant sign explicitly, as required for exact branch phases.
            builder.z(outcome)
            builder.push_condition(outcome)
            builder.z(data_bit)
            builder.pop_condition()
        else:
            repay_prefix_phase(builder, outcome, prefixes[length-2], data_bit)
        builder.free(outcome)

    retained_flags = set(flags)
    helpers = [wire for wire in prefixes if wire not in retained_flags]
    if len(helpers) != 17:
        raise AssertionError('The complete prefix basis must return seventeen helper wires.')
    builder.free(km.array(helpers))
    late.consumptions += 1
    if builder.num_allocated_qubits != entry-6:
        raise AssertionError('The inverse did not preserve exactly the four zeroed original flags.')
    return dict(status='RAW_BIT_PREFIX_INVERSE_COMPLETED',
                packed_decoder_ANDs_already_paid=9,
                new_mixed_prefix_basis_ANDs=10,
                inverse_payload_controlled_swaps=swaps,
                inverse_kernel_Toffoli_like=10+swaps,
                complete_restore_input_Toffoli_like=9+10+swaps,
                raw_prefix_measurements=21,
                conditional_prefix_CZ_repayments=20,
                explicit_first_prefix_global_phase=True,
                final_prefix_repayment_Toffoli_like=0,
                original_thermometer_repayment_not_repeated=True,
                full_prefix_frame=frame,
                added_quantum_wires=11,
                freed_helper_wires=17,
                original_four_flags_left_allocated_zero=True,
                final_count_owner_consumed_once=True,
                pending_new_measurement_owners=0,
                native_all_input_and_all_outcome_proof_required=True)
