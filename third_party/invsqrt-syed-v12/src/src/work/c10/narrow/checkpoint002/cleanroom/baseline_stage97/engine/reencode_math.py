# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Small exact affine-quotient synthesis of a reversible packed remainder code.

Every search state is four eight-bit truth columns on the nine k=2..10
inputs, modulo affine output coordinates. No compiled circuit is an input.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations, product


DOMAIN = tuple(range(2, 11))


def parity(value):
    return int(value).bit_count() & 1


def packed_code(k):
    return ((k >> 1)&1) | ((((k >> 2) ^ (k >> 3))&1) << 1) | ((k&1) << 2) | ((k >> 3) << 3)


def lin(mask, vectors):
    out = 0
    for i, value in enumerate(vectors):
        if (mask >> i)&1:
            out ^= value
    return out


def rank(vectors):
    basis = {}
    for value in vectors:
        while value:
            pivot = value.bit_length()-1
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return len(basis)


def canonical(vectors):
    """RREF and the exact input-coordinate matrix, with fixed zero origin."""
    basis = {}
    for i, value in enumerate(vectors):
        coefficient = 1 << i
        for pivot in sorted(basis, reverse=True):
            if value >> pivot & 1:
                row, mask = basis[pivot]
                value ^= row; coefficient ^= mask
        if not value:
            continue
        pivot = value.bit_length()-1
        for other, (row, mask) in list(basis.items()):
            if row >> pivot & 1:
                basis[other] = row ^ value, mask ^ coefficient
        basis[pivot] = value, coefficient
    ordered = [basis[pivot] for pivot in sorted(basis, reverse=True)]
    return tuple(row for row, _ in ordered), tuple(mask for _, mask in ordered)


def normalized_columns(values):
    return tuple(sum((((value ^ values[0]) >> bit)&1) << i
                     for i, value in enumerate(values[1:])) for bit in range(4))


def state_key(columns):
    if len(columns) != 4 or any(not 0 <= row < 256 for row in columns):
        raise ValueError('A state has four independent eight-bit normalized columns.')
    return sum(row << (8*i) for i, row in enumerate(columns))


def state_columns(key):
    return tuple((key >> (8*i))&255 for i in range(4))


def affine_value(matrix, offset, value):
    return sum((parity(mask & value) ^ ((offset >> i)&1)) << i
               for i, mask in enumerate(matrix))


def invert_matrix(matrix):
    if len(matrix) != 4 or rank(matrix) != 4:
        raise ValueError('An affine output frame must have rank four.')
    rows = list(matrix); inverse = [1 << i for i in range(4)]
    for column in range(4):
        pivot = next(i for i in range(column, 4) if rows[i] >> column & 1)
        rows[column], rows[pivot] = rows[pivot], rows[column]
        inverse[column], inverse[pivot] = inverse[pivot], inverse[column]
        for i in range(4):
            if i != column and rows[i] >> column & 1:
                rows[i] ^= rows[column]; inverse[i] ^= inverse[column]
    if rows != [1, 2, 4, 8]:
        raise AssertionError('The affine matrix elimination did not produce identity.')
    return tuple(inverse)


def initial_state():
    values = tuple(packed_code(k) for k in DOMAIN)
    columns, matrix = canonical(normalized_columns(values))
    offset = affine_value(matrix, 0, values[0])
    return state_key(columns), dict(kind='affine', matrix=list(matrix), offset=offset)


@lru_cache(maxsize=1)
def actions():
    """105 one-Toffoli affine classes: 15 directions times seven planes."""
    result = []
    for direction in range(1, 16):
        annihilator = tuple(mask for mask in range(1, 16) if not parity(mask & direction))
        planes = sorted({tuple(sorted((a, b, a ^ b)))
                         for a, b in combinations(annihilator, 2)})
        if len(planes) != 7:
            raise AssertionError('The direction annihilator is not a three-dimensional space.')
        for plane in planes:
            result.append((direction, plane[0], plane[1]))
    if len(result) != 105:
        raise AssertionError('The affine Toffoli quotient changed size.')
    return tuple(result)


