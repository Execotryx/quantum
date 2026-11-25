# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Deterministic product-sharing compiler for the mathematical high-word decoder.

The existing source compiler supplies quadratic decoder IR, never a parsed
circuit or gate list. At most two product coordinates of its high2 plan are
retained through the remaining high decodes and erased exactly before the
callback. All original output slots and the seed bank are preserved.

The production entry point is convert_shared_high. It derives the original
numeric high plans from the current mathematical table, evaluates all 46
zero/one/two-helper choices, and emits the deterministic minimum on every
invocation. It reads no report, profile cache, selected-index file, or circuit.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import kickmix as km
from codebook import Codebook, emit_xor, emit_phase, factor_polynomial
from deferred_phase import DeferredTablePhases
import transition_codebook as transition
from transition_codebook import LiveFunction
from universal_phase_basis import product_plan


FULL = (1 << 256)-1
ORIGINAL_CONVERTER = transition.convert_codebook
ORIGINAL_EMIT = transition.emit_xor


@dataclass(frozen=True)
class Decoder:
    name: str
    variables: tuple[str, ...]
    functions: tuple[int, ...]
    truth: int
    plan: object


def high_settings(source):
    """The unchanged settings of initial_retained's first conversion."""
    return dict(trials=80, seed=20261901, preserving_rounds=0,
                structured_subsets=True, basis_search_products=3,
                basis_natural_limit=256, basis_random_trials=256,
                basis_random_max_products=5, preserve_future=True,
                extra_subset_functions=tuple(item.truth for item in source[8:]))


def derive_baseline(source, desired, settings):
    """Run the existing source compiler on an abstract allocation geometry.

Capture only each complete quadratic decoder (semantic compiler IR). The
shadow circuit is never serialized, parsed, or used as a sequence of gates.
"""
    source, desired = list(source), list(desired)
    if len(source) != 30 or len(desired) != 8:
        raise ValueError('Expected the original address8/seed22 and high8 geometry.')
    if len({item.name for item in source}) != 30 or len({truth for _, truth in desired}) != 8:
        raise AssertionError('The selected named high-code geometry changed.')
    builder = km.CircuitBuilder()
    builder.set_max_qubits(57)
    allocated = list(builder.alloc_qubits(45))
    abstract = [LiveFunction(item.name, allocated[i], int(item.truth)) for i, item in enumerate(source)]
    known = {item.wire: item for item in abstract}
    desired_names = {int(truth): str(name) for name, truth in desired}
    trace = []
    if transition.emit_xor is not ORIGINAL_EMIT:
        raise RuntimeError('A different coefficient-IR capture is active.')

    def capture(b, variables, target, plan):
        variables = list(variables)
        items = [known[wire] for wire in variables]
        functions = tuple(int(item.truth) for item in items)
        truth = plan.evaluate_factored_functions(functions, FULL)
        if plan.evaluate_functions(functions, FULL) != truth or truth not in desired_names:
            raise AssertionError('The captured decoder is not an original numeric high output.')
        name = desired_names[truth]
        trace.append(Decoder(name, tuple(item.name for item in items), functions, truth, plan))
        ORIGINAL_EMIT(b, variables, target, plan)
        known[target] = LiveFunction(name, target, truth)

    transition.emit_xor = capture
    try:
        produced, metadata = ORIGINAL_CONVERTER(
            builder, abstract, [], desired, DeferredTablePhases(8), **settings)
    finally:
        transition.emit_xor = ORIGINAL_EMIT
    if len(trace) != 8 or metadata['and_count'] != 35 or metadata['output_basis_cnots']:
        raise AssertionError('The frozen 35-AND numeric high decoder changed.')
    if any(row['action'] != 'allocate' or row.get('basis_mix') for row in metadata['steps']):
        raise AssertionError('This narrow pass accepts only the original allocating high decoder.')
    if [row.name for row in trace] != [step['name'] for step in metadata['steps']]:
        raise AssertionError('The captured mathematical decoder order is inconsistent.')
    if len({item.wire for item in produced.values()}) != 8:
        raise AssertionError('The high decoder did not allocate eight distinct outputs.')
    if builder.num_allocated_qubits != 53:
        raise AssertionError('The original high callback geometry changed.')
    focus = next(i for i, row in enumerate(trace) if row.name == 'high2')
    if focus != 5 or trace[focus].plan.and_count != 9:
        raise AssertionError('The intended nine-product high2 snapshot changed.')
    if [row.name for row in trace[focus+1:]] != ['high0', 'high1']:
        raise AssertionError('The two following high outputs changed order.')
    return tuple(trace), metadata


def extend(plan, width):
    if width < plan.width:
        raise ValueError('Cannot shrink a decoder by extension.')
    return factor_polynomial(width, plan.constant, plan.linear, plan.edges)


