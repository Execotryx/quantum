# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Separate v3 deferred-flag pipeline; C5, v1 and v2 sources stay intact.

Options choose public implementation variants only. The emitted circuit has
public j_min15 and receives no terminal, profile, contacts, aliases, or salt.
The default composes individually passed components, not a passed decoder.
Native integration, reproducibility, domain transfer, and four official runs
remain separate external gates for every serialized candidate.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import integration_paths  # noqa: F401
import kickmix as km
import public_geometry as Public
import fused_crt_synthesis as Synthesis
import projective_finish as BaselineFinish
import additive_fft_phase_scan as Scan
import mask_gauge_blocked as Masks
import rolling_tail_deferred as Tail
import scalar_seed_padded as Seed
import direct_carry_extractor as Direct
import direct_carry_arithmetic as DirectArithmetic
import gauge_park_outer as Outer
import local_flag_window as Window
import local_flag_core as Core
import window_tensor_shared as SharedTensor
import window_transpose_shared as SharedTranspose
import gf24_arithmetic as BaselineArithmetic


@dataclass(frozen=True)
class Options:
    first_two_charts: bool = False
    nested_norm: bool = False
    finish_seam: bool = False
    infinity3_finish: bool = False


_options = None
Extractor = Arithmetic = Seam = None
Finish = BaselineFinish


def configure(options=None):
    """Bind one public configuration per process, before any emission."""
    global _options, Extractor, Arithmetic, Seam, Finish
    options = Options() if options is None else options
    assert isinstance(options, Options)
    if _options is not None:
        assert options == _options, 'Use a fresh process for another configuration'
        return runtime_bindings()
    Arithmetic = BaselineArithmetic
    if options.nested_norm:
        import gf24_nested_norm
        import nested_norm_inverse
        Arithmetic = gf24_nested_norm
        DirectArithmetic.Prior = nested_norm_inverse
    DirectArithmetic.A = Arithmetic
    Direct.A = Arithmetic
    Direct.Arithmetic = DirectArithmetic
    Direct.Tail = Tail
    Extractor = Direct
    if options.first_two_charts:
        import direct_carry_first2
        Extractor = direct_carry_first2
        Extractor.A = Arithmetic
        Extractor.Arithmetic = DirectArithmetic
        Extractor.Tail = Tail
    Synthesis.Arithmetic = Arithmetic
    Outer.core = Core
    assert Window.C is Core and Outer.core is Core
    if options.infinity3_finish:
        import projective_finish_infinity3
        Finish = projective_finish_infinity3
    Finish.Arithmetic = Arithmetic
    # This is the scan's public 1/M mask factor, not merely a source label.
    Scan.Finish = Finish
    Window.tensor = SharedTensor
    Window.transpose_tensor = SharedTranspose
    if options.finish_seam:
        import finish_outer_seam
        Seam = finish_outer_seam
        Seam.Outer = Outer
        Seam.Finish = Finish
    _options = options
    return runtime_bindings()


def runtime_bindings():
    assert _options is not None
    return dict(options=asdict(_options), extractor=Extractor.__name__,
                extractor_arithmetic=DirectArithmetic.__name__,
                gf24_arithmetic=Arithmetic.__name__,
                norm_inverse_provider=DirectArithmetic.Prior.__name__,
                rolling_tail=Tail.__name__, scalar_seed=Seed.__name__,
                outer=Outer.__name__, core=Outer.core.__name__, window=Window.__name__,
                deferred_tail_masks=True, deferred_local_masks=True,
                forward_tensor=Window.tensor.__name__,
                transpose_tensor=Window.transpose_tensor.__name__,
                projective_finish=Finish.__name__,
                scan_finish=Scan.Finish.__name__,
                finite_modulus_degree=32 if _options.infinity3_finish else 34,
                finite_quadratic_blocks=16 if _options.infinity3_finish else 17,
                infinity_jet_words=3 if _options.infinity3_finish else 1,
                finish_seam=None if Seam is None else Seam.__name__)


