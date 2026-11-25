# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Exact CRT routing of the six even shifts of the twenty-bit phase word.

No saved screen or circuit is read. The finite C5 search is rerun from r=0..5,
then a deterministic seven-plane dynamic program chooses the two-flag lifetime.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction
from functools import lru_cache
import kickmix as km
from cyclic_phase import rotation_pairs, _pow2, _erase_polynomial
from packed_phase import _flag
from quadratic_terms import xor_polynomial
from crt_c10_synthesis import screen


def planes():
    """All two-dimensional subspaces of GF(2)^3, without the zero vector."""
    result = tuple(sorted({tuple(sorted((a, b, a ^ b)))
                           for a in range(1, 8) for b in range(a+1, 8)}))
    if len(result) != 7:
        raise AssertionError('The exact three-bit plane family changed.')
    return result


def choose_planes(demands):
    """Minimize initial products plus one product per changed two-flag plane.

    Any two distinct planes share one nonzero vector. Clifford rebasing keeps
    that vector while one measured flag slot is replaced by a new product.
    """
    family = planes(); demands = tuple(map(int, demands))
    if not demands or any(mask not in range(1, 8) for mask in demands):
        raise ValueError('Require nonzero linear controls on the three bits of r.')
    states = {i:(2, (i,)) for i, plane in enumerate(family) if demands[0] in plane}
    for mask in demands[1:]:
        nxt = {}
        for j, plane in enumerate(family):
            if mask not in plane:
                continue
            nxt[j] = min((cost+int(i != j), path+(j,))
                         for i, (cost, path) in states.items())
        states = nxt
    products, selection = min(states.values())
    schedule = tuple(family[i] for i in selection)
    if any(mask not in plane for mask, plane in zip(demands, schedule)):
        raise AssertionError('A selected control is outside its two-flag plane.')
    if any(len(set(a)&set(b)) != 1 for a, b in zip(schedule, schedule[1:]) if a != b):
        raise AssertionError('A changed plane has no unique retained flag.')
    return schedule, dict(plane_family_size=7, flag_capacity=2,
        initial_products=2, replacement_products=products-2,
        total_products_per_direction=products,
        optimal_in_two_flag_plane_replacement_family=True,
        masks=list(demands), planes=[list(p) for p in schedule])


@lru_cache(maxsize=1)
def synthesize():
    finite = screen()
    if (finite.get('outcome') != 'FOUND_EXACT_NETWORK'
            or finite.get('minimum_length') != 7
            or finite.get('exhaustive_boolean_rows') != 192
            or finite.get('no_wall_clock_selection') is not True):
        raise AssertionError('The fresh six-case C5 synthesis did not meet the scoped target.')
    operations = [dict(kind='c5', control_mask=int(item['control_mask']),
                       swap=tuple(item['swap'])) for item in finite['network']]
    # CRT: j = 5*p + 6*t mod10. Translation by r changes p by r mod2
    # and t by r mod5. The parity flip commutes with the C5 translations.
    operations.append(dict(kind='parity', control_mask=1))
    schedule, control = choose_planes(op['control_mask'] for op in operations)
    if control['total_products_per_direction'] != 4:
        raise AssertionError('The two-flag schedule no longer uses four products per direction.')
    return tuple(operations), schedule, dict(finite_search=finite, control_schedule=control,
        crt_formula='j = (5*p + 6*t) mod10', outer_twenty_bit_cycles=2,
        c5_cycles_per_C10=2, C10_swaps_per_direction=19,
        twenty_word_even_swaps_per_direction=38,
        mathematical_inputs_only=True, saved_network_input=False)


def flag_terms(mask):
    """u times a linear form in packed bits zero, one, three; plus t and u."""
    if not 0 < mask < 8:
        raise ValueError('A route flag must be a nonzero three-bit linear form.')
    # r bits on every valid packed state: (u*q0, u*(q1 XOR q3), u*q3).
    coefficients = (mask & 1, (mask >> 1) & 1, ((mask >> 1) ^ (mask >> 2)) & 1)
    return tuple((1 << 5)|(1 << bit) for bit, active in zip((0, 1, 3), coefficients)
                 if active)


