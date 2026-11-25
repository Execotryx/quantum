# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Emit a simultaneously factored, fixed-code inverse coefficient block.

Every quadratic and shared product is regenerated from the mathematical
coefficient truths.  Neither the earlier screen JSON nor a circuit file is
an input.  Search bounds are iteration counts; elapsed time never selects
a decomposition.  The original52-live cut and restored48-live cut match
the isolated early-low experiment, with a strictly frozen23-wire code.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

import kickmix as km
from codebook import (Codebook, emit_erase, emit_xor, factor_polynomial,
                      word_functions)
from simultaneous_quadratic import certify_truths, extract_shared, product_polynomial
from new_lookup_design import StaticCode, coefficient_delta
from r17_lookup import retire_low_bits
from split_lookup import live_word


SCALAR_SEED = 20261106200
SCALAR_TRIALS = 80
KERNEL_TRIALS = 15000
SHARING_SEED = 2026110641
FACTOR_TRIALS = 64
MAXIMUM_STEPS = 32
DELTA_BITS = (0, 1, 2, 3, 5)


def emit_shared_fanout(builder, variables, outputs, helper, left, right,
                       *, omit_repayment=False):
    """XOR one affine product into several outputs and clear its helper.

    The reset helper remains allocated for caller reuse.  For outcome m,
    HMR contributes (-1)^(m*p). emit_erase pays that identical polynomial
    using conditional Z/CZ, so every outcome has phase exactly+1.  The
    omit flag exists only for an independently falsifiable unit fixture.
    """
    variables, outputs = list(variables), list(outputs)
    if (len(set(variables)) != len(variables) or len(set(outputs)) != len(outputs)
            or set(variables) & set(outputs)
            or helper in set(variables)|set(outputs)):
        raise ValueError('The fixed code, output wires and reusable helper must be disjoint.')
    polynomial = product_polynomial(len(variables), left, right)
    if polynomial.and_count != 1:
        raise ValueError('A shared product must have exactly one nonlinear factor.')
    emit_xor(builder, variables, helper, polynomial)
    for target in outputs:
        builder.cx(helper, target)
    if omit_repayment:
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(helper, outcome)
        builder.free(outcome)
    else:
        emit_erase(builder, variables, [helper], [polynomial])
    return polynomial


def synthesize_fixed_block(functions, targets, *, progress=None):
    """Recompute and certify every target on the same23 physical inputs."""
    if len(functions) != 23 or len(targets) != 7:
        raise ValueError('This bounded inverse experiment expects23 coordinates and seven targets.')
    code = Codebook(functions)
    if len(code.span.pivots) != 256:
        raise AssertionError('The fixed input code lacks complete quadratic table coverage.')
    plans, scalar_records = [], []
    for index, target in enumerate(targets):
        plan = code.represent(target, trials=SCALAR_TRIALS, seed=SCALAR_SEED+index)
        alternative, kernel = code.represent_kernel(
            target, trials=KERNEL_TRIALS, seed=SCALAR_SEED+1000+index)
        if alternative is not None and alternative.and_count < plan.and_count:
            plan = alternative
        plans.append(plan)
        scalar_records.append(dict(output=index, and_count=plan.and_count,
                                   kernel_search=kernel, polynomial=asdict(plan)))
        if progress is not None:
            progress('fixed_form_certified', output=index, and_count=plan.and_count)
    certify_truths(functions, targets, plans, [])

    def sharing_progress(event):
        if progress is not None:
            fields = {key: value for key, value in event.items()
                      if key not in ('event', 'certificate_checkpoint')}
            progress(event['event'], **fields)

    residuals, sharing = extract_shared(
        functions, targets, plans, seed=SHARING_SEED, factor_trials=FACTOR_TRIALS,
        maximum_steps=MAXIMUM_STEPS, deadline=None, progress=sharing_progress)
    if sharing['stop_reason'] == 'soft_deadline':
        raise AssertionError('Elapsed time may not select this deterministic circuit.')
    certificate = certify_truths(functions, targets, residuals, sharing['steps'])
    plan_record = dict(fixed_inputs=[hex(f) for f in functions], targets=[hex(f) for f in targets],
                       shared_products=sharing['steps'],
                       residual_polynomials=[asdict(plan) for plan in residuals])
    canonical = json.dumps(plan_record, sort_keys=True, separators=(',', ':')).encode()
    return residuals, dict(sharing, scalar_forms=scalar_records,
        parameters=dict(scalar_seed=SCALAR_SEED, scalar_trials=SCALAR_TRIALS,
                        kernel_trials=KERNEL_TRIALS, sharing_seed=SHARING_SEED,
                        factor_trials=FACTOR_TRIALS, maximum_steps=MAXIMUM_STEPS,
                        elapsed_time_selection=False),
        full_truth_certificate=certificate, plan_sha256=hashlib.sha256(canonical).hexdigest(),
        plan_record=plan_record, generator_read_saved_plan=False)


