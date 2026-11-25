#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Prove newly emitted normalization and restoration on every valid input.

The quantum data and every syntactic X-measurement outcome are independent
Boolean symbols.  Exact square-free GF(2) polynomials represent both data
and Pauli phases.  Twenty-two leading-one support classes cover every
positive original input below three times the top-pair place value, a
strict superset of the required benchmark interval.  Vanishing Boolean
ANF coefficients proves all input and outcome assignments simultaneously.

The fixture observes the unchanged initial-owner boundary: the original
prefix exposes g9, and packing retains u.  It checks these values before
transferring their measured phases to the original threshold/u ledgers.
It does not rebuild or claim a new proof of the unrelated lookup body.
The actual selected InitialHighOwners protocol is exercised by the later
full generator build.  No compiled circuit is loaded as a source here.

Run this tool only as the sole heavy job under the project memory guard.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
from copy import copy
from fractions import Fraction
import hashlib
import importlib
import json
from pathlib import Path
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'official'), str(ROOT / 'engine'), str(ROOT / 'tests')]

import kickmix as km
from branch_prover import Operation, Program, generated_text
from fourier_resource_expectation import exact_expectation
from fusion.normalization import ShiftFlags
import fusion.normalization as normalization
import normalization_fused
from packed_shift import PackedShift
import prefix_normalization
import shared_normalization_controls
import thermometer_cleanup
from threshold_phase_ledger import PackedThresholdPhasePass


ZERO = frozenset()
ONE = frozenset((0,))
WIDTH = 22
MAXIMUM_INPUT = 3 * (2 ** 10 - 2) ** 2
STRONGER_EXCLUSIVE_BOUND = 3 * (1 << (WIDTH - 2))
REGIONS = ('normalization', 'probe_debts', 'pack_shift', 'probe_initial_owners',
           'probe_packed_uses', 'restore_input')
CUTS = ('normalization', 'pack_shift', 'probe_initial_owners',
        'probe_packed_uses', 'restore_unpack', 'restore_input')


def product(*values):
    """Multiply square-free Boolean polynomials exactly, with no sampling."""
    result = ONE
    for value in values:
        if not value:
            return ZERO
        if value == ONE:
            continue
        if result == ONE:
            result = value
            continue
        terms = set()
        for left in result:
            for right in value:
                term = left | right
                if term in terms:
                    terms.remove(term)
                else:
                    terms.add(term)
        if len(terms) > 200000:
            raise MemoryError('The exact Boolean proof exceeded its bounded term budget.')
        result = frozenset(terms)
    return result


def integer_symbol(value):
    if value not in (0, 1):
        raise ValueError('A fixed Boolean value must be zero or one.')
    return ONE if value else ZERO


def leading_support(leading):
    """One disjoint support class, including the original exclusive-top pair."""
    if not 0 <= leading < WIDTH:
        raise ValueError('A leading-one position is outside the original word.')
    values = [frozenset((1 << bit,)) if bit < leading else
              (ONE if bit == leading else ZERO) for bit in range(WIDTH)]
    variables = leading
    if leading == WIDTH - 1:
        values[WIDTH - 2] = ZERO
        variables -= 1
    return values, variables


def mathematical_semilog(source, leading):
    zeros = WIDTH - 1 - leading
    count, low_half = divmod(zeros, 2)
    cleared = list(source)
    if low_half:
        cleared[leading] = ZERO
    aligned = [ZERO] * WIDTH
    for bit in range(WIDTH - zeros):
        aligned[bit + zeros] = cleared[bit]
    return aligned, count


def symbolic_witness(polynomial, leading):
    """An inclusion-minimal ANF monomial yields a concrete failing assignment."""
    if not polynomial:
        raise ValueError('A zero polynomial has no failing witness.')
    assignment = min(polynomial, key=lambda term: (term.bit_count(), term))
    if sum(term & assignment == term for term in polynomial) % 2 != 1:
        raise AssertionError('The independent Boolean witness construction failed.')
    original = (1 << leading) | (assignment & ((1 << leading) - 1))
    if leading == WIDTH - 1:
        original &= ~(1 << (WIDTH - 2))
    return dict(original_input=original, HMR_transcript=assignment >> WIDTH,
                leading_position=leading, phase_or_data_assignment_mask=assignment,
                inside_required_interval=original <= MAXIMUM_INPUT)


