# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Exact finite rank search for the unchanged restored outer carry code.

The selected17 low-coefficient coordinates and all six original helpers are
kept in the original order.  Only the final outer-bit quadratic polynomial
is changed.  The fixed code has21 vanishing quadratic relations, so its
complete2**21 representation coset can be enumerated deterministically.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json

from codebook import Codebook, emit_xor, word_functions
from return_from_low import helper_plan
from r17_lookup import table_words
from transition_codebook import _word_table


SCALAR_SEED = 20261905
KERNEL_SEED = SCALAR_SEED+1000


def outer_low_labels(data):
    """Logical L labels of the restored outer code: L0..16, or L1..16 for the A-even table."""
    return list(range(1, 17)) if data.get('consuming_odd_last_row') else list(range(17))


def code_from_math(data):
    values = table_words(data)
    low = word_functions(values['low'], 17)
    functions = [low[bit] for bit in outer_low_labels(data)]
    target = word_functions(values['blo'], 10)[9]
    # Both selected codes have 23 coordinates: L0..16 with six greedy helpers,
    # or the A-even consuming table's L1..16 with seven.
    helpers = helper_plan(_word_table(functions), [target], width=len(functions), maximum=7)
    if helpers['and_count'] != 23-len(functions):
        raise AssertionError('This finite comparison preserves the selected greedy helpers.')
    coordinates = functions+[functions[left] & functions[right] for left, right in helpers['pairs']]
    code = Codebook(coordinates)
    if code.width != 23 or len(code.span.pivots) != 256 or len(code.span.nullspace) != 21:
        raise AssertionError('The unchanged carry code no longer has the selected21-dimensional coset.')
    return code, target, helpers


def synthesize(data):
    code, target, helpers = code_from_math(data)
    scalar = code.represent(target, trials=80, seed=SCALAR_SEED)
    approximate, old_details = code.represent_kernel(target, trials=15000, seed=KERNEL_SEED)
    original = approximate if approximate.and_count < scalar.and_count else scalar
    exact, details = code.represent_kernel(target, seed=KERNEL_SEED, exhaustive=True)
    if exact.and_count > original.and_count:
        raise AssertionError('An exhaustive representation search lost the selected valid polynomial.')
    if (exact.evaluate_functions(code.functions, code.full) != target
            or exact.evaluate_factored_functions(code.functions, code.full) != target):
        raise AssertionError('The exhaustive rank result differs on a mathematical coefficient row.')
    record = dict(functions=[hex(value) for value in code.functions], target=hex(target),
                  helpers=helpers, polynomial=asdict(exact))
    canonical = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    return exact, dict(
        status='EXACT_FIXED_CODE_QUADRATIC_MINIMUM', source_rows=256,
        helper_ANDs=helpers['and_count'], helpers=helpers,
        original_decoder_ANDs=original.and_count, exact_decoder_ANDs=exact.and_count,
        original_total_ANDs=helpers['and_count']+original.and_count,
        exact_total_ANDs=helpers['and_count']+exact.and_count,
        saving=original.and_count-exact.and_count, original_search=old_details,
        exact_search=details, fixed_code_and_helper_phase_owners_unchanged=True,
        parameters=dict(scalar_seed=SCALAR_SEED, scalar_trials=80,
            kernel_seed=KERNEL_SEED, original_kernel_trials=15000,
            exhaustive_representation_limit=1 << 21, elapsed_time_selection=False),
        plan_record=record, plan_sha256=hashlib.sha256(canonical).hexdigest(),
        generator_saved_plan_input=False, global_circuit_optimality_claim=False)


