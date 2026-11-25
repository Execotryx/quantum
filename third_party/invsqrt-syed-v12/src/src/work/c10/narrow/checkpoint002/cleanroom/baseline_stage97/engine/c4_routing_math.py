# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Deterministic cyclic-permutation synthesis and exact packed-shift flags."""
from __future__ import annotations
from collections import deque
from functools import lru_cache
from itertools import combinations

@lru_cache(maxsize=1)
def c4_synthesis():
    """Shortest full four-state C4 network in S4^3, with linear controls."""
    identity = tuple(range(4))
    start = (identity,)*3
    goal = tuple(tuple((i-k) % 4 for i in range(4)) for k in (1, 2, 3))
    actions = tuple((mask, pair) for mask in (1, 2, 3)
                    for pair in combinations(range(4), 2))
    previous = {start:None}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        if state == goal:
            break
        for mask, pair in actions:
            other = []
            for k, permutation in zip((1, 2, 3), state):
                value = list(permutation)
                if (mask & k).bit_count() & 1:
                    i, j = pair; value[i], value[j] = value[j], value[i]
                other.append(tuple(value))
            other = tuple(other)
            if other not in previous:
                previous[other] = (state, mask, pair)
                queue.append(other)
        if len(previous) > 24**3:
            raise AssertionError('The declared finite C4 state bound changed.')
    if goal not in previous:
        raise AssertionError('The finite C4 family did not reach its target.')
    path = []
    cursor = goal
    while previous[cursor] is not None:
        cursor, mask, pair = previous[cursor]
        path.append(dict(kind='c4', control_mask=mask, swap=list(pair)))
    path.reverse()
    if len(path) != 4:
        raise AssertionError('The proposed four-swap C4 reduction did not synthesize.')
    return path, dict(shortest_length=4, ordinary_separate_length=5,
                     finite_state_bound=24**3, states_discovered=len(previous),
                     control_domain=[0, 1, 2, 3], mathematical_search_only=True)

def flag_terms(mask):
    """One product plus affine terms for any linear function of binary k.

    Variables are(packed[0],packed[1],packed[2],packed[3],t,u).
    k0=t XOR u XOR u*packed[2]; k1=u*packed[0];
    k2=u*(packed[1] XOR packed[3]); k3=u*packed[3] on every valid state.
    """
    if not 0 < mask < 16:
        raise ValueError('A nonzero four-bit linear control is required.')
    terms = [16, 32] if mask & 1 else []
    for bit, active in ((2, mask & 1), (0, (mask >> 1) & 1),
                        (1, (mask >> 2) & 1), (3, ((mask >> 2) ^ (mask >> 3)) & 1)):
        if active:
            terms.append((1 << 5) | (1 << bit))
    return tuple(terms)
