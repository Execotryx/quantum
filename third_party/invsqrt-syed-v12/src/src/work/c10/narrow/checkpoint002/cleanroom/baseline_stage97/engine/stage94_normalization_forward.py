# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Expose every pair-count selector through copies of the existing prefixes.

The original count scope already computes t_j=[k>=j].  Every function of
k which is zero at k=0 is the parity of those thresholds at its successive
value changes.  Three extra copies provide the products of the low count
bit with each higher count bit.  Together with the original count flags,
two coarse products and t=[k>0], they span all ten nonconstant functions.

After the source-derived pair shift, all five product helpers are erased
with their unchanged binary-count parents.  Only the original count and
the two original packed-count indicator wires survive the boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from codebook import BinarySpan, bits, parity_function
import prefix_normalization


EXTRA_PRODUCT_MASKS = (3, 5, 9)
ROUTE_PRODUCT_MASKS = (6, 10) + EXTRA_PRODUCT_MASKS


def count_function(mask, count):
    return int(count & mask == mask)


@lru_cache(maxsize=2048)
def selector_expression(mask):
    """Derive an exact homogeneous parity on the eleven valid count labels."""
    if not isinstance(mask, int) or mask < 0 or mask >> 11 or mask & 1:
        raise ValueError('A pair-route selector must be zero at count zero.')
    masks = tuple(1 << bit for bit in range(4)) + ROUTE_PRODUCT_MASKS
    functions = [sum(count_function(term, count) << count for count in range(11))
                 for term in masks]
    functions.append(sum(int(count > 0) << count for count in range(11)))
    span = BinarySpan(functions)
    if len(span.pivots) != 10:
        raise AssertionError('The copied pair-count functions do not span every valid selector.')
    expression = span.solve(mask)
    if expression is None or parity_function(expression, functions) != mask:
        raise AssertionError('A complete count-function basis did not express its selector.')
    return expression


@contextmanager
def borrow_selector(builder, basis, mask):
    """Expose a selector in a Clifford frame, restoring the entire basis."""
    basis = list(basis)
    if len(basis) != 10 or len(set(basis)) != 10:
        raise ValueError('A pair selector requires ten distinct retained count functions.')
    indices = list(bits(selector_expression(mask)))
    if not indices:
        yield None
        return
    control = basis[indices[0]]
    parents = [basis[index] for index in indices[1:]]
    for parent in parents:
        builder.cx(parent, control)
    try:
        yield control
    finally:
        for parent in reversed(parents):
            builder.cx(parent, control)


