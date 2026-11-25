# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Retain raw prefixes through a 42-swap exact normalization butterfly.

The existing eighteen-AND pair-count chain supplies its original flags,
packing indicators, and initial-owner threshold.  Retaining that chain,
copying its first input, and extending it by one AND exposes all twenty-one
leading-zero thresholds.  Removing the original leading one is affine in
those thresholds.  The binary butterfly then aligns the remaining payload.

Every raw prefix is measured and its phase is repaid from the retained pair
count basis and the final high/low branch bit.  Even prefixes are count
thresholds; odd prefixes are quadratic in that basis and the branch.  The
five copied quadratic count products are erased last from their original
binary parents.  No new measurement owner crosses the normalization cut.
"""
from __future__ import annotations

from contextlib import contextmanager

from codebook import bits
import prefix_normalization
from stage94_bit_routing_math import certificate, leading_indicator_terms, operations
from stage94_normalization_forward import (
    FullCountForwardControls, ROUTE_PRODUCT_MASKS, borrow_selector)


@contextmanager
def borrow_prefix_selector(builder, prefixes, terms):
    """Borrow a parity of physical leading-zero thresholds and restore it."""
    terms = tuple(terms)
    if not terms:
        yield None
        return
    if 0 in terms or any(index not in prefixes for index in terms):
        raise ValueError('A routing selector must be a nonconstant parity of retained prefixes.')
    control = prefixes[terms[0]]
    parents = [prefixes[index] for index in terms[1:]]
    for parent in parents:
        builder.cx(parent, control)
    try:
        yield control
    finally:
        for parent in reversed(parents):
            builder.cx(parent, control)


def threshold_truth(threshold, maximum=10):
    """Return T_j=[k>=j], including the constant endpoints T_0 and T_11."""
    if not 0 <= threshold <= maximum+1:
        raise ValueError('The count threshold is outside its finite domain.')
    return sum(int(count >= threshold) << count for count in range(maximum+1))


def _conditioned_phase(builder, outcome, target, branch):
    builder.push_condition(outcome)
    if branch is None:
        builder.z(target)
    elif target is True:
        builder.z(branch)
    else:
        builder.cz(branch, target)
    builder.pop_condition()


def _phase_count_function(builder, count_basis, truth, outcome, *, branch=None):
    """Repay m*f(k), or m*branch*f(k), without nonlinear quantum gates."""
    if truth & 1:
        _conditioned_phase(builder, outcome, True, branch)
        truth ^= (1 << 11)-1
    if truth:
        with borrow_selector(builder, count_basis, truth) as control:
            if control is None:
                raise AssertionError('A nonzero count function produced an empty parity.')
            _conditioned_phase(builder, outcome, control, branch)


def repay_raw_prefix_phase(builder, outcome, index, count_basis, branch):
    """Pay the complete exact sign of one measured raw prefix.

Here branch=1 denotes the high half of the normalized word.  Thus
P_(2j)=T_j and P_(2j+1)=T_j XOR branch*(T_j XOR T_(j+1)).
The j=0 constant is included explicitly, so both HMR outcomes are exact
even for the first prefix and its observable branch-global phase.
"""
    if not 1 <= index <= 21:
        raise ValueError('A retained raw prefix must have length one through twenty-one.')
    threshold = index//2
    first = threshold_truth(threshold)
    _phase_count_function(builder, count_basis, first, outcome)
    if index & 1:
        difference = first ^ threshold_truth(threshold+1)
        _phase_count_function(builder, count_basis, difference, outcome, branch=branch)


class RetainedPrefixBitForward:
    """Own retained raw prefixes and the matched forward butterfly.