def plan_variant(trace, selected):
    selected = tuple(map(int, selected))
    focus = next(i for i, row in enumerate(trace) if row.name == 'high2')
    source = trace[focus]
    if len(selected) > 2 or tuple(sorted(set(selected))) != selected:
        raise ValueError('Select zero, one, or two distinct ordered source product indices.')
    if any(i < 0 or i >= len(source.plan.products) for i in selected):
        raise ValueError('A selected semantic product index is absent from high2.')
    products = [product_plan(source.plan.width, *source.plan.products[i][:2]) for i in selected]
    truths = [plan.evaluate_factored_functions(source.functions, FULL) for plan in products]
    if any(plan.and_count != 1 for plan in products):
        raise AssertionError('A retained product must cost exactly one AND.')
    plans = []
    for position, row in enumerate(trace):
        if not selected or position < focus:
            plan = row.plan
        elif position == focus:
            linear, edges = row.plan.linear, set(row.plan.edges)
            constant = row.plan.constant
            for index, product in enumerate(products):
                constant ^= product.constant
                linear ^= product.linear ^ (1 << (row.plan.width+index))
                edges.symmetric_difference_update(product.edges)
            plan = factor_polynomial(row.plan.width+len(selected), constant, linear, edges)
            if plan.and_count+len(selected) > row.plan.and_count:
                raise AssertionError('Factoring out selected products increased high2 cost.')
        else:
            functions = list(row.functions)+truths
            original = extend(row.plan, len(functions))
            plan = Codebook(functions).represent(
                row.truth, trials=80, seed=20261901+position, initial_plan=original)
            if plan is None or plan.and_count > row.plan.and_count:
                raise AssertionError('A following decoder regressed despite its original certificate.')
        functions = list(row.functions)+(truths if selected and position >= focus else [])
        if (plan.evaluate_functions(functions, FULL) != row.truth
                or plan.evaluate_factored_functions(functions, FULL) != row.truth):
            raise AssertionError('A shared-product numeric high truth changed.')
        plans.append(plan)
    count = len(selected)+sum(plan.and_count for plan in plans)
    certificate = dict(
        selected_products=list(selected), helper_count=len(selected), high_ands=count,
        saved_high_ands=35-count, output_order=[row.name for row in trace],
        output_and_counts=[plan.and_count for plan in plans],
        original_output_and_counts=[row.plan.and_count for row in trace],
        helper_truths_hex=[f'{truth:064x}' for truth in truths],
        helper_source_names=list(source.variables),
        helper_source_truths_hex=[f'{truth:064x}' for truth in source.functions],
        helper_polynomials=[dict(constant=plan.constant, linear=plan.linear,
                                 edges=plan.edges, products=plan.products) for plan in products],
        checked_addresses=256, helper_cleanup='HMR plus exact conditional Z/CZ',
        no_helper_phase_debt_left_pending=True,
        expected_callback_live=53, temporary_helper_limit=2)
    return tuple(plans), tuple(products), tuple(truths), certificate


def survey(trace, progress=None, *, helper_limit=2):
    """Evaluate all 46 variants; select the minimum that fits `helper_limit` helpers."""
    if helper_limit not in (0, 1, 2):
        raise ValueError('The high decoder shares at most two temporary products.')
    focus = next(row for row in trace if row.name == 'high2')
    choices = [()] + [(i,) for i in range(len(focus.plan.products))]
    choices += list(combinations(range(len(focus.plan.products)), 2))
    if len(choices) != 46:
        raise AssertionError('This probe is bounded to exactly 46 zero/one/two-helper variants.')
    records = []
    best = None
    for selected in choices:
        plans, products, truths, certificate = plan_variant(trace, selected)
        records.append(certificate)
        key = (certificate['high_ands'], len(selected), selected)
        if len(selected) <= helper_limit and (best is None or key < best[0]):
            best = (key, selected, plans, products, truths, certificate)
        if progress:
            progress(len(records), len(choices), certificate)
    return best[1], records