def restore_selected_outer(builder, data, low, debts, *, bits=(9,), low_bits=None,
                           decoder_trials=80, rank_rounds=0, basis_options=None):
    """Emit the same six helper functions and one exact restored outer bit."""
    import kickmix as km
    low = list(low)
    labels = outer_low_labels(data)
    indices = list(labels) if low_bits is None else list(map(int, low_bits))
    entry = 32+len(labels)
    if (list(map(int, bits)) != [9] or len(low) != len(labels) or indices != labels
            or builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != entry
            or decoder_trials != 80 or rank_rounds != 0 or dict(basis_options or {})):
        raise ValueError('This exact hook belongs only to the selected low/outer9 restore call.')
    plan, synthesis = synthesize(data)
    code, target_truth, helpers = code_from_math(data)
    if plan.and_count > 8:
        raise AssertionError('The selected exhaustive outer-bit decoder lost its accepted eight-product bound.')
    helper_wires = []
    for left, right in helpers['pairs']:
        wire = builder.alloc_qubits(1)[0]
        builder.ccx(low[left], low[right], wire)
        helper_wires.append(wire)
    target = builder.alloc_qubits(1)[0]
    emit_xor(builder, low+helper_wires, target, plan)
    pending_before = len(debts.pending)
    erased_before = debts.erased_qubits
    debts.erase(builder, _word_table(code.functions[len(low):]), helper_wires)
    builder.free(km.array(helper_wires))
    if (builder.num_allocated_qubits != entry+1 or len(debts.pending) != pending_before+1
            or debts.erased_qubits != erased_before+len(helper_wires)
            or plan.evaluate_factored_functions(code.functions, code.full) != target_truth):
        raise AssertionError('The exact restore changed its final data or its one-word helper ledger cut.')
    conversion = dict(
        and_count=plan.and_count, steps=[dict(name='saved9', products=plan.and_count,
            action='allocate', old_name=None, code_width=23,
            quadratic_feature_rank=256, basis_mix=None, all_addresses_checked=256)],
        qubits_after=builder.num_allocated_qubits,
        helper_phase_word_group_unchanged=True)
    return {9: target}, dict(
        helpers=helpers, conversion=conversion, and_count=len(helper_wires)+plan.and_count,
        qubits_after=builder.num_allocated_qubits, physical_blo_bits=[9], low_labels=labels,
        exact_rank_synthesis=synthesis, original_ledger_helper_functions_unchanged=True,
        original_ledger_helper_group_size=len(helper_wires), original_helper_order_unchanged=True,
        quantum_entry=entry)


@contextmanager
def installed():
    """Patch only the schedule's already imported restore-carry function."""
    import scheduled_generator
    previous = scheduled_generator.restore_saved_blo_bits
    if getattr(previous, '_restore_outer_exact_rank', False):
        raise RuntimeError('Exact restored-outer rank synthesis is already installed.')
    calls = []

    def restored(builder, data, low, debts, **options):
        requested = list(map(int, options.get('bits', (4, 9))))
        if requested != [9] or len(low) != len(outer_low_labels(data)):
            return previous(builder, data, low, debts, **options)
        result, metadata = restore_selected_outer(builder, data, low, debts, **options)
        helper_ands = metadata['helpers']['and_count']
        before = helper_ands+metadata['exact_rank_synthesis']['original_decoder_ANDs']
        calls.append(dict(region='restore_curvature_carry', before_ANDs=before,
                          after_ANDs=metadata['and_count'], saving=before-metadata['and_count'],
                          helper_ANDs=helper_ands, quantum_entry=metadata['quantum_entry'],
                          quantum_exit=metadata['qubits_after'],
                          original_helper_phase_owners_unchanged=True))
        return result, metadata

    restored._restore_outer_exact_rank = True
    scheduled_generator.restore_saved_blo_bits = restored
    report = dict(binding='scheduled_generator.restore_saved_blo_bits', calls=calls,
                  scope='selected restore_curvature_carry call only',
                  exhaustive_representation_limit=1 << 21)
    try:
        yield report
        if len(calls) != 1:
            raise AssertionError('Exactly one selected restored-outer call must use the exact rank plan.')
    finally:
        scheduled_generator.restore_saved_blo_bits = previous