def finish_geometry_binding():
    """Bind the actual public polynomial used by both finish and phase scan."""
    assert _options is not None and Scan.Finish is Finish
    coefficients = list(Finish.geometry()['M'])
    degree = 32 if _options.infinity3_finish else 34
    assert len(coefficients) == degree+1 and coefficients[-1] == 1
    assert all(isinstance(x, int) and 0 <= x < 4096 for x in coefficients)
    payload = json.dumps(coefficients, separators=(',', ':')).encode()
    return dict(finish_module=Finish.__name__, scan_finish_module=Scan.Finish.__name__,
                same_module_object=True, modulus_degree=degree,
                modulus_coefficients_ascending=coefficients,
                modulus_coefficients_sha256=hashlib.sha256(payload).hexdigest(),
                finite_node_indices=list(range(35, 51 if _options.infinity3_finish else 52)),
                infinity_jet_words=3 if _options.infinity3_finish else 1,
                scan_factor='The inherited scan uses this exact M in its public 1/(a*U(a)*M(a)) mask scaling.',
                additional_failure_event=False)


def source_ledger(scan_static_T=44275):
    assert _options is not None
    first = 642 if _options.first_two_charts else 0
    key_norm_calls = 72 if _options.first_two_charts else 70
    key_nested = 3*key_norm_calls if _options.nested_norm else 0
    synthesis_nested = 3*34 if _options.nested_norm else 0
    finish_norm_calls = 16 if _options.infinity3_finish else 17
    finish_nested = 3*finish_norm_calls if _options.nested_norm else 0
    parts = {
        'extractor_rolling_gauge_padded_seed': 153449-first-key_nested-418,
        'synthesis': 65178-synthesis_nested,
        'preimage_gauge_parking_shared_windows': 115656+571-280-320,
        'projective_finish': (7904 if _options.infinity3_finish else 8030)-finish_nested,
        'finish_outer_seam_delta': -92 if _options.finish_seam else 0,
        'scan': scan_static_T,
    }
    return dict(status='SOURCE_MODEL_UNTIL_JOINED_NATIVE_CHECK',
                components_static_T=parts, total_static_T=sum(parts.values()),
                peak_Q_model=889, original_C5_static_T=390556,
                full_scan_static_delta_T=sum(parts.values())-scan_static_T+44275-390556,
                nested_norm_key_calls=key_norm_calls,
                nested_norm_finish_calls=finish_norm_calls,
                nested_norm_total_calls=key_norm_calls+34+finish_norm_calls,
                permanent_deferred_flag_static_delta_T=-738,
                permanent_deferred_flag_uniform_mean_delta_T=-369,
                options=asdict(_options),
                input_dependent_compiler_parameters=[],
                admitted_domain_change=False,
                domain_transfer_status='Algebraic component equivalence; joined checks still required')


def emit_key_prefix(builder, syndromes, *, j_min=15, stage=lambda _: None):
    assert _options is not None and j_min == 15 and len(syndromes) == 70
    Public.emit(builder, syndromes)
    heads = [km.array([*syndromes[2*i], *syndromes[2*i+1]]) for i in range(35)]
    carry = builder.alloc_qubits(24)
    builder.x(carry[0])
    extraction = Extractor.emit_prefix(builder, heads, carry, j_min=15, stage=stage)
    extraction.tail.release_spare()
    gauge = Tail.gauge_prefix(builder, carry)
    seed = Seed.emit_prefix(builder, carry[:12], heads[34])
    extraction.tail.seed_prefix(carry[:12], heads[34][12:])
    N, D = [carry[:12]], [heads[34][:12], heads[34][12:]]
    synthesis = []
    for i in range(33, -1, -1):
        P = [heads[i][:12], heads[i][12:]]
        rec = Synthesis.emit_prefix(builder, N, D, P, i, guarded=False)
        synthesis.append((N, D, P, rec))
        N, D = D, N+P
        stage(dict(stage='synthesis_prefix', node=i, degree=len(D)-1))
    assert len(N) == 35 and len(D) == 36
    return dict(builder_id=id(builder), syndromes=syndromes, heads=heads,
                carry=carry, extraction=extraction, gauge=gauge, seed=seed,
                synthesis=synthesis, N=N, D=D, options=_options, closed=False)