def step(key, action):
    columns = state_columns(key)
    direction, left, right = actions()[action]
    nonlinear = lin(left, columns) & lin(right, columns)
    changed = tuple(value ^ (nonlinear if direction >> i & 1 else 0)
                    for i, value in enumerate(columns))
    normalized, matrix = canonical(changed)
    if len(normalized) != 4:
        raise AssertionError('A reversible map collapsed nine distinct values into an affine hyperplane.')
    return state_key(normalized), dict(kind='shear_frame', direction=direction,
        left=left, right=right, matrix=list(matrix), inverse=False)


def apply_operation(operation, value):
    kind = operation['kind']
    if kind == 'affine':
        return affine_value(operation['matrix'], operation['offset'], value)
    if kind != 'shear_frame':
        raise ValueError('Unknown generated mathematical encoding operation.')
    matrix = operation['matrix']
    def shear(v):
        return v ^ (operation['direction'] if parity(v & operation['left']) and parity(v & operation['right']) else 0)
    if operation.get('inverse', False):
        return shear(affine_value(invert_matrix(matrix), 0, value))
    return affine_value(matrix, 0, shear(value))


def inverse_operation(operation):
    if operation['kind'] == 'shear_frame':
        return dict(operation, inverse=not operation.get('inverse', False))
    inverse = invert_matrix(operation['matrix'])
    return dict(kind='affine', matrix=list(inverse),
                offset=affine_value(inverse, 0, operation['offset']))


def apply_program(program, value, *, inverse=False):
    sequence = [inverse_operation(operation) for operation in reversed(program)] if inverse else program
    for operation in sequence:
        value = apply_operation(operation, value)
    return value


def primitive_shear_frame(direction, left, right):
    """One ordinary Toffoli conjugated by an explicit invertible linear map."""
    if parity(direction & left) or parity(direction & right) or rank((left, right)) != 2:
        raise ValueError('The product controls must be independent and invariant along the toggle direction.')
    target = next(mask for mask in range(1, 16) if parity(mask & direction))
    fourth = next(mask for mask in range(1, 16)
                  if not parity(mask & direction) and rank((left, right, target, mask)) == 4)
    frame = (left, right, target, fourth)
    if affine_value(frame, 0, direction) != 4:
        raise AssertionError('The generalized toggle direction did not map to the Toffoli target.')
    return frame, invert_matrix(frame)


def goal_states():
    """Enumerate the 32 injective fourth-bit choices, obtaining two frames."""
    values = tuple(k % 5 for k in DOMAIN)
    result = {}
    accepted = 0
    for assignment in range(1 << len(DOMAIN)):
        encoded = tuple(value | (((assignment >> i)&1) << 3) for i, value in enumerate(values))
        if len(set(encoded)) != len(DOMAIN):
            continue
        columns, _ = canonical(normalized_columns(encoded))
        if len(columns) != 4:
            raise AssertionError('An injective nine-point remainder code has insufficient affine rank.')
        result.setdefault(state_key(columns), assignment)
        accepted += 1
    if accepted != 32 or len(result) != 2:
        raise AssertionError('The exact remainder-code quotient is not the expected two goals.')
    return tuple(sorted(result)), dict(injective_fourth_bit_assignments=accepted,
                                      affine_equivalence_goal_spaces=len(result))


def output_frames(key):
    """All 16 affine auxiliary choices while fixing the three residue bits."""
    columns = state_columns(key)
    wanted = normalized_columns(tuple(k % 5 for k in DOMAIN))[:3]
    masks = tuple(next(mask for mask in range(16) if lin(mask, columns) == target) for target in wanted)
    if rank(masks) != 3:
        raise AssertionError('The residue output functions are not independent.')
    result = []
    for auxiliary in range(1, 16):
        if rank(masks+(auxiliary,)) != 4:
            continue
        for complement in (0, 1):
            offset = (DOMAIN[0] % 5) | (complement << 3)
            result.append(dict(kind='affine', matrix=list(masks+(auxiliary,)), offset=offset))
    if len(result) != 16:
        raise AssertionError('The affine auxiliary family changed size.')
    return tuple(result)