class TwoLinearFlags:
    """Two clean flag slots, with exact measured replacement and CZ repayment."""
    def __init__(self, builder, packed, u, plane, *, omit_repayment=False):
        self.builder = builder
        self.variables = list(packed.residual[:4])+[packed.t, u]
        if len(set(self.variables)) != 6:
            raise ValueError('The packed flag variables must be distinct.')
        if tuple(plane) not in planes():
            raise ValueError('The initial flag set is not a three-bit plane.')
        self.masks = list(plane[:2])
        self.wires = list(builder.alloc_qubits(2))
        self.products = 0
        self.measurements = 0
        self.transitions = []
        self.omit_repayment = bool(omit_repayment)
        for wire, mask in zip(self.wires, self.masks):
            self._compute(wire, mask)

    def _compute(self, target, mask):
        plan = xor_polynomial(self.builder, self.variables, target, flag_terms(mask))
        if len(plan.products) != 1:
            raise AssertionError('A linear r flag did not compile to one quadratic product.')
        self.products += 1

    def _erase(self, index):
        if self.omit_repayment:
            outcome = self.builder.alloc_bits(1)[0]
            self.builder.hmr(self.wires[index], outcome)
            self.builder.free(self.wires[index]); self.builder.free(outcome)
        else:
            _erase_polynomial(self.builder, self.wires[index], self.variables,
                              flag_terms(self.masks[index]))
        self.measurements += 1

    @property
    def plane(self):
        a, b = self.masks
        return tuple(sorted((a, b, a ^ b)))

    def move_to(self, plane):
        plane = tuple(plane)
        if plane == self.plane:
            return
        if plane not in planes():
            raise ValueError('The replacement flag set is not a three-bit plane.')
        previous = self.plane
        common, = set(previous)&set(plane)
        if common == self.masks[0]:
            replace = 1
        elif common == self.masks[1]:
            replace = 0
        else:
            self.builder.cx(self.wires[1], self.wires[0])
            self.masks[0] ^= self.masks[1]
            if self.masks[0] != common:
                raise AssertionError('The Clifford rebase did not expose the common flag.')
            replace = 1
        discarded = self.masks[replace]
        self._erase(replace)
        chosen = min(mask for mask in plane if mask != common)
        self.wires[replace] = self.builder.alloc_qubits(1)[0]
        self.masks[replace] = chosen
        self._compute(self.wires[replace], chosen)
        if self.plane != plane:
            raise AssertionError('The live replacement flags do not span the chosen plane.')
        self.transitions.append(dict(old=list(previous), new=list(plane), retained=common,
                                     erased=discarded, computed=chosen))

    @contextmanager
    def control(self, mask):
        if mask == self.masks[0]:
            yield self.wires[0]
        elif mask == self.masks[1]:
            yield self.wires[1]
        elif mask == self.masks[0] ^ self.masks[1]:
            self.builder.cx(self.wires[1], self.wires[0])
            try:
                yield self.wires[0]
            finally:
                self.builder.cx(self.wires[1], self.wires[0])
        else:
            raise ValueError('The requested control is not in the current two-flag plane.')

    def close(self):
        for index in (1, 0):
            self._erase(index)


def coordinate(outer, parity, residue):
    return outer+2*((5*parity+6*residue) % 10)


def emit_even_route(builder, value, packed, u, *, inverse=False, omit_repayment=False):
    value = list(value)
    if len(value) != 20 or len(set(value)) != 20 or packed.max_k != 10:
        raise ValueError('The certified CRT route is word20 and k in0..10.')
    operations, schedule, _certificate = synthesize()
    steps = list(zip(operations, schedule))
    if inverse:
        steps.reverse()
    flags = TwoLinearFlags(builder, packed, u, steps[0][1], omit_repayment=omit_repayment)
    swaps = 0
    try:
        for operation, plane in steps:
            flags.move_to(plane)
            with flags.control(operation['control_mask']) as control:
                if operation['kind'] == 'c5':
                    left, right = operation['swap']
                    for outer in range(2):
                        for parity in range(2):
                            builder.cswap(control, value[coordinate(outer, parity, left)],
                                          value[coordinate(outer, parity, right)])
                            swaps += 1
                else:
                    for outer in range(2):
                        for residue in range(5):
                            builder.cswap(control, value[coordinate(outer, 0, residue)],
                                          value[coordinate(outer, 1, residue)])
                            swaps += 1
    finally:
        flags.close()
    if swaps != 38 or flags.products != 4 or flags.measurements != 4:
        raise AssertionError('The emitted CRT route differs from its complete control budget.')
    return dict(cswaps=swaps, flag_products=flags.products,
                flag_measurements=flags.measurements, plane_transitions=flags.transitions)


