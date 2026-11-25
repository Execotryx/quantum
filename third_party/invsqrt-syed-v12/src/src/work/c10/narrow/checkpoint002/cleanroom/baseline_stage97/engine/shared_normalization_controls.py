# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Use existing count functions for every coarse-normalization selector.

Forward normalization already exposes every leading-zero prefix.  Four
CNOT-only copies give the nonzero coarse count products and the two packed
count indicators.  Product cleanup uses conditional CZ on the unchanged
count flags.  PackedShift.pack consumes the indicator wires with its original
residual encoding and measurement phases.  Inverse routing borrows the same
products from the late packed cleanup's retained monomials.

The original source-synthesized route is retained: twenty-four physical
controlled swaps per direction.  All six-label selectors with false at zero
are linear combinations of the three coarse flags and their two nonzero
products.  No selector AND, saved route, or compiled-circuit input is used.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from itertools import groupby

from codebook import BinarySpan, bits, parity_function
from late_packed_cleanup import LatePackedCleanupPass
import kickmix as km
import normalization_fused
import prefix_normalization
from packed_shift import PackedShift, _erase_u_from_flags


COARSE_MONOMIALS = (1, 2, 4, 3, 5)


@lru_cache(maxsize=32)
def selector_expression(mask):
    """Return an exact parity of the five cached coarse-count functions."""
    if not isinstance(mask, int) or mask < 0 or mask >> 6 or mask & 1:
        raise ValueError('A coarse selector must cover six labels and be false at zero.')
    functions = [sum(int(label & term == term) << label for label in range(6))
                 for term in COARSE_MONOMIALS]
    span = BinarySpan(functions)
    if len(span.pivots) != 5:
        raise AssertionError('The cached count functions do not span the five nonzero labels.')
    expression = span.solve(mask)
    if expression is None or parity_function(expression, functions) != mask:
        raise AssertionError('A zero-false selector has no exact cached parity.')
    return expression


@contextmanager
def borrow_selector(builder, basis_wires, mask):
    """Borrow a wire for a selector parity, restoring every source on exit.

    The identically false selector yields None.  Otherwise the first active
    basis wire is a temporary Clifford-frame pivot and requires no allocation.
    """
    basis_wires = list(basis_wires)
    if len(basis_wires) != 5 or len(set(basis_wires)) != 5:
        raise ValueError('A coarse selector needs five distinct cached basis wires.')
    indices = list(bits(selector_expression(mask)))
    if not indices:
        yield None
        return
    pivot = basis_wires[indices[0]]
    others = [basis_wires[index] for index in indices[1:]]
    for source in others:
        builder.cx(source, pivot)
    try:
        yield pivot
    finally:
        for source in reversed(others):
            builder.cx(source, pivot)


