#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Bounded exact-integer search for coarse zero-supported normalization moves.

There are six legal shifts of zero through five four-bit blocks.  Two lanes
contain six positions; two contain five.  Each context has independent live
input symbols followed by known zeros.  A nonexistent position may be used
only when its partner is also zero in both shorter lanes.

All selector functions on six valid three-bit labels admit a quadratic
completion on the other two labels.  Each nonlinear selector therefore
costs at most one AND, plus Clifford control framing, and has exact HMR
cleanup.  This search charges that AND at every selector change unless it
can be retained for the next exchange.  Linear selectors cost no AND.

The search is deliberately bounded by fixed beam width, depth, and candidate
count.  It is not an optimality proof.  No elapsed-time cutoff selects a
circuit.  Every completed route is rechecked on all independent symbols.
Run only through the project resource guard, one search at a time.
"""
from __future__ import annotations

from dataclasses import dataclass


CONTEXTS = 6
FULL_WIDTH = 6
SHORT_WIDTH = 5
STRIDE = FULL_WIDTH+SHORT_WIDTH


def initial_and_target():
    initial, target = [], []
    for shift in range(CONTEXTS):
        for width in (FULL_WIDTH, SHORT_WIDTH):
            occupied = max(0, width-shift)
            symbols = list(range(1, occupied+1))
            initial.extend(symbols+[0]*(width-occupied))
            target.extend([0]*(width-occupied)+symbols)
    return tuple(initial), tuple(target)


def linear_selectors():
    return {sum(((label & form).bit_count() & 1) << label
                for label in range(CONTEXTS)): form for form in range(1, 8)}


def selector_terms(mask):
    """Derive a degree-at-most-two truth completion, with no saved table."""
    choices = []
    for completion in range(4):
        truth = mask | (completion << CONTEXTS)
        coefficients = [(truth >> index) & 1 for index in range(8)]
        for bit in range(3):
            for index in range(8):
                if index >> bit & 1:
                    coefficients[index] ^= coefficients[index ^ (1 << bit)]
        if coefficients[-1]:
            continue
        terms = tuple(index for index, enabled in enumerate(coefficients) if enabled)
        nonlinear = any(term.bit_count() == 2 for term in terms)
        choices.append((int(nonlinear), len(terms), terms, truth))
    if not choices:
        raise AssertionError('Six-label selector lacked a quadratic completion.')
    cost, _, terms, truth = min(choices)
    for label in range(CONTEXTS):
        value = sum((label & term) == term for term in terms) & 1
        assert value == ((mask >> label) & 1)
    return dict(mask=mask, and_count=cost, terms=list(terms), complete_truth=truth)


def candidate_masks(state, target, first, second, linear):
    allowed = 0
    useful = 0
    for context in range(1, CONTEXTS):
        offset = context*STRIDE
        full = offset
        short = offset+FULL_WIDTH
        if second == SHORT_WIDTH and state[short+first] != 0:
            continue
        positions = [(full+first, full+second)]
        if second < SHORT_WIDTH:
            positions.append((short+first, short+second))
        before = after = 0
        changed = False
        for left, right in positions:
            before += (state[left] == target[left])+(state[right] == target[right])
            after += (state[right] == target[left])+(state[left] == target[right])
            changed |= state[left] != state[right]
        if after >= before and changed:
            allowed |= 1 << context
            if after > before:
                useful |= 1 << context
    if not useful:
        return ()
    # Prefer all locally useful contexts, then complete affine controls, then
    # every monotone subset.  Tie-breaking is independent of dict hash order.
    masks = {useful, allowed}
    masks.update(mask for mask in linear if mask & useful and not mask & ~allowed)
    mask = allowed
    while mask:
        if mask & useful:
            masks.add(mask)
        mask = (mask-1) & allowed
    return tuple(sorted(masks))


def apply(state, first, second, mask):
    result = list(state)
    for context in range(CONTEXTS):
        if not mask >> context & 1:
            continue
        offset = context*STRIDE
        for left, right in ((offset+first, offset+second),):
            result[left], result[right] = result[right], result[left]
        offset += FULL_WIDTH
        if second < SHORT_WIDTH:
            left, right = offset+first, offset+second
            result[left], result[right] = result[right], result[left]
        elif result[offset+first] != 0:
            raise AssertionError('A move used a nonexistent nonzero short-lane position.')
    return tuple(result)


def mismatch(state, target):
    return sum(value != wanted for value, wanted in zip(state, target))


@dataclass(frozen=True)
class Node:
    state: tuple
    selector: int
    cost: int
    path: tuple
    missing: int

    def order(self):
        # A swap can correct at most twenty labelled cells; the factor makes
        # this an exploration heuristic, not an admissible lower-bound claim.
        return (self.cost+2*self.missing, self.cost, self.missing, self.path)


def search(*, beam=128, depth=10, candidate_limit=200000, maximum_cost=31, progress=None):
    start, target = initial_and_target()
    linear = linear_selectors()
    frontier = [Node(start, 0, 0, (), mismatch(start, target))]
    examined = 0
    complete = []
    layers = []
    stopped = 'maximum_depth'
    for level in range(depth):
        retained = {}
        for node in frontier:
            for first in range(FULL_WIDTH):
                for second in range(first+1, FULL_WIDTH):
                    for mask in candidate_masks(node.state, target, first, second, linear):
                        examined += 1
                        if examined > candidate_limit:
                            stopped = 'fixed_candidate_limit'
                            break
                        selector_cost = int(mask not in linear and mask != node.selector)
                        cost = node.cost+(2 if second == SHORT_WIDTH else 4)+selector_cost
                        if cost > maximum_cost:
                            continue
                        state = apply(node.state, first, second, mask)
                        path = node.path+((first, second, mask),)
                        child = Node(state, mask, cost, path, mismatch(state, target))
                        if not child.missing:
                            complete.append(child)
                            maximum_cost = min(maximum_cost, cost)
                            continue
                        key = (state, mask)
                        old = retained.get(key)
                        if old is None or (child.cost, child.path) < (old.cost, old.path):
                            retained[key] = child
                        if len(retained) > beam*32:
                            best = sorted(retained.values(), key=Node.order)[:beam*8]
                            retained = {(item.state, item.selector): item for item in best}
                    if examined > candidate_limit:
                        break
                if examined > candidate_limit:
                    break
            if examined > candidate_limit:
                break
        frontier = sorted(retained.values(), key=Node.order)[:beam]
        layers.append(dict(depth=level+1, frontier=len(frontier),
                           examined_candidates=examined,
                           best_missing=min((item.missing for item in frontier), default=None),
                           complete_candidates=len(complete)))
        if progress is not None:
            progress(dict(layers[-1]))
        if examined > candidate_limit or not frontier:
            if not frontier and stopped != 'fixed_candidate_limit':
                stopped = 'empty_frontier'
            break
    result = dict(status='CERTIFIED_ROUTE_FOUND' if complete else 'BOUNDED_NO_ROUTE_FOUND',
                  search_complete=False, global_optimality_proved=False,
                  fixed_beam=beam, maximum_depth=depth, candidate_limit=candidate_limit,
                  examined_candidates=examined, stop_reason=stopped, layers=layers,
                  reference_fused_three_shift_cost=32, target_upper_cost=31)
    if complete:
        best = min(complete, key=lambda item:(item.cost, len(item.path), item.path))
        state = start
        controls = []
        for first, second, mask in best.path:
            controls.append(selector_terms(mask))
            state = apply(state, first, second, mask)
        assert state == target
        for first, second, mask in reversed(best.path):
            state = apply(state, first, second, mask)
        assert state == start
        result.update(total_Toffoli_cost=best.cost,
                      saving_per_direction=32-best.cost,
                      coarse_block_exchanges=[list(item) for item in best.path],
                      selectors=controls,
                      quantum_scratch=1 if any(row['and_count'] for row in controls) else 0,
                      exact_symbolic_forward_and_inverse=True,
                      full_generator_emission_and_verification='REQUIRED')
    return result

