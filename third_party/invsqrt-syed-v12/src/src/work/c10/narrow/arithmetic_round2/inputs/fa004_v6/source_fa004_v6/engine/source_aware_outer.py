# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Restore original Blo9 from L1..16 and the still-live physical R12..16.

The cared code is derived from every row's exact all-residual R interval.
Only products of original input coordinates are materialized. Their HMR
signs are paid immediately before the source R can change. The caller's
existing table phase ledger and every original quantum input are preserved.
No coefficient file, saved plan, or compiled circuit is read by this module.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import itertools
import json

import kickmix as km
from codebook import BinarySpan, Codebook, emit_xor
from numerical_core import Parameters
from r17_lookup import table_words

LOW_LABELS = tuple(range(1, 17))
R_BITS = tuple(range(12, 17))
SCALAR_TRIALS = 80
SCALAR_SEED = 2026111912
RANK_ROUNDS = 256
RANK_SUBSPACE_BITS = 9
RANK_SEED = 2026112912


def cared_code(data):
    """Cover every high-bit bin in an analytically rederived R interval."""
    parameters = Parameters(**data['parameters'])
    if (data.get('lookup_view_only') is not True
            or data.get('consuming_odd_last_row') is not True
            or int(data.get('r_storage_width', -1)) != 17
            or int(data.get('r_storage_shift', -1)) != 1
            or int(data.get('low_width', -1)) != 20
            or (parameters.residual_bits, parameters.first_row_fraction_bits,
                parameters.rounding) != (14, 15, 'nearest')):
        raise ValueError('Require the framed consuming R17/L20 fourteen-digit curvature model.')
    values = table_words(data)
    states = []
    for address, row in enumerate(data['coefficients']):
        b, c = int(row['b']), int(row['c'])
        if b < 0 or c < 0 or b & 1:
            raise ValueError('The selected unsigned stored derivative has even B and nonnegative curvature.')
        magnitude = sum((c+(1 << (14-i))) >> (15-i) for i in range(14))
        lower, upper = (b-magnitude) >> 1, (b+magnitude) >> 1
        if ((lower, upper) != (int(row['r_min']), int(row['r_max']))
                or not 0 <= lower <= upper < (1 << 17)):
            raise ValueError('Every fitted R bound must equal its exact all14-bit-residual interval.')
        for high in range(lower >> 12, (upper >> 12)+1):
            first, last = max(lower, high << 12), min(upper, ((high+1) << 12)-1)
            if first > last:
                raise AssertionError('An empty R bin entered the cared code.')
            states.append((address, high, first, last))
    functions = [sum(((values['low'][address] >> bit) & 1) << index
                     for index, (address, _, _, _) in enumerate(states)) for bit in LOW_LABELS]
    functions += [sum(((high >> (bit-12)) & 1) << index
                      for index, (_, high, _, _) in enumerate(states)) for bit in R_BITS]
    target = sum(((values['blo'][address] >> 9) & 1) << index
                 for index, (address, _, _, _) in enumerate(states))
    words = [sum(((truth >> index) & 1) << bit for bit, truth in enumerate(functions))
             for index in range(len(states))]
    if len(states) != 272 or len(set(words)) != len(states):
        raise ValueError('The selected source-aware input code must retain its exact272 distinct cared states.')
    return functions, target, states


def helper_code(functions, target, *, size):
    """Deterministic rank/coverage search over original-input products only."""
    original = list(functions)
    current, pairs, ranks = list(functions), [], []
    while True:
        code = Codebook(current, size=size)
        covered = code.span.solve(target) is not None
        ranks.append(dict(variables=len(current), quadratic_rank=len(code.span.pivots),
                          target_covered=covered))
        if covered:
            return code, pairs, ranks
        if len(pairs) >= 2:
            raise ValueError('The source-aware restore exceeded its certified two-helper budget.')
        linear = BinarySpan([code.full]+current)
        best = None
        for a, b in itertools.combinations(range(len(original)), 2):
            function = original[a] & original[b]
            if linear.solve(function) is not None:
                continue
            candidate = Codebook(current+[function], size=size)
            score = (len(candidate.span.pivots), candidate.span.solve(target) is not None, -a, -b)
            if best is None or score > best[0]:
                best = score, a, b, function
        if best is None or best[0][0] <= len(code.span.pivots):
            raise ValueError('No original-input product increases the cared quadratic span.')
        _, a, b, function = best
        pairs.append((a, b))
        current.append(function)


