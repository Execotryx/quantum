# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Deterministic from-source synthesis of the fourteen-swap high rotation.

The mathematical inputs are the eight-cycle and the two low count bits.
There is no gate-list, witness, profile, file, random seed, or wall-clock input.
A fixed state cap fails closed; it never selects a partial search result.
"""
from __future__ import annotations

from functools import lru_cache

from c4_routing_math import flag_terms
from c20_routing_math import packed_states


def parity(value):
    return int(value).bit_count() & 1


def cycle_labels(permutation):
    labels = [-1] * len(permutation)
    cycles = 0
    for start in range(len(permutation)):
        if labels[start] >= 0:
            continue
        at = start
        while labels[at] < 0:
            labels[at] = cycles
            at = permutation[at]
        if at != start:
            raise AssertionError('A cyclic-route residual is not a permutation.')
        cycles += 1
    return tuple(labels), len(permutation) - cycles


def swap_tuple(permutation, left, right):
    value = list(permutation)
    value[left], value[right] = value[right], value[left]
    return tuple(value)


def apply(operations, count, word):
    word = list(word)
    for mask, left, right in operations:
        if parity(count & mask):
            word[left], word[right] = word[right], word[left]
    return tuple(word)


def search_low_count(*, state_limit=500000):
    """Find a distance-optimal route for counts zero through three on eight bits.

The three target distances are seven, six, seven. Every linear two-bit flag
activates two branches, so ten swaps are a lower bound. An attaining path
must split a cycle in both active residual permutations at every step.
"""
    width = 8
    identity = tuple(range(width))
    start = tuple(tuple((index - count) % width for index in range(width))
                  for count in range(1, 4))
    initial_distances = tuple(cycle_labels(permutation)[1] for permutation in start)
    target_length = sum(initial_distances) // 2
    if sum(initial_distances) % 2 or target_length != 10:
        raise AssertionError('The exact eight-cycle lower bound changed.')
    failed = set()
    visits = transitions = 0

    def search(state, depth):
        nonlocal visits, transitions
        if state in failed:
            return None
        visits += 1
        if visits > state_limit:
            raise RuntimeError('The deterministic high-route state cap was exceeded.')
        rows = tuple(cycle_labels(permutation) for permutation in state)
        labels = tuple(row[0] for row in rows)
        distances = tuple(row[1] for row in rows)
        if sum(distances) != 2 * (target_length - depth):
            raise AssertionError('A high-route search step violated its exact distance budget.')
        if not any(distances):
            if state != (identity,) * 3:
                raise AssertionError('A zero-distance high-route state is not identity.')
            return ()
        incidence = (distances[0] + distances[2] - distances[1],
                     distances[1] + distances[2] - distances[0],
                     distances[0] + distances[1] - distances[2])
        if any(value < 0 or value & 1 for value in incidence):
            failed.add(state)
            return None
        candidates = []
        for mask in range(1, 4):
            remaining = incidence[mask - 1] // 2
            if not remaining:
                continue
            active = tuple(index for index, count in enumerate(range(1, 4))
                           if parity(mask & count))
            if len(active) != 2:
                raise AssertionError('A two-bit linear flag must activate exactly two nonzero counts.')
            for left in range(width):
                for right in range(left + 1, width):
                    # A simultaneous cyclic translation fixes all targets.
                    # Every first unordered pair has this representative.
                    if depth == 0 and (left != 0 or right > width // 2):
                        continue
                    if all(labels[index][left] == labels[index][right] for index in active):
                        candidates.append((-remaining, mask, left, right, active))
        for _priority, mask, left, right, active in sorted(candidates):
            other = tuple(swap_tuple(permutation, left, right) if index in active else permutation
                          for index, permutation in enumerate(state))
            transitions += 1
            suffix = search(other, depth + 1)
            if suffix is not None:
                return ((mask, left, right),) + suffix
        failed.add(state)
        return None

    peeled = search(start, 0)
    if peeled is None:
        raise AssertionError('The complete declared high-route family has no ten-swap construction.')
    operations = tuple(reversed(peeled))
    if len(operations) != target_length:
        raise AssertionError('The fresh high-route program does not attain the proved lower bound.')
    return operations, dict(width=width, exact_low_count_distance_lower_bound=target_length,
                            initial_distances=list(initial_distances), search_visits=visits,
                            exhausted_residuals=len(failed), transitions=transitions,
                            fixed_state_visit_limit=state_limit,
                            first_pair_translation_quotient=True,
                            every_transition_splits_both_active_cycles=True,
                            no_wall_clock_or_random_selection=True)


@lru_cache(maxsize=1)
def synthesize():
    """Recompute and prove the selected exact route from mathematical parameters."""
    core, search = search_low_count()
    # Shift four is four disjoint opposite pairs; derive every wire index.
    upper = tuple((4, index, index + 4) for index in range(4))
    route = core + upper
    cases = 0
    for count in range(11):
        for value in range(1 << 8):
            original = tuple((value >> bit) & 1 for bit in range(8))
            expected = tuple(original[(index - count) % 8] for index in range(8))
            actual = apply(route, count, original)
            if actual != expected or apply(tuple(reversed(route)), count, actual) != original:
                raise AssertionError('The fresh high route changed an exact input or its inverse.')
            cases += 1
    packed_cases = outcome_cases = 0
    for mask in sorted({row[0] for row in route}):
        terms = flag_terms(mask)
        products = tuple(term for term in terms if term.bit_count() == 2)
        if not products or any(not term & (1 << 5) for term in products):
            raise AssertionError('A route flag is not one common-factor product.')
        for assignment in range(64):
            actual = sum(int(assignment & term == term) for term in terms) & 1
            affine = sum(int(assignment & term == term)
                         for term in terms if term.bit_count() < 2) & 1
            factor = sum(int(assignment & (term ^ (1 << 5)) == (term ^ (1 << 5)))
                         for term in products) & 1
            if actual != (affine ^ (((assignment >> 5) & 1) & factor)):
                raise AssertionError('A route flag differs from its charged product expression.')
            for outcome in range(2):
                if (outcome & actual) ^ (sum(outcome & int(assignment & term == term)
                                             for term in terms) & 1):
                    raise AssertionError('A route-flag measurement has an unpaid sign.')
                outcome_cases += 1
        for row in packed_states():
            assignment = row['q'] | (row['t'] << 4) | (row['u'] << 5)
            if (sum(int(assignment & term == term) for term in terms) & 1) != parity(row['k'] & mask):
                raise AssertionError('A route flag is incorrect on a legal packed input.')
            packed_cases += 1
    if len(core) != 10 or len(upper) != 4:
        raise AssertionError('The charged mathematical high-route dimensions changed.')
    certificate = dict(search, source='eight-cycle and two-bit linear parities only',
                       total_swaps_per_direction=14, flag_products_per_direction=3,
                       maximum_live_flags=2, quantum_phase_from_routing_exactly_zero=True,
                       complete_high_word_count_cases=cases,
                       complete_packed_flag_cases=packed_cases,
                       complete_flag_outcome_cases=outcome_cases,
                       helper_cleanup='Immediate exact Z/CZ, with no external debt',
                       reads_saved_witness_or_circuit=False)
    return core, upper, certificate
