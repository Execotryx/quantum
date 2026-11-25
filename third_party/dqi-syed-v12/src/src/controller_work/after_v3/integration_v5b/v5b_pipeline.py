# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed T-only v5b candidate with mandatory completed component gates.

No input profile, terminal, gap set, polynomial alias or verifier salt is
provided to the compiler. The physical maximum remains889. This source is
not a whole-decoder correctness claim; all external gates are still required.
"""
from fractions import Fraction
import v5b_paths as Paths
from v5b_binding import verify_components, verify_preservation

Runtime = P = None
Phase = Last = NewWindow = NewCore = NewOuter = NewTranspose = NewScan = MaskedPark = Paired = JointPhase = None
First2 = RetainedNorm = BaseExtractor = None


def configure():
    global Runtime, P, Phase, Last, NewWindow, NewCore, NewOuter, NewTranspose, NewScan, MaskedPark, Paired, JointPhase
    global First2, RetainedNorm, BaseExtractor
    if P is not None:
        assert_bindings()
        return runtime_bindings()
    verify_components()
    import accepted_runtime as Accepted
    Runtime = Accepted.load()
    P = Runtime.pipeline
    Paths.enable_new_sources()
    import quotient_phase84_mask_guard as Phase
    import last_return_retained_norm as Last
    import transpose14_core as NewCore
    import transpose14_window as NewWindow
    import transpose_handoff_outer as NewOuter
    import masked_parked_scale_phase as MaskedPark
    import window_transpose_handoff as NewTranspose
    import paired_phase62 as Paired
    import quotient_phase62 as JointPhase
    import zero_mask_scan as NewScan

    assert P.Arithmetic is Phase.Arithmetic is Last.A
    assert P.DirectArithmetic is Last.Original
    assert Last.Original.A is Last.A and Last.Original.Prior is Last.Nested
    assert P.Arithmetic.inverse_closed.__module__ == P.Arithmetic.__name__
    # Only this closed-inverse entry is replaced. Last.Original.restore
    # remains intact so its32 next-word calls cannot recurse through itself.
    P.Arithmetic.inverse_closed = Phase.inverse_closed
    P.Direct.Arithmetic = Last
    P.Extractor.Arithmetic = Last
    # Import the matched production adapter after binding its unchanged
    # generic arithmetic. Both special seams own the public constant1 carry.
    BaseExtractor = P.Extractor
    import first2_retained_norm_deferred_adapter as First2
    import inverse_retained_norm_deferred as RetainedNorm
    assert First2.Base is BaseExtractor
    assert First2.Arithmetic is BaseExtractor.Arithmetic is Last
    assert First2.A is RetainedNorm.Arithmetic is P.Arithmetic
    assert First2.Tail is BaseExtractor.Tail
    P.Extractor = First2
    P.Core = NewCore
    P.Window = NewWindow
    P.Outer = NewOuter
    NewOuter.core = NewCore
    NewWindow.transpose_tensor = NewTranspose
    NewCore.paired_scale = NewOuter.paired_scale = Paired
    assert P.Seam is not None
    P.Seam.Outer = NewOuter
    P.Scan = NewScan
    NewScan.Finish = P.Finish
    assert_bindings()
    verify_preservation(Runtime)
    return runtime_bindings()


def assert_bindings():
    assert P is not None
    assert P.Extractor is First2 and First2.Base is BaseExtractor
    assert First2.Arithmetic is BaseExtractor.Arithmetic is Last
    assert First2.A is RetainedNorm.Arithmetic is P.Arithmetic
    assert First2.Tail is BaseExtractor.Tail is P.Tail
    assert P.Direct.Arithmetic is P.Extractor.Arithmetic is Last
    assert Last.Original is P.DirectArithmetic
    assert Last.Original.restore_with_shared_norm is not Last.restore_with_shared_norm
    assert Last.Original.A is Last.A is P.Arithmetic is Phase.Arithmetic
    assert P.Arithmetic.inverse_closed is Phase.inverse_closed
    assert Last.Original.Prior is Last.Nested
    assert P.Window is NewWindow and NewWindow.C is NewCore
    assert NewWindow.WINDOWS == {17,14} and NewWindow.TRANSPOSE_WINDOWS == {17,14}
    assert P.Core is NewCore and P.Outer is NewOuter and NewOuter.core is NewCore
    assert NewWindow.transpose_tensor is NewTranspose
    assert NewCore.paired_scale is NewOuter.paired_scale is Paired
    assert Paired.phase_inverse_trace_twelve is JointPhase.phase_inverse_trace_twelve
    assert JointPhase.STATIC_T == 62 and JointPhase.HELPERS == 22
    assert NewWindow.tensor.__name__ == 'window_forward_retained_flag'
    assert P.Seam.Outer is NewOuter
    assert P.Scan is NewScan and NewScan.Finish is P.Finish
    assert P.Finish.__name__ == 'projective_finish_infinity3'


def runtime_bindings():
    assert_bindings()
    result = P.runtime_bindings()
    result.update(extractor_arithmetic=Last.__name__,
                  unchanged_next_word_return_provider=P.DirectArithmetic.__name__,
                  closed_K24_inverse_provider=Phase.__name__,
                  production_first_two_inverse_provider=RetainedNorm.__name__,
                  production_first_two_adapter=First2.__name__,
                  first_two_chart_reference_provider=BaseExtractor.__name__,
                  matched_first_two_prefix_provider=First2.__name__,
                  first_two_initial_carry=1,
                  first_two_owned_clean_storage_bits=24,
                  first_two_pending_prefix_classical_mask_bits=18,
                  first_two_prefix_inverse_T=191,
                  first_two_return_inverse_T=195,
                  arbitrary_initial_carry_extension=False,
                  last_return_retained_child=True,
                  parked_scale_phase_provider=MaskedPark.__name__,
                  paired_quotient_phase_provider=Paired.__name__,
                  joint_norm_phase_provider=JointPhase.__name__,
                  joint_norm_phase_helpers=22,
                  prior_joint_norm_phase_helpers=18,
                  future_width_merge_requires_new_lifetime_check=True,
                  transpose_predicate_handoff=True,
                  transpose_windows=sorted(NewWindow.TRANSPOSE_WINDOWS),
                  scan_provider=NewScan.__name__,
                  maximum_Q=889, width_engineering=False,
                  new_population_event=False, fixed_v5b=True)
    return result


def finish_geometry_binding():
    assert_bindings()
    return P.finish_geometry_binding()


def source_ledger(scan_static_T=44275):
    assert_bindings()
    result = P.source_ledger(scan_static_T)
    parts = dict(result['components_static_T'])
    parts['extractor_rolling_gauge_padded_seed'] -= 12+8+243+3
    parts['preimage_gauge_parking_shared_windows'] -= 56+88+24+176+22+144+36+18+38
    result.update(status='SOURCE_MODEL_REQUIRES_JOINED_NATIVE_AND_OFFICIAL_GATES',
                  components_static_T=parts, total_static_T=sum(parts.values()),
                  accepted_v3_static_T=384915,
                  frozen_v4_static_T=384349,
                  frozen_initial_v5_static_T=384068,
                  incremental_static_delta_from_v4=-302,
                  incremental_expected_T_saving_from_v4_exact='2534932345/8388608',
                  incremental_static_delta_from_initial_v5=-21,
                  incremental_expected_T_saving_from_initial_v5_exact='176160759/8388608',
                  incremental_expected_T_is_official_measurement=False,
                  historical_v3_nested_norm_key_stages=72,
                  historical_v3_nested_norm_total_stages=122,
                  nested_norm_key_calls=66,
                  nested_norm_total_calls=116,
                  nested_norm_counts_scope='Source-derived stage count, not instrumented literal calls; the last return retains its child explicitly.',
                  full_scan_static_delta_T=sum(parts.values())-scan_static_T+44275-384915,
                  changes_static_T=dict(quotient_phase84=-12, last_return=-8,
                       borrowed_forward=-56, retained_forward_predicate=-88,
                       parked_scale_phase=-24, retained_transpose_predicates=-176,
                       transpose_predicate_handoff=-22, rare_paired_branch=-144,
                       joint_norm_phase=-36,
                       first_two_retained_norm_stack=-243,
                       first_two_matched_prefix_debt=-3,
                       cubic_inner_trace_phase=-18,
                       transpose14=-38,
                       zero_classical_mask_scan=0),
                  input_dependent_compiler_parameters=[], admitted_domain_change=False)
    return result


def expected_mean(static_T, scan_active):
    """Independent exact ledger, used to audit the observed helper events."""
    old_non_scan_discount = Fraction(981320399, 1048576)
    # Remove the three old closed-inverse mask-tuple phase events and add
    # three existing4/64 scalar events. The matched prefix removes3 fixedT,
    # not another mask event. Transpose14 has no mask discount. The paired62
    # main branch reduces the18 RHS-zero discounts by oneT each.
    discount = (old_non_scan_discount - Fraction(27,4096) + Fraction(19,64)
                + Fraction(46,4096) + Fraction(11*scan_active,4096)
                - 144 + Fraction(90,1 << 24) + Fraction(486,1 << 36))
    return Fraction(static_T)-discount


def emit_key_prefix(*args, **kwargs):
    assert_bindings()
    record = P.emit_key_prefix(*args, **kwargs)
    assert isinstance(record['extraction'], First2.ProductionRecord)
    assert record['extraction'].declared_initial_carry == 1
    assert record['extraction'].closed_inverse_calls == 0
    assert len(record['extraction'].first_inverses) == 3
    assert all(isinstance(item,RetainedNorm.PrefixRecord) and not item.closed
               and item.prefix_static_T == 191 and item.child_mask_bits == 6
               for item in record['extraction'].first_inverses)
    return record


def emit_key_closing(*args, **kwargs):
    assert_bindings()
    assert len(args) >= 2
    record = args[1]
    assert isinstance(record['extraction'], First2.ProductionRecord)
    result = P.emit_key_closing(*args, **kwargs)
    extraction = record['extraction']
    assert record['closed'] and extraction.closed and extraction.clean_carry_seam_reached
    assert extraction.closed_inverse_calls == len(extraction.borrow_receipts) == 3
    assert all(row['all_owned_storage_bits_reset'] and row['retained_storage_bits'] == 24
               and row['deferred_prefix_mask_paid'] is True
               for row in extraction.borrow_receipts)
    assert all(item.closed for item in extraction.first_inverses)
    return result


def emit(builder, syndromes, masks, *, j_min=15, scan_positions=4095,
         stage=lambda _: None):
    assert_bindings()
    assert j_min == 15 and len(syndromes) == 70 and len(masks) == 4095
    assert 0 < scan_positions <= 4095
    geometry = finish_geometry_binding()
    plan = P.Public.syndrome_gauge_plan()
    P.Masks.open_gauge(builder, list(syndromes), masks, plan)
    stage('original_syndrome_weight_gauge')
    key = emit_key_prefix(builder, syndromes, j_min=15, stage=stage)
    N, D = key['N'], key['D']
    outer = NewOuter.emit_prefix(builder, D, N, gauge_flag=key['gauge'].flag,
                                gauge_other=key['carry'][12:], fused=False, stage=stage)
    finish = P.Finish.emit_prefix(builder, D, N)
    stage('projective_finish_prefix')
    scan = NewScan.emit(builder, D, N, masks, positions=scan_positions, stage=stage)
    assert outer.source_builder_id == id(builder)
    reciprocal = P.Finish.emit_closing_keep_inverse(builder, D, N, finish)
    stage('shared_seam_finish_return_live_inverse')
    P.Seam.outer_closing_with_inverse(outer.lender, D, N, outer,
                                     reciprocal, stage=stage)
    carrier = outer.core.gauge_carrier
    carrier.clean_boundary()
    assert outer.core.gauge_h_requeries == 1
    assert not outer.core.local_flags
    assert len(outer.core.local_created) == len(outer.core.local_retired) == 32
    # These are the actual new lifecycle counts, not aliases for old counts.
    assert (carrier.parks, carrier.unparks) == (14,14)
    assert carrier.parked_phase_payments == 2
    emit_key_closing(builder, key, stage=stage)
    P.Masks.close_gauge(builder, masks, plan)
    stage('all_original_inputs_restored')
    return dict(candidate='post_v3_fixed_v5b_T_only', j_min=15, scan=scan,
                fixed_schedule=True, compiler_profile=False,
                source_ledger=source_ledger(scan['static_T']),
                finish_geometry=geometry, runtime_bindings=runtime_bindings(),
                admitted_domain_change=False,
                status='BUILT_CANDIDATE_REQUIRES_EXTERNAL_VERIFICATION')
