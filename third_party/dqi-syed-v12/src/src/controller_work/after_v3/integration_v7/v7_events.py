# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact v7 event ownership; no source expectation is an official mean.

The retained norm stack uses the existing scalar_inverse_six wrapper. No
extra manual event is added for its six fresh six-bit return masks. The old
three retained-child/outer-mask phase events must be absent from v7. The
matched prefix's saved mask is paid by CZ, with no extra event. Paired62
replaces only the18 main-branch RHS-zero discounts36 by35. The repaired
third chart removes one generic84/24 and one27/12 event, adds three4/6
events and one22/1 event; its prefix predicate debt is paid by CZ.
"""
from collections import Counter
from fractions import Fraction
import exact_occupancy as Occupancy


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
        assert pipeline.First3.A is pipeline.RetainedNorm.Arithmetic is pipeline.P.Arithmetic
        # The provider is imported before this alias-aware installation;
        # its Scalar module receives the same existing wrapper exactly once.
        self.prior.install(pipeline.P)
        pipeline.MaskedPark.record_uniform_hmr_event = self.prior.record
        pipeline.Paired.record_uniform_hmr_event = self.prior.record

    def snapshot(self, static_T, scan_active=0):
        rows = list(self.rows)
        if scan_active:
            # The selector correlates all4026 point masks. Its exact finite
            # occupancy expectation replaces the old independent-cell row.
            assert scan_active == 4026
        counts = Counter(rows)
        assert not any(name.startswith(('paired_converter_','paired_rare27_','paired_dual63_'))
                       for name,_,_ in rows)
        paired_count = counts[('paired_dual62_exclusive_overlap',27,0)]
        assert paired_count in (0,18)
        assert counts[('paired_dual62_rhs_zero',35,24)] == paired_count
        assert counts[('paired_dual62_all_masks_zero',27,36)] == paired_count
        wanted = Counter({
            ('direct_carry84_selected_target_parities',84,24):32,
            ('inverse_phase27_12_helpers',27,12):82 if paired_count else 66,
            ('last_return_child_norm_guard',15,6):1,
            ('scalar_inverse_six',4,6):7,
            ('tail_or_gauge_fresh_zero_phase',10,1):1,
            ('tail_or_gauge_fresh_zero_phase',22,1):21,
        })
        if paired_count:
            wanted.update({
                ('converter_inverse_phase27',27,12):18,
                ('converter_zero_predicate',10,1):16,
                ('paired_dual62_exclusive_overlap',27,0):18,
                ('paired_dual62_rhs_zero',35,24):18,
                ('paired_dual62_all_masks_zero',27,36):18,
                ('parked_scale_fresh_mask_guard',23,12):2,
            })
        if scan_active:
            assert paired_count == 18
        assert counts == wanted, (counts,wanted)
        discount = sum((Fraction(t,1 << bits) for _,t,bits in rows), Fraction())
        scan_expectation = None
        if scan_active:
            _,new_scan,_ = Occupancy.certificate_values()
            discount += Occupancy.NEW_SCAN_STATIC-new_scan
            scan_expectation = Occupancy.binding()
        expected = Fraction(static_T)-discount
        return dict(status='EXACT_SOURCE_EXPECTATION_UNDER_UNIFORM_FRESH_MASKS',
                    static_T=static_T,
                    discount_exact=Occupancy.encode(discount) if scan_active else str(discount),
                    expected_T_exact=Occupancy.encode(expected) if scan_active else str(expected),
                    expected_T=None if scan_active else float(expected),
                    exact_encoding='signed_hex_numerator_over_power_of_two' if scan_active else 'small_rational_string',
                    correlated_scan_expectation=scan_expectation,
                    old_independent_scan_discount_applied=False,
                    measured_mean_T=None,
                    events=[dict(name=name, conditional_T=t, mask_bits=bits,
                       occurrences=count, total_discount_exact=str(Fraction(t*count,1 << bits)))
                       for (name,t,bits),count in sorted(counts.items())],
                    scope='Actual helper-call expectation plus the certified full correlated adaptive scan; no official sampling or measured price.')