class FullCountForwardControls:
    """Extend the accepted shared count scope by three free prefix copies.

Install inside the existing SharedNormalizationControls context.  Call
emit_pair_route in place of the old coarse and last-pair route.  The caller
then performs the unchanged ordinary semilog alignment.  This owner does
not alter PackedShift.pack or any inverse cleanup.
"""
    def __init__(self, shared_controls):
        self.shared = shared_controls
        self.products = {}
        self.input_bounds = {}
        self.captures = 0
        self.routes = []

    @staticmethod
    def _key(builder, flags):
        return id(builder), tuple(flags)

    @contextmanager
    def install(self):
        previous_count = prefix_normalization.xor_pair_count

        def count(builder, inputs, flags, *, original_input_max=None):
            inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
            if len(inputs) != 22 or maximum != 10:
                raise ValueError('The complete count basis needs the selected pair-count geometry.')
            if (not isinstance(original_input_max, int)
                    or not 0 < original_input_max < 3*(1 << (len(inputs)-2))):
                raise ValueError('The selected normalization requires an explicit exclusive-top-pair input bound.')
            key = self._key(builder, flags)
            if key in self.products:
                raise AssertionError('Extra prefix products already have an owner.')
            extra = list(builder.alloc_qubits(len(EXTRA_PRODUCT_MASKS)))
            previous_prefixes = prefix_normalization._prefixes
            captured = 0

            @contextmanager
            def capture(active_builder, zero_bits, length, **options):
                nonlocal captured
                if active_builder is not builder or length != 2*maximum or captured:
                    raise AssertionError('The original count-prefix scope changed its selected lifetime.')
                with previous_prefixes(active_builder, zero_bits, length, **options) as prefixes:
                    for mask, destination in zip(EXTRA_PRODUCT_MASKS, extra):
                        for threshold in range(1, maximum+1):
                            if count_function(mask, threshold) ^ count_function(mask, threshold-1):
                                builder.cx(prefixes[2*threshold], destination)
                    captured += 1
                    yield prefixes

            prefix_normalization._prefixes = capture
            try:
                previous_count(builder, inputs, flags, original_input_max=original_input_max)
            finally:
                prefix_normalization._prefixes = previous_prefixes
            if captured != 1:
                raise AssertionError('The extra count products did not share the original prefix computation.')
            self.products[key] = extra
            self.input_bounds[key] = original_input_max
            self.captures += 1

        prefix_normalization.xor_pair_count = count
        try:
            yield self
        finally:
            prefix_normalization.xor_pair_count = previous_count
        if self.products or self.input_bounds:
            raise AssertionError('A forward count-product owner remained unconsumed.')

    def emit_pair_route(self, builder, inputs, flags, certificate):
        inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
        if len(inputs) != 22 or maximum != 10:
            raise ValueError('The selected pair route requires twenty-two data bits.')
        if (certificate.get('status') != 'CERTIFIED_PAIR_ROUTE_FOUND'
                or not certificate.get('exact_symbolic_forward_and_inverse')
                or certificate.get('width') != 11):
            raise AssertionError('A pair route requires its fresh complete symbol certificate.')
        key = self._key(builder, flags)
        extra = self.products.get(key)
        coarse = self.shared.forward_products.get(key)
        indicators = self.shared.pack_indicators.get(key)
        if extra is None or coarse is None or indicators is None:
            raise AssertionError('A forward pair route lacks its captured original count functions.')
        entry = builder.num_allocated_qubits
        basis = list(flags) + list(coarse) + list(extra) + [indicators[0]]
        exchanges = certificate['pair_exchanges']
        swaps = 0
        for first, second, mask in exchanges:
            with borrow_selector(builder, basis, mask) as control:
                if control is None:
                    continue
                for lane in range(2):
                    builder.cswap(control, inputs[2*first+lane], inputs[2*second+lane])
                    swaps += 1
        if swaps != 2*certificate['pair_exchange_count']:
            raise AssertionError('Pair-route emission disagrees with its mathematical count.')
        for mask, wire in zip(ROUTE_PRODUCT_MASKS, list(coarse)+list(extra)):
            indices = list(bits(mask))
            if len(indices) != 2:
                raise AssertionError('A retained route product is no longer quadratic.')
            builder.del_and(flags[indices[0]], flags[indices[1]], wire)
            builder.free(wire)
        self.products.pop(key)
        input_bound = self.input_bounds.pop(key)
        self.shared.forward_products.pop(key)
        self.shared.forward_product_erasures += len(coarse)
        if builder.num_allocated_qubits != entry-len(ROUTE_PRODUCT_MASKS):
            raise AssertionError('The full count basis did not return all five product helpers.')
        record = dict(direction='forward', physical_controlled_swaps=swaps,
                      selector_ANDs=0, extra_prefix_product_ANDs=0,
                      extra_prefix_product_copies=len(extra),
                      all_product_helpers_erased_from_retained_flags=True,
                      old_pack_indicators_and_binary_flags_preserved=True,
                      original_input_max=input_bound,
                      exclusive_original_top_pair=True,
                      pending_new_measurement_debts=0)
        self.routes.append(record)
        self.shared.routes.append(dict(record))
        return record

    def metadata(self):
        if self.products or self.input_bounds or self.captures != 1 or len(self.routes) != 1:
            raise AssertionError('The complete forward count-function lifecycle is unfinished.')
        return dict(status='FULL_FORWARD_COUNT_FUNCTIONS_CONSUMED',
                    route=self.routes[0], count_ANDs_unchanged=18,
                    full_selector_span_dimension=10,
                    additional_qubits_during_count=len(EXTRA_PRODUCT_MASKS),
                    new_qubits_at_normalization_exit=0,
                    source_tables_or_compiled_circuits=False)
