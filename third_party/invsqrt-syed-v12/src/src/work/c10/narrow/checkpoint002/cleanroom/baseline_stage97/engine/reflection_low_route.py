# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Dihedral low-phase route: five controlled reflections of Z20 replace the C4 x C5 CRT route.

The low phase must present the twenty result bits rotated by the packed exponent class k = 0..10.  Instead of
the CRT product (4 row transpositions x 5 plus 7 column transpositions x 4 = 48 CSWAPs per direction with six
flag products), this route applies five reflections R_c(i) = c - i (mod 20) of the physical word, each switched
by one exponent-class control.  A product of an even number of reflections is a translation, so the eleven
classes select eleven translations.  Unconditional relabellings are free, so a reflection costs its 2-cycles:
9 + 9 + 9 + 9 + 10 = 46 CSWAPs per direction.  Every control is a GF(2)-linear form of k's binary bits plus an
affine t/u/1 frame, i.e. one flag product of the existing packed code (c20_routing_math.flag_terms), erased by
HMR with an immediate Z/CZ repayment.  An exact schedule with at most two live flags needs four products per
direction, and the forward schedule ends with the threshold [k >= 4] (= k2 XOR k3 for k <= 10) available as the
XOR of the two live flags, which replaces the Stage 93 threshold-four handoff at no product.

Because the route reads the raw packed code, the Stage 93 remainder encoding (3 + 3 Toffolis) is no longer needed:
the overflow thresholds [k >= j], j = 3, 5..8, are computed from the raw code at the same product counts
(RAW_THRESHOLD_TERMS, certified on every valid packed state).  Base taps, overflow features, angles and the
threshold ledger are the unchanged Stage 93 kernel.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction

import reencoded_c20_phase as original
from c20_routing_math import flag_terms, packed_states
from cyclic_phase import _pow2, _erase_polynomial
from quadratic_terms import compile_polynomial, xor_polynomial
from reencode_synthesis import synthesize
from threshold_phase_ledger import PackedThresholdPhasePass

N, CLASSES = 20, 11
CENTRES = (0, 18, 14, 0, 19)                              # reflection centres, applied in this order
ACTIVE = (30, 6, 27, 3, 17, 9, 18, 10, 23, 15, 20)        # class k -> bitmask of active stages
THRESHOLD_FOUR_MASK = 12                                  # parity(12 & k) = [k >= 4] for k <= 10
# [k >= j] = u * g_j(raw q) on valid states (j >= 3); ANF terms over q0..q3 (bit i = q_i), one product each at most.
RAW_THRESHOLD_TERMS = {3: (2, 4, 6), 5: (3, 4, 5, 9, 10, 12), 6: (3, 9, 10), 7: (4, 5, 6, 8), 8: (8,)}
ORIGINAL_LOW = original.low_phase_reencoded


def _parity(value):
    return bin(value).count('1') & 1


def reflection_pairs(centre):
    """Disjoint transpositions of i -> centre - i (mod 20), fixed points omitted."""
    return tuple((i, (centre - i) % N) for i in range(N) if i < (centre - i) % N)


def stage_controls():
    """Per stage: (linear k-mask, t coefficient, u coefficient, constant) reproducing its class truth table."""
    controls = []
    for stage in range(len(CENTRES)):
        truth = [(ACTIVE[k] >> stage) & 1 for k in range(CLASSES)]
        found = None
        for mask in range(1, 16):
            for at in (0, 1):
                for au in (0, 1):
                    for one in (0, 1):
                        if all(_parity(mask & k) ^ (at & int(k >= 1)) ^ (au & int(k >= 2)) ^ one == truth[k]
                               for k in range(CLASSES)):
                            found = found or (mask, at, au, one)
        if found is None:
            raise AssertionError('A reflection control is not a one-product linear class form.')
        controls.append(found)
    return tuple(controls)


def output_slots():
    """Return sigma with arrangement_k[sigma[i]] = symbol (i - k) mod 20 for every class (the free relabel)."""
    arrangements = []
    for k in range(CLASSES):
        word = list(range(N))
        for stage, centre in enumerate(CENTRES):
            if ACTIVE[k] >> stage & 1:
                for a, b in reflection_pairs(centre):
                    word[a], word[b] = word[b], word[a]
        arrangements.append(word)
    position = [None] * N
    inverse0 = {symbol: p for p, symbol in enumerate(arrangements[0])}
    sigma = [inverse0[i] for i in range(N)]
    # arrangement_0[sigma[i]] = i.  Check every class against the rotated target.
    for k in range(CLASSES):
        if any(arrangements[k][sigma[i]] != (i - k) % N for i in range(N)):
            raise AssertionError('The reflection route does not realize the low-phase rotation.')
    return tuple(sigma)


