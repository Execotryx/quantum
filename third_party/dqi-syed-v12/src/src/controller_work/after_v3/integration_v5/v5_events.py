# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact v5 event ownership; no source expectation is an official mean.

The retained norm stack uses the existing scalar_inverse_six wrapper. No
extra manual event is added for its three fresh six-bit masks. The old
three retained-child/outer-mask phase events must be absent from v5.
"""
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
        assert pipeline.First2.A is pipeline.RetainedNorm.Arithmetic is pipeline.P.Arithmetic
        # The provider is imported before this alias-aware installation;
        # its Scalar module receives the same existing wrapper exactly once.
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
        wanted = Counter({
            ('direct_carry84_selected_target_parities',84,24):33,
            ('inverse_phase27_12_helpers',27,12):83 if paired_count else 67,
            ('last_return_child_norm_guard',15,6):1,
            ('scalar_inverse_six',4,6):4,
            ('tail_or_gauge_fresh_zero_phase',10,1):1,
            ('tail_or_gauge_fresh_zero_phase',22,1):20,
        })
        if paired_count:
            wanted.update({
                ('converter_inverse_phase27',27,12):18,
                ('converter_zero_predicate',10,1):16,
                ('paired_dual63_exclusive_overlap',27,0):18,
                ('paired_dual63_rhs_zero',36,24):18,
                ('paired_dual63_all_masks_zero',27,36):18,
                ('parked_scale_fresh_mask_guard',23,12):2,
            })
        if scan_active:
            assert paired_count == 18
            wanted[('zero_mask_whole_point_scan',11*scan_active,12)] = 1
        assert counts == wanted, (counts,wanted)
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
