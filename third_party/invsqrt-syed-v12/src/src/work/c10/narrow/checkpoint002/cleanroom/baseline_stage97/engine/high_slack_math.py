# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Fresh exact twelve-swap HIGH8 routing with four flag products.

The source family gives one merge allowance to each of two odd count
branches and keeps count four geodesic. The four mandatory opposite-pair
gates and the odd-cycle diameter incidence bound derive the eligible count
pairs. No selected gate list, report, seed, clock, or numerical input exists.
Fixed deterministic visit caps fail closed; successful routes are proved
on every high word, packed input, and local flag measurement outcome.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations

from c4_routing_math import flag_terms
from c20_routing_math import packed_states
from high_geodesic_math import apply, cycle_labels, swap_tuple
from reencode_math import flag_schedule, parity


class FamilyLimit(RuntimeError):
    """A fixed source-family cap, never a clock-dependent selection."""


def planes():
    return tuple(sorted({tuple(sorted((first, second, first ^ second)))
                         for first, second in combinations(range(1, 8), 2)}))


def relative(first, second):
    inverse = [0]*len(first)
    for position, label in enumerate(first):
        inverse[label] = position
    return tuple(inverse[label] for label in second)


def multiplicities(budgets):
    total = sum(budgets)
    numerators = tuple(2*sum(value for count, value in enumerate(budgets) if parity(mask & count))-total
                       for mask in range(1, 8))
    if any(value < 0 or value % 4 for value in numerators):
        return None
    result = tuple(value//4 for value in numerators)
    if any(sum(result[mask-1] for mask in range(1, 8) if parity(mask & count)) != budgets[count]
           for count in range(8)):
        raise AssertionError('The exact control incidence inverse failed.')
    return result


def source_families():
    distances = tuple(cycle_labels(tuple((position-count) % 8 for position in range(8)))[1]
                      for count in range(8))
    result = []
    for exceptional in combinations(range(1, 8, 2), 2):
        budgets = tuple(distance+2*int(count in exceptional) for count, distance in enumerate(distances))
        counts = multiplicities(budgets)
        if counts is None or sum(counts) != 12 or budgets[4] != 4:
            continue
        if any(count not in exceptional and
               sum(counts[mask-1] for mask in range(4, 8) if parity(mask & count)) > 1
               for count in range(1, 8, 2)):
            continue
        result.append((exceptional, counts))
    if len(result) != 4:
        raise AssertionError('The source-derived odd-pair diameter family changed.')
    return tuple(result)


def search_family(exceptional, initial_counts, total, *, family_limit=10000, total_limit=100000):
    identity = tuple(range(8))
    start = tuple(tuple((position-count) % 8 for position in range(8)) for count in range(1, 8))
    family = planes()
    plane_bits = tuple(sum(1 << (mask-1) for mask in plane) for plane in family)
    masks = tuple(mask for mask in range(1, 8) if initial_counts[mask-1])
    active = {mask: tuple(count-1 for count in range(1, 8) if parity(mask & count)) for mask in masks}
    pair_indices = tuple(combinations(range(8), 2))
    cuts = {mask: tuple(pair for pair in pair_indices if parity(mask & pair[0]) != parity(mask & pair[1]))
            for mask in masks}
    failed = set()
    counters = dict(visits=0, transitions=0, maximum_depth=0, flag_cover_rejections=0,
                    pair_budget_rejections=0, common_partition_rank_rejections=0)

    @lru_cache(maxsize=1024)
    def additional_planes(required, before):
        if not required & ~plane_bits[before]:
            return 0
        reached = {plane_bits[before]}
        for changes in range(1, len(family)+1):
            reached = {covered | following for covered in reached for following in plane_bits}
            if any(not required & ~covered for covered in reached):
                return changes
        raise AssertionError('The complete Fano-plane family failed to cover a control.')

    def search(state, remaining, plane, products, depth):
        key = state, remaining, plane, products
        if key in failed:
            return None
        counters['visits'] += 1
        total['visits'] += 1
        counters['maximum_depth'] = max(counters['maximum_depth'], depth)
        if total['visits'] > total_limit:
            raise RuntimeError('The fixed total HIGH8 source-synthesis cap was exceeded.')
        if counters['visits'] > family_limit:
            raise FamilyLimit('The fixed per-family HIGH8 synthesis cap was exceeded.')
        if sum(remaining) != 12-depth:
            raise AssertionError('The high route left its exact swap multiplicities.')
        if not sum(remaining):
            if state == (identity,)*7:
                return ()
            failed.add(key)
            return None
        required = sum(1 << index for index, value in enumerate(remaining) if value)
        if plane >= 0 and products+additional_planes(required, plane) > 4:
            counters['flag_cover_rejections'] += 1
            failed.add(key)
            return None
        budgets = tuple(sum(remaining[mask-1] for mask in masks if parity(mask & count))
                        for count in range(8))
        branch_info = tuple(cycle_labels(value) for value in state)
        pair_info = {(0, count): information for count, information in enumerate(branch_info, start=1)}
        for first, second in combinations(range(1, 8), 2):
            pair_info[first, second] = cycle_labels(relative(state[first-1], state[second-1]))
        for (first, second), (_labels, distance) in pair_info.items():
            budget = budgets[first ^ second]
            if distance > budget or (budget-distance) & 1:
                counters['pair_budget_rejections'] += 1
                failed.add(key)
                return None
        candidates = []
        for mask in masks:
            if not remaining[mask-1]:
                continue
            monotone = tuple(branch for branch in active[mask]
                             if branch_info[branch][1] == budgets[branch+1])
            if monotone:
                blocks = {tuple(branch_info[branch][0][position] for branch in monotone) for position in range(8)}
                if remaining[mask-1] > 8-len(blocks):
                    counters['common_partition_rank_rejections'] += 1
                    failed.add(key)
                    return None
            if plane >= 0 and mask in family[plane]:
                destinations = ((plane, products),)
            else:
                charge = 2 if plane < 0 else products+1
                if charge > 4:
                    continue
                destinations = tuple((index, charge) for index, values in enumerate(family) if mask in values)
            requirements = tuple((pair_info[pair], budgets[pair[0] ^ pair[1]]) for pair in cuts[mask])
            for left in range(8):
                for right in range(left+1, 8):
                    if depth == 0 and (left or right > 4):
                        continue
                    if any(labels[left] != labels[right] and budget-distance < 2
                           for (labels, distance), budget in requirements):
                        continue
                    for destination, charge in destinations:
                        candidates.append((-remaining[mask-1], charge, mask, left, right, destination))
        for _priority, charge, mask, left, right, destination in sorted(candidates):
            following = tuple(swap_tuple(value, left, right) if branch in active[mask] else value
                              for branch, value in enumerate(state))
            next_counts = list(remaining)
            next_counts[mask-1] -= 1
            counters['transitions'] += 1
            suffix = search(following, tuple(next_counts), destination, charge, depth+1)
            if suffix is not None:
                return ((mask, left, right),)+suffix
        failed.add(key)
        return None

    peeled = search(start, initial_counts, -1, 0, 0)
    route = None if peeled is None else tuple(reversed(peeled))
    metadata = dict(exceptional_counts=list(exceptional), initial_multiplicities=list(initial_counts),
                    fixed_family_visit_cap=family_limit, fixed_total_visit_cap=total_limit,
                    exhausted_residuals=len(failed), **counters)
    return route, metadata


@lru_cache(maxsize=1)
def synthesize():
    total = {'visits': 0}
    history = []
    for exceptional, counts in source_families():
        try:
            route, search = search_family(exceptional, counts, total)
        except FamilyLimit:
            history.append(dict(exceptional_counts=list(exceptional), status='FIXED_FAMILY_CAP'))
            continue
        history.append(dict(search, status='FOUND' if route is not None else 'EXHAUSTED'))
        if route is not None:
            break
    else:
        raise RuntimeError('The deterministic HIGH8 source family did not synthesize its charged route.')
    schedule = flag_schedule([mask for mask, _left, _right in route])
    if len(route) != 12 or schedule['products_per_direction'] != 4:
        raise AssertionError('The synthesized high route changed its charged twelve-plus-four dimensions.')
    data_cases = packed_cases = outcome_cases = 0
    for count in range(11):
        for word in range(1 << 8):
            original = tuple((word >> bit) & 1 for bit in range(8))
            expected = tuple(original[(index-count) % 8] for index in range(8))
            actual = apply(route, count, original)
            if actual != expected or apply(tuple(reversed(route)), count, actual) != original:
                raise AssertionError('The fresh high route changed an exact input or failed its inverse.')
            data_cases += 1
    for mask in sorted({operation[0] for operation in route}):
        terms = flag_terms(mask)
        products = tuple(term for term in terms if term.bit_count() == 2)
        if not products or any(not term & (1 << 5) for term in products):
            raise AssertionError('A fresh high flag is not one common-factor product.')
        for assignment in range(64):
            actual = sum(int(assignment & term == term) for term in terms) & 1
            affine = sum(int(assignment & term == term) for term in terms if term.bit_count() < 2) & 1
            factor = sum(int(assignment & (term ^ (1 << 5)) == (term ^ (1 << 5))) for term in products) & 1
            if actual != affine ^ (((assignment >> 5) & 1) & factor):
                raise AssertionError('The source flag does not equal its charged one-product polynomial.')
            for outcome in range(2):
                if (outcome & actual) ^ (sum(outcome & int(assignment & term == term) for term in terms) & 1):
                    raise AssertionError('A local flag measurement has an unpaid sign.')
                outcome_cases += 1
        for row in packed_states():
            assignment = row['q'] | (row['t'] << 4) | (row['u'] << 5)
            if (sum(int(assignment & term == term) for term in terms) & 1) != parity(mask & row['k']):
                raise AssertionError('The fresh count flag changed a valid packed input.')
            packed_cases += 1
    certificate = dict(source='eight-cycle, two odd merge allowances, and exact linear control incidence',
                       family='count-four-geodesic-derived-odd-pairs', eligible_families=len(source_families()),
                       search_history=history, total_search_visits=total['visits'],
                       total_swaps_per_direction=len(route), flag_products_per_direction=4,
                       maximum_live_flags=2, complete_high_word_count_cases=data_cases,
                       complete_packed_flag_cases=packed_cases, complete_flag_outcome_cases=outcome_cases,
                       quantum_phase_from_routing_exactly_zero=True,
                       helper_cleanup='Immediate exact Z/CZ with no external debt',
                       no_wall_clock_random_or_saved_witness_selection=True,
                       reads_saved_witness_or_circuit=False)
    return route, schedule, certificate
