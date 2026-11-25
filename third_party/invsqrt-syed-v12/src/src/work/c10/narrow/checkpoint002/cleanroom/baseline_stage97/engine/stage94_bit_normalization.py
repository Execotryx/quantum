# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Own exact bit-prefix normalization and its matched inverse lifecycle.

Both directions use a source-derived zero-supported binary butterfly.  The
forward direction retains the original count prefixes; the inverse expands
the existing final count basis into those prefixes.  All measurement signs
are repaid locally, and the original packed-state boundary is preserved.
"""
from __future__ import annotations

from contextlib import contextmanager
import sys

import fusion.normalization as normalization
from late_packed_cleanup import LatePackedCleanupPass
import normalization_fused
import prefix_normalization
from shared_normalization_controls import SharedNormalizationControls
from stage94_bit_normalization_forward import RetainedPrefixBitForward
from stage94_bit_normalization_inverse import restore_with_bit_prefixes
from stage94_bit_routing_math import certificate
import thermometer_cleanup


class Stage94BitNormalizationCleanupPass:
    """Match the original normalization, semilog, and final cleanup calls."""
    def __init__(self, *, semilog_modules=()):
        self.late = LatePackedCleanupPass()
        self.controls = SharedNormalizationControls(self.late)
        self.forward = RetainedPrefixBitForward(self.controls)
        self.semilog_modules = tuple(semilog_modules)
        self.states = {}
        self.inverse_flags = {}
        self.inverse_routes = []
        self.align_calls = []
        self.cleanup_calls = 0

    @property
    def prepared(self):
        return self.late.prepared

    @property
    def decodings(self):
        return self.late.decodings

    @property
    def consumptions(self):
        return self.late.consumptions

    @staticmethod
    def _key(builder, inputs):
        return id(builder), tuple(inputs)

    @contextmanager
    def install(self):
        if self.states:
            raise RuntimeError('Use a fresh bit-normalization owner for each complete emission.')
        with self.late.install(), self.controls.install(), self.forward.install():
            previous_shift = normalization_fused._fused_shift
            previous_cleanup = thermometer_cleanup.erase_pair_count_thermometer
            if (previous_shift.__module__ != normalization_fused.__name__
                    or previous_shift.__name__ != '_fused_shift'):
                raise RuntimeError('The selected normalization route already has another owner.')
            modules = [normalization]
            scheduled = sys.modules.get('scheduled_generator')
            for module in self.semilog_modules + ((scheduled,) if scheduled is not None else ()):
                if module not in modules:
                    modules.append(module)
            previous_align = [(module, module.semilog_align) for module in modules]
            if any(function is not normalization.semilog_align for _, function in previous_align):
                raise RuntimeError('A semilog alias already has an incompatible scoped owner.')

            def shift(builder, inputs, flags, *, inverse):
                inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
                if len(inputs) != 22 or maximum != 10:
                    raise ValueError('The bit-prefix route requires the selected original geometry.')
                key = self._key(builder, inputs)
                route = certificate(21)
                if inverse:
                    if self.states.get(key) != 'inverse_semilog_matched':
                        raise AssertionError('Inverse routing lacks its matched semilog boundary.')
                    record = restore_with_bit_prefixes(builder, inputs, flags, self.late, route)
                    self.inverse_routes.append(record)
                    self.controls.routes.append(dict(direction='inverse', **record))
                    self.inverse_flags[key] = tuple(flags)
                    self.states[key] = 'inverse_prefixes_erased'
                else:
                    if key in self.states:
                        raise AssertionError('The selected forward normalization may run only once.')
                    self.forward.emit(builder, inputs, flags, route)
                    self.states[key] = 'forward_route_emitted'

            def align(builder, inputs, *, inverse=False):
                key = self._key(builder, inputs)
                expected = 'forward_semilog_matched' if inverse else 'forward_route_emitted'
                if self.states.get(key) != expected:
                    raise AssertionError('The semilog call is not at its matched bit-route boundary.')
                self.states[key] = 'inverse_semilog_matched' if inverse else 'forward_semilog_matched'
                self.align_calls.append('inverse' if inverse else 'forward')

            def cleanup(builder, inputs, flags):
                key = self._key(builder, inputs)
                if (self.states.get(key) != 'inverse_prefixes_erased'
                        or self.inverse_flags.pop(key, None) != tuple(flags)):
                    raise AssertionError('Count cleanup was not already performed by its matched inverse.')
                self.states[key] = 'completed'
                self.cleanup_calls += 1
                return dict(method='already_erased_through_raw_bit_prefixes',
                            added_Toffoli_like=0, original_flags_allocated_zero=True)

            normalization_fused._fused_shift = shift
            thermometer_cleanup.erase_pair_count_thermometer = cleanup
            for module, _ in previous_align:
                module.semilog_align = align
            try:
                yield self
            finally:
                normalization_fused._fused_shift = previous_shift
                thermometer_cleanup.erase_pair_count_thermometer = previous_cleanup
                for module, function in previous_align:
                    module.semilog_align = function
        if (list(self.states.values()) != ['completed'] or self.inverse_flags
                or self.align_calls != ['forward', 'inverse'] or self.cleanup_calls != 1):
            raise AssertionError('The complete bit-normalization lifecycle did not close exactly once.')

    def metadata(self):
        if (list(self.states.values()) != ['completed']
                or self.decodings != 1 or self.consumptions != 1
                or len(self.inverse_routes) != 1 or self.cleanup_calls != 1
                or self.controls.prefix_captures != 1
                or self.controls.forward_product_erasures != 2
                or self.controls.captured_indicator_packs != 1
                or self.prepared or self.controls.forward_products
                or self.controls.pack_indicators or self.inverse_flags
                or [record['direction'] for record in self.controls.routes] != ['forward', 'inverse']):
            raise AssertionError('A count, routing, packing, or measurement owner remains incomplete.')
        return dict(status='STAGE94_BIT_NORMALIZATION_LIFECYCLE_COMPLETED',
                    source_component='retained_raw_prefix_binary_butterfly',
                    mathematical_route=certificate(21), forward=self.forward.metadata(),
                    inverse=self.inverse_routes[0], matched_semilog_calls=self.align_calls,
                    normalization_mean=61, restore_input_mean=61,
                    baseline_normalization_mean=76, baseline_restore_input_mean='143/2',
                    exact_mean_Toffoli_saving='51/2', expected_cost_saving_at_57_qubits='2907/2',
                    original_pack_residual_and_phase_debts_preserved=True,
                    original_initial_control_owners_preserved=True,
                    all_other_region_boundaries_unchanged=True,
                    threshold_repayments=self.late.threshold_repayments,
                    all_new_measurement_phases_repaid_locally=True,
                    full_generator_official_verification_required=True)