def _span(live):
    masks = list(live)
    return set(masks) | ({masks[0] ^ masks[1]} if len(masks) == 2 else set())


def flag_schedule(masks, final_mask=None):
    """Exact minimum-product schedule with at most two live flags (DP with cost-to-go).

    Returns per-stage live sets and the product count; if final_mask is given it must be in the final span."""
    masks = list(masks)
    def transitions(state, need):
        if need in _span(state):
            yield state, 0
            return
        live = list(state)
        for keep in [()] + [(x,) for x in live]:
            yield frozenset(keep + (need,)), 1
        for x in live:
            yield frozenset((x, need ^ x)), 1
    states = [frozenset()]
    # forward enumeration of all reachable (stage, state) with best cost and parent
    layers = [{frozenset(): (0, None)}]
    for need in masks:
        nxt = {}
        for state, (cost, _) in layers[-1].items():
            for new, extra in transitions(state, need):
                if new not in nxt or cost + extra < nxt[new][0]:
                    nxt[new] = (cost + extra, state)
        layers.append(nxt)
    finals = {s: c for s, (c, _) in layers[-1].items()
              if final_mask is None or final_mask in _span(s)}
    if not finals:
        raise AssertionError('No schedule leaves the requested final flag available.')
    best = min(sorted(finals, key=lambda s: sorted(s)), key=lambda s: finals[s])
    path = [best]
    for layer in reversed(layers[1:]):
        path.append(layer[path[-1]][1])
    path.reverse()
    return path[1:], finals[best]


class _Flags:
    """At most two live linear-form flags of the packed code; every product is repaid immediately."""
    def __init__(self, builder, variables):
        self.builder, self.variables, self.live, self.products = builder, list(variables), {}, 0

    def compute(self, mask):
        wire = self.builder.alloc_qubits(1)[0]
        plan = xor_polynomial(self.builder, self.variables, wire, flag_terms(mask))
        if len(plan.products) != 1:
            raise AssertionError('A route flag is not a one-product polynomial.')
        self.live[mask] = wire
        self.products += 1

    def erase(self, mask):
        _erase_polynomial(self.builder, self.live.pop(mask), self.variables, flag_terms(mask))

    def move_to(self, state):
        for mask in [m for m in self.live if m not in state]:
            self.erase(mask)
        for mask in sorted(state):
            if mask not in self.live:
                self.compute(mask)
        if set(self.live) != set(state) or len(self.live) > 2:
            raise AssertionError('The flag schedule changed its live set.')

    @contextmanager
    def control(self, mask, at, au, one, t, u):
        builder = self.builder
        if mask in self.live:
            wire, partner = self.live[mask], None
        else:
            a, b = sorted(self.live)
            if a ^ b != mask:
                raise AssertionError('The requested control is outside the live flag span.')
            wire, partner = self.live[a], self.live[b]
            builder.cx(partner, wire)
        if at: builder.cx(t, wire)
        if au: builder.cx(u, wire)
        if one: builder.x(wire)
        try:
            yield wire
        finally:
            if one: builder.x(wire)
            if au: builder.cx(u, wire)
            if at: builder.cx(t, wire)
            if partner is not None: builder.cx(partner, wire)

    def close(self):
        for mask in list(self.live):
            self.erase(mask)


def emit_route(builder, value, packed, u, *, inverse=False):
    """Apply the five controlled reflections (forward), or their reverse.  Forward returns the live [k>=4] wire."""
    controls = stage_controls()
    order = list(range(len(CENTRES)))
    if inverse:
        order.reverse()
    masks = [controls[s][0] for s in order]
    states, products = flag_schedule(masks, None if inverse else THRESHOLD_FOUR_MASK)
    flags = _Flags(builder, list(packed.residual[:4]) + [packed.t, u])
    swaps = 0
    for stage, state in zip(order, states):
        flags.move_to(state)
        mask, at, au, one = controls[stage]
        with flags.control(mask, at, au, one, packed.t, u) as wire:
            for a, b in reflection_pairs(CENTRES[stage]):
                builder.cswap(wire, value[a], value[b])
                swaps += 1
    threshold_four = None
    if not inverse:
        if THRESHOLD_FOUR_MASK in flags.live:
            threshold_four = flags.live.pop(THRESHOLD_FOUR_MASK)
        else:
            a, b = sorted(flags.live)
            if a ^ b != THRESHOLD_FOUR_MASK:
                raise AssertionError('The forward schedule did not end with threshold four in its span.')
            builder.cx(flags.live[b], flags.live[a])
            threshold_four = flags.live.pop(a)       # now holds parity(12 & k) = [k >= 4]
    flags.close()
    if swaps != 46 or flags.products != products or products != 4:
        raise AssertionError('The reflection route changed its 46-CSWAP / 4-product charge.')
    return threshold_four, dict(inverse=bool(inverse), cswaps=swaps, flag_products=flags.products,
                                stages=[CENTRES[s] for s in order], live_sets=[sorted(s) for s in states])