def synthesize(data):
    """Regenerate and certify the selected eleven-AND construction."""
    functions, target, states = cared_code(data)
    code, pairs, ranks = helper_code(functions, target, size=len(states))
    plan = code.represent(target, trials=SCALAR_TRIALS, seed=SCALAR_SEED)
    if plan is None:
        raise AssertionError('The selected helper code no longer represents original Blo9.')
    initial = plan.and_count
    plan = code.improve_preserving_kernel(plan, rounds=RANK_ROUNDS,
        subspace_bits=RANK_SUBSPACE_BITS, seed=RANK_SEED)
    if (pairs != [(0, 1), (2, 4)] or plan.and_count != 9 or code.width != 23
            or len(code.span.pivots) != 270 or len(code.span.nullspace) != 7
            or plan.evaluate_functions(code.functions, code.full) != target
            or plan.evaluate_factored_functions(code.functions, code.full) != target):
        raise AssertionError('The source-derived outer restore changed its certified truth or resource contract.')
    record = dict(care_states=[dict(physical_address=a, R_high=high, R_min=first, R_max=last)
                              for a, high, first, last in states],
        functions_hex=[hex(value) for value in code.functions], target_hex=hex(target),
        helper_pairs=pairs, helper_progress=ranks, polynomial=asdict(plan))
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata = dict(status='EXACT_CARED_TRUTH_CERTIFICATE_WITH_DETERMINISTIC_HEURISTIC_PRICE',
        low_labels=list(LOW_LABELS), source_R_bits=list(R_BITS),
        cared_states=len(states), cared_integer_R_values=sum(last-first+1 for _, _, first, last in states),
        all256_R_intervals_rederived=True, every_interval_bin_covered=True,
        stronger_all14bit_residual_bound=True, all_original_input_codes_distinct=True,
        helper_ANDs=len(pairs), helper_pairs=pairs, initial_decoder_ANDs=initial,
        decoder_ANDs=plan.and_count, total_ANDs=len(pairs)+plan.and_count,
        quadratic_rank=len(code.span.pivots), quadratic_nullity=len(code.span.nullspace),
        parameter_seed=SCALAR_SEED, scalar_trials=SCALAR_TRIALS,
        rank_seed=RANK_SEED, rank_rounds=RANK_ROUNDS, rank_subspace_bits=RANK_SUBSPACE_BITS,
        synthesis_sha256=digest, generator_saved_plan_input=False,
        global_or_fixed_code_minimality_claim=False)
    return plan, pairs, metadata


def ledger_identity(debts):
    return (tuple((tuple(values), tuple(outcomes)) for values, outcomes in debts.pending),
            debts.address_bits, debts.erased_words, debts.erased_qubits)


def restore_outer_from_source(builder, data, low, source, debts, *, bits=(9,),
                              low_bits=None, decoder_trials=80, rank_rounds=0,
                              basis_options=None):
    """Add one original Blo9 output at the unchanged48-live ownership cut."""
    low, source = list(low), list(source)
    labels = list(LOW_LABELS) if low_bits is None else list(map(int, low_bits))
    if (list(map(int, bits)) != [9] or labels != list(LOW_LABELS)
            or len(low) != 16 or len(source) != 17 or len(set(low+source)) != 33
            or any(not isinstance(wire, km.q) for wire in low+source)
            or builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != 48
            or decoder_trials != 80 or rank_rounds != 0 or dict(basis_options or {})):
        raise ValueError('Require the selected48-live L1..16 and exact unsigned R17 outer-restore cut.')
    incoming = ledger_identity(debts)
    plan, pairs, synthesis = synthesize(data)
    variables = low+[source[bit] for bit in R_BITS]
    helpers = []
    for a, b in pairs:
        helper = builder.alloc_qubits(1)[0]
        builder.ccx(variables[a], variables[b], helper)
        helpers.append(helper)
    outer = builder.alloc_qubits(1)[0]
    emit_xor(builder, variables+helpers, outer, plan)
    for helper, (a, b) in reversed(list(zip(helpers, pairs))):
        builder.del_and(variables[a], variables[b], helper)
        builder.free(helper)
    if builder.num_allocated_qubits != 49 or ledger_identity(debts) != incoming:
        raise AssertionError('The source-aware restore changed an original table owner or leaked workspace.')
    return {9: outer}, dict(component='source_aware_original_Blo9_restore', and_count=11,
        helper_ANDs=2, decoder_ANDs=9, low_labels=list(LOW_LABELS),
        source_R_bits=list(R_BITS), physical_blo_bits=[9],
        quantum_entry=48, qubits_after=49, maximum_live=51,
        source_aware_synthesis=synthesis, original_table_ledger_unchanged=True,
        original_quantum_inputs_preserved=True, helper_HMR_phases_repaid_locally=True,
        no_dynamic_R_function_added_to_table_ledger=True,
        prior_seven_deferred_helper_outcomes_removed=True,
        claimed_full_circuit_or_official_status=False)


@contextmanager
def installed():
    """Bind the exact main-source owner to the immediately following restore.

    Install in place of restore_outer_exact_rank.installed, at the same
    outer context position. All original main arithmetic still runs through
    its existing wrappers. No source wire is inferred from an allocator ID.
    """
    import fourier_main
    import scheduled_generator
    old_main = fourier_main.inverse_main_groups
    old_restore = scheduled_generator.restore_saved_blo_bits
    pending = []
    records = []

    def main(builder, digits, source, retained, groups, debt):
        source = list(source)
        if pending or len(source) != 17 or len(set(source)) != 17:
            raise ValueError('The source-aware outer scope requires one exact original R17 main owner.')
        result = old_main(builder, digits, source, retained, groups, debt)
        if (debt.stage != 'main_reversed' or debt.suffix.consumed
                or builder.num_allocated_qubits != 48):
            raise AssertionError('The complete original main inverse did not reach its selected48-live boundary.')
        pending.append((builder, tuple(source), debt))
        return result

    def restore(builder, data, low, debts, **options):
        if (len(pending) != 1 or pending[0][0] is not builder
                or pending[0][2].stage != 'main_reversed' or pending[0][2].suffix.consumed):
            raise ValueError('The original main-source owner must remain live until the selected outer restore.')
        _, source, _ = pending[0]
        result, metadata = restore_outer_from_source(builder, data, low, source, debts, **options)
        pending.pop()
        records.append(metadata)
        return result, metadata

    fourier_main.inverse_main_groups = main
    scheduled_generator.restore_saved_blo_bits = restore
    try:
        yield dict(binding='selected_main_R17_to_immediately_following_original_Blo9_restore', calls=records)
        if pending or len(records) != 1:
            raise AssertionError('Exactly one source-aware outer restore must consume the captured R17 owner.')
    finally:
        fourier_main.inverse_main_groups = old_main
        scheduled_generator.restore_saved_blo_bits = old_restore
