# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Bounded simultaneous synthesis of the first two forward delta bits.

The selected transition currently decodes these bits independently for sixteen
ANDs.  At that cut both output wires and one reusable product wire fit in the
existing fifty-seven-qubit limit.  Keep the original twenty-nine coordinates
fixed, factor both exact functions jointly, and repay every private product
measurement immediately.  The remaining transition and original table ledger
are unchanged.  This module never reads a saved plan or circuit.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json

from codebook import Codebook, emit_xor
from joint_inverse_lookup import emit_shared_fanout
from simultaneous_quadratic import certify_truths, extract_shared
from transition_codebook import LiveFunction


SCALAR_SEED = 20261106101
SCALAR_TRIALS = 80
PRESERVING_ROUNDS = 1024
SHARING_SEED = 202611079301
FACTOR_TRIALS = 64
MAXIMUM_SHARED_STEPS = 8
BASELINE_PAIR_ANDS = 16


@lru_cache(maxsize=1)
def _synthesize_pair(functions, targets):
    if len(functions) not in (28, 29) or len(targets) != 2:
        raise ValueError('The first forward pair has its complete input code and two outputs.')
    code = Codebook(functions)
    if len(code.span.pivots) != 256:
        raise AssertionError('The unchanged input code must span every coefficient truth.')
    plans = []
    scalar_records = []
    for index, target in enumerate(targets):
        plan = code.represent(target, trials=SCALAR_TRIALS, seed=SCALAR_SEED+index)
        initial_products = plan.and_count
        if plan.and_count >= 9:
            plan = code.improve_preserving_kernel(
                plan, rounds=PRESERVING_ROUNDS, seed=SCALAR_SEED+2000+index)
        plans.append(plan)
        scalar_records.append(dict(output=index, initial_ANDs=initial_products,
                                   refined_ANDs=plan.and_count, polynomial=asdict(plan)))
    certify_truths(functions, targets, plans, [])
    residuals, sharing = extract_shared(
        functions, targets, plans, seed=SHARING_SEED,
        factor_trials=FACTOR_TRIALS, maximum_steps=MAXIMUM_SHARED_STEPS,
        deadline=None)
    if sharing['stop_reason'] == 'soft_deadline':
        raise AssertionError('Elapsed time cannot select a from-source decomposition.')
    certificate = certify_truths(functions, targets, residuals, sharing['steps'])
    record = dict(inputs=[hex(value) for value in functions],
                  targets=[hex(value) for value in targets],
                  products=sharing['steps'], residuals=[asdict(plan) for plan in residuals])
    canonical = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    metadata = dict(sharing, scalar_forms=scalar_records,
        exact_certificate=certificate, plan_record=record,
        plan_sha256=hashlib.sha256(canonical).hexdigest(),
        original_pair_ANDs=BASELINE_PAIR_ANDS,
        saving=BASELINE_PAIR_ANDS-sharing['total_decoder_ANDs'],
        parameters=dict(scalar_seed=SCALAR_SEED, scalar_trials=SCALAR_TRIALS,
            preserving_rounds=PRESERVING_ROUNDS, sharing_seed=SHARING_SEED,
            factor_trials=FACTOR_TRIALS, maximum_shared_steps=MAXIMUM_SHARED_STEPS,
            elapsed_time_selection=False),
        in_process_cache_only=True, saved_plan_input=False)
    return tuple(residuals), metadata


def synthesize_pair(functions, targets):
    """Regenerate one bounded plan; cache only identical in-process math inputs."""
    return _synthesize_pair(tuple(map(int, functions)), tuple(map(int, targets)))