def certificate():
    """Exact check of the route mathematics on every valid packed state."""
    controls, sigma = stage_controls(), output_slots()
    rows = 0
    for row in packed_states():
        k, q, t, u = row['k'], row['q'], row['t'], row['u']
        assignment = q | (t << 4) | (u << 5)
        for stage, (mask, at, au, one) in enumerate(controls):
            terms = flag_terms(mask)
            flag = sum(int(assignment & term == term) for term in terms) & 1
            if flag != _parity(mask & k):
                raise AssertionError('A flag polynomial differs from its linear class form.')
            if flag ^ (at & t) ^ (au & u) ^ one != (ACTIVE[k] >> stage) & 1:
                raise AssertionError('A framed control differs from its stage activity.')
        terms = flag_terms(THRESHOLD_FOUR_MASK)
        if (sum(int(assignment & term == term) for term in terms) & 1) != int(k >= 4):
            raise AssertionError('The threshold-four flag form is wrong.')
        rows += 1
    forward, fwd_products = flag_schedule([c[0] for c in controls], THRESHOLD_FOUR_MASK)
    backward, bwd_products = flag_schedule([c[0] for c in reversed(controls)])
    return dict(centres=list(CENTRES), active=list(ACTIVE), controls=[list(c) for c in controls],
                output_slots=list(sigma), packed_rows_checked=rows,
                cswaps_per_direction=sum(len(reflection_pairs(c)) for c in CENTRES),
                flag_products=[fwd_products, bwd_products],
                every_class_rotation_exact=True, threshold_four_from_route_flags=True)


def raw_threshold_certificate():
    """Every raw threshold polynomial, masked by u, equals [k >= j] on all valid packed states."""
    rows = 0
    for row in packed_states():
        q, u = row['q'], row['u']
        for j, terms in RAW_THRESHOLD_TERMS.items():
            value = sum(int(q & term == term) for term in terms) & 1
            if (u & value) != int(row['k'] >= j):
                raise AssertionError('A raw threshold polynomial changed a phase feature.')
        rows += 1
    products = {j: len(compile_polynomial(4, terms).products) for j, terms in RAW_THRESHOLD_TERMS.items()}
    return dict(packed_rows_checked=rows, products=products,
                compute_ANDs={j: p + 1 for j, p in products.items()})


@contextmanager
def raw_threshold(builder, packed, u, threshold, phase_pass):
    """[k >= threshold] from the raw packed code: one product (or none) plus the u mask; exact ledger erase."""
    if threshold == 1:
        yield packed.t, 0
        return
    if threshold == 2:
        yield u, 0
        return
    terms = RAW_THRESHOLD_TERMS[threshold]
    q = list(packed.residual[:4])
    helper = builder.alloc_qubits(1)[0]
    compiled = xor_polynomial(builder, q, helper, terms)
    control = builder.alloc_qubits(1)[0]
    builder.ccx(u, helper, control)
    _erase_polynomial(builder, helper, q, terms)
    try:
        yield control, len(compiled.products) + 1
    finally:
        phase_pass.ledger(packed).erase(builder, control, threshold)


def _feature(builder, control, data, angle):
    temporary = builder.alloc_qubits(1)[0]
    builder.ccx(control, data, temporary)
    builder.z_pow(temporary, angle)
    builder.del_and(control, data, temporary)
    builder.free(temporary)


