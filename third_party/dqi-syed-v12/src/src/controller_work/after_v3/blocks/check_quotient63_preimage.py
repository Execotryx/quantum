#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded handoff preimage with the joint-norm phase sibling.

Both actual paired-scale callers use the same provider, with the unchanged
rare classical-only branch. Eighteen emitted quotient calls and the exact
nested mask events are required; old exclusive-branch events are absent.
The new63-T body saves36*(1-2**-24) expected T beyond the rare-branch bundle.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys
import time

from collections import Counter
from fractions import Fraction
from types import SimpleNamespace
from accepted_runtime import load, pinned_sources, loaded_sources

Runtime = load()
Pipeline = Runtime.pipeline
Binding = Runtime.binding
AFTER = Path(__file__).resolve().parents[2]/'after_c5'
from event_ledger import Events  # noqa: E402
import kickmix as km  # noqa: E402
import numpy as np  # noqa: E402
import night_reference as Ref  # noqa: E402
from quantum_reciprocal import bit_matrix  # noqa: E402
import window_forward_retained_flag as Candidate
import transpose_handoff_core as NewCore
import transpose_handoff_window as NewWindow
import transpose_handoff_outer as NewOuter
import masked_parked_scale_phase as MaskedPhase
import window_transpose_handoff as Transpose  # noqa: E402
import paired_phase63 as Joint  # noqa: E402
import quotient_phase63 as JointPhase  # noqa: E402

CALLS = []
TRANSPOSE_CALLS = []
TRANSPOSE_HANDOFFS = []
PAIRED_CALLS = []
JointProviderFunction = None
TransposeProvider = None

