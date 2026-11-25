# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""From-source joint routing of mutually exclusive +4/+8 low-word rotations.

The selected shift range is 0..10, so binary shift flags2 and3 cannot both
be one. On each of four five-wire cycles, synthesize the two required cyclic
permutations jointly in S5 x S5. Every action is one physical SWAP controlled
by a, b or a XOR b. Breadth-first search proves minimum network length within
this exact action family. No gate sequence or circuit file is an input.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
import kickmix as km
from cyclic_phase import rotation_pairs, _pow2, _erase_polynomial
from packed_phase import _flag
from quadratic_terms import xor_polynomial


def _swap(permutation, i, j):
    result = list(permutation); result[i], result[j] = result[j], result[i]
    return tuple(result)


@lru_cache(maxsize=1)
def synthesize_c5():
    """Deterministic shortest path on at most 120**2 states."""
    identity = tuple(range(5))
    start = (identity, identity)
    # Stored tuples give the old wire value found at each final wire.
    target = (tuple((i-1) % 5 for i in range(5)),
              tuple((i-2) % 5 for i in range(5)))
    actions = tuple((control, i, j) for control in ('xor', 'a', 'b')
                    for i, j in combinations(range(5), 2))
    queue = deque([start]); previous = {start: None}; distance = {start: 0}
    transitions = 0
    while queue:
        state = queue.popleft()
        if state == target:
            break
        for action in actions:
            control, i, j = action
            nxt = (_swap(state[0], i, j) if control in ('a', 'xor') else state[0],
                   _swap(state[1], i, j) if control in ('b', 'xor') else state[1])
            transitions += 1
            if nxt not in previous:
                previous[nxt] = (state, action); distance[nxt] = distance[state]+1
                queue.append(nxt)
                if len(previous) > 14400:
                    raise AssertionError('The finite S5 x S5 state bound was exceeded.')
    if target not in previous:
        raise AssertionError('The exact finite routing family did not reach its target.')
    path = []; state = target
    while previous[state] is not None:
        state, action = previous[state]; path.append(action)
    path.reverse()
    if len(path) != 6:
        raise AssertionError('The proposed six-swap structural saving did not synthesize.')
    return tuple(path), dict(status='SHORTEST_EXACT_TERNARY_C5_NETWORK',
        state_space_bound=14400, states_discovered=len(previous), transitions_examined=transitions,
        action_family='physical transposition controlled by a, b or a XOR b',
        control_domain=[[0, 0], [1, 0], [0, 1]], shortest_length=len(path),
        ordinary_separate_length=8, target_permutations=[list(p) for p in target],
        network=[list(action) for action in path], deterministic=True)


def permutation_certificate():
    path, metadata = synthesize_c5()
    checked5 = checked20 = 0
    for a, b in ((0, 0), (1, 0), (0, 1)):
        active = {'a': a, 'b': b, 'xor': a ^ b}
        for value in range(32):
            word = [(value >> i) & 1 for i in range(5)]
            original = list(word)
            for control, i, j in path:
                if active[control]: word[i], word[j] = word[j], word[i]
            shift = a+2*b
            if word != [original[(i-shift) % 5] for i in range(5)]:
                raise AssertionError('A five-wire Boolean truth row differs.')
            for control, i, j in reversed(path):
                if active[control]: word[i], word[j] = word[j], word[i]
            if word != original: raise AssertionError('The inverse C5 route did not restore its word.')
            checked5 += 1
        # A routing circuit is a coordinate permutation; the basis vectors
        # certify the map for all 2**20 word assignments by linearity.
        for bit in range(20):
            word = [int(i == bit) for i in range(20)]; original = list(word)
            for control, i, j in path:
                if active[control]:
                    for offset in range(4):
                        left, right = offset+4*i, offset+4*j
                        word[left], word[right] = word[right], word[left]
            if word != [original[(i-4*a-8*b) % 20] for i in range(20)]:
                raise AssertionError('The four-cycle 20-wire permutation differs.')
            checked20 += 1
    return dict(metadata, five_wire_truth_rows=checked5, twenty_wire_basis_rows=checked20,
        both_directions_exact=True, arbitrary_twenty_bit_words_by_coordinate_linearity=True,
        forward_cswap_count=24, old_forward_cswap_count=32,
        round_trip_cswap_saving=16)