def evaluate_state_points(key):
    columns = state_columns(key)
    return (0,)+tuple(sum(((column >> i)&1) << bit for bit, column in enumerate(columns))
                     for i in range(8))


def solve_columns(columns, target):
    basis = {}; kernel = []
    for i, value in enumerate(columns, start=0):
        coefficient = 1 << i
        while value:
            pivot = value.bit_length()-1
            if pivot not in basis:
                basis[pivot] = value, coefficient
                break
            row, mask = basis[pivot]; value ^= row; coefficient ^= mask
        if not value:
            kernel.append(coefficient)
    answer = 0
    while target:
        pivot = target.bit_length()-1
        if pivot not in basis:
            return None, tuple(kernel)
        row, mask = basis[pivot]; target ^= row; answer ^= mask
    return answer, tuple(kernel)


def polynomial_value(terms, value):
    return sum(int(value & mask == mask) for mask in terms) & 1


def threshold_plans(encoded_points, compile_polynomial):
    monomials = tuple(mask for mask in range(16) if mask.bit_count() <= 2)
    columns = tuple(sum(int(value & mask == mask) << i for i, value in enumerate(encoded_points))
                    for mask in monomials)
    plans = []
    for threshold in range(3, 9):
        wanted = sum(int(k >= threshold) << i for i, k in enumerate(DOMAIN))
        particular, kernel = solve_columns(columns, wanted)
        if particular is None:
            return None
        if len(kernel) > 7:
            raise AssertionError('Unexpectedly large threshold extension nullspace.')
        choices = []
        for bits in range(1 << len(kernel)):
            selected = particular ^ lin(bits, kernel)
            terms = tuple(mask for i, mask in enumerate(monomials) if selected >> i & 1)
            plan = compile_polynomial(4, terms)
            key = len(plan.products), len(terms), terms
            choices.append((key, plan))
        _, plan = min(choices, key=lambda item: item[0])
        if any(polynomial_value(plan.original, value) != int(k >= threshold)
               for k, value in zip(DOMAIN, encoded_points)):
            raise AssertionError('A synthesized threshold fails its complete valid code domain.')
        plans.append(dict(threshold=threshold, terms=list(plan.original),
            quadratic_products=len(plan.products), compute_ANDs=len(plan.products)+1,
            helper_cleanup='Immediate exact quadratic Z/CZ repayment before the encoded inputs change.',
            control_cleanup='Defer original-k threshold truth to the existing binary-k ledger.'))
    return plans


def choose_output_frame(key, compile_polynomial):
    points = evaluate_state_points(key); candidates = []
    for frame in output_frames(key):
        encoded = tuple(apply_operation(frame, value) for value in points)
        plans = threshold_plans(encoded, compile_polynomial)
        if plans is None:
            continue
        candidates.append(((sum(p['compute_ANDs'] for p in plans),
                            tuple(frame['matrix']), frame['offset']), frame, encoded, plans))
    if not candidates:
        return None
    key_cost, frame, encoded, plans = min(candidates, key=lambda item: item[0])
    return dict(frame=frame, encoded_valid_points=list(encoded), threshold_plans=plans,
                total_threshold_compute_ANDs=key_cost[0], affine_output_frames_checked=16,
                threshold_costs_by_affine_frame=sorted(set(item[0][0] for item in candidates)))