def execute(program, initial, cuts):
    """Independent exact semantics, including inactive conditional HMR writes."""
    state = {wire: ZERO for wire in program.wires}
    state.update(initial)
    state.update({'0': ZERO, '1': ONE, 'False': ZERO, 'True': ONE})
    phase, stack = ZERO, [ONE]
    snapshots = {}
    cuts_at = defaultdict(list)
    for name, instruction in cuts.items():
        cuts_at[instruction].append(name)
    maximum_data_terms = maximum_phase_terms = 0
    for index, operation in enumerate(program.operations):
        kind, args = operation.kind, operation.arguments
        active = stack[-1]
        if operation.condition is not None:
            active = product(active, state[operation.condition])
        if kind == 'PUSH_CONDITION':
            stack.append(active)
        elif kind == 'POP_CONDITION':
            if len(stack) == 1:
                raise AssertionError('A native condition frame has an unmatched pop.')
            stack.pop()
        elif active:
            if kind in ('Z', 'CZ', 'CCZ', 'NEG', 'Z_POW'):
                if kind == 'Z_POW' and operation.half_turns.denominator != 1:
                    raise AssertionError('The normalization fixture introduced a non-Pauli phase.')
                if kind != 'Z_POW' or int(operation.half_turns) % 2:
                    phase ^= product(active, *(state[wire] for wire in args))
            elif kind in ('X', 'BIT_INVERT'):
                state[args[0]] ^= active
            elif kind == 'CX':
                state[args[1]] ^= product(active, state[args[0]])
            elif kind == 'CCX':
                state[args[2]] ^= product(active, state[args[0]], state[args[1]])
            elif kind in ('SWAP', 'CSWAP'):
                if kind == 'SWAP':
                    first, second = args
                    enabled = active
                else:
                    control, first, second = args
                    enabled = product(active, state[control])
                difference = product(enabled, state[first] ^ state[second])
                state[first] ^= difference
                state[second] ^= difference
            elif kind in ('BIT_STORE0', 'BIT_STORE1'):
                target = ONE if kind == 'BIT_STORE1' else ZERO
                state[args[0]] ^= product(active, state[args[0]] ^ target)
            elif kind == 'HMR':
                outcome = frozenset((1 << (WIDTH + operation.event),))
                old_quantum = state[args[0]]
                phase ^= product(active, outcome, old_quantum)
                state[args[0]] ^= product(active, old_quantum)
                state[args[1]] ^= product(active, state[args[1]] ^ outcome)
            elif kind == 'R':
                if product(active, state[args[0]]):
                    raise AssertionError(('nonzero_reset', index, args[0]))
            else:
                raise AssertionError(('unsupported_native_instruction', index, kind))
        maximum_phase_terms = max(maximum_phase_terms, len(phase))
        maximum_data_terms = max(maximum_data_terms,
                                 max((len(state[wire]) for wire in args), default=0))
        for name in cuts_at[index + 1]:
            if len(stack) != 1:
                raise AssertionError(('condition_frame_crossed_boundary', name))
            snapshots[name] = (dict(state), phase)
    if len(stack) != 1 or set(snapshots) != set(cuts):
        raise AssertionError('A native condition frame or boundary snapshot remained incomplete.')
    return snapshots, dict(maximum_data_monomials=maximum_data_terms,
                          maximum_phase_monomials=maximum_phase_terms)