def emit_variant(builder, source, trace, selected, *, omit_helper_phase=False, owned_controls=None):
    source = list(source)
    if owned_controls is None:
        if builder.num_allocated_qubits != 45:
            raise AssertionError('The high decoder must enter with the original 45 live qubits.')
    else:
        from owned_initial_controls import require_owners
        require_owners(owned_controls).check_decode_live(builder, 47)
    plans, products, truths, certificate = plan_variant(trace, selected)
    if owned_controls is not None:
        certificate = dict(certificate, base_callback_live=53, expected_callback_live=55,
                           retained_initial_controls_are_separate_owners=True)
    # Allocating all numeric outputs up front preserves exactly the slots
    # that the original allocating decoder requests one by one. Its emit_xor
    # primitive never allocates scratch, so no intervening allocation differs.
    slots = list(builder.alloc_qubits(8))
    high_slots = {row.name: wire for row, wire in zip(trace, slots)}
    wires = {item.name: item.wire for item in source}
    current_truths = {item.name: int(item.truth) for item in source}
    helpers = []
    focus = next(i for i, row in enumerate(trace) if row.name == 'high2')
    helper_inputs = None
    steps = []
    for position, (row, plan) in enumerate(zip(trace, plans)):
        if [current_truths[name] for name in row.variables] != list(row.functions):
            raise AssertionError('An original high-decoder input truth changed.')
        variables = [wires[name] for name in row.variables]
        if position == focus and products:
            helper_inputs = list(variables)
            helpers = list(builder.alloc_qubits(len(products)))
            for target, product in zip(helpers, products):
                emit_xor(builder, helper_inputs, target, product)
        if position >= focus:
            variables += helpers
        target = high_slots[row.name]
        emit_xor(builder, variables, target, plan)
        wires[row.name] = target
        current_truths[row.name] = row.truth
        steps.append(dict(name=row.name, products=plan.and_count, action='allocate_reserved_slot',
                          all_addresses_checked=256, basis_mix=None))
    if helpers:
        outcomes = builder.alloc_bits(len(helpers))
        for i in range(len(helpers)-1, -1, -1):
            builder.hmr(helpers[i], outcomes[i])
            if not omit_helper_phase:
                emit_phase(builder, helper_inputs, outcomes[i], products[i])
        builder.free(km.array(list(reversed(outcomes))))
        builder.free(km.array(list(reversed(helpers))))
    if owned_controls is None:
        if builder.num_allocated_qubits != 53:
            raise AssertionError('Temporary helpers survived into the high callback.')
    else:
        owned_controls.check_decode_live(builder, 55)
    output = {row.name: LiveFunction(row.name, high_slots[row.name], row.truth) for row in trace}
    metadata = dict(and_count=certificate['high_ands'], steps=steps, output_basis_cnots=0,
                    reversible_in_place=False, qubits_after=53 if owned_controls is None else 55,
                    temporary_product_sharing=certificate,
                    omitted_helper_phase_negative_control=bool(omit_helper_phase),
                    output_slots_reserved_in_original_source_order=True)
    return output, metadata


def convert_shared_high(builder, retained, consumed, desired, phase_debts, *, owned_controls=None, **settings):
    """Replace only the selected initializer's allocating high conversion.

    This has the same calling convention as convert_codebook. The narrow
    geometry guards deliberately fail closed for an unproved decoder shape.
    Search decisions are derived afresh; recorded choices are output evidence.
    Temporary helpers are measured and exactly repaid before returning, so
    neither the caller's phase ledger nor its 53-live handoff is changed.
    """
    source, consumed, desired = list(retained), list(consumed), list(desired)
    if consumed:
        raise ValueError('High product sharing requires a purely allocating high conversion.')
    if phase_debts.address_bits != 8:
        raise ValueError('High product sharing requires the selected eight-bit address.')
    if owned_controls is None:
        if builder.num_allocated_qubits != 45:
            raise ValueError('High product sharing requires the selected forty-five-live entry.')
    else:
        from owned_initial_controls import require_owners
        require_owners(owned_controls).begin_decode(builder, source)
    if len({item.wire for item in source}) != len(source):
        raise ValueError('Each original high-decoder coordinate must own a distinct wire.')
    trace, baseline = derive_baseline(source, desired, settings)
    # The eight reserved output slots come first; shared products may use
    # only the free wires that remain above them under the build's cap.
    helper_limit = max(0, min(2, builder.max_qubits-builder.num_allocated_qubits-8))
    selected, records = survey(trace, helper_limit=helper_limit)
    if len(records) != 46:
        raise AssertionError('The deterministic high-product search did not cover all 46 choices.')
    produced, metadata = emit_variant(builder, source, trace, selected, owned_controls=owned_controls)
    if owned_controls is not None:
        owned_controls.finish_decode(builder, [produced[f'high{i}'].wire for i in range(8)])
    metadata['high_product_sharing_search'] = dict(
        algorithm='source-quadratic-high-products-v1',
        choices_evaluated=len(records), helper_limit=helper_limit,
        winner_key='(high_ands, helper_count, selected_product_indices)',
        selected_products=list(selected),
        baseline_high_ands=baseline['and_count'],
        selected_high_ands=metadata['and_count'],
        baseline_decoder_seed=int(settings.get('seed', 314159)),
        baseline_decoder_trials=int(settings.get('trials', 400)),
        following_decoder_seed_base=20261901, following_decoder_trials=80,
        candidates=[dict(selected_products=row['selected_products'],
                         helper_count=row['helper_count'], high_ands=row['high_ands'],
                         output_and_counts=row['output_and_counts']) for row in records],
        recomputed_from_mathematical_truths=True,
        parsed_or_loaded_gate_input=False,
        extra_table_ledger_entries=0,
    )
    return produced, metadata