class SharedNormalizationControls:
    """Scoped adapter preserving the Stage85 route and normalization semantics."""
    def __init__(self, late_cleanup):
        self.late_cleanup = late_cleanup
        self.forward_products = {}
        self.pack_indicators = {}
        self.routes = []
        self.prefix_captures = 0
        self.forward_product_erasures = 0
        self.captured_indicator_packs = 0

    @staticmethod
    def _key(builder, flags):
        return id(builder), tuple(flags)

    def retained_monomials(self, builder, flags):
        """Expose the live inverse count basis without changing its ownership."""
        prepared = self.late_cleanup.prepared.get(self._key(builder, flags))
        if prepared is None:
            raise AssertionError('Inverse cached routing has no retained late cleanup basis.')
        return prepared.monomials

    def _emit_coarse(self, builder, inputs, flags, *, inverse):
        flags = list(flags)
        key = self._key(builder, flags)
        if inverse:
            monomials = self.retained_monomials(builder, flags)
            basis = [monomials[term << 1] for term in COARSE_MONOMIALS]
            products = None
        else:
            products = self.forward_products.get(key)
            if products is None:
                raise AssertionError('Forward cached routing has no captured prefix products.')
            basis = list(flags[1:]) + list(products)
        certificate = normalization_fused.synthesize()
        if not certificate['exact_symbolic_forward_and_inverse']:
            raise AssertionError('The existing route lost its exact symbolic certificate.')
        path = certificate['coarse_block_exchanges']
        sequence = list(reversed(path)) if inverse else list(path)
        physical_swaps = 0
        selector_groups = 0
        try:
            for mask, group in groupby(sequence, key=lambda operation: operation[2]):
                selector_groups += 1
                with borrow_selector(builder, basis, mask) as control:
                    for first, second, _ in group:
                        if control is None:
                            continue
                        for lane in range(4):
                            left, right = 4 * first + lane, 4 * second + lane
                            if left < len(inputs) and right < len(inputs):
                                builder.cswap(control, inputs[left], inputs[right])
                                physical_swaps += 1
            if physical_swaps != 24:
                raise AssertionError('The selected cached route no longer has twenty-four physical swaps.')
        finally:
            if products is not None:
                # The parity-frame context restores every flag before these
                # exact product erasures.  No original input is consulted.
                builder.del_and(flags[1], flags[2], products[0])
                builder.free(products[0])
                builder.del_and(flags[1], flags[3], products[1])
                builder.free(products[1])
                self.forward_products.pop(key)
                self.forward_product_erasures += 2
        self.routes.append(dict(direction='inverse' if inverse else 'forward',
                                physical_controlled_swaps=physical_swaps,
                                selector_ANDs=0, selector_groups=selector_groups,
                                products_borrowed_from='retained_count_monomials' if inverse else 'leading_zero_prefixes',
                                reference_selector_inclusive_ANDs=certificate['total_Toffoli_cost']))

    @contextmanager
    def install(self):
        old_count = prefix_normalization.xor_pair_count
        old_coarse = normalization_fused._coarse
        old_pack = PackedShift.pack

        def count(builder, inputs, flags, *, original_input_max=None):
            inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
            if len(inputs) != 22 or maximum != 10:
                raise ValueError('Shared selectors require the selected twenty-two-bit count geometry.')
            key = self._key(builder, flags)
            if key in self.forward_products or key in self.pack_indicators:
                raise AssertionError('The forward count functions already have an owner.')
            copied = list(builder.alloc_qubits(4))
            products, indicators = copied[:2], copied[2:]
            old_prefixes = prefix_normalization._prefixes
            captures = 0

            @contextmanager
            def captured(active_builder, zero_bits, length, **options):
                nonlocal captures
                if active_builder is not builder or length != 20 or captures:
                    raise AssertionError('The original pair-count prefix lifetime changed.')
                with old_prefixes(active_builder, zero_bits, length, **options) as prefixes:
                    # On k<=10, f1*f2 = [k>=6] XOR [k>=8],
                    # and f1*f3 = [k>=10].
                    builder.cx(prefixes[12], products[0])
                    builder.cx(prefixes[16], products[0])
                    builder.cx(prefixes[20], products[1])
                    builder.cx(prefixes[2], indicators[0])
                    builder.cx(prefixes[4], indicators[1])
                    captures += 1
                    yield prefixes

            prefix_normalization._prefixes = captured
            try:
                old_count(builder, inputs, flags, original_input_max=original_input_max)
            finally:
                prefix_normalization._prefixes = old_prefixes
            if captures != 1:
                raise AssertionError('The forward product copy did not use exactly one existing prefix scope.')
            self.forward_products[key] = products
            self.pack_indicators[key] = indicators
            self.prefix_captures += 1

        def pack(packed):
            if packed.is_packed:
                return old_pack(packed)
            packed._require_no_borrowed_controls()
            key = self._key(packed.builder, packed._flags)
            indicators = self.pack_indicators.get(key)
            if indicators is None:
                return old_pack(packed)
            if packed.max_k != 10 or packed._flag_debts or packed._u_debts:
                raise AssertionError('Captured indicators were supplied to a different packed-count interface.')
            builder = packed.builder
            flags = packed._flags
            retained, higher = indicators
            # The five lines below preserve the original pack residual map,
            # u-HMR phase, and flag ownership; only the two ANDs are absent.
            packed._xor_residual_code(flags, higher, retained)
            _erase_u_from_flags(builder, flags, higher)
            outcomes = builder.alloc_bits(4)
            builder.hmr(km.array(flags), outcomes)
            builder.free(km.array(flags))
            packed._flag_debts = list(outcomes)
            packed._flags = None
            packed._t = retained
            self.pack_indicators.pop(key)
            self.captured_indicator_packs += 1
            return packed

        prefix_normalization.xor_pair_count = count
        normalization_fused._coarse = self._emit_coarse
        PackedShift.pack = pack
        try:
            yield self
        finally:
            prefix_normalization.xor_pair_count = old_count
            normalization_fused._coarse = old_coarse
            PackedShift.pack = old_pack
        if self.forward_products or self.pack_indicators:
            raise AssertionError('A captured forward count function was not consumed.')


class SharedNormalizationCleanupPass:
    """Install shared forward/inverse controls and the nine-AND final decoder.

    Place this scope outside refined_generator.build, so its threshold owner
    wraps the final decoder normally.  Stage85 production files need no edits
    to use this isolated component in a research fixture.
    """
    def __init__(self):
        self.late = LatePackedCleanupPass()
        self.controls = SharedNormalizationControls(self.late)

    @property
    def prepared(self):
        return self.late.prepared

    @property
    def decodings(self):
        return self.late.decodings

    @property
    def consumptions(self):
        return self.late.consumptions

    @contextmanager
    def install(self):
        with self.late.install(), self.controls.install():
            yield self

    def metadata(self):
        directions = [item['direction'] for item in self.controls.routes]
        if directions != ['forward', 'inverse'] or self.decodings != 1 or self.consumptions != 1:
            raise AssertionError('The selected full normalization lifecycle was not completed once.')
        if self.controls.prefix_captures != 1 or self.controls.forward_product_erasures != 2:
            raise AssertionError('Forward prefix-product ownership was not balanced.')
        if self.controls.captured_indicator_packs != 1:
            raise AssertionError('The captured packing indicators were not consumed exactly once.')
        return dict(source_component='shared_forward_prefix_and_late_count_basis',
                    coarse_routes=self.controls.routes,
                    direct_final_decoder_ANDs=9,
                    original_coarse_route_preserved=True,
                    original_prefix_chain_preserved=True,
                    prefix_product_copies=2, prefix_product_ANDs=0,
                    prefix_indicator_copies=2, prefix_indicator_ANDs=0,
                    original_packed_indicator_ANDs_avoided=2,
                    original_pack_residual_and_phase_debts_preserved=True,
                    prefix_products_erased_by_exact_HMR=True,
                    late_basis_consumed_once=True,
                    threshold_repayments=self.late.threshold_repayments,
                    component_saving_E_vs_stage85='23/2',
                    overlap_note='Includes all six old selector ANDs; do not add trajectory-selector refinement savings again.',
                    separate_Fourier_carry_reuse_excluded=True,
                    full_generator_official_acceptance_required=True)