class BoundaryOwnersProbe:
    """Observe the same g9 copy and u retention used by initial ownership.

    Only the unchanged two local interface operations are replayed.  The
    high decoder/callback itself is outside this component proof.  Its
    input values are checked, then their exact signs enter the same two
    original ledgers before testing final unpack and restoration.
    """
    def __init__(self):
        self.g9 = self.u = None
        self.captures = self.retentions = 0

    @contextmanager
    def install(self):
        old_prefixes = prefix_normalization._prefixes
        old_erase = shared_normalization_controls._erase_u_from_flags

        @contextmanager
        def prefixes(builder, zero_bits, length, **settings):
            if length != WIDTH - 2 or self.captures:
                raise AssertionError('The prefix observer must capture exactly one full count chain.')
            with old_prefixes(builder, zero_bits, length, **settings) as values:
                self.g9 = builder.alloc_qubits(1)[0]
                builder.cx(values[18], self.g9)
                self.captures += 1
                yield values

        def retain(builder, flags, wire, pending=()):
            if pending or self.retentions or self.g9 is None:
                raise AssertionError('The initial packed-u ownership boundary changed.')
            self.u = wire
            self.retentions += 1

        prefix_normalization._prefixes = prefixes
        shared_normalization_controls._erase_u_from_flags = retain
        try:
            yield self
        finally:
            prefix_normalization._prefixes = old_prefixes
            shared_normalization_controls._erase_u_from_flags = old_erase
        if (self.captures, self.retentions) != (1, 1):
            raise AssertionError('The original normalization/packing observer was not used once.')

    def transfer_original_debts(self, builder, packed, threshold_pass):
        if self.g9 is None or self.u is None:
            raise AssertionError('Both retained initial controls must exist before transfer.')
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(self.g9, outcome)
        builder.free(self.g9)
        threshold_pass.ledger(packed).record(9, outcome)
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(self.u, outcome)
        builder.free(self.u)
        packed._u_debts.append(outcome)


def add_threshold_debts(builder, packed, flags, phase_pass):
    """Exercise repeated and guarded threshold owners without altering data."""
    guards = []
    for _ in range(2):
        zero = builder.alloc_qubits(1)[0]
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(zero, outcome)
        builder.free(zero)
        guards.append(outcome)
    copies = list(builder.alloc_qubits(4))
    for source, target in zip(flags, copies):
        builder.cx(source, target)
    thresholds, _ = thermometer_cleanup.binary_to_thermometer(builder, copies, 10)
    ledger = phase_pass.ledger(packed)
    for threshold, wire in enumerate(thresholds, 1):
        if threshold in (1, 7, 10):
            duplicate = builder.alloc_qubits(1)[0]
            outcome = builder.alloc_bits(1)[0]
            builder.cx(wire, duplicate)
            builder.hmr(duplicate, outcome)
            builder.free(duplicate)
            conditions = tuple(guards[:1] if threshold == 1 else guards)
            builder.push_condition(outcome)
            builder.z(wire)
            for guard in conditions:
                builder.push_condition(guard)
            builder.z(wire)
            for _ in conditions:
                builder.pop_condition()
            builder.pop_condition()
            ledger.record(threshold, outcome, conditions=conditions)
        outcome = builder.alloc_bits(1)[0]
        builder.hmr(wire, outcome)
        builder.free(wire)
        ledger.record(threshold, outcome)
    return guards


def debt_snapshot(packed, phase_pass):
    return dict(flags=list(map(str, packed._flag_debts)),
                higher=list(map(str, packed._u_debts)),
                thresholds=[(tuple(terms), str(outcome), tuple(map(str, conditions)))
                            for terms, outcome, conditions in phase_pass.ledger(packed).pending])


