# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Repay original Fourier-suffix phases at the unchanged fixed23 code.

Only mathematical coefficient tables enter this module. Missing L18/L17 are
temporary phase outputs, never persistent reconstructed coefficient wires.
Conditional HMR debts are repaid immediately on the still-live fixed code.
Only uniform Fourier/snapshot outcome parities enter the table phase ledger.
"""
from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction

import kickmix as km
from codebook import Codebook, emit_xor, emit_erase, word_functions
from r17_lookup import table_words

FULL = (1 << 256)-1
SCALAR_TRIALS = 80
KERNEL_TRIALS = 15000
SEED = 20261106810


def fixed_code(data):
    """The existing joint inverse's L14+Bhi7+outer+L0L1 coordinates."""
    values = table_words(data)
    low = word_functions(values['low'], 19)
    high = word_functions(values['bhi'], 7)
    outer = word_functions(values['blo'], 10)[9]
    if data.get('consuming_odd_last_row'):
        # A-even consuming table: L1..15 with Bhi7 and the outer bit already
        # have complete quadratic coverage, so no product helper is kept.
        names = [f'L{i}' for i in range(1, 16)]+[f'Bhi{i}' for i in range(7)]+['outer_B10']
        functions = low[1:16]+high+[outer]
    else:
        names = [f'L{i}' for i in range(14)]+[f'Bhi{i}' for i in range(7)]+['outer_B10', 'L0_times_L1']
        functions = low[:14]+high+[outer, low[0] & low[1]]
    if any(((value >> 19) ^ (value >> 18)) & 1 != 1 for value in values['low']):
        raise AssertionError('The initial nearest-anchor suffix relation changed.')
    if len(functions) != 23 or len(Codebook(functions).span.pivots) != 256:
        raise AssertionError('The fixed23 code lacks complete256-row quadratic coverage.')
    return names, functions, {18: low[18], 17: low[17]}


def synthesize(data, removed):
    if removed not in (1, 2):
        raise ValueError('This isolated experiment removes one or two physical high result bits.')
    names, functions, truths = fixed_code(data)
    code = Codebook(functions)
    plans, details = {}, {}
    for bit in (18,) if removed == 1 else (18, 17):
        plan = code.represent(truths[bit], trials=SCALAR_TRIALS, seed=SEED+bit)
        alternate, kernel = code.represent_kernel(truths[bit], trials=KERNEL_TRIALS,
                                                  seed=SEED+1000+bit)
        if alternate is not None and alternate.and_count < plan.and_count:
            plan = alternate
        if (plan.evaluate_functions(functions, FULL) != truths[bit]
                or plan.evaluate_factored_functions(functions, FULL) != truths[bit]):
            raise AssertionError('A temporary original-top decoder failed its truth certificate.')
        plans[bit] = plan
        details[bit] = dict(ANDs=plan.and_count, polynomial=asdict(plan),
                            kernel_search=kernel, exact_rows=256)
    return plans, dict(removed=removed, names=names,
                       input_truth_hex=[hex(value) for value in functions],
                       output_truth_hex={bit: hex(truths[bit]) for bit in plans},
                       decoders=details,
                       deterministic_parameters=dict(scalar_trials=SCALAR_TRIALS,
                           kernel_trials=KERNEL_TRIALS, seed=SEED))


