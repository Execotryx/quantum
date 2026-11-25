# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Portable deterministic mathematical synthesis for the packed C20 encoding.

This module contains pure finite mathematical derivations copied from the
independently checked source search. It reads no saved witness or circuit.
"""
from functools import lru_cache
import resource
import sys
import time
import reencode_math as math4
import crt_c10_synthesis
import c20_routing_math as routing_math
import quadratic_terms


def mathematics():
    return math4,sys.modules[__name__]


def ball(root, check):
    """Complete affine-quotient radius two, at most 11,131 states."""
    seen = {root:(0, None, None)}
    frontier = [root]; layers = [1]; transitions = 0
    for depth in (1, 2):
        following = []
        for key in frontier:
            for action in range(len(math4.actions())):
                other, _ = math4.step(key, action); transitions += 1
                if transitions % 1024 == 0: check()
                if other not in seen:
                    seen[other] = depth, key, action
                    following.append(other)
        layers.append(len(following)); frontier = following
        if len(seen) > 11131:
            raise AssertionError('The declared complete radius-two combinatorial bound was exceeded.')
    return seen, dict(layers=layers, states=len(seen), transitions=transitions,
                     complete_radius=2, state_key_bits=32)

def build_program(start_frame, output_frame, left, right, meet):
    beginning = []; cursor = meet
    while left[cursor][1] is not None:
        _, parent, action = left[cursor]
        other, operation = math4.step(parent, action)
        if other != cursor: raise AssertionError('A forward BFS edge is inconsistent.')
        beginning.append(operation); cursor = parent
    program = [start_frame]+list(reversed(beginning))
    cursor = meet
    while right[cursor][1] is not None:
        _, parent, action = right[cursor]
        other, operation = math4.step(parent, action)
        if other != cursor: raise AssertionError('A backward BFS edge is inconsistent.')
        program.append(math4.inverse_operation(operation)); cursor = parent
    return program+[output_frame]

def certify_program(program):
    outputs = [math4.apply_program(program, value) for value in range(16)]
    if len(set(outputs)) != 16:
        raise AssertionError('The encoding is not a total reversible permutation.')
    for value, encoded in enumerate(outputs):
        if math4.apply_program(program, encoded, inverse=True) != value:
            raise AssertionError('The encoded residual did not restore on the complete 4-bit cube.')
    for k in range(2, 11):
        if outputs[math4.packed_code(k)] & 7 != k % 5:
            raise AssertionError('The generated nonlinear encoding has the wrong remainder.')
    count = sum(operation['kind'] == 'shear_frame' for operation in program)
    for operation in program:
        if operation['kind'] == 'shear_frame':
            frame, inverse = math4.primitive_shear_frame(operation['direction'], operation['left'], operation['right'])
            for value in range(16):
                framed = math4.affine_value(frame, 0, value)
                changed = framed ^ (4 if framed & 3 == 3 else 0)
                result = math4.affine_value(inverse, 0, changed)
                desired = value ^ (operation['direction'] if math4.parity(operation['left'] & value)
                                    and math4.parity(operation['right'] & value) else 0)
                if result != desired:
                    raise AssertionError('A claimed one-Toffoli affine shear is incorrect.')
    return dict(complete_four_bit_permutation=outputs, both_directions_full_cube_checked=True,
                encoding_Toffolis=count, quantum_helpers_for_encoding=0,
                nonlinear_primitives_each_exactly_one_Toffoli=True, phase_from_encoding_exactly_zero=True)

def certify_phase(candidate):
    program = candidate['encode_program']; c5 = candidate['c5_network']; c4 = candidate['c4_network']
    if len(c4) != 4 or len(c5) != 7:
        raise AssertionError('The charged C4/C5 physical-word lengths changed.')
    for network, size, maximum_mask in ((c4, 4, 3), (c5, 5, 7)):
        for action in network:
            if (not 1 <= action['control_mask'] <= maximum_mask or len(action['swap']) != 2
                    or len(set(action['swap'])) != 2 or any(not 0 <= i < size for i in action['swap'])):
                raise AssertionError('A charged routing action has an invalid control or transposition.')
    if candidate['encoded_valid_points'] != [math4.apply_program(program, math4.packed_code(k)) for k in range(2, 11)]:
        raise AssertionError('The recorded encoded point labels differ from the exact program.')
    plan_by_j = {row['threshold']:row for row in candidate['threshold_plans']}
    if len(candidate['threshold_plans']) != 6 or set(plan_by_j) != set(range(3, 9)):
        raise AssertionError('The six charged encoded thresholds are not complete and distinct.')
    for plan in candidate['threshold_plans']:
        actual = quadratic_terms.compile_polynomial(4, plan['terms'])
        if len(actual.products) != plan['quadratic_products'] or plan['compute_ANDs'] != len(actual.products)+1:
            raise AssertionError('An encoded threshold omitted its actual product or masking cost.')
    packed_rows = routing_math.packed_states()
    control_rows = phase_feature_rows = 0
    for state in packed_rows:
        k, q, t, u = state['k'], state['q'], state['t'], state['u']
        encoded = math4.apply_program(program, q)
        if math4.apply_program(program, encoded, inverse=True) != q:
            raise AssertionError('The nonlinear code failed on arbitrary k0/1 residual data.')
        def c5_control(mask):
            return (u & math4.parity(mask & encoded)) ^ ((mask & 1) & (t ^ u))
        for mask in range(1, 8):
            if c5_control(mask) != math4.parity(mask & (k % 5)):
                raise AssertionError('An encoded one-product remainder flag has the wrong value.')
            control_rows += 1
        for j in range(1, 9):
            threshold = t if j == 1 else u if j == 2 else u & math4.polynomial_value(plan_by_j[j]['terms'], encoded)
            if threshold != int(k >= j):
                raise AssertionError('An encoded threshold changed a phase feature.')
        for original_bit in range(20):
            word = list(range(20))
            def apply(action, kind, active):
                if not active: return
                a, b = action['swap']
                pairs = ([((5*a+16*r)%20, (5*b+16*r)%20) for r in range(5)] if kind == 'c4'
                         else [((5*p+16*a)%20, (5*p+16*b)%20) for p in range(4)])
                for left, right in pairs: word[left], word[right] = word[right], word[left]
            for action in c4: apply(action, 'c4', math4.parity(action['control_mask'] & k))
            for action in c5: apply(action, 'c5', c5_control(action['control_mask']))
            if word != [(i-k)%20 for i in range(20)]:
                raise AssertionError('C4 then encoded C5 did not rotate by the original shift.')
            rotated = [int(label == original_bit) for label in word]
            # Each of the 20 base and 8 overflow features is tested as an
            # independent symbol. This proves every frozen angle assignment.
            if rotated != [int((i-k)%20 == original_bit) for i in range(20)]:
                raise AssertionError('A base phase feature changed.')
            for j in range(8):
                actual = rotated[j] & (t if j == 0 else u if j == 1 else
                    u & math4.polynomial_value(plan_by_j[j+1]['terms'], encoded))
                expected = int((j-k)%20 == original_bit) & int(k >= j+1)
                if actual != expected: raise AssertionError('An overflow phase feature changed.')
            for action in reversed(c5): apply(action, 'c5', c5_control(action['control_mask']))
            for action in reversed(c4): apply(action, 'c4', math4.parity(action['control_mask'] & k))
            if word != list(range(20)): raise AssertionError('The C20 data word did not restore.')
            phase_feature_rows += 1
    measurement = math4.verify_threshold_measurements(candidate['threshold_plans'])
    flag_cases = 0
    for mask in range(1, 8):
        terms = [(32 | (1 << bit)) for bit in range(3) if mask >> bit & 1]
        if mask & 1: terms.extend((16, 32))
        for assignment in range(64):
            computed = (((assignment >> 5)&1) & math4.parity(mask & assignment)) ^ (
                (mask & 1) & (((assignment >> 4) ^ (assignment >> 5))&1))
            for outcome in (0, 1):
                correction = outcome & math4.polynomial_value(terms, assignment)
                if (outcome & computed) ^ correction:
                    raise AssertionError('An encoded C5 flag has an unpaid HMR phase.')
                flag_cases += 1
    return dict(packed_control_rows=control_rows, packed_input_basis_feature_cases=phase_feature_rows,
        all_28_features_separately_identical=True, arbitrary_word_by_coordinate_linearity=True,
        original_input_and_encoded_q_restored=True, threshold_measurement_proof=measurement,
        encoded_flag_all_input_outcome_cases=flag_cases,
        emitted_C5_flag_HMR_and_complete_generator_composition_pending=True)

def run(args, report, check):
    lower = math4.encoding_product_lower_bound(); report['encoding_lower_bound'] = lower
    goals, goal_proof = math4.goal_states(); report['goal_quotient'] = goal_proof
    start, frame = math4.initial_state()
    left, left_meta = ball(start, check); report['left_radius2'] = left_meta
    finite = crt_c10_synthesis.screen()
    if finite['outcome'] != 'FOUND_EXACT_NETWORK' or finite['minimum_length'] != 7:
        raise AssertionError('Fresh source-mathematical C5 synthesis failed.')
    c5 = [dict(kind='c5', control_mask=action['control_mask'], swap=action['swap']) for action in finite['network']]
    c4, c4_proof = routing_math.c4_synthesis()
    controls = math4.flag_schedule([action['control_mask'] for action in c5])
    report['fresh_C5_synthesis'] = finite; report['fresh_C4_synthesis'] = c4_proof
    report['separated_C5_flag_schedule'] = controls
    report['goal_records'] = []; candidates = []
    for goal in goals:
        check()
        right, right_meta = ball(goal, check)
        output = math4.choose_output_frame(goal, quadratic_terms.compile_polynomial)
        if output is None: raise AssertionError('A remainder code has no bounded quadratic threshold extension.')
        meet_options = [(left[key][0]+right[key][0], key) for key in right if key in left]
        record = dict(goal_state=goal, right_radius2=right_meta, threshold_output_frame=output,
                      complete_encoding_length_checked=4)
        report['goal_records'].append(record)
        if not meet_options:
            record['status'] = 'NO_ENCODING_WITH_AT_MOST_FOUR_TOFFOLIS_IN_AFFINE_QUOTIENT'
            continue
        length, meet = min(meet_options)
        if length < lower['minimum_encoding_Toffolis']:
            raise AssertionError('The exact synthesis contradicted its function-span lower bound.')
        program = build_program(frame, output['frame'], left, right, meet)
        certificate = certify_program(program)
        if certificate['encoding_Toffolis'] != length:
            raise AssertionError('The decoded reversible program has the wrong product count.')
        p5 = controls['products_per_direction']; threshold_cost = output['total_threshold_compute_ANDs']
        # Both C4 directions: 40 swaps + 4 flag products. Both C5 directions:
        # 56 swaps + 2*P5. Encode/decode: 2*C. Threshold computes + eight
        # phase-feature products + one shared-u lifecycle of two ANDs.
        cost = 110+2*p5+2*length+threshold_cost
        candidate = dict(goal_state=goal, encode_program=program, encode_certificate=certificate,
            encoded_valid_points=output['encoded_valid_points'], threshold_plans=output['threshold_plans'],
            c4_network=c4, c5_network=c5, C5_flag_schedule=controls,
            C4_flag_products_per_direction=2, C4_flag_interleaving_across_encoding=False,
            complete_low_kernel_E=cost, baseline_low_kernel_E=144, projected_low_E_saving=144-cost,
            budget=dict(C4_swaps_both_directions=40, C5_swaps_both_directions=56,
                C4_flags_both_directions=4, C5_flags_both_directions=2*p5,
                encode_decode_Toffolis=2*length, threshold_compute_ANDs=threshold_cost,
                overflow_feature_ANDs=8, shared_u_lifecycle_ANDs=2,
                extra_generic_rotations=0, extra_T_gates=0,
                extra_conditioned_CCZ_when_external_t_ledger_preserved=0,
                standalone_merged_threshold_ledger_expected_CCZ=0.5),
            width_argument='54 unchanged phase inputs + shared u + at most two helpers = 57; encoding has zero helpers.',
            actual_emitted_width_depth_ANDs_and_HMR_composition_pending=True)
        candidate['mathematical_phase_certificate'] = certify_phase(candidate)
        record.update(status='EXACT_REVERSIBLE_REMAINDER_ENCODING_FOUND', minimum_encoding_Toffolis=length,
                      complete_low_kernel_E=cost, projected_low_E_saving=144-cost)
        candidates.append(candidate)
    if candidates:
        report['best_completed_witness'] = min(candidates, key=lambda c:(c['complete_low_kernel_E'],c['goal_state']))
        if report['best_completed_witness']['projected_low_E_saving'] >= 8:
            report['candidate'] = report['best_completed_witness']
            return 'FOUND_COMPETITIVE_REENCODED_PHASE_COMPONENT_EMISSION_PENDING'
        return 'EXACT_ENCODINGS_FOUND_BUT_COMPLETE_LIFECYCLE_NOT_COMPETITIVE'
    return 'NO_AT_MOST_FOUR_TOFFOLI_REMAINDER_ENCODING'


@lru_cache(maxsize=1)
def synthesize():
    """Complete both finite radius-two goal searches, or fail without a candidate.

    The internal guard is supplementary to the parent's process-group watchdog.
    Elapsed time never chooses between candidates. No report, saved route,
    compiled circuit, or previous witness is opened by this construction.
    """
    math4,search=mathematics();started=time.monotonic();report={}
    def check():
        if time.monotonic()-started>45:
            raise TimeoutError('Fresh complete finite encoding synthesis exceeded45 seconds.')
        rss_units = 1 if sys.platform == 'darwin' else 1024
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*rss_units>512*(1<<20):
            raise MemoryError('Fresh encoding synthesis exceeded its conservative512MiB process budget.')
    status=search.run(None,report,check);check()
    if status!='FOUND_COMPETITIVE_REENCODED_PHASE_COMPONENT_EMISSION_PENDING':
        raise AssertionError('Fresh mathematical encoding did not produce the declared competitive candidate.')
    candidate=report['candidate']
    if (candidate['encode_certificate']['encoding_Toffolis']!=3
            or candidate['C5_flag_schedule']['products_per_direction']!=4
            or candidate['budget']['threshold_compute_ANDs']!=11
            or len(candidate['c4_network'])!=4 or len(candidate['c5_network'])!=7
            or candidate['complete_low_kernel_E']!=135):
        raise AssertionError('The current fixed seven-swap mathematical construction changed its measured target.')
    return candidate,dict(status='FRESH_COMPLETE_PARAMETER_SYNTHESIS',
        mathematical_inputs='k=0..10, packed four-bit code, cyclic C4/C5 permutations',
        no_saved_witness_or_circuit_input=True,selection_is_deterministic=True,
        both_goal_classes_completed=len(report['goal_records'])==2,
        encoding_lower_bound=report['encoding_lower_bound'],
        left_radius2=report['left_radius2'],goal_records=report['goal_records'],
        complete_search_status=status)