FIXTURES = AFTER/'converter_width/runs/full/fixtures.json'
FIXTURE_SHA = '6e023eb39758c15cc5e3835bc6bcdb0f8ad08c3ec15185d2c970dfbb201fac73'
RETAINED = 865
SEEDS = (137, 1137, 2137)
EXPECTED_STATIC = 115081
EXPECTED_MEAN = 114514.87007855662
EXPECTED_PREFIX_STATIC = 57053
PROBE_T = 3
PROVIDER_PINS = {
    'accepted_runtime.py': 'e978226b01af63e3c43f418de5e73887bdbb07c45423f4c9f09b04ad940eef22',
    'window_forward_retained_flag.py': '8d84b64de0c7d221a418afbabf913dd9a5fd5d53993ab81525538b1f9b067200',
    'parked_scale_phase.py': '07af5f682e7a04b1782f107d38785125c645e537f9ccd50c6efa7b5d4966cbb6',
    'masked_parked_scale_phase.py': '202f391f8be4bbc88b40ed9fede962a6b1cf469dae37b9cf2fb5a733e0a2a0ec',
    'masked_parked_phase_core.py': '2bae2f3c5a75f0131226b41421307e9ec5a3d6a7a089bdbaab17dc4a853abf9e',
    'masked_parked_phase_window.py': '265bab78eff48614db921b5a981e1048280f44e1f4091cf356129f6836948de0',
    'masked_parked_phase_outer.py': '7a4ec7e0ce2e367e64c83d5a90a863e5a405f71f2d1964dc3477a826d2354463',
    'window_transpose_retained.py': '5de6b48270d3098ca3ffa37474f2c10959d02ee3ccdb902e58b3ee8bcba129da',
    'transpose_handoff_outer.py': 'f2284acd4fd7c1f24fb4460a24ce7a449103412629bae59d06b2c1945788b699',
    'transpose_handoff_core.py': 'c7453a0a4b75819b75bc8fc3c918e0ec33ae52a4ef55f37c10e07a41865fab17',
    'transpose_handoff_window.py': '000864e4f2a87465bb882571f79e7c7fd35b04f25779fe4bb947c19183036281',
    'window_transpose_handoff.py': 'bb8423494ded91d4b42e83b147de4d45cf5bdb87695788ea66ef73cc3f817b21',
    'paired_phase_rare27.py': '96e296122043a03948704816ed79fe3e96ad2ec1f0e36008ede773da920d83a1',
    'paired_phase63.py': '960f7d1a732eeb8b0246cdb80b3b18110a03be676512670caeb0183af38cd37d',
    'quotient_phase63.py': 'f34552c29673a823f1a1f82c05894fd8c0fd5aad443495caa8914570e8262bdb',
    'dual64_tensor.py': 'ee0e7c3fc4d0c16b56f808a999f59ddd4614c9729de9ed8c8efe4c755bc6439e',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def configure():
    global TransposeProvider, JointProviderFunction
    assert Pipeline.Window.tensor is Runtime.reference
    assert Pipeline.Window.transpose_tensor is Runtime.transpose

    def tracked(builder, F, G, q0, q1, rhss, record_flag, third_flag):
        slots = []
        retained = builder.num_allocated_qubits
        def record(slot, mask):
            slots.append(slot)
            record_flag(slot, mask)
        Candidate.emit(builder, F, G, q0, q1, rhss, record, third_flag)
        assert slots == [0, 1]
        assert builder.num_allocated_qubits == retained
        CALLS.append(dict(m=len(G)-1, retained_Q=retained,
                          returned_source_mask_slots=slots,
                          core_static_T=168*(len(G)-1)+634,
                          retained_third_flag=True))
    Pipeline.Core = NewCore
    Pipeline.Outer = NewOuter
    Pipeline.Outer.core = NewCore
    if Pipeline.Seam is not None:
        Pipeline.Seam.Outer = NewOuter
    Pipeline.Window = NewWindow
    assert NewWindow.C is NewCore
    NewWindow.tensor = SimpleNamespace(__name__=Candidate.__name__, emit=tracked)
    def tracked_transpose(builder, F, G, q0, q1, rhss, record_flag):
        slots = []
        retained = builder.num_allocated_qubits
        def record(slot, mask):
            slots.append(slot)
            record_flag(slot, mask)
        handoff = Transpose.emit(builder, F, G, q0, q1, rhss, record)
        assert isinstance(handoff, Transpose.ThirdFlagHandoff)
        assert not handoff.claimed and handoff.witness == tuple(G[-1])
        assert Counter(slots) == {0: 5, 1: 5, 2: 3}, slots
        assert builder.num_allocated_qubits == retained+1
        TRANSPOSE_CALLS.append(dict(m=len(G)-1, retained_Q=retained,
                                   source_mask_slot_counts=dict(Counter(slots)),
                                   core_static_T=168*(len(G)-1)+876,
                                   returned_live_third_flag=True))
        return handoff
    TransposeProvider = SimpleNamespace(__name__=Transpose.__name__, emit=tracked_transpose)
    NewWindow.transpose_tensor = TransposeProvider
    assert Pipeline.Window.transpose_tensor is TransposeProvider
    original_adopt = NewWindow.Step.adopt
    def tracked_adopt(step, handoff, pay=False):
        assert step.flag is None and not handoff.claimed
        assert handoff.witness == tuple(step.B[-1])
        allocated = step.b.num_allocated_qubits
        original_adopt(step, handoff, pay=pay)
        assert handoff.claimed and tuple(step.flag) == tuple(handoff.flag)
        assert step.b.num_allocated_qubits == allocated
        if pay:
            assert step.flagmask is None and step.n not in step.context.local_flags
        TRANSPOSE_HANDOFFS.append(dict(n=step.n, closing=step.closing,
                                      pay_existing_masks=bool(pay),
                                      new_quantum_allocations=0,
                                      exact_witness_owned=True))
    NewWindow.Step.adopt = tracked_adopt
    NewCore.paired_scale = Joint
    NewOuter.paired_scale = Joint
    assert Joint.phase_inverse_trace_twelve is JointPhase.phase_inverse_trace_twelve
    original_joint = Joint.quotient_phases
    def tracked_joint(builder, factor, targets, inverse_mask):
        allocated = builder.num_allocated_qubits
        assert len(factor) == len(inverse_mask) == 12 and len(targets) == 2
        original_joint(builder, factor, targets, inverse_mask)
        assert builder.num_allocated_qubits == allocated
        PAIRED_CALLS.append(dict(retained_Q=allocated, targets=2,
                               static_T=90, peak_owned_helpers=18))
    JointProviderFunction = tracked_joint
    Joint.quotient_phases = JointProviderFunction


def recheck_replacement():
    """Preserve original bytes and honestly identify the new transpose."""
    actual_provider_hashes = {
        name: digest(Path(__file__).with_name(name)) for name in PROVIDER_PINS}
    assert actual_provider_hashes == PROVIDER_PINS
    assert pinned_sources() == Runtime.pinned_sources
    assert Runtime.bootstrap.validate_normalization() == Runtime.derivation
    assert Runtime.binding.verify_accepted_sources() == Runtime.baseline_binding
    assert Pipeline.Window is NewWindow
    assert NewWindow.tensor.__name__ == Candidate.__name__
    assert NewWindow.transpose_tensor is TransposeProvider
    assert TransposeProvider.emit.__name__ == 'tracked_transpose'
    assert Pipeline.Outer is NewOuter and Pipeline.Outer.core is NewCore
    assert NewCore.paired_scale is Joint and NewOuter.paired_scale is Joint
    assert Joint.quotient_phases is JointProviderFunction
    assert Joint.phase_inverse_trace_twelve is JointPhase.phase_inverse_trace_twelve
    assert Pipeline.Seam is None or Pipeline.Seam.Outer is NewOuter
    assert Path(Transpose.__file__).resolve() == Path(__file__).with_name('window_transpose_handoff.py')
    return dict(pins=Runtime.pinned_sources, new_provider_sha256=actual_provider_hashes,
                unchanged_original_gate=Runtime.baseline_binding,
                normalization_derivation=Runtime.derivation,
                reference_transpose_path=str(Path(Runtime.transpose.__file__).resolve()),
                reference_transpose_sha256=digest(Runtime.transpose.__file__),
                actual_transpose_path=str(Path(Transpose.__file__).resolve()),
                actual_transpose_sha256=digest(Transpose.__file__),
                actual_core_path=str(Path(NewCore.__file__).resolve()),
                actual_window_path=str(Path(NewWindow.__file__).resolve()),
                actual_outer_path=str(Path(NewOuter.__file__).resolve()),
                actual_paired_scale_path=str(Path(Joint.__file__).resolve()),
                actual_paired_scale_sha256=digest(Joint.__file__),
                actual_quantum_phase_path=str(Path(JointPhase.__file__).resolve()),
                actual_quantum_phase_sha256=digest(JointPhase.__file__),
                both_core_and_outer_use_joint_norm_provider=True,
                original_provider_equality_claimed=False,
                temporary_rebinding_for_preservation_check=False)


def fixture_panel(smoke):
    assert digest(FIXTURES) == FIXTURE_SHA
    rows = json.loads(FIXTURES.read_text())
    assert len(rows) == 256
    used = list(range(8)) if smoke else list(range(256))
    fixtures = [rows[i] for i in used]
    seen = {}
    for row in fixtures:
        assert row['gauge_flag'] in (0, 1)
        assert not row['gauge_flag'] or row['gauge_other'] == 0
        assert Ref.admitted(row['D'])
        key = (tuple(row['D']), tuple(row['O']))
        if key not in seen:
            seen[key] = Ref.full_preimage(row['D'], row['O'])
        assert seen[key] == row['expected']
        assert Ref.profile(row['D']) == row['half_profile']
    assert {r['gauge_flag'] for r in fixtures} == {0, 1}
    return fixtures, dict(path=str(FIXTURES), sha256=FIXTURE_SHA,
                          original_cases=256, used_cases=len(fixtures),
                          selected_indices=used, smoke=smoke,
                          omissions=[] if not smoke else list(range(8, 256)),
                          new_fixtures_or_random_draws=0)


def build(events, prefix_path=None, label='a'):
    events.rows.clear()
    CALLS.clear()
    TRANSPOSE_CALLS.clear()
    TRANSPOSE_HANDOFFS.clear()
    PAIRED_CALLS.clear()
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    D = [b.create_quantum_register(12, f'D{i}') for i in range(36)]
    O = [b.create_quantum_register(12, f'O{i}') for i in range(35)]
    other = b.create_quantum_register(12, 'gauge_other')
    flag = b.create_quantum_register(1, 'gauge_flag')
    probe = b.create_classical_register(RETAINED, 'phase_probe')
    stages = []

    def stage(message):
        stages.append(dict(stage=message, allocated_Q=b.num_allocated_qubits))
        print(json.dumps(dict(stage=message, build=label,
                              allocated_Q=b.num_allocated_qubits)), flush=True)

    record = Pipeline.Outer.emit_prefix(b, D, O, gauge_flag=flag[0],
                                       gauge_other=other, stage=stage)
    assert not record.core.local_flags
    assert set(record.core.local_created) == {(False, n) for n in range(2, 18)}
    assert len(record.core.local_created) == len(record.core.local_retired) == 16
    prefix = b.finish_circuit()
    prefix_static = prefix.operation_statistics().num_toffoli_like
    prefix_calls = list(CALLS)
    prefix_transpose_calls = list(TRANSPOSE_CALLS)
    prefix_handoffs = list(TRANSPOSE_HANDOFFS)
    assert len(prefix_handoffs) == 1 and prefix_handoffs[0]['n'] == 15
    assert Counter(row['m'] for row in prefix_transpose_calls) == {14: 1}
    assert Counter(row['m'] for row in prefix_calls) == {11: 1, 14: 1}, prefix_calls
    prefix_expectation = events.snapshot(prefix_static)
    assert not PAIRED_CALLS, 'paired quotient phases belong to closing'
    assert not any(e['name'].startswith('paired_dual63_') for e in prefix_expectation['events'])
    assert prefix_static == EXPECTED_PREFIX_STATIC, prefix_static
    assert prefix.num_qubits == 889 and b.num_allocated_qubits == RETAINED
    if prefix_path is not None:
        prefix.to_file(prefix_path, format='kmb')
    del prefix

    wires = km.array([q for word in D+O for q in word] + list(other) + list(flag))
    b.cz(probe, wires)
    b.ccz(flag[0], D[0][0], O[0][1])
    b.ccz(other[3], O[17][2], O[34][5])
    b.ccz(D[35][7], O[2][4], O[30][6])
    Pipeline.Outer.emit_closing(b, D, O, (), record, stage=stage)
    assert b.num_allocated_qubits == RETAINED
    assert not record.core.local_flags
    expected = {(closing, n) for closing in (False, True) for n in range(2, 18)}
    assert len(record.core.local_created) == len(record.core.local_retired) == 32
    assert set(record.core.local_created) == set(record.core.local_retired) == expected
    assert not record.core.beta and not record.core.flags
    assert not record.core.quotients and not record.core.outer
    record.core.gauge_carrier.clean_boundary()
    circuit = b.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    assert static - PROBE_T == EXPECTED_STATIC, static
    assert circuit.num_qubits == 889, circuit.num_qubits
    assert Counter(row['m'] for row in CALLS) == {11: 2, 14: 2}, CALLS
    assert Counter(row['m'] for row in TRANSPOSE_CALLS) == {14: 2}
    assert len(TRANSPOSE_HANDOFFS) == 2
    assert Counter(row['pay_existing_masks'] for row in TRANSPOSE_HANDOFFS) == {False: 1, True: 1}
    assert all(row['n'] == 15 for row in TRANSPOSE_HANDOFFS)
    expectation = events.snapshot(static-PROBE_T)
    assert abs(expectation['expected_T'] - EXPECTED_MEAN) < 1e-7, expectation
    assert len(PAIRED_CALLS) == 18, PAIRED_CALLS
    assert not any(row['name'].startswith(('paired_converter_', 'paired_rare27_'))
                   for row in expectation['events'])
    observed_joint = {(row['name'], row['conditional_T'], row['mask_bits']): row['occurrences']
                     for row in expectation['events'] if row['name'].startswith('paired_dual63_')}
    assert observed_joint == {
        ('paired_dual63_exclusive_overlap', 27, 0): 18,
        ('paired_dual63_rhs_zero', 36, 24): 18,
        ('paired_dual63_all_masks_zero', 27, 36): 18}, observed_joint
    expected_rare_saving = Fraction(295155, 34359738368)
    expected_joint_saving = Fraction(36)*(1-Fraction(1, 1 << 24))
    assert Fraction(expectation['expected_T_exact']) == Fraction(480461172601, 4194304)-expected_rare_saving-expected_joint_saving
    carrier = record.core.gauge_carrier
    assert (carrier.parks, carrier.unparks) == (14, 14)
    assert carrier.parked_phase_payments == 2
    metrics = dict(
        static_T=static-PROBE_T, circuit_static_T=static, probe_T=PROBE_T,
        Q=circuit.num_qubits, retained_data=RETAINED,
        prefix_static_T=prefix_static, prefix_expectation=prefix_expectation,
        expectation=expectation,
        accepted_v3_preimage_static_T=115627,
        accepted_v3_preimage_HMR_mean_T=114916.88131546974,
        delta_static_T=-546,
        delta_uniform_fresh_mask_mean_T=-366.01123046875-float(expected_rare_saving)-float(expected_joint_saving),
        delta_uniform_fresh_mask_mean_T_exact=str(-Fraction(366)-Fraction(46,4096)-expected_rare_saving-expected_joint_saving),
        rare_branch_additional_static_delta_T=-144,
        rare_branch_additional_mean_delta_T_exact=str(-expected_rare_saving),
        rare_branch_additional_mean_delta_T=-float(expected_rare_saving),
        joint_quotient_calls=list(PAIRED_CALLS),
        joint_phase_additional_static_delta_T=-36,
        joint_phase_additional_mean_delta_T_exact=str(-expected_joint_saving),
        joint_phase_additional_mean_delta_T=-float(expected_joint_saving),
        transpose_incremental_static_and_expected_delta_T=-198,
        handoff_additional_static_and_expected_delta_T=-22,
        mask_guard_additional_exact_expected_delta_T=-0.01123046875,
        delta_from_retained_flag_static_T=-402,
        delta_from_retained_flag_expected_T=-222.01123046875-float(expected_rare_saving)-float(expected_joint_saving),
        delta_from_self_contained_borrowed_static_T=-490,
        delta_from_self_contained_borrowed_expected_T=-310.01123046875-float(expected_rare_saving)-float(expected_joint_saving),
        prefix_delta_static_T=-183,
        prefix_forward_calls=prefix_calls,
        all_forward_calls=list(CALLS),
        prefix_transpose_calls=prefix_transpose_calls,
        all_transpose_calls=list(TRANSPOSE_CALLS),
        prefix_transpose_handoffs=prefix_handoffs,
        all_transpose_handoffs=list(TRANSPOSE_HANDOFFS),
        transpose_provider=Pipeline.Window.transpose_tensor.__name__,
        created_local_debts=record.core.local_created,
        retired_local_debts=record.core.local_retired,
        maximum_pending_local_masks=record.core.local_max_pending,
        pending_local_masks_after_pair=len(record.core.local_flags),
        gauge_parks=carrier.parks, gauge_unparks=carrier.unparks,
        parked_phase_payments=carrier.parked_phase_payments,
        top16_gauge_requeries=record.core.gauge_h_requeries,
        operations=len(circuit), stages=stages,
    )
    return circuit, metrics


def simulate(circuit, fixtures, seed, prefix=False):
    count = len(fixtures)
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    registers = circuit.register_data
    for letter, length in (('D', 36), ('O', 35)):
        for i in range(length):
            values = np.array([f[letter][i] for f in fixtures], dtype=np.int64)
            sim.write_across_shots(registers[f'{letter}{i}'], bit_matrix(values, 12))
    for name, width in (('gauge_other', 12), ('gauge_flag', 1)):
        values = np.array([f[name] for f in fixtures], dtype=np.int64)
        sim.write_across_shots(registers[name], bit_matrix(values, width))
    masks = np.random.default_rng(202611114502).integers(
        0, 2, size=(RETAINED, count), dtype=np.int8).astype(bool)
    sim.write_across_shots(registers['phase_probe'], masks)
    sim.do(circuit)
    bad = np.zeros(count, dtype=bool)
    for letter, length in (('D', 36), ('O', 35)):
        key = 'expected' if prefix and letter == 'O' else letter
        for i in range(length):
            wanted = bit_matrix(np.array([f[key][i] for f in fixtures]), 12)
            bad |= np.any(sim.read_across_shots(registers[f'{letter}{i}']) != wanted, axis=0)
    for name, width in (('gauge_other', 12), ('gauge_flag', 1)):
        wanted = bit_matrix(np.array([f[name] for f in fixtures]), width)
        bad |= np.any(sim.read_across_shots(registers[name]) != wanted, axis=0)
    scratch = [km.q(i) for i in range(RETAINED, circuit.num_qubits)]
    assert scratch
    bad |= np.any(sim.read_across_shots(scratch), axis=0)
    assert np.array_equal(sim.read_across_shots(registers['phase_probe']), masks)
    phase_bad = np.zeros(count, dtype=bool)
    if not prefix:
        boundary = []
        for f in fixtures:
            row = []
            for word in f['D'] + f['expected'] + [f['gauge_other']]:
                row.extend((word >> i) & 1 for i in range(12))
            row.append(f['gauge_flag'])
            boundary.append(row)
        expected_phase = np.logical_xor.reduce(np.array(boundary, dtype=bool).T & masks, axis=0)
        for i, f in enumerate(fixtures):
            O, D = f['expected'], f['D']
            expected_phase[i] ^= bool(f['gauge_flag'] and D[0] & 1 and O[0] & 2)
            expected_phase[i] ^= bool(f['gauge_other'] & 8 and O[17] & 4 and O[34] & 32)
            expected_phase[i] ^= bool(D[35] & 128 and O[2] & 16 and O[30] & 64)
        phase_bad = sim.read_phase_flipped_across_shots() != expected_phase
    row = dict(seed=seed, shots=count, prefix_values_only=prefix,
               value_restoration_scratch_errors=int(bad.sum()),
               phase_errors=None if prefix else int(phase_bad.sum()),
               sampled_mean_T_including_probes=sim.operation_statistics().num_toffoli_like/count,
               bad_value_indices=np.flatnonzero(bad).tolist(),
               bad_phase_indices=np.flatnonzero(phase_bad).tolist())
    assert not bad.any() and not phase_bad.any(), row
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--keep-circuits', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    started = time.monotonic()
    accepted_before = Binding.verify_accepted_sources()
    configure()
    recheck_replacement()
    events = Events()
    events.install(Pipeline)
    MaskedPhase.record_uniform_hmr_event = events.record
    Joint.record_uniform_hmr_event = events.record
    fixtures, fixture_source = fixture_panel(args.smoke)
    (args.output/'fixtures-used.json').write_text(json.dumps(fixtures, indent=2)+'\n')
    print(json.dumps(dict(stage='fixtures_ready', fixtures=fixture_source)), flush=True)
    prefix_path = args.output/'prefix-a.kmb'
    prefix_second_path = args.output/'prefix-b.kmb'
    paths = [args.output/f'build-{letter}.kmb' for letter in ('a', 'b')]
    circuit, metrics = build(events, prefix_path, 'a')
    circuit.to_file(paths[0], format='kmb')
    sha = digest(paths[0])
    roundtrip = [simulate(circuit, fixtures, seed) for seed in SEEDS]
    del circuit
    gc.collect()
    circuit, second = build(events, prefix_second_path, label='b')
    circuit.to_file(paths[1], format='kmb')
    assert sha == digest(paths[1]) and metrics == second
    assert digest(prefix_path) == digest(prefix_second_path)
    del circuit
    gc.collect()
    prefix = km.Circuit.from_file(prefix_path, format='kmb')
    prefixes = [simulate(prefix, fixtures, seed, True) for seed in SEEDS]
    del prefix
    gc.collect()
    accepted_after = Binding.verify_accepted_sources()
    assert accepted_before == accepted_after
    report = dict(
        status='PASS_NATIVE_JOINT63_HANDOFF_PREIMAGE_COMPONENT_ONLY',
        fixture_source=fixture_source, fixtures=len(fixtures),
        gauge_charts=sorted({f['gauge_flag'] for f in fixtures}),
        forced_top_gap_fixtures=sum(f['forced_top_gap'] for f in fixtures),
        two_identical_builds=True, circuit_sha256=sha,
        metrics=metrics, roundtrip=roundtrip, prefix_values=prefixes,
        source_bindings=loaded_sources(),
        accepted_normalized_runtime_preservation=recheck_replacement(),
        actual_runtime_providers=Pipeline.runtime_bindings(),
        prefix_two_identical_builds=True, prefix_sha256=digest(prefix_path),
        accepted_and_frozen_sources=accepted_after,
        elapsed_seconds=time.monotonic()-started,
        limitations=[
            'Component only; no full candidate, official salts or population draws.',
            'Prefix checks values and clean scratch; inherited arithmetic HMR debts remain open until closing.',
            'The unchanged32 local masks and all returned source-query masks are retired at the caller witnesses.',
            'Borrowed forward/third-flag/parked phase changes, retimed transpose and actual third-flag handoffs are explicit providers.',
            'Both paired-scale callers use the joint63 provider with its separately priced rare27 branch.',
            'All accepted C5/v3/release sources and historical receipts remain unchanged.',
        ],
    )
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], metrics=metrics,
                          fixtures=len(fixtures), circuit_sha256=sha), indent=2), flush=True)
    if not args.keep_circuits:
        for path in [prefix_path, prefix_second_path, *paths]:
            path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
