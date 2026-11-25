# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""The existing event hooks plus the two new classical mask bypasses."""
from collections import Counter
from fractions import Fraction


class Events:
    def __init__(self):
        # configure() has already loaded the immutable v3 event provider.
        from event_ledger import Events as PriorEvents
        self.prior = PriorEvents()

    @property
    def rows(self):
        return self.prior.rows

    def install(self, pipeline):
        pipeline.assert_bindings()
        self.prior.install(pipeline.P)
        pipeline.MaskedPark.record_uniform_hmr_event = self.prior.record
        pipeline.Paired.record_uniform_hmr_event = self.prior.record

    def snapshot(self, static_T, scan_active=0):
        rows = list(self.rows)
        if scan_active:
            # Replaces the old one-T/4096 scan discount with eleven-T/4096.
            rows.append(('zero_mask_whole_point_scan', 11*scan_active, 12))
        counts = Counter(rows)
        assert not any(name.startswith('paired_converter_') or name.startswith('paired_rare27_')
                       for name,_,_ in rows)
        paired_count = counts[('paired_dual63_exclusive_overlap',27,0)]
        assert paired_count in (0,18)
        assert counts[('paired_dual63_rhs_zero',36,24)] == paired_count
        assert counts[('paired_dual63_all_masks_zero',27,36)] == paired_count
        discount = sum((Fraction(t,1 << bits) for _,t,bits in rows), Fraction())
        expected = Fraction(static_T)-discount
        return dict(status='EXACT_SOURCE_EXPECTATION_UNDER_UNIFORM_FRESH_MASKS',
                    static_T=static_T, discount_exact=str(discount),
                    expected_T_exact=str(expected), expected_T=float(expected),
                    measured_mean_T=None,
                    events=[dict(name=name, conditional_T=t, mask_bits=bits,
                       occurrences=count, total_discount_exact=str(Fraction(t*count,1 << bits)))
                       for (name,t,bits),count in sorted(counts.items())],
                    scope='Source expectation from actual helper calls and uniform fresh masks; not official sampling.')