def repay_at_fixed_code(builder, data, variables, plans, *, odd, twice,
                        original_snapshot, debts, four_times=None,
                        omit_temporary_cleanup=False, wrong_T_sign=False):
    """Pay S/T phases conditionally, transferring only remaining Pauli debts.

    Caller owns the existing23 fixed coordinates (48 live with external25).
    No mandatory joint-inverse output has been allocated yet. Every temporary
    is returned to zero before that decoder resumes. Classical input ownership
    transfers here exactly once; only the returned Pauli ledger bits survive.
    Negative-control flags are confined to independent component proof fixtures.
    """
    variables = list(variables)
    if len(variables) != 23 or len(set(variables)) != 23:
        raise ValueError('The exact existing23-coordinate inverse code is required.')
    removed = 2 if four_times is not None else 1
    expected = {18} if removed == 1 else {18, 17}
    if set(plans) != expected:
        raise ValueError('Temporary decoder plans do not match the omitted suffix width.')
    controls = [odd, twice, original_snapshot]+([] if four_times is None else [four_times])
    if len(set(controls)) != len(controls):
        raise ValueError('Fourier and snapshot outcome ownership must be distinct.')
    _, functions, truths = fixed_code(data)
    for bit, plan in plans.items():
        if plan.width != 23 or plan.evaluate_functions(functions, FULL) != truths[bit]:
            raise AssertionError('A supplied in-memory decoder does not match the mathematical model.')
    entry = builder.num_allocated_qubits
    if entry != 48:
        raise ValueError('Expected the existing48-live code before mandatory inverse outputs.')
    phase18 = builder.alloc_bits(1)[0]
    builder.bit_store(phase18, False)
    builder.cx(twice, phase18); builder.cx(original_snapshot, phase18)
    temporary = builder.alloc_qubits(1)[0]

    def clear(bit):
        if omit_temporary_cleanup:
            outcome = builder.alloc_bits(1)[0]
            builder.hmr(temporary, outcome)
            builder.free(outcome)
        else:
            # This is inside the same classical activation block as compute.
            # No biased outcome is registered in DeferredTablePhases.
            emit_erase(builder, variables, [temporary], [plans[bit]])

    builder.push_condition(odd)
    emit_xor(builder, variables, temporary, plans[18])
    builder.z_pow(temporary, Fraction(1, 2))
    clear(18)
    builder.pop_condition()
    activation17 = None
    if removed == 2:
        activation17 = builder.alloc_bits(1)[0]
        builder.bit_store(activation17, False)
        builder.bit_store(activation17, True, control=odd)
        builder.bit_store(activation17, True, control=twice)
        builder.push_condition(activation17)
        emit_xor(builder, variables, temporary, plans[17])
        builder.push_condition(odd)
        builder.z_pow(temporary, Fraction(1 if wrong_T_sign else -1, 4))
        builder.pop_condition()
        builder.push_condition(twice)
        builder.z_pow(temporary, Fraction(-1, 2))
        builder.pop_condition()
        clear(17)
        builder.pop_condition()
        builder.free(activation17)
    builder.free(temporary)
    builder.z(odd)  # The complete branch-global constant is retained.
    outcomes = [phase18]+([] if four_times is None else [four_times])
    table = [((truths[18] >> address) & 1)
             | (0 if removed == 1 else (((truths[17] >> address) & 1) << 1))
             for address in range(256)]
    debts.record_measurements(table, outcomes)
    builder.free(odd); builder.free(twice); builder.free(original_snapshot)
    if builder.num_allocated_qubits != entry:
        raise AssertionError('Conditional phase decoding leaked quantum workspace.')
    mean = Fraction(plans[18].and_count, 2)
    if removed == 2:
        mean += Fraction(3*plans[17].and_count, 4)
    return dict(
        removed=removed, entry_live=entry, final_live=entry, maximum_live=entry+1,
        temporary_decode_static_ANDs=sum(plan.and_count for plan in plans.values()),
        temporary_decode_mean_ANDs=float(mean), temporary_decode_exact=[mean.numerator, mean.denominator],
        expected_T=0 if removed == 1 else 0.5,
        T_charge_already_in_historical_arithmetic_budget=True,
        activation_probabilities={'L18': [1, 2], **({'L17': [3, 4]} if removed == 2 else {})},
        immediate_cleanup_ANDs=0, conditional_measurements_enter_table_ledger=False,
        original_top_bits_restored_as_persistent_data=False,
        expected_joint_decoder_cut_unchanged=True,
        pauli_records=[dict(outcome=str(wire), truth_hex=hex(truths[bit]), bit=bit)
                        for wire, bit in zip(outcomes, [18, 17])],
        uniform_ledger_coordinates=True,
        ledger_coordinate_identities=['twice XOR original_snapshot']+
            ([] if removed == 1 else ['four_times']),
        negative_control=bool(omit_temporary_cleanup or wrong_T_sign))


def ideal_initial_repayment(a18, a17, *, odd, twice, original_snapshot, four_times=None):
    """Independent scalar oracle in half turns; no decoder or gate inspection."""
    if four_times is None:
        suffix, weight, denominator = 2-a18, odd+2*twice, 2
    else:
        suffix, weight, denominator = 4-2*a18+a17, odd+2*twice+4*four_times, 4
    return (-Fraction(weight*suffix, denominator)-original_snapshot*a18) % 2