def low_phase_reencoded(builder, value, packed, fractional_bits, *, turn_offsets,
                        threshold, beta=1, negative=None):
    """The unchanged 28 low-phase features, routed by five controlled reflections."""
    if negative is not None:
        raise ValueError('The reflection route has no negative-control variants.')
    value = list(value)
    offsets, beta = tuple(map(Fraction, turn_offsets)), Fraction(beta)
    if (len(value) != 20 or fractional_bits != 37 or len(offsets) != 30 or
            packed.max_k != 10 or not packed.is_packed):
        raise ValueError('Require the selected packed word20/F37/k0..10 geometry.')
    # Narrowed ownership contract: every route, threshold and shared-u
    # operation below reads only packed.residual[:4], packed.t and u.  The
    # A-even consuming main hands the last sign wire over as result bit zero,
    # which is the one permitted alias of a residual slot.
    controls = list(packed.residual[:4]) + [packed.t]
    aliases = [wire for wire in value if wire in packed.residual]
    consumed_sign_alias = aliases == [packed.residual[-1]] and value[0] == packed.residual[-1]
    if (len(set(value)) != 20 or len(set(value + controls)) != 25
            or (aliases and not consumed_sign_alias)):
        raise ValueError('Phase data must be distinct and disjoint from the packed route controls.')
    phase_pass = getattr(threshold, '__self__', None)
    if not isinstance(phase_pass, PackedThresholdPhasePass) or not phase_pass.merge_external_t:
        raise ValueError('Require the original bound threshold owner with merged external-t repayment.')
    if packed._cached_u is not None:
        raise ValueError('The low kernel requires its original fresh shared-u lifecycle.')
    entry_live = builder.num_allocated_qubits
    if entry_live not in (53, 54) or builder.max_qubits-entry_live < 3 or builder.max_qubits > 57:
        raise ValueError('The reflection route requires its three-wire margin above a 53- or 54-live entry.')
    proof = certificate()
    thresholds = raw_threshold_certificate()
    slot = [value[p] for p in proof['output_slots']]
    candidate, source_certificate = synthesize()
    q = list(packed.residual[:4])
    plans = {int(plan['threshold']): plan for plan in candidate['threshold_plans']}
    base_angles = [beta * _pow2(bit - fractional_bits + 1) + 2 * offsets[bit] for bit in range(20)]
    overflow_angles = [beta * ((1 << 20) - 1) * _pow2(bit - fractional_bits + 1)
                       + 2 * offsets[20 + bit] for bit in range(8)]
    routes, encoding, threshold_products = [], [], 0
    with packed.higher_nonzero() as u:
        threshold_four, forward = emit_route(builder, value, packed, u)
        routes.append(forward)
        for wire, angle in zip(slot, base_angles):
            builder.z_pow(wire, angle)
        _feature(builder, threshold_four, slot[3], overflow_angles[3])
        phase_pass.ledger(packed).erase(builder, threshold_four, 4)
        for bit in range(8):
            if bit == 3:
                continue
            with raw_threshold(builder, packed, u, bit + 1, phase_pass) as (control, cost):
                threshold_products += cost
                _feature(builder, control, slot[bit], overflow_angles[bit])
        _, backward = emit_route(builder, value, packed, u, inverse=True)
        routes.append(backward)
    swaps = sum(item['cswaps'] for item in routes)
    products = (sum(item['flag_products'] for item in routes) +
                sum(item['Toffolis'] for item in encoding) + threshold_products + 8 + 2)
    if threshold_products != 9 or swaps != 92 or products != 27 or encoding:
        raise AssertionError('The raw-threshold reflection low kernel differs from its 119-E charge.')
    if builder.num_allocated_qubits != entry_live:
        raise AssertionError('The reflection route changed the low-phase allocation boundary.')
    return dict(width=20, max_k=10, reencoded_C20=True, cswaps=swaps, and_products=products,
                expected_toffolis=swaps + products, expected_extra_T=0, expected_generic_rotations=28,
                z_pow_calls=28, half_turn_angles=list(map(str, base_angles + overflow_angles)),
                turn_offsets=list(map(str, offsets)), skipped_overflow=[8, 9], route_controllers=routes,
                encoding=encoding, threshold_compute_ANDs=threshold_products,
                source_synthesis=source_certificate, reflection_route=proof,
                raw_thresholds=thresholds, remainder_encoding_removed=True,
                low_kernel_E_before=134, low_kernel_E_after=swaps + products,
                numerical_angles_unchanged=True, entry_live=entry_live,
                peak_limit=int(builder.max_qubits), consumed_sign_alias_of_result_bit_zero=consumed_sign_alias)


@contextmanager
def installed(*, audit=None):
    """Install the reflection-routed low phase at the existing dynamic-import hook."""
    previous = original.low_phase_reencoded
    if previous is not ORIGINAL_LOW:
        raise RuntimeError('Another low-phase replacement is active.')
    records = [] if audit is None else audit
    def emit(*args, **kwargs):
        metadata = low_phase_reencoded(*args, **kwargs)
        records.append(dict(reflection_route=metadata['reflection_route'],
                            low_kernel_E_before=134, low_kernel_E_after=metadata['expected_toffolis'], remainder_encoding_removed=True,
                            route_controllers=metadata['route_controllers']))
        return metadata
    original.low_phase_reencoded = emit
    try:
        yield records
    finally:
        original.low_phase_reencoded = previous