@contextmanager
def joint_flags(builder, packed, u, *, omit_repayment=False):
    """Two one-product flag functions, sharing u and no further workspace."""
    variables = list(packed.residual[:4])+[packed.t, u]
    a, b = list(builder.alloc_qubits(2))
    terms_a, terms_b = (34, 40), (40,)
    xor_polynomial(builder, variables, a, terms_a)
    xor_polynomial(builder, variables, b, terms_b)
    try:
        yield a, b
    finally:
        for target, terms in ((b, terms_b), (a, terms_a)):
            if omit_repayment:
                measured = builder.alloc_bits(1)[0]
                builder.hmr(target, measured); builder.free(target); builder.free(measured)
            else:
                _erase_polynomial(builder, target, variables, terms)


def emit_joint_route(builder, value, packed, u, *, inverse=False, omit_repayment=False):
    value = list(value)
    if len(value) != 20 or len(set(value)) != 20 or packed.max_k != 10:
        raise ValueError('This certified family is exactly word20 and shift0..10.')
    path, _metadata = synthesize_c5()
    actions = tuple(reversed(path)) if inverse else path
    with joint_flags(builder, packed, u, omit_repayment=omit_repayment) as (a, b):
        for control, left, right in actions:
            if control == 'xor': builder.cx(b, a)
            selected = a if control in ('a', 'xor') else b
            for offset in range(4):
                builder.cswap(selected, value[offset+4*left], value[offset+4*right])
            if control == 'xor': builder.cx(b, a)


def low_phase_joint(builder, value, packed, fractional_bits, *, turn_offsets,
                    threshold, beta=1, omit_flag_repayment=False):
    """The selected tail43 low phase with only its +4/+8 routes replaced."""
    value = list(value); offsets = tuple(map(Fraction, turn_offsets)); beta = Fraction(beta)
    if len(value) != 20 or fractional_bits != 37 or len(offsets) != 30:
        raise ValueError('Require the selected 20-bit, F37, thirty-feature geometry.')
    if not packed.is_packed or packed.max_k != 10:
        raise ValueError('Require the packed shift range0..10.')
    if len(set(value+list(packed.residual)+[packed.t])) != 20+len(packed.residual)+1:
        raise ValueError('The phase word must be disjoint from the packed shift.')
    base = [beta*_pow2(i-fractional_bits+1) for i in range(20)]
    overflow = [beta*((1 << 20)-1)*_pow2(j-fractional_bits+1) for j in range(10)]
    angles = []; products = 0; conditional = 0
    with packed.higher_nonzero() as u:
        emit_joint_route(builder, value, packed, u, omit_repayment=omit_flag_repayment)
        products += 2
        low_routes = []
        for index in (1, 0):
            pairs = rotation_pairs(20, 1 << index)
            with _flag(builder, packed, u, index) as flag:
                for left, right in pairs: builder.cswap(flag, value[left], value[right])
            products += 1; low_routes.append((index, pairs))
        for i, wire in enumerate(value):
            angle = base[i]+2*offsets[i]; builder.z_pow(wire, angle); angles.append(angle)
        for j in range(8):
            with threshold(builder, packed, u, j+1) as (control, cost, ccz):
                products += cost; conditional += ccz
                temporary = builder.alloc_qubits(1)[0]
                builder.ccx(control, value[j], temporary)
                angle = overflow[j]+2*offsets[20+j]
                builder.z_pow(temporary, angle)
                builder.del_and(control, value[j], temporary); builder.free(temporary)
                products += 1; angles.append(angle)
        for index, pairs in reversed(low_routes):
            with _flag(builder, packed, u, index) as flag:
                for left, right in reversed(pairs): builder.cswap(flag, value[left], value[right])
            products += 1
        emit_joint_route(builder, value, packed, u, inverse=True,
                         omit_repayment=omit_flag_repayment)
        products += 2
    swaps = 2*(24+18+19)
    return dict(width=20, max_k=10, direct_packed=True, joint_ternary_c5=True,
        cswaps=swaps, and_products=products+2, hmr_conditioned_ccz=conditional,
        expected_toffolis=swaps+products+2+conditional/2,
        z_pow_calls=len(angles), half_turn_angles=list(map(str, angles)),
        turn_offsets=list(map(str, offsets)), skipped_overflow=[8, 9],
        exact_network=permutation_certificate())