def native_fixture(factory):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(57)
    inputs = list(builder.alloc_qubits(WIDTH))
    flags = ShiftFlags(builder.alloc_qubits(4), 10)
    adapter, observer, phase_pass = factory(), BoundaryOwnersProbe(), PackedThresholdPhasePass()
    live, boundary = {}, {}

    @contextmanager
    def region(name):
        entry = builder.num_allocated_qubits
        with builder.mark(name):
            yield
        live[name] = dict(entry=entry, exit=builder.num_allocated_qubits)

    with adapter.install(), observer.install(), phase_pass.install():
        with region('normalization'):
            normalization_fused.normalize(builder, inputs, flags,
                                            original_input_max=MAXIMUM_INPUT)
            normalization.semilog_align(builder, inputs)
        key = id(builder), tuple(flags)
        indicators = list(adapter.controls.pack_indicators[key])
        if len(indicators) != 2 or observer.g9 is None:
            raise AssertionError('The normalization boundary must retain t, u, and g9.')
        boundary['normalization'] = dict(inputs=list(inputs), flags=list(flags),
                                         indicators=indicators, g9=observer.g9)
        packed = PackedShift(builder, inputs[:14], flags)
        with region('probe_debts'):
            guards = add_threshold_debts(builder, packed, flags, phase_pass)
        with region('pack_shift'):
            packed.pack()
        boundary['pack_shift'] = dict(t=packed.t, u=observer.u, g9=observer.g9,
                                      debts=debt_snapshot(packed, phase_pass))
        with region('probe_initial_owners'):
            observer.transfer_original_debts(builder, packed, phase_pass)
        boundary['probe_initial_owners'] = dict(t=packed.t,
                                                debts=debt_snapshot(packed, phase_pass))
        with region('probe_packed_uses'):
            for _ in range(2):
                with packed.higher_nonzero():
                    pass
        boundary['probe_packed_uses'] = dict(t=packed.t,
                                             debts=debt_snapshot(packed, phase_pass))
        with region('restore_input'):
            with builder.mark('restore_unpack'):
                restored = packed.unpack()
            if packed.pending_measurements or any(
                    ledger.pending or ledger._owned for ledger in phase_pass.ledgers.values()):
                raise AssertionError('Final unpack did not consume every original phase owner.')
            prepared = adapter.prepared[(id(builder), tuple(restored))]
            boundary['restore_unpack'] = dict(monomials=dict(prepared.monomials))
            normalization.semilog_align(builder, inputs, inverse=True)
            normalization_fused.normalize(builder, inputs, restored,
                                            inverse=True, cleanup='thermometer')
            builder.free(km.array(restored))
        for guard in guards:
            builder.free(guard)
    if builder.num_allocated_qubits != WIDTH:
        raise AssertionError('The complete fixture retained a count, helper, or other quantum owner.')
    required_live = {'normalization': (26, 29), 'pack_shift': (29, 25),
                     'restore_input': (23, 22)}
    for name, pair in required_live.items():
        if (live[name]['entry'], live[name]['exit']) != pair:
            raise AssertionError(('selected_region_live_boundary_changed', name, live[name], pair))
    circuit = builder.finish_circuit()
    if circuit.num_qubits > 57:
        raise AssertionError('The emitted component exceeded the selected qubit cap.')
    text = generated_text(circuit)
    return Program(text), dict(inputs=inputs, flags=list(flags), live=live,
        boundary=boundary, peak_qubits=circuit.num_qubits, text=text,
        adapter_metadata=adapter.metadata(),
        boundary_observer=dict(g9_prefix_copies=observer.captures,
                               initial_u_retentions=observer.retentions,
                               initial_lookup_body_not_executed=True))


def region_map(program, text):
    stack, owners, kinds, cuts = [], [], [], {}
    for line in text.splitlines():
        fields = shlex.split(line, comments=True)
        if not fields:
            continue
        kind = fields[0]
        if kind == 'INFO_TAG':
            tag = fields[1]
            if tag.startswith('@enter:'):
                stack.append(tag[7:])
            elif tag.startswith('@exit:'):
                name = tag[6:]
                if not stack or stack.pop() != name:
                    raise AssertionError('Native region marks are not nested.')
                if name in CUTS:
                    cuts[name] = len(owners)
            continue
        if kind in ('DEBUG_PRINT', 'APPEND_TO_REGISTER', 'REGISTER'):
            continue
        owners.append(next((name for name in reversed(stack) if name in REGIONS), None))
        kinds.append(kind)
    if stack or kinds != [operation.kind for operation in program.operations] or set(cuts) != set(CUTS):
        raise AssertionError('The native proof/accounting boundary map is incomplete.')
    return owners, cuts


