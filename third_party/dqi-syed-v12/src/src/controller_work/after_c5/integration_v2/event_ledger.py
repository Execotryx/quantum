# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Record exact fresh-mask expectations without changing emitted operations.

This records conditional event sizes already proved for the local primitives.
It is a source expectation, not a measured input-distribution or official mean.
"""
from collections import Counter
from fractions import Fraction
import functools
import sys


class Events:
    def __init__(self):
        self.rows = []
        self.installed = False

    def record(self, name, conditional_t, bits):
        assert isinstance(conditional_t, int) and isinstance(bits, int)
        assert conditional_t >= 0 and bits >= 0
        self.rows.append((name, conditional_t, bits))

    def _replace_aliases(self, original, replacement):
        for module in tuple(sys.modules.values()):
            if module is None:
                continue
            for name, value in tuple(vars(module).items()):
                if value is original:
                    setattr(module, name, replacement)

    def install(self, pipeline):
        assert not self.installed
        self.installed = True
        import gf24_arithmetic
        import phase_inverse12
        import narrow_field130
        import scalar_inverse_phase
        import zero_erasure
        import inverse_phase27
        import gauge_park_paired
        import rolling_tail_conditional
        for module in (gf24_arithmetic, pipeline.Arithmetic,
                       phase_inverse12, narrow_field130):
            module.record_uniform_hmr_event = self.record
        original = scalar_inverse_phase.phase_inverse_six
        @functools.wraps(original)
        def six(*args, _original=original, **kwargs):
            self.record('scalar_inverse_six', 4, 6)
            return _original(*args, **kwargs)
        self._replace_aliases(original, six)
        original = zero_erasure.phase_zero
        @functools.wraps(original)
        def zero(builder, word, mask, clean=None, quantum_control=None, _original=original):
            self.record('converter_zero_predicate',
                        len(word)-2+int(quantum_control is not None), 1)
            return _original(builder, word, mask, clean, quantum_control)
        self._replace_aliases(original, zero)
        original = gauge_park_paired.quotient_phases
        @functools.wraps(original)
        def paired(*args, _original=original, **kwargs):
            # Static100 counts both exclusive65/35 branches. Removing the
            # impossible simultaneous35 is a constant discount, not a mask
            # that was measured to be zero. The residual discount is30/2^24.
            self.record('paired_converter_exclusive_branch_overlap', 35, 0)
            self.record('paired_converter_quotient_zero_mask', 30, 24)
            return _original(*args, **kwargs)
        self._replace_aliases(original, paired)
        original = inverse_phase27.phase_inverse_twelve_polynomial
        @functools.wraps(original)
        def phase27(*args, _original=original, **kwargs):
            self.record('converter_inverse_phase27', 27, 12)
            return _original(*args, **kwargs)
        self._replace_aliases(original, phase27)
        original = rolling_tail_conditional.zero_phase
        @functools.wraps(original)
        def tail_zero(builder, source, mask, _original=original):
            self.record('tail_or_gauge_fresh_zero_phase', len(source)-2, 1)
            return _original(builder, source, mask)
        self._replace_aliases(original, tail_zero)

    def snapshot(self, static_T, scan_active=0):
        rows = list(self.rows)
        if scan_active:
            rows.append(('uniform_original_mask_scan', scan_active, 12))
        counts = Counter(rows)
        discount = sum((Fraction(t, 1 << bits) for _, t, bits in rows), Fraction())
        expected = Fraction(static_T)-discount
        return dict(status='EXACT_SOURCE_EXPECTATION_UNDER_UNIFORM_FRESH_MASKS',
                    static_T=static_T, discount_exact=str(discount),
                    expected_T_exact=str(expected), expected_T=float(expected),
                    measured_mean_T=None,
                    events=[dict(name=name, conditional_T=t, mask_bits=bits,
                                 occurrences=count,
                                 total_discount_exact=str(Fraction(t*count, 1 << bits)))
                            for (name, t, bits), count in sorted(counts.items())],
                    scope='HMR masks plus independent uniform original phase weights; no new official sample or failure factor')