def emit_pair(code, desired):
    """Materialize the same delta functions, with a locally repaid shared wire."""
    builder = code.builder
    items = list(code.live.values())
    # The consuming table stores one low wire fewer: 28 inputs at 53 live.
    entry = 25+len(items)
    if (len(items) not in (28, 29) or builder.num_allocated_qubits != entry
            or builder.max_qubits not in (56, 57) or code.preserving_rounds != PRESERVING_ROUNDS
            or code.decoder_trials != SCALAR_TRIALS or dict(code.basis_options or {})):
        raise ValueError('This pair emitter belongs only to the selected first forward decode.')
    functions = [item.truth for item in items]
    targets = [truth for _, truth in desired]
    residuals, synthesis = synthesize_pair(functions, targets)
    if synthesis['total_decoder_ANDs'] >= BASELINE_PAIR_ANDS:
        raise ValueError('The bounded first-pair synthesis has no strictly positive saving.')
    variables = [item.wire for item in items]
    output_wires = list(builder.alloc_qubits(len(desired)))
    product_wire = builder.alloc_qubits(1)[0]
    pending_before = tuple((tuple(values), tuple(outcomes))
                           for values, outcomes in code.debts.pending)
    erased_before = code.debts.erased_qubits
    shared_truths = [0]*len(targets)
    for step in synthesis['steps']:
        product = emit_shared_fanout(
            builder, variables, [output_wires[index] for index in step['outputs']],
            product_wire, step['left'], step['right'])
        truth = product.evaluate_factored_functions(functions, (1 << 256)-1)
        for index in step['outputs']:
            shared_truths[index] ^= truth
    builder.free(product_wire)
    produced = {}
    for index, ((name, target), wire, residual) in enumerate(
            zip(desired, output_wires, residuals)):
        emit_xor(builder, variables, wire, residual)
        actual = shared_truths[index] ^ residual.evaluate_factored_functions(
            functions, (1 << 256)-1)
        if actual != target:
            raise AssertionError('The first-pair emitter differs on a coefficient truth.')
        item = LiveFunction(name, wire, actual)
        code.live[wire] = item
        produced[name] = item
    pending_after = tuple((tuple(values), tuple(outcomes))
                          for values, outcomes in code.debts.pending)
    if (builder.num_allocated_qubits != entry+2 or pending_after != pending_before
            or code.debts.erased_qubits != erased_before):
        raise AssertionError('Joint emission changed the original live cut or table ledger.')
    code.decoded.append(dict(
        and_count=synthesis['total_decoder_ANDs'], qubits_after=entry+2,
        bounded_preserving_rounds=PRESERVING_ROUNDS,
        simultaneous_first_pair=synthesis,
        private_product_HMRs=synthesis['shared_product_ANDs'],
        private_measurements_repaid_immediately=True,
        original_table_ledger_unchanged=True,
        helpers=dict(pairs=[], and_count=0),
        conversion=dict(and_count=synthesis['total_decoder_ANDs'],
            steps=[dict(name=name, action='allocate', old_name=None,
                        products=residual.and_count, code_width=len(items),
                        quadratic_feature_rank=256, all_addresses_checked=256)
                   for (name, _), residual in zip(desired, residuals)])))
    return produced


@contextmanager
def installed():
    """Change exactly the selected first decode, inside the existing rank scope."""
    from curvature_rank_refinement import RankRefinedStaticCode
    previous = RankRefinedStaticCode.decode
    if getattr(previous, '_stage93_forward_pair', False):
        raise RuntimeError('The forward shared-pair emitter is already installed.')
    calls = []

    def decode(code, desired, seed, *, retire=()):
        desired = list(desired)
        selected = (not code.decoded and not retire and seed == SCALAR_SEED
                    and [name for name, _ in desired] == ['delta0', 'delta1'])
        if not selected:
            return previous(code, desired, seed, retire=retire)
        produced = emit_pair(code, desired)
        metadata = code.decoded[-1]
        calls.append(dict(region='curvature_to_derivative_high',
            original_pair_ANDs=BASELINE_PAIR_ANDS, new_pair_ANDs=metadata['and_count'],
            saving=BASELINE_PAIR_ANDS-metadata['and_count'],
            private_product_HMRs=metadata['private_product_HMRs'],
            original_table_ledger_unchanged=True,
            quantum_entry=metadata['qubits_after']-2, quantum_exit=metadata['qubits_after']))
        return produced

    decode._stage93_forward_pair = True
    RankRefinedStaticCode.decode = decode
    report = dict(scope='first forward delta pair only', calls=calls,
                  binding='curvature_rank_refinement.RankRefinedStaticCode.decode')
    try:
        yield report
        if len(calls) != 1:
            raise AssertionError('The selected transition must execute exactly one shared pair.')
    finally:
        RankRefinedStaticCode.decode = previous
