# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed T-only v7 candidate with mandatory completed component gates.

No input profile, terminal, gap set, polynomial alias or verifier salt is
provided to the compiler. The emission ceiling is889; the new whole tape
must independently establish its actual peak. This source is
not a whole-decoder correctness claim; all external gates are still required.
"""
from fractions import Fraction
import v7_paths as Paths
from v7_binding import verify_components, verify_preservation
import exact_occupancy as Occupancy

Runtime = P = None
Phase = Last = NewWindow = NewCore = NewOuter = NewTranspose = NewScan = MaskedPark = Paired = JointPhase = None
First3 = RetainedNorm = BaseExtractor = None
Adaptive = None


def configure():
    global Runtime, P, Phase, Last, NewWindow, NewCore, NewOuter, NewTranspose, NewScan, MaskedPark, Paired, JointPhase
    global First3, RetainedNorm, BaseExtractor, Adaptive
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
    import adaptive_gauge64 as Adaptive

    assert P.Arithmetic is Phase.Arithmetic is Last.A
    assert P.DirectArithmetic is Last.Original
    assert Last.Original.A is Last.A and Last.Original.Prior is Last.Nested
    assert P.Arithmetic.inverse_closed.__module__ == P.Arithmetic.__name__
    # Only this closed-inverse entry is replaced. Last.Original.restore
    # remains intact so its32 next-word calls cannot recurse through itself.
    P.Arithmetic.inverse_closed = Phase.inverse_closed
    P.Direct.Arithmetic = Last
    P.Extractor.Arithmetic = Last
    # Import the repaired third-chart adapter after binding its unchanged
    # generic arithmetic. All six matched inverses own the public constant1 carry.
    BaseExtractor = P.Extractor
    import first3_retained_norm_adapter as First3
    import inverse_retained_norm_deferred as RetainedNorm
    assert First3.Base is First3.Third.Base is BaseExtractor
    assert First3.Phase is First3.Third.Norm is RetainedNorm
    assert First3.Arithmetic is BaseExtractor.Arithmetic is Last
    assert First3.A is RetainedNorm.Arithmetic is P.Arithmetic
    assert First3.Tail is BaseExtractor.Tail
    P.Extractor = First3
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
    # The new scan reads this existing provider object dynamically. It does
    # not read a separate Adaptive.Finish alias.
    assert Adaptive.OriginalScan is NewScan
    assert Adaptive.OriginalMasks is P.Masks
    assert_bindings()
    verify_preservation(Runtime)
    return runtime_bindings()


def assert_bindings():
    assert P is not None
    assert P.Extractor is First3 and First3.Base is First3.Third.Base is BaseExtractor
    assert First3.Phase is First3.Third.Norm is RetainedNorm
    assert First3.Arithmetic is BaseExtractor.Arithmetic is Last
    assert First3.A is RetainedNorm.Arithmetic is P.Arithmetic
    assert First3.Tail is BaseExtractor.Tail is P.Tail
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
    assert Adaptive.OriginalScan is NewScan
    assert Adaptive.OriginalScan.Finish is P.Finish
    assert Adaptive.OriginalMasks is P.Masks
    assert P.Finish.__name__ == 'projective_finish_infinity3'


def runtime_bindings():
    assert_bindings()
    result = P.runtime_bindings()
    result.update(extractor_arithmetic=Last.__name__,
                  unchanged_next_word_return_provider=P.DirectArithmetic.__name__,
                  closed_K24_inverse_provider=Phase.__name__,
                  production_special_inverse_provider=RetainedNorm.__name__,
                  production_first_three_adapter=First3.__name__,
                  first_two_chart_reference_provider=BaseExtractor.__name__,
                  repaired_third_chart_provider=First3.Third.__name__,
                  generic_extraction_start_index=3,
                  special_chart_initial_carry=1,
                  special_chart_owned_clean_storage_bits=24,
                  special_chart_pending_prefix_classical_mask_bits=37,
                  special_prefix_inverse_count=6,
                  special_return_inverse_count=6,
                  special_prefix_inverse_T=191,
                  special_return_inverse_T=195,
                  third_chart_prefix_static_T=620,
                  third_chart_return_static_T=654,
                  third_raw_residue_zero_supported=True,
                  borrowed_initial_tail_flag_reset_without_free=True,
                  old_gauge_label_used_as_new_coverage=False,
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
                  scan_provider=Adaptive.__name__,
                  inherited_scan_provider=NewScan.__name__,
                  adaptive_gauge_provider=Adaptive.__name__,
                  adaptive_gauge_record_explicit=True,
                  adaptive_fixed_zero_points=69,
                  adaptive_virtual_pivot=70,
                  adaptive_candidates=64, adaptive_count_cap=7,
                  adaptive_selector_classical_bits=322,
                  adaptive_retained_pivot_classical_bits=12,
                  adaptive_additional_quantum_bits=0,
                  maximum_Q_source_model=889, whole_v7_width_measured=False,
                  width_engineering=False,
                  new_population_event=False, fixed_v7=True)
    return result


def finish_geometry_binding():
    assert_bindings()
    result = P.finish_geometry_binding()
    result.update(actual_scan_provider=Adaptive.__name__,
                  actual_finish_provider=Adaptive.OriginalScan.Finish.__name__,
                  adaptive_same_finish_module_object=Adaptive.OriginalScan.Finish is P.Finish,
                  scan_factor='The adaptive scan uses g(a)/(a*U(a)*M(a)) on its normalized classical masks; M is this exact shared Finish polynomial.',
                  adaptive_gauge_polynomial='x times the product of x+r for public r=1,...,69',
                  public_freed_pivot_field_value=70)
    return result


def source_ledger(scan_static_T=44286):
    assert_bindings()
    result = P.source_ledger(scan_static_T)
    parts = dict(result['components_static_T'])
    parts['extractor_rolling_gauge_padded_seed'] -= 12+8+243+3+55
    parts['preimage_gauge_parking_shared_windows'] -= 56+88+24+176+22+144+36+18+38
    result.update(status='SOURCE_MODEL_REQUIRES_JOINED_NATIVE_AND_OFFICIAL_GATES',
                  components_static_T=parts, total_static_T=sum(parts.values()),
                  accepted_v3_static_T=384915,
                  frozen_v4_static_T=384349,
                  frozen_initial_v5_static_T=384068,
                  frozen_v5b_static_T=384047,
                  frozen_v6_static_T=383992,
                  incremental_static_delta_from_v6=11,
                  adaptive_occupancy=Occupancy.binding(),
                  incremental_static_delta_from_v4=-346,
                  incremental_expected_T_saving_from_v4_exact=Occupancy.encode(
                      Fraction(3090097999,8388608)+Occupancy.certificate_values()[2]),
                  incremental_static_delta_from_v5b=-44,
                  incremental_expected_T_saving_from_v5b_exact=Occupancy.encode(
                      Fraction(277582827,4194304)+Occupancy.certificate_values()[2]),
                  incremental_static_delta_from_initial_v5=-65,
                  incremental_expected_T_saving_from_initial_v5_exact=Occupancy.encode(
                      Fraction(731326413,8388608)+Occupancy.certificate_values()[2]),
                  incremental_expected_T_is_official_measurement=False,
                  historical_v3_nested_norm_key_stages=72,
                  historical_v3_nested_norm_total_stages=122,
                  nested_norm_key_calls=64,
                  nested_norm_total_calls=114,
                  nested_norm_counts_scope='Source-derived stage count, not instrumented literal calls; the last return retains its child explicitly.',
                  full_scan_static_delta_T=sum(parts.values())-scan_static_T+44286-384915,
                  changes_static_T=dict(quotient_phase84=-12, last_return=-8,
                       borrowed_forward=-56, retained_forward_predicate=-88,
                       parked_scale_phase=-24, retained_transpose_predicates=-176,
                       transpose_predicate_handoff=-22, rare_paired_branch=-144,
                       joint_norm_phase=-36,
                       first_two_retained_norm_stack=-243,
                       first_two_matched_prefix_debt=-3,
                       third_zero_repaired_public_chart=-55,
                       cubic_inner_trace_phase=-18,
                       transpose14=-38,
                       zero_classical_mask_scan=0, adaptive64_scan_static=11),
                  input_dependent_compiler_parameters=[], admitted_domain_change=False)
    return result


def expected_mean(static_T, scan_active):
    """Exact full-scan ledger; no independent-cell discount after selection."""
    old_non_scan_discount = Fraction(981320399, 1048576)
    # Start with the frozen v5b discount. The third chart removes one27/4096
    # inverse-phase event and one84/2^24 target-mask event, then adds three
    # existing4/64 scalar events and one22/2 return zero-predicate event.
    # The prefix's saved predicate mask is paid by CZ, not a second event.
    discount = (old_non_scan_discount - Fraction(27,4096) + Fraction(19,64)
                + Fraction(46,4096)
                - 144 + Fraction(90,1 << 24) + Fraction(486,1 << 36)
                - Fraction(27,4096) - Fraction(84,1 << 24)
                + Fraction(12,64) + 11)
    if scan_active == 0:
        return Fraction(static_T)-discount
    assert scan_active == 4026, 'Only the certified full adaptive scan has an exact mean here'
    _,new_scan,_ = Occupancy.certificate_values()
    return Fraction(static_T)-discount-Occupancy.NEW_SCAN_STATIC+new_scan


def emit_key_prefix(*args, **kwargs):
    assert_bindings()
    record = P.emit_key_prefix(*args, **kwargs)
    assert isinstance(record['extraction'], First3.ProductionRecord)
    assert record['extraction'].declared_initial_carry == 1
    assert record['extraction'].closed_inverse_calls == 0
    extraction = record['extraction']
    assert len(extraction.first_inverses) == len(extraction.third.inverses) == 3
    assert not extraction.third.closed and extraction.third.prefix_static_T == 620
    assert extraction.third.zero_mask is not None and len(extraction.third.zero_mask) == 1
    assert all(isinstance(item,RetainedNorm.PrefixRecord) and not item.closed
               and item.prefix_static_T == 191 and item.child_mask_bits == 6
               for item in (*extraction.first_inverses, *extraction.third.inverses))
    return record


def emit_key_closing(*args, **kwargs):
    assert_bindings()
    assert len(args) >= 2
    record = args[1]
    assert isinstance(record['extraction'], First3.ProductionRecord)
    result = P.emit_key_closing(*args, **kwargs)
    extraction = record['extraction']
    assert record['closed'] and extraction.closed and extraction.clean_carry_seam_reached
    assert extraction.closed_inverse_calls == len(extraction.borrow_receipts) == 6
    assert all(row['all_owned_storage_bits_reset'] and row['retained_storage_bits'] == 24
               and row['deferred_prefix_mask_paid'] is True
               for row in extraction.borrow_receipts)
    assert all(item.closed for item in (*extraction.first_inverses, *extraction.third.inverses))
    assert extraction.third.closed and extraction.third.zero_mask is None
    assert extraction.third_receipt['prefix_zero_mask_paid'] is True
    assert extraction.third_receipt['return_zero_flag_retired'] is True
    assert extraction.third_receipt['closed_inverse_calls'] == 3
    assert extraction.third_receipt['owned_clean_bank_bits'] == 24
    return result


def emit(builder, syndromes, masks, *, j_min=15, scan_positions=4095,
         stage=lambda _: None):
    assert_bindings()
    assert j_min == 15 and len(syndromes) == 70 and len(masks) == 4095
    assert scan_positions == 4095, 'V7 currently exposes only the certified full adaptive scan'
    geometry = finish_geometry_binding()
    gauge_record = Adaptive.open_gauge(builder, list(syndromes), masks, stage=stage)
    assert gauge_record.kind == 'gauge' and gauge_record.compensated
    assert not gauge_record.closed and gauge_record.scans == 0
    assert gauge_record.entry_qubits == builder.num_allocated_qubits == 840
    stage('adaptive64_syndrome_weight_gauge')
    key = emit_key_prefix(builder, syndromes, j_min=15, stage=stage)
    N, D = key['N'], key['D']
    outer = NewOuter.emit_prefix(builder, D, N, gauge_flag=key['gauge'].flag,
                                gauge_other=key['carry'][12:], fused=False, stage=stage)
    finish = P.Finish.emit_prefix(builder, D, N)
    stage('projective_finish_prefix')
    scan = Adaptive.emit_scan(builder, D, N, masks, gauge_record,
                              positions=scan_positions, stage=stage)
    assert scan['point_tests'] == 4026 and scan['full_cycle']
    assert gauge_record.scans == 1 and not gauge_record.closed
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
    gauge_closure = Adaptive.close_gauge(builder, masks, gauge_record, stage=stage)
    assert gauge_record.closed and gauge_record.scans == 1
    assert gauge_closure['all_owned_classical_bits_retired_zero']
    stage('all_original_inputs_restored')
    return dict(candidate='post_v3_fixed_v7_T_only', j_min=15, scan=scan,
                fixed_schedule=True, compiler_profile=False,
                source_ledger=source_ledger(scan['static_T']),
                finish_geometry=geometry, runtime_bindings=runtime_bindings(),
                adaptive_gauge=dict(selector_ledger=gauge_record.selector_ledger,
                    compensation_instructions=gauge_record.compensation_instructions,
                    normalization_instructions_per_direction=gauge_record.normalization_instructions,
                    exact_occupancy=Occupancy.binding(), record_consumed_once=True,
                    all_owned_classical_bits_retired_zero=True,
                    additional_quantum_bits_source_model=0,
                    whole_width_measured=False),
                admitted_domain_change=False,
                status='BUILT_CANDIDATE_REQUIRES_EXTERNAL_VERIFICATION')