def flag_schedule(demands):
    """Exact C5-only lifetimes; C4 flags are explicitly closed separately."""
    family = ((),)+tuple((a,) for a in range(1, 8))+tuple(sorted({tuple(sorted((a,b,a^b)))
        for a,b in combinations(range(1, 8), 2)}))
    dimension = lambda space: {0:0, 1:1, 3:2}[len(space)]
    states = {0:(0, ())}
    for mask in demands:
        following = {}
        for j, after in enumerate(family):
            if mask not in after:
                continue
            following[j] = min((cost+dimension(after)-dimension(set(family[i]) & set(after)), path+(j,))
                               for i, (cost, path) in states.items())
        states = following
    cost, chosen = min(states.values())
    return dict(products_per_direction=cost, chosen_subspaces=[list(family[i]) for i in chosen],
                at_most_two_flags=True, starts_empty_and_erases_all_at_end=True,
                C4_interleaving_allowed=False)


def encoding_product_lower_bound():
    source, _ = initial_state(); columns = state_columns(source)
    remainder = normalized_columns(tuple(k % 5 for k in DOMAIN))[:3]
    missing = rank(columns+remainder)-4
    if missing != 3:
        raise AssertionError('The independently derived three-product residue lower bound changed.')
    return dict(minimum_encoding_Toffolis=missing,
        reason='Each product enlarges the affine span of all computed Boolean functions by at most one; the three remainder outputs are independent modulo all original affine functions.',
        scope='Exact k mod5 output in three wires on k2..10, with a total reversible four-wire permutation and free affine frames.')


def binary_threshold_terms(threshold):
    monomials = tuple(mask for mask in range(16) if mask.bit_count() <= 2 or mask == 7)
    columns = tuple(sum(int(k & mask == mask) << k for k in range(11)) for mask in monomials)
    target = sum(int(k >= threshold) << k for k in range(11))
    particular, kernel = solve_columns(columns, target)
    if particular is None:
        raise AssertionError('A logical threshold has no common-cubic binary-k repayment.')
    choices = []
    for bits in range(1 << len(kernel)):
        selected = particular ^ lin(bits, kernel)
        terms = tuple(mask for i, mask in enumerate(monomials) if selected >> i & 1)
        choices.append(((int(7 in terms), len(terms), terms), terms))
    return min(choices)[1]


def verify_threshold_measurements(plans):
    count = 0; negative = False
    for plan in plans:
        terms = tuple(plan['terms'])
        for q in range(16):
            computed = polynomial_value(terms, q)
            for outcome in (0, 1):
                correction = sum(outcome & int(q & term == term) for term in terms) & 1
                if (outcome & computed) ^ correction:
                    raise AssertionError('Encoded-threshold helper HMR phase was not repaid.')
                count += 1
                if terms:
                    negative |= bool((outcome & computed) ^ (outcome & polynomial_value(terms[:-1], q)))
    thresholds = (1,)+tuple(plan['threshold'] for plan in plans)
    repayments = [binary_threshold_terms(threshold) for threshold in thresholds]
    if 7 not in repayments[0]:
        raise AssertionError('The external t phase no longer supplies an independent common-cubic coefficient.')
    checked = 0
    for outcomes in range(1 << len(thresholds)):
        combined = set()
        for index, terms in enumerate(repayments):
            if outcomes >> index & 1:
                combined.symmetric_difference_update(terms)
        if any(term.bit_count() > 2 and term != 7 for term in combined):
            raise AssertionError('Threshold debts require more than the one common cubic.')
        for k in range(11):
            branch = sum(((outcomes >> i)&1) & int(k >= threshold)
                         for i, threshold in enumerate(thresholds)) & 1
            if branch ^ polynomial_value(combined, k):
                raise AssertionError('A deferred threshold branch was not repaid on every legal shift.')
            checked += 1
    if not negative:
        raise AssertionError('The missing-helper-phase negative control was not detected.')
    return dict(helper_all_input_outcome_cases=count, logical_ledger_all_outcome_cases=checked,
        missing_helper_phase_negative_rejected=True, common_cubic='f0*f1*f2',
        at_most_one_conditioned_CCZ_for_merged_ledger=True,
        standalone_ledger_CCZ_expected_E=0.5,
        extra_CCZ_expected_E_when_existing_external_t_ledger_is_preserved=0,
        merge_external_t_and_original_binary_k_restoration_required=True)