def expected_debt_phase(snapshot, count, state):
    phase = ZERO
    for bit, outcome in enumerate(snapshot['flags']):
        if count >> bit & 1:
            phase ^= state[outcome]
    if count >= 2:
        for outcome in snapshot['higher']:
            phase ^= state[outcome]
    for terms, outcome, conditions in snapshot['thresholds']:
        if sum(count & term == term for term in terms) % 2:
            phase ^= product(state[outcome], *(state[guard] for guard in conditions))
    return phase


def expected_boundary(fixture, name, source, aligned, count, state):
    inputs = fixture['inputs']
    if name == 'restore_input':
        return {str(wire): value for wire, value in zip(inputs, source)}, ZERO
    expected = {str(wire): value for wire, value in zip(inputs, aligned)}
    detail = fixture['boundary'][name]
    if name == 'normalization':
        expected.update({str(wire): integer_symbol((count >> bit) & 1)
                         for bit, wire in enumerate(detail['flags'])})
        expected[str(detail['indicators'][0])] = integer_symbol(count > 0)
        expected[str(detail['indicators'][1])] = integer_symbol(count >= 2)
        expected[str(detail['g9'])] = integer_symbol(count >= 9)
        return expected, ZERO
    if name == 'restore_unpack':
        expected.update({str(wire): integer_symbol(count & mask == mask)
                         for mask, wire in detail['monomials'].items()})
        return expected, ZERO
    first, second, third, fourth = [(count >> bit) & 1 for bit in range(4)]
    code = (second, third ^ fourth, int(count > 0) ^ first ^ int(count >= 2), fourth)
    for wire, bit in zip(inputs, code):
        expected[str(wire)] ^= integer_symbol(bit)
    expected[str(detail['t'])] = integer_symbol(count > 0)
    if name == 'pack_shift':
        expected[str(detail['u'])] = integer_symbol(count >= 2)
        expected[str(detail['g9'])] = integer_symbol(count >= 9)
    return expected, expected_debt_phase(detail['debts'], count, state)


def prove(program, fixture, cuts, *, only_final=False):
    cases = []
    total = maximum_data_terms = maximum_phase_terms = 0
    selected_cuts = {'restore_input': cuts['restore_input']} if only_final else cuts
    for leading in range(WIDTH):
        source, variables = leading_support(leading)
        aligned, count = mathematical_semilog(source, leading)
        initial = {str(wire): value for wire, value in zip(fixture['inputs'], source)}
        snapshots, sizes = execute(program, initial, selected_cuts)
        for name, (state, phase) in snapshots.items():
            expected, wanted_phase = expected_boundary(fixture, name, source, aligned, count, state)
            for wire in set(program.quantum_wires) | set(expected):
                wrong = state.get(wire, ZERO) ^ expected.get(wire, ZERO)
                if wrong:
                    raise AssertionError(('boundary_data_mismatch', name, str(wire),
                                          symbolic_witness(wrong, leading)))
            wrong_phase = phase ^ wanted_phase
            if wrong_phase:
                raise AssertionError(('boundary_phase_mismatch', name,
                                      symbolic_witness(wrong_phase, leading)))
        total += 1 << variables
        maximum_data_terms = max(maximum_data_terms, sizes['maximum_data_monomials'])
        maximum_phase_terms = max(maximum_phase_terms, sizes['maximum_phase_monomials'])
        cases.append(dict(leading_position=leading, pair_count=count,
                          independent_lower_input_bits=variables,
                          exact_original_inputs=1 << variables))
    if total != STRONGER_EXCLUSIVE_BOUND - 1 or total < MAXIMUM_INPUT:
        raise AssertionError('The leading-support classes did not cover the complete promised interval.')
    return dict(status='ALL_ORIGINAL_INPUTS_AND_ALL_HMR_OUTCOMES_EXACT_PASS',
        required_input_minimum=1, required_input_maximum=MAXIMUM_INPUT,
        stronger_proved_input_minimum=1, stronger_proved_input_maximum=total,
        symbolic_support_classes=cases, independent_HMR_variables=program.measurements,
        equivalent_enumerated_cases=total * (1 << program.measurements),
        all_original_inputs_restored=True, all_quantum_scratch_zero=True,
        exact_semilog_binary_flags_and_initial_t_u_g9=True,
        packed_residual_and_original_debt_interface_preserved=True,
        every_Pauli_phase_coefficient_zero_after_final_repayment=True,
        every_HMR_assignment_proved_without_sampling=True,
        verified_boundaries=list(selected_cuts),
        maximum_data_monomials=maximum_data_terms,
        maximum_phase_monomials=maximum_phase_terms)