def emit_key_closing(builder, record, *, stage=lambda _: None):
    assert record['builder_id'] == id(builder) and not record['closed']
    assert record['options'] == _options
    heads, carry = record['heads'], record['carry']
    extraction, gauge, seed = record['extraction'], record['gauge'], record['seed']
    for old_N, old_D, old_P, rec in reversed(record['synthesis']):
        Synthesis.emit_closing(builder, old_N, old_D, old_P, rec)
        stage(dict(stage='synthesis_return', node=rec.node_index))
    # The parity remains erased across all24-helper scalar-return arithmetic.
    returning = Seed.close_padded(builder, carry[:12], heads[34], seed)
    extraction.tail.seed_return(carry[:12], heads[34][12:])
    Seed.finish_after_swap(builder, carry[:12], heads[34],
                           extraction.tail.current, returning)
    assert seed.closed and returning.closed
    Tail.gauge_return(builder, carry, gauge)
    extraction.tail.resume_return()
    Extractor.emit_closing(builder, heads, carry, extraction, stage=stage)
    builder.x(carry[0])
    builder.free(carry)
    Public.emit(builder, record['syndromes'], True)
    record['closed'] = True


def emit(builder, syndromes, masks, *, j_min=15, scan_positions=4095,
         stage=lambda _: None):
    assert _options is not None and j_min == 15
    assert len(syndromes) == 70 and len(masks) == 4095
    assert 0 < scan_positions <= 4095
    geometry_binding = finish_geometry_binding()
    plan = Public.syndrome_gauge_plan()
    Masks.open_gauge(builder, list(syndromes), masks, plan)
    stage('original_syndrome_weight_gauge')
    key = emit_key_prefix(builder, syndromes, j_min=15, stage=stage)
    N, D = key['N'], key['D']
    outer = Outer.emit_prefix(builder, D, N, gauge_flag=key['gauge'].flag,
                              gauge_other=key['carry'][12:], fused=False, stage=stage)
    finish = Finish.emit_prefix(builder, D, N)
    stage('projective_finish_prefix')
    scan = Scan.emit(builder, D, N, masks, positions=scan_positions, stage=stage)
    if Seam is None:
        Finish.emit_closing(builder, D, N, finish)
        Outer.emit_closing(builder, D, N, (), outer, stage=stage)
    else:
        assert outer.source_builder_id == id(builder)
        if _options.infinity3_finish:
            # The old seam helper hardcodes seventeen finite blocks. The new
            # finish closes sixteen and its complete three-word infinity jet.
            reciprocal = Finish.emit_closing_keep_inverse(builder, D, N, finish)
        else:
            reciprocal = Seam.finish_closing_keep_inverse(builder, D, N, finish)
        stage('shared_seam_finish_return_live_inverse')
        # Context ownership belongs to the existing GaugeLender, not raw builder.
        Seam.outer_closing_with_inverse(outer.lender, D, N, outer,
                                        reciprocal, stage=stage)
        outer.core.gauge_carrier.clean_boundary()
        assert outer.core.gauge_h_requeries == 1
        assert not outer.core.local_flags
        assert len(outer.core.local_created) == len(outer.core.local_retired) == 32
        assert (outer.core.gauge_carrier.parks,
                outer.core.gauge_carrier.unparks) == (16, 16)
    emit_key_closing(builder, key, stage=stage)
    Masks.close_gauge(builder, masks, plan)
    stage('all_original_inputs_restored')
    return dict(candidate='post_C5_v3_fixed_quadratic_node_j15', j_min=15, scan=scan,
                fixed_schedule=True, compiler_profile=False,
                implementation_options=asdict(_options),
                source_ledger=source_ledger(scan['static_T']),
                finish_geometry=geometry_binding,
                runtime_bindings=runtime_bindings(),
                status='BUILT_CANDIDATE_REQUIRES_EXTERNAL_VERIFICATION')
