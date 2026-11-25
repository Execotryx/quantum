# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed quadratic-node DQI candidate emitter; completion gates are external.

This module receives public cutoff/scan extent only, never an input-dependent
profile, terminal, contact list, count, polynomial alias table or failure salt.
Production uses j_min15 and the complete4095-point scan. Short scans exist only
for expressly labelled engineering checks and cannot be submitted as a decoder.
"""
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parents[2]
for directory in (WORK/'work/round2/milestone152/source', WORK/'night_converter',
                  WORK/'night_schedule', WORK/'night_root',
                  WORK/'night_c27/arithmetic', WORK/'night_c27/controller',
                  WORK/'night_c27/mask_gauge'):
    sys.path.insert(0, str(directory))

import kickmix as km
import public_geometry as Public
import fused_crt_synthesis as Synthesis
import projective_finish as Finish
import additive_fft_phase_scan as Scan
import mask_gauge_blocked as Masks
import night_outer as Outer
import rolling_tail as Tail
import scalar_seed as Seed


def emit_key_prefix(builder, syndromes, *, j_min=15, stage=lambda _: None):
    """Expose the actual fixed extractor/synthesis boundary for native checks.

    The record contains physical register views, never a classical input profile.
    Closing consumes this record exactly once and restores all seventy inputs.
    """
    import raw_query_extractor as Extractor
    assert len(syndromes) == 70
    assert j_min in (15, 16, 17)
    Public.emit(builder, syndromes)
    heads = [km.array([*syndromes[2*i], *syndromes[2*i+1]]) for i in range(35)]
    carry = builder.alloc_qubits(24)
    builder.x(carry[0])
    extraction = Extractor.emit_prefix(builder, heads, carry, j_min=j_min, stage=stage)
    extraction.tail.release_spare()
    gauge = Tail.gauge_prefix(builder, carry)
    seed = Seed.emit_prefix(builder, carry[:12], heads[34])
    extraction.tail.seed_prefix(carry[:12], heads[34][12:])
    N, D = [carry[:12]], [heads[34][:12], heads[34][12:]]
    synthesis = []
    for i in range(33, -1, -1):
        P = [heads[i][:12], heads[i][12:]]
        # On the admitted domain a zero source can occur only at a tail
        # slot, whose head is also zero. The native462 pair's inv0 extension
        # preserves that joint-zero subspace; no zero flag is needed here.
        rec = Synthesis.emit_prefix(builder, N, D, P, i, guarded=False)
        synthesis.append((N, D, P, rec))
        N, D = D, N+P
        stage(dict(stage='synthesis_prefix', node=i, degree=len(D)-1))
    assert len(N) == 35 and len(D) == 36
    return dict(builder_id=id(builder), syndromes=syndromes, heads=heads,
                carry=carry, extraction=extraction, gauge=gauge, seed=seed,
                synthesis=synthesis, N=N, D=D, closed=False)


def emit_key_closing(builder, record, *, stage=lambda _: None):
    import raw_query_extractor as Extractor
    assert record['builder_id'] == id(builder) and not record['closed']
    heads, carry = record['heads'], record['carry']
    extraction, gauge, seed = record['extraction'], record['gauge'], record['seed']
    for old_N, old_D, old_P, rec in reversed(record['synthesis']):
        Synthesis.emit_closing(builder, old_N, old_D, old_P, rec)
        stage(dict(stage='synthesis_return', node=rec.node_index))
    extraction.tail.seed_return(carry[:12], heads[34][12:])
    Seed.emit_closing(builder, carry[:12], heads[34], seed)
    Tail.gauge_return(builder, carry, gauge)
    extraction.tail.resume_return()
    Extractor.emit_closing(builder, heads, carry, extraction, stage=stage)
    builder.x(carry[0])
    builder.free(carry)
    Public.emit(builder, record['syndromes'], True)
    record['closed'] = True


def emit(builder, syndromes, masks, *, j_min=15, scan_positions=4095, stage=lambda _: None):
    assert len(syndromes) == 70 and len(masks) == 4095
    plan = Public.syndrome_gauge_plan()
    Masks.open_gauge(builder, list(syndromes), masks, plan)
    stage('original_syndrome_weight_gauge')
    key = emit_key_prefix(builder, syndromes, j_min=j_min, stage=stage)
    N, D = key['N'], key['D']
    outer = Outer.emit_prefix(builder, D, N, fused=False, stage=stage)
    finish = Finish.emit_prefix(builder, D, N)
    stage('projective_finish_prefix')
    scan = Scan.emit(builder, D, N, masks, positions=scan_positions, stage=stage)
    Finish.emit_closing(builder, D, N, finish)
    Outer.emit_closing(builder, D, N, (), outer, stage=stage)
    emit_key_closing(builder, key, stage=stage)
    Masks.close_gauge(builder, masks, plan)
    stage('all_original_inputs_restored')
    return dict(candidate='fixed_quadratic_node_j15', j_min=j_min, scan=scan,
                fixed_schedule=True, compiler_profile=False,
                status='BUILT_CANDIDATE_REQUIRES_EXTERNAL_VERIFICATION')