def omitted_phase_negative_control(program, fixture, cuts, owners, region):
    start = cuts['restore_unpack'] if region == 'restore_input' else 0
    attempts = 0
    for index, operation in enumerate(program.operations):
        if index < start or owners[index] != region or operation.kind not in ('CZ', 'CCZ'):
            continue
        attempts += 1
        broken = copy(program)
        broken.operations = list(program.operations)
        # A zero phase preserves instruction indices, classical guards, and
        # every HMR event.  Only this one repayment contribution is omitted.
        broken.operations[index] = Operation('Z', ('False',), operation.condition)
        try:
            prove(broken, fixture, cuts, only_final=True)
        except AssertionError as error:
            detail = error.args[0] if error.args else None
            if not isinstance(detail, tuple) or detail[0] != 'boundary_phase_mismatch':
                raise
            return dict(rejected=True, region=region, instruction=index,
                        omitted_operation=operation.kind,
                        tested_phase_candidates=attempts, witness=detail[-1])
    raise AssertionError(('no_effective_phase_negative_control', region, attempts))


def missing_inverse_prefix_cz_negative_control(factory, accepted_measurements):
    """Remove only the first new retained-prefix bilinear repayment."""
    import stage94_bit_normalization_inverse as inverse
    previous = inverse.repay_prefix_phase
    calls = 0

    def missing_cz(builder, outcome, wire_parent, data_bit):
        nonlocal calls
        calls += 1
        if calls == 1:
            builder.push_condition(outcome)
            builder.z(wire_parent)
            builder.pop_condition()
        else:
            previous(builder, outcome, wire_parent, data_bit)

    inverse.repay_prefix_phase = missing_cz
    try:
        broken, fixture = native_fixture(factory)
    finally:
        inverse.repay_prefix_phase = previous
    if calls != WIDTH-2 or broken.measurements != accepted_measurements:
        raise AssertionError('The negative fixture did not isolate one of the twenty prefix repayments.')
    _, cuts = region_map(broken, fixture['text'])
    try:
        prove(broken, fixture, cuts, only_final=True)
    except AssertionError as error:
        detail = error.args[0] if error.args else None
        if not isinstance(detail, tuple) or detail[0] != 'boundary_phase_mismatch':
            raise
        return dict(rejected=True, omitted='first_outcome*retained_parent*original_data_bit',
                    prefix_repayment_calls=calls, omitted_calls=1, witness=detail[-1],
                    emitted_native_sha256=hashlib.sha256(fixture['text'].encode()).hexdigest()), fixture['text']
    raise AssertionError('The missing new inverse-prefix CZ repayment negative control passed.')


def native_budgets(text, owners):
    whole = exact_expectation(text, include_gates=True)
    means = {name: defaultdict(Fraction) for name in REGIONS}
    static = {name: defaultdict(int) for name in REGIONS}
    for gate in whole.pop('charged_gates'):
        name = owners[gate['instruction']]
        if name not in means:
            raise AssertionError('An emitted charged gate has no component resource owner.')
        means[name][gate['category']] += Fraction(gate['probability'])
        static[name][gate['category']] += 1
    categories = ('toffoli_like', 'T', 'generic_rotations')
    rows = {name: dict(mean={category: str(means[name][category]) for category in categories},
                      static=dict(static[name])) for name in REGIONS}
    for category in categories:
        if sum(means[name][category] for name in REGIONS) != Fraction(whole['mean'][category]):
            raise AssertionError('The native component resource split does not sum to its whole.')
    return whole, rows


