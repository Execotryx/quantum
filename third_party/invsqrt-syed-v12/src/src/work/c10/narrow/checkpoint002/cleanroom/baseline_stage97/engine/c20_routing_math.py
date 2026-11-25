# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Finite permutation and two-flag mathematics for a possible full C20 route.

No circuit, coefficient table, saved search output or numerical phase fit is
read. The mathematical inputs are cyclic rotations and k in0..10.
"""
from __future__ import annotations

from collections import deque
from functools import lru_cache
from itertools import combinations, permutations


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


@lru_cache(maxsize=1)
def planes4():
    """All35 two-dimensional linear subspaces of GF(2)^4, excluding zero."""
    result = tuple(sorted({tuple(sorted((a, b, a ^ b)))
                           for a in range(1, 16) for b in range(a+1, 16)}))
    if len(result) != 35:
        raise AssertionError('The four-bit two-flag plane family changed.')
    return result


def plane_distance(first, second):
    if first == second:
        return 0
    common = set(first) & set(second)
    if len(common) not in (0, 1):
        raise AssertionError('Distinct two-dimensional planes have invalid intersection.')
    return 1 if common else 2


def interleave_controls(c5, c4):
    """Minimize flag products while interleaving the commuting CRT factors.

    Each C5 action acts identically on all four C4 coordinates and vice versa,
    so actions from opposite factors commute. Relative order inside either
    supplied factor is preserved. A disjoint plane transition requires two
    erased/recomputed slots; a one-vector intersection requires only one.
    """
    family = planes4()
    states = {(0, 0, -1):(0, ())}
    for total in range(len(c5)+len(c4)):
        following = {}
        for (i, j, before), (cost, path) in states.items():
            if i+j != total:
                raise AssertionError('The finite interleaving state has the wrong depth.')
            choices = []
            if i < len(c5): choices.append(('c5', i, i+1, j, c5[i]))
            if j < len(c4): choices.append(('c4', j, i, j+1, c4[j]))
            for kind, index, ni, nj, action in choices:
                mask = int(action['control_mask'])
                for after, plane in enumerate(family):
                    if mask not in plane:
                        continue
                    extra = 2 if before < 0 else plane_distance(family[before], plane)
                    candidate = (cost+extra, path+((kind, index, after),))
                    key = ni, nj, after
                    if key not in following or candidate < following[key]:
                        following[key] = candidate
        states = following
    cost, path = min(states.values())
    actions = []
    for kind, index, plane in path:
        source = c5 if kind == 'c5' else c4
        actions.append(dict(source[index], kind=kind, plane=list(family[plane])))
    actual = 2+sum(plane_distance(tuple(a['plane']), tuple(b['plane']))
                   for a, b in zip(actions, actions[1:]))
    if actual != cost:
        raise AssertionError('The reconstructed flag lifetime has a different product cost.')
    return actions, dict(flag_capacity=2, total_products_per_direction=cost,
                         planes_considered=35, order_within_each_factor_preserved=True,
                         opposite_factor_actions_commute=True,
                         deterministic_dynamic_program=True)


def packed_states():
    """The29 valid low residual patterns used by the existing packed shift."""
    rows = []
    for k in range(11):
        if k == 0:
            originals = range(16)
        elif k == 1:
            originals = range(0, 16, 4)
        else:
            originals = (0,)
        f = [(k >> i) & 1 for i in range(4)]
        u, t = int(k >= 2), int(k >= 1)
        for original in originals:
            q = original ^ f[1] ^ ((f[2] ^ f[3]) << 1) ^ ((f[0] & u) << 2) ^ (f[3] << 3)
            rows.append(dict(k=k, original=original, q=q, t=t, u=u))
    if len(rows) != 29:
        raise AssertionError('The packed valid-domain count changed.')
    return rows


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


def evaluate_terms(terms, variables):
    return sum((variables & term) == term for term in terms) & 1


def verify_flags():
    checked = 0
    for row in packed_states():
        variables = row['q'] | (row['t'] << 4) | (row['u'] << 5)
        for mask in range(1, 16):
            if evaluate_terms(flag_terms(mask), variables) != ((mask & row['k']).bit_count() & 1):
                raise AssertionError('A linear k control differs on a valid packed state.')
            checked += 1
    # Every nonlinear term contains the same u factor: the whole nonlinear
    # part is one AND of u with one nonzero affine input parity. HMR cleanup
    # is exactly the same polynomial phase, hence only Z/CZ corrections.
    for mask in range(1, 16):
        nonlinear = [term for term in flag_terms(mask) if term.bit_count() == 2]
        if not nonlinear or any(not (term & 32) for term in nonlinear):
            raise AssertionError('A route flag lost its common-factor one-AND form.')
    return dict(valid_packed_truth_rows=checked, products_per_new_flag=1,
                 cleanup_polynomial_degree=2, immediate_cleanup_ANDs=0,
                 cleanup_exact_for_every_HMR_outcome=True)


def certificate(c5, *, operations=None):
    """Check every small word and all20 basis vectors, both directions."""
    c4, c4_meta = c4_synthesis()
    if operations is None:
        operations, controls = interleave_controls(c5, c4)
    else:
        controls = None
    rows5 = rows20 = 0
    for k in range(11):
        for value in range(32):
            old = [(value >> i) & 1 for i in range(5)]; word = list(old)
            for action in c5:
                if (int(action['control_mask']) & k).bit_count() & 1:
                    a,b = action['swap']; word[a],word[b] = word[b],word[a]
            if word != [old[(i-k) % 5] for i in range(5)]:
                raise AssertionError('The C5 search result has the wrong cyclic permutation.')
            for action in reversed(c5):
                if (int(action['control_mask']) & k).bit_count() & 1:
                    a,b = action['swap']; word[a],word[b] = word[b],word[a]
            if word != old:
                raise AssertionError('The reversed C5 route failed.')
            rows5 += 1
        for bit in range(20):
            old = [int(i == bit) for i in range(20)]; word = list(old)
            def apply(action):
                if not ((int(action['control_mask']) & k).bit_count() & 1): return
                a,b = action['swap']
                if action['kind'] == 'c4':
                    pairs = [((5*a+16*t) % 20, (5*b+16*t) % 20) for t in range(5)]
                else:
                    pairs = [((5*p+16*a) % 20, (5*p+16*b) % 20) for p in range(4)]
                for left,right in pairs: word[left],word[right] = word[right],word[left]
            for action in operations: apply(action)
            if word != [old[(i-k) % 20] for i in range(20)]:
                raise AssertionError('The complete CRT C20 basis permutation failed.')
            for action in reversed(operations): apply(action)
            if word != old: raise AssertionError('The inverse CRT C20 route failed.')
            rows20 += 1
    return dict(C5_exhaustive_rows=rows5, C20_basis_rows=rows20,
                 both_directions=True, arbitrary_words_by_coordinate_linearity=True,
                 crt_coordinate='j=(5*p+16*t) mod20', c4=c4_meta,
                 controls=controls, flags=verify_flags())


def c5_reference():
    """An ordinary16-swap valid reference, synthesized from cycle powers."""
    result = []
    for bit in range(4):
        shift = (1 << bit) % 5
        cycle = [(i*shift) % 5 for i in range(5)]
        # Consecutive swaps with the first pivot rotate this five-cycle left
        # in value positions, giving old(i-shift) at output i.
        for j in range(1, 5):
            result.append(dict(kind='c5', control_mask=1 << bit,
                               swap=[cycle[0], cycle[j]]))
    return result