Install this context inside SharedNormalizationControls.install().  It
adds the three extra count-product copies through FullCountForwardControls
and leaves the shared packing adapter and initial-owner prefix hook intact.
Call emit(builder, inputs, flags) at the original fused-shift point.  The
outer factory must match and suppress the following ordinary semilog call.
"""
    def __init__(self, shared_controls):
        self.shared = shared_controls
        self.full = FullCountForwardControls(shared_controls)
        self.retained = {}
        self.prefix_captures = 0
        self.routes = []

    @staticmethod
    def _prefix_key(builder, zero_bits):
        return id(builder), tuple(zero_bits)

    @contextmanager
    def install(self):
        previous_prefixes = prefix_normalization._prefixes

        @contextmanager
        def retain(builder, zero_bits, length, *, affine_first_pair=False):
            zero_bits = list(zero_bits)
            if length != 20 or len(zero_bits) != 20 or not affine_first_pair:
                raise ValueError('Retained normalization prefixes require the bounded original twenty-bit chain.')
            key = self._prefix_key(builder, zero_bits)
            if self.prefix_captures or key in self.retained:
                raise AssertionError('The selected raw-prefix owner may be created only once.')
            first = builder.alloc_qubits(1)[0]
            builder.cx(zero_bits[0], first)
            prefixes = {1:first}
            for index in range(1, length):
                target = builder.alloc_qubits(1)[0]
                if index == 1:
                    # The original input promise excludes both top bits
                    # being one, so this first zero-pair test is affine.
                    builder.x(target)
                    builder.cx(prefixes[index], target)
                    builder.cx(zero_bits[index], target)
                else:
                    builder.ccx(prefixes[index], zero_bits[index], target)
                prefixes[index+1] = target
            self.retained[key] = prefixes
            self.prefix_captures += 1
            # Deliberately retain all twenty wires across scope exit.  The
            # original input frame is restored by xor_pair_count before emit.
            # Calling the old parent's cleanup after routing would be wrong;
            # emit instead repays each exact prefix phase from retained k,b.
            yield prefixes

        prefix_normalization._prefixes = retain
        try:
            with self.full.install():
                yield self
        finally:
            prefix_normalization._prefixes = previous_prefixes
        if self.retained:
            raise AssertionError('A raw-prefix owner survived its normalization scope.')

    def emit(self, builder, inputs, flags, route_certificate=None):
        inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
        if len(inputs) != 22 or maximum != 10:
            raise ValueError('The binary normalization butterfly requires the selected original geometry.')
        route_certificate = certificate(21) if route_certificate is None else route_certificate
        if (route_certificate.get('status') != 'EXACT_ZERO_SUPPORTED_BINARY_BUTTERFLY'
                or route_certificate.get('controlled_swaps') != 42
                or not route_certificate.get('forward_and_inverse_proved')):
            raise AssertionError('The forward butterfly lacks its fresh mathematical certificate.')
        key = self.full._key(builder, flags)
        raw_key = self._prefix_key(builder, reversed(inputs[2:]))
        prefixes = self.retained.get(raw_key)
        coarse = self.shared.forward_products.get(key)
        extra = self.full.products.get(key)
        indicators = self.shared.pack_indicators.get(key)
        input_bound = self.full.input_bounds.get(key)
        if (prefixes is None or coarse is None or extra is None or indicators is None
                or not isinstance(input_bound, int)
                or not 0 < input_bound < 3*(1 << 20)):
            raise AssertionError('The forward butterfly lacks its original prefix/count owners or input bound.')
        count_basis = list(flags)+list(coarse)+list(extra)+[indicators[0]]
        entry = builder.num_allocated_qubits
        # Extend the zero-prefix chain once.  Its original raw data frame
        # was restored by xor_pair_count before this route was called.
        final_prefix = builder.alloc_qubits(1)[0]
        builder.x(inputs[1])
        builder.ccx(prefixes[20], inputs[1], final_prefix)
        builder.x(inputs[1])
        prefixes[21] = final_prefix
        for position, target in enumerate(inputs):
            for index in leading_indicator_terms(position, len(inputs)):
                if index:
                    builder.cx(prefixes[index], target)
                else:
                    builder.x(target)
        swaps = 0
        for operation in operations(21):
            with borrow_prefix_selector(builder, prefixes, operation['prefix_terms']) as control:
                if control is None:
                    raise AssertionError('A physical butterfly edge has an identically false selector.')
                builder.cswap(control, inputs[operation['first']], inputs[operation['second']])
                swaps += 1
        if swaps != route_certificate['controlled_swaps']:
            raise AssertionError('The physical forward route changed its certified swap count.')
        # The original high/low branch is the complement of ell's low bit.
        # That low bit is the parity of every nonconstant prefix threshold.
        branch = inputs[-1]
        builder.x(branch)
        for index in range(1, 22):
            builder.cx(prefixes[index], branch)
        for index in reversed(range(1, 22)):
            wire = prefixes[index]
            outcome = builder.alloc_bits(1)[0]
            builder.hmr(wire, outcome)
            repay_raw_prefix_phase(builder, outcome, index, count_basis, branch)
            builder.free(outcome)
            builder.free(wire)
        self.retained.pop(raw_key)
        for mask, wire in zip(ROUTE_PRODUCT_MASKS, list(coarse)+list(extra)):
            parents = list(bits(mask))
            if len(parents) != 2:
                raise AssertionError('A captured count-product parent ceased to be quadratic.')
            builder.del_and(flags[parents[0]], flags[parents[1]], wire)
            builder.free(wire)
        self.full.products.pop(key)
        self.full.input_bounds.pop(key)
        self.shared.forward_products.pop(key)
        self.shared.forward_product_erasures += len(coarse)
        # Twenty prefixes entered this method, the twenty-first was local,
        # and all five product helpers also leave.  Other owners survive.
        if builder.num_allocated_qubits != entry-20-len(ROUTE_PRODUCT_MASKS):
            raise AssertionError('The forward butterfly changed the accepted normalization live boundary.')
        record = dict(direction='forward', original_input_max=input_bound,
                      exclusive_original_top_pair=True,
                      original_pair_count_ANDs=18, extra_last_prefix_ANDs=1,
                      physical_controlled_swaps=swaps,
                      exact_Toffoli_equivalents=19+swaps,
                      selector_ANDs=0, retained_raw_prefixes=21,
                      raw_prefix_HMRs=21, raw_prefix_repayment_Toffolis=0,
                      quadratic_count_products_erased=len(ROUTE_PRODUCT_MASKS),
                      extra_prefix_product_copies=len(extra),
                      old_pack_indicators_and_binary_flags_preserved=True,
                      initial_owner_threshold_preserved=True,
                      original_semilog_representation_preserved=True,
                      pending_new_measurement_debts=0)
        self.routes.append(record)
        self.full.routes.append(dict(record))
        self.shared.routes.append(dict(record))
        return record

    def metadata(self):
        if self.retained or self.prefix_captures != 1 or len(self.routes) != 1:
            raise AssertionError('The retained-prefix forward lifecycle is unfinished.')
        return dict(status='EXACT_RETAINED_PREFIX_BINARY_NORMALIZATION',
                    route=self.routes[0], mathematical_route=certificate(21),
                    count_functions=self.full.metadata(),
                    new_qubits_at_normalization_exit=0,
                    all_original_input_and_HMR_cases_required=True)