def permutation_certificate():
    operations, _schedule, certificate = synthesize()
    checked10 = checked20 = 0
    def apply(word, r, *, inverse=False):
        steps = reversed(operations) if inverse else operations
        for op in steps:
            if not ((op['control_mask'] & r).bit_count() & 1):
                continue
            if op['kind'] == 'c5':
                i, j = op['swap']
                pairs = [((5*p+6*i) % 10, (5*p+6*j) % 10) for p in range(2)]
            else:
                pairs = [(6*t % 10, (5+6*t) % 10) for t in range(5)]
            for i, j in pairs:
                word[i], word[j] = word[j], word[i]
    for r in range(6):
        for value in range(1 << 10):
            old = [(value >> i) & 1 for i in range(10)]
            word = list(old); apply(word, r)
            if word != [old[(i-r) % 10] for i in range(10)]:
                raise AssertionError('A complete ten-bit CRT truth row differs.')
            apply(word, r, inverse=True)
            if word != old:
                raise AssertionError('The inverse CRT route did not restore its word.')
            checked10 += 1
        for bit in range(20):
            old = [int(i == bit) for i in range(20)]
            word = list(old)
            for outer in range(2):
                cycle = word[outer::2]; apply(cycle, r); word[outer::2] = cycle
            if word != [old[(i-2*r) % 20] for i in range(20)]:
                raise AssertionError('A twenty-bit CRT coordinate basis row differs.')
            checked20 += 1
    return dict(certificate, C10_exhaustive_truth_rows=checked10,
        twenty_word_basis_rows=checked20, both_directions_exact=True,
        arbitrary_twenty_bit_words_by_coordinate_linearity=True)


def low_phase_crt(builder, value, packed, fractional_bits, *, turn_offsets,
                  threshold, beta=1, omit_flag_repayment=False):
    """Same tail43 low phase; replace its even-shift routing by the CRT route."""
    value = list(value); offsets = tuple(map(Fraction, turn_offsets)); beta = Fraction(beta)
    if len(value) != 20 or fractional_bits != 37 or len(offsets) != 30:
        raise ValueError('Require the selected word20, F37, thirty-feature geometry.')
    if not packed.is_packed or packed.max_k != 10:
        raise ValueError('Require the packed shift range0..10.')
    if len(set(value+list(packed.residual)+[packed.t])) != 20+len(packed.residual)+1:
        raise ValueError('The phase word must be disjoint from the packed shift.')
    base = [beta*_pow2(i-fractional_bits+1) for i in range(20)]
    overflow = [beta*((1 << 20)-1)*_pow2(j-fractional_bits+1) for j in range(10)]
    products = conditional = 0
    angles = []; routes = []
    with packed.higher_nonzero() as u:
        routes.append(emit_even_route(builder, value, packed, u,
                                     omit_repayment=omit_flag_repayment))
        products += routes[-1]['flag_products']
        pairs = rotation_pairs(20, 1)
        with _flag(builder, packed, u, 0) as flag:
            for a, b in pairs:
                builder.cswap(flag, value[a], value[b])
        products += 1
        for i, wire in enumerate(value):
            angle = base[i]+2*offsets[i]
            builder.z_pow(wire, angle); angles.append(angle)
        for j in range(8):
            with threshold(builder, packed, u, j+1) as (control, cost, ccz):
                products += cost; conditional += ccz
                temporary = builder.alloc_qubits(1)[0]
                builder.ccx(control, value[j], temporary)
                angle = overflow[j]+2*offsets[20+j]
                builder.z_pow(temporary, angle)
                builder.del_and(control, value[j], temporary); builder.free(temporary)
                products += 1; angles.append(angle)
        with _flag(builder, packed, u, 0) as flag:
            for a, b in reversed(pairs):
                builder.cswap(flag, value[a], value[b])
        products += 1
        routes.append(emit_even_route(builder, value, packed, u, inverse=True,
                                     omit_repayment=omit_flag_repayment))
        products += routes[-1]['flag_products']
    swaps = 2*(38+19)
    return dict(width=20, max_k=10, direct_packed=True, crt_c10_phase=True,
        cswaps=swaps, and_products=products+2, hmr_conditioned_ccz=conditional,
        expected_toffolis=swaps+products+2+conditional/2,
        z_pow_calls=len(angles), half_turn_angles=list(map(str, angles)),
        turn_offsets=list(map(str, offsets)), skipped_overflow=[8, 9],
        route_controllers=routes, exact_network=permutation_certificate())