def bound_sources():
    files = {Path(__file__).resolve()}
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.suffix == '.py' and path.is_relative_to(ROOT):
                files.add(path)
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter-module', default='stage94_bit_normalization')
    parser.add_argument('--adapter-class', default='Stage94BitNormalizationCleanupPass')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    artifact = args.output.with_suffix('.kmx')
    negative_artifact = args.output.with_name(args.output.stem + '_missing_inverse_prefix_CZ.kmx')
    if args.output.exists() or artifact.exists() or negative_artifact.exists():
        parser.error('Use fresh evidence paths; earlier proof outputs are never overwritten.')
    started = time.monotonic()
    module = importlib.import_module(args.adapter_module)
    factory = getattr(module, args.adapter_class)
    program, fixture = native_fixture(factory)
    owners, cuts = region_map(program, fixture['text'])
    proof = prove(program, fixture, cuts)
    print(json.dumps(dict(proof=proof['status'], stronger_inputs=proof['stronger_proved_input_maximum'],
                          symbolic_HMR_variables=program.measurements)), flush=True)
    negatives = {'normalization': omitted_phase_negative_control(
        program, fixture, cuts, owners, 'normalization')}
    negatives['inverse_retained_prefix'], negative_text = missing_inverse_prefix_cz_negative_control(
        factory, program.measurements)
    negatives['inverse_retained_prefix']['emitted_native_artifact'] = negative_artifact.name
    whole, regions = native_budgets(fixture['text'], owners)
    before = {'normalization': Fraction(76), 'restore_input': Fraction(143, 2)}
    targets = {'normalization': Fraction(66), 'restore_input': Fraction(61)}
    after = {name: Fraction(regions[name]['mean']['toffoli_like']) for name in before}
    if any(Fraction(regions[name]['mean'][kind])
           for name in before for kind in ('T', 'generic_rotations')):
        raise AssertionError('Normalization introduced a non-Clifford rotation or T count.')
    saving = sum(before.values()) - sum(after.values())
    target_met = all(after[name] <= targets[name] for name in targets)
    report = dict(status='STAGE94_NORMALIZATION_NATIVE_COMPONENT_PASS' if target_met else
                  'STAGE94_NORMALIZATION_COMPONENT_EXACT_BUT_BUDGET_TARGET_NOT_MET',
        component_proof=proof, omitted_repayment_negative_controls=negatives,
        native_resources=whole, regions=regions, live_boundaries=fixture['live'],
        peak_qubits=fixture['peak_qubits'], production_metadata=fixture['adapter_metadata'],
        boundary_observer=fixture['boundary_observer'],
        before_after={name: dict(before=str(before[name]), after=str(after[name]),
                                saving=str(before[name] - after[name])) for name in before},
        saved_Toffoli_equivalents=str(saving), expected_cost_saving_at57=float(57 * saving),
        projected_expected_full_cost=95328.23775015284-float(57*saving),
        target_met=target_met, source_sha256=bound_sources(),
        emitted_native_artifact=artifact.name,
        emitted_native_sha256=hashlib.sha256(fixture['text'].encode()).hexdigest(),
        elapsed_seconds=time.monotonic()-started,
        scope='New normalization/restore component and unchanged packed/debt boundary contracts',
        compiled_circuit_loaded_as_source=False,
        full_generator_audit_two_builds_all_other_regions_unchanged_and_four_salts_still_required=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with artifact.open('x') as stream:
        stream.write(fixture['text'])
    with negative_artifact.open('x') as stream:
        stream.write(negative_text)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status=report['status'], regions=report['before_after'],
                          saving=str(saving), peak=fixture['peak_qubits'],
                          output=str(args.output))), flush=True)
    if not target_met:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