def reverse_joint_quadratic(builder, data, high, low, saved_outer, debts, *, progress=None,
                            fourier_debt=None):
    """Return C8, inner and L14 after exact simultaneous fixed-code decoding."""
    removed=0 if fourier_debt is None else fourier_debt.removed
    consuming=bool(data.get('consuming_odd_last_row'))
    if consuming:
        # A-even consuming table with a literal top: the retained word is
        # L1..16.  L16 is retired first; L1..15 with Bhi7 and the outer bit
        # are the fixed 23-wire code, which needs no product helper.
        if removed != 3 or len(high) != 7 or len(low) != 16 or builder.num_allocated_qubits != 49:
            raise ValueError('Expected the selected L1..16/Bhi7/outer inverse cut.')
        labels,kept_labels,fixed_live=list(range(1,17)),list(range(1,16)),48
    else:
        low_width=19-removed
        if removed not in (0,1,2) or len(high) != 7 or len(low) != low_width or builder.num_allocated_qubits != 52-removed:
            raise ValueError('Expected the selected partial-L/Bhi7/outer inverse cut.')
        labels,kept_labels,fixed_live=list(range(low_width)),list(range(14)),47
    if int(data.get('c_storage_shift', -1)) != 3 or int(data.get('c_storage_width', -1)) != 8:
        raise ValueError('This experiment keeps the unchanged C8/shift3 mathematical profile.')
    # data is already in the caller's physical table frame. Never reapply
    # address_affine_rows here: that would silently permute the table twice.
    values, delta, negative = coefficient_delta(data)
    kept_low, indices, retirement = retire_low_bits(
        builder, data, low, debts, remove=[bit for bit in labels if bit not in kept_labels],
        bit_indices=labels)
    if list(indices) != kept_labels or builder.num_allocated_qubits != fixed_live:
        raise AssertionError('Early retirement did not preserve exactly the fixed low code.')
    live = live_word('low', kept_low, values['low'], bit_indices=kept_labels)
    live += live_word('high', high, values['bhi'])
    live += live_word('outer', [saved_outer], [v >> 9 for v in values['blo']])
    code = StaticCode(builder, debts, live, decoder_trials=SCALAR_TRIALS, basis_options={})
    original_wires = [item.wire for item in live]
    original_functions = [item.truth for item in live]
    rank_before = len(Codebook(original_functions).span.pivots)
    if consuming:
        helper = None
        input_wires, functions = list(original_wires), list(original_functions)
    else:
        helper = code.alloc('low0_times_low1')
        code.ccx(kept_low[0], kept_low[1], helper)
        input_wires = original_wires+[helper]
        functions = original_functions+[code.live[helper].truth]
    fourier_metadata=None
    if fourier_debt is not None:
        from fourier_main import repay_result_at_fixed_code
        fourier_metadata=repay_result_at_fixed_code(
            builder,data,input_wires,functions,fourier_debt,debts)
        if builder.num_allocated_qubits!=48:
            raise AssertionError('Fourier repayment changed the mandatory fixed-code allocation cut.')
    negative_functions = word_functions(negative, 7)
    c0 = word_functions(values['curvature'], 1)[0]
    inner_truth = word_functions(values['blo'], 5)[4]
    names = ['curvature0', 'inner_boundary']+[f'negative_delta{i}' for i in DELTA_BITS]
    targets = [c0, inner_truth]+[negative_functions[i] for i in DELTA_BITS]
    residuals, decoder = synthesize_fixed_block(functions, targets, progress=progress)

    output_wires = [code.alloc(name) for name in names]
    product_wire = builder.alloc_qubits(1)[0]
    shared_truths = [0]*len(targets)
    for index, step in enumerate(decoder['steps']):
        product = emit_shared_fanout(
            builder, input_wires, [output_wires[i] for i in step['outputs']],
            product_wire, step['left'], step['right'])
        truth = product.evaluate_functions(functions, (1 << 256)-1)
        for output in step['outputs']:
            shared_truths[output] ^= truth
        if progress is not None:
            progress('shared_product_emitted', index=index, outputs=step['outputs'])
    builder.free(product_wire)
    for index, (wire, residual, target) in enumerate(zip(output_wires, residuals, targets)):
        emit_xor(builder, input_wires, wire, residual)
        emitted_truth = shared_truths[index]^residual.evaluate_functions(functions, (1 << 256)-1)
        if emitted_truth != target:
            raise AssertionError('The emitted simultaneous decoder has a wrong full truth vector.')
        # No StaticCode operation consumed outputs before this complete
        # independent truth certificate; now install their exact live truths.
        code.live[wire].truth = emitted_truth
    after_decode = builder.num_allocated_qubits

    # This helper is an exact product of two still-live original coordinates.
    # Repay immediately, including every measurement outcome, rather than
    # adding another independent coordinate to the final table phase ledger.
    if helper is not None:
        helper_plan = factor_polynomial(22, False, 0, [(0, 1)])
        emit_erase(builder, original_wires, [helper], [helper_plan])
        code.live.pop(helper)
        builder.free(helper)
    code.erase(saved_outer)
    produced = dict(zip(names, output_wires))
    target = list(high)
    carry = None
    arithmetic_before = code.and_count
    for bit in range(4):
        carry = code.add_bit(target[bit], produced[f'negative_delta{bit}'], carry)
    top = produced['negative_delta5']
    code.x(top)
    carry = code.add_bit(target[4], top, carry, consume_source=False)
    code.x(top)
    carry = code.add_bit(target[5], top, carry)
    code.add_bit(target[6], 1, carry, last=True)
    arithmetic_ands = code.and_count-arithmetic_before
    if arithmetic_ands != 6:
        raise AssertionError('The unchanged consuming subtraction must emit six arithmetic ANDs.')
    for wire, truth in zip(target, word_functions([c >> 1 for c in values['curvature']], 7)):
        if code.live[wire].truth != truth:
            raise AssertionError('The inverse arithmetic differs from C>>1 on a table row.')
    c0_wire, inner = produced['curvature0'], produced['inner_boundary']
    low_truths = word_functions(values['low'], 19)
    for wire, truth in [(c0_wire, c0), (inner, inner_truth)]+list(
            zip(kept_low, [low_truths[bit] for bit in kept_labels])):
        if code.live[wire].truth != truth:
            raise AssertionError('An unchanged output was modified by inverse arithmetic.')
    expected_wires = set(kept_low)|set(target)|{c0_wire, inner}
    helper_ands = int(helper is not None)
    if set(code.live) != expected_wires or builder.num_allocated_qubits != 34+len(kept_low):
        raise AssertionError('Unexpected inverse output/scratch allocation.')
    mandatory_count = code.and_count+decoder['total_decoder_ANDs']
    if mandatory_count != helper_ands+decoder['shared_product_ANDs']+decoder['residual_decoder_ANDs']+6:
        raise AssertionError('The complete inverse count does not include every helper and arithmetic AND.')
    phase_static=0 if fourier_metadata is None else fourier_metadata['temporary_decode_static_ANDs']
    phase_mean=0 if fourier_metadata is None else fourier_metadata['temporary_decode_mean_ANDs']
    count=mandatory_count+phase_static
    return km.array([c0_wire, *target]), inner, km.array(kept_low), dict(
        and_count=count, mandatory_inverse_ands=mandatory_count,
        expected_mean_ANDs=mandatory_count+phase_mean,
        fourier_return=fourier_metadata, physical_low_width_on_entry=len(labels),
        early_low_retirement=retirement, helper_ands=helper_ands,
        helper_inputs=['L0', 'L1'] if helper_ands else [],
        helper_measurement_repaid_immediately=True,
        quadratic_rank_before=rank_before, quadratic_rank_after=256,
        joint_decoder=decoder, joint_decoder_ands=decoder['total_decoder_ANDs'],
        arithmetic_ands=arithmetic_ands, decoded_outputs=names,
        delta_range=[min(delta), max(delta)], negative_delta_range=[min(negative), max(negative)],
        qubits_after_early_retirement=fixed_live, qubits_after_joint_decode=after_decode,
        qubits_after=builder.num_allocated_qubits, restored_low_bits=False,
        low_bits=list(kept_labels), erased_outer_boundary=True, inner_restored=True,
        independent_delta_bits=list(DELTA_BITS), arithmetic_truths_checked=256,
        table_measurements=len(code.measurements), no_dynamic_derivative_input=True,
        shared_product_measurements_repaid_immediately=decoder['shared_product_ANDs'],
        source_basis_unchanged_until_all_outputs_complete=True,
        numerical_model_unchanged=True, saved_search_plan_input=False)
