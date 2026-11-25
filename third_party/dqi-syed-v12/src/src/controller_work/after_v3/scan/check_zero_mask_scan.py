#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Caller-guarded complete zero-mask scan/value-view panels; unchanged domain."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import random
import sys
import time

HERE = Path(__file__).resolve().parent
WORK, ROOT = HERE.parents[1], HERE.parents[2]
for directory in (WORK/'work/round2/milestone152/source',
                  ROOT/'pro1_controller_bundle/1_task/official',
                  WORK/'night_schedule', WORK/'night_root', WORK/'night_converter',
                  WORK/'night_c27/arithmetic', WORK/'night_c27/census',
                  WORK/'night_c27/arithmetic/panel_audit', WORK/'research_audit',
                  WORK/'night_c27/synthesis', WORK/'after_c5/arithmetic_t'):
    sys.path.insert(0, str(directory))
import kickmix as km
import numpy as np
import zero_mask_scan as New
import reference as R
import night_reference as OuterReference
import physical_boundary_oracle as Physical


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def polynomial_list_product(factors):
    result = [1]
    for factor in factors:
        result = R.product(result, factor)
    return result


def H(poly, vector):
    return [sum_xor(R.mul(poly[k+j+1], vector[j])
                    for j in range(min(len(vector), len(poly)-k-1)))
            for k in range(35)]


def sum_xor(values):
    result = 0
    for value in values:
        result ^= value
    return result


def novel_values(values):
    result = list(values)
    basis = New.fft_geometry()['basis']
    for i in reversed(range(len(result))):
        result[i] = R.divide(result[i], basis[i][-1])
        for j, value in enumerate(basis[i][:-1]):
            result[j] ^= R.mul(value, result[i])
    return result


def encode_words(words_by_case):
    values = np.asarray(words_by_case, dtype=np.uint16).T
    return (((values[:, None, :] >> np.arange(12)[None, :, None]) & 1)
            .reshape(values.shape[0]*12, values.shape[1]).astype(bool))


def make_fixtures(args, M):
    rng = random.Random(202611110134)
    fixtures = []

    def append(label, D, K, **metadata):
        assert len(D) <= 36 and len(K) <= 35
        fixtures.append(dict(label=label, D=list(D)+[0]*(36-len(D)),
                             K=list(K)+[0]*(35-len(K)), **metadata))

    for i in range(args.arbitrary_cases):
        append(f'arbitrary_dense_{i}', [rng.randrange(4096) for _ in range(36)],
               [rng.randrange(4096) for _ in range(35)])
    append('zero_locator_dense_value', [], [rng.randrange(4096) for _ in range(35)])
    append('constant_unit_locator', [317], [rng.randrange(4096) for _ in range(35)])
    append('zero_everything', [], [])
    append('joint_zero_masks', [], [rng.randrange(4096) for _ in range(35)], mask_mode='zero')
    append('all_one_masks', [], [rng.randrange(4096) for _ in range(35)], mask_mode='ones')
    append('repeated_root_35', polynomial_list_product([[71, 1]]*35),
           [rng.randrange(4096) for _ in range(35)])
    append('selected_and_scanned_roots',
           polynomial_list_product([[a, 1] for a in (1, 32, 70, 71, 72, 511, 2048, 4095)]),
           [rng.randrange(4096) for _ in range(35)])
    if args.physical_terminals:
        corpus = json.loads(args.physical_fixtures.read_text())
        assert corpus['format'] == 'C27_PHYSICAL_PANEL_V1'
        for j in args.physical_terminals:
            candidates = [item for item in corpus['cases']
                          if item['weight'] == j and item['classification']['admitted']]
            assert len(candidates) >= args.physical_per_weight, ('missing_saved_fixture', j)
            for item in candidates[:args.physical_per_weight]:
                boundary = Physical.boundary(item['roots'], item['values'])
                D, numerator = boundary['D'], boundary['N']
                X = OuterReference.full_preimage(D, numerator)
                K = R.add(R.product(D, H(M, X)), R.product(M, H(D, X)))
                assert len(K) <= 35
                append('physical_'+item['case_id'], D, K, physical=True,
                       roots=item['roots'], values=item['values'], weight=j,
                       source_case_id=item['case_id'], source_label=item['label'])
    return fixtures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--positions', type=int, default=4095)
    p.add_argument('--start-index', type=int, default=0)
    p.add_argument('--arbitrary-cases', type=int, default=8)
    p.add_argument('--physical-fixtures', type=Path,
                   default=WORK/'night_c27/arithmetic/panel_audit/prepared/cases.json')
    p.add_argument('--physical-terminals', type=int, nargs='*', default=list(range(15, 36)))
    p.add_argument('--physical-per-weight', type=int, default=1)
    p.add_argument('--view-coset', type=int, default=2016)
    p.add_argument('--seeds', type=int, nargs='+', default=[1109, 2109, 3109])
    p.add_argument('--keep-circuits', action='store_true')
    args = p.parse_args()
    assert args.arbitrary_cases >= 0 and args.physical_per_weight >= 0
    assert 0 <= args.start_index < 4095 and 0 < args.positions <= 4095-args.start_index
    assert args.view_coset in range(0, 4096, 32)
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    U = polynomial_list_product(R.QUADRATICS)
    M = polynomial_list_product([[R.KAPPA ^ R.mul(2*i, 2*i) ^ (2*i), 1, 1]
                                 for i in range(35, 51)])
    assert len(U) == 71 and len(M) == 33
    assert tuple(U) == tuple(New.geometry()['U']) and tuple(M) == tuple(New.Finish.geometry()['M'])
    selected = frozenset(range(1, 71))
    assert selected == frozenset(New.syndrome_gauge_plan().selected)
    fixtures = make_fixtures(args, M)
    cases = len(fixtures)
    (args.output/'fixtures.json').write_text(json.dumps(fixtures, indent=2)+'\n')
    rng = np.random.default_rng(202611110135)
    masks = rng.integers(0, 4096, (cases, 4095), dtype=np.uint16)
    for i, fixture in enumerate(fixtures):
        if fixture.get('mask_mode') == 'zero':
            masks[i].fill(0)
        elif fixture.get('mask_mode') == 'ones':
            masks[i].fill(4095)
    initial = dict(D=encode_words([f['D'] for f in fixtures]),
                   K=encode_words([f['K'] for f in fixtures]),
                   dirty=rng.integers(0, 2, (13, cases), dtype=np.int8).astype(bool),
                   masks=encode_words(masks),
                   probe_D=rng.integers(0, 2, (432, cases), dtype=np.int8).astype(bool),
                   probe_K=rng.integers(0, 2, (420, cases), dtype=np.int8).astype(bool))
    active = [(index, R.EXP[index])
              for index in range(args.start_index, args.start_index+args.positions)
              if R.EXP[index] not in selected]
    scan_phase = np.zeros(cases, dtype=bool)
    physical_root_checks = 0
    for index, point in active:
        divisor = R.mul(point, R.mul(R.evaluate(U, point), R.evaluate(M, point)))
        assert divisor
        factor = R.INV[divisor]
        for case, fixture in enumerate(fixtures):
            if R.evaluate(fixture['D'], point) == 0:
                value = R.mul(R.evaluate(fixture['K'], point), factor)
                scan_phase[case] ^= (int(masks[case, index]) & value).bit_count() & 1
    for case, fixture in enumerate(fixtures):
        if fixture.get('physical'):
            expected = 0
            for point, value in zip(fixture['roots'], fixture['values']):
                factor = R.mul(point, R.mul(R.evaluate(U, point), R.evaluate(M, point)))
                assert R.evaluate(fixture['D'], point) == 0
                assert R.evaluate(fixture['K'], point) == R.mul(value, factor)
                physical_root_checks += 1
                index = R.LOG[point]
                if args.start_index <= index < args.start_index+args.positions and point not in selected:
                    expected ^= (int(masks[case, index]) & value).bit_count() & 1
            assert scan_phase[case] == expected
    scan_total_T = 11*sum(int(np.count_nonzero(masks[:, index])) for index, _ in active)
    expected_view = {}
    for name in ('D', 'K'):
        values = []
        for fixture in fixtures:
            novel = novel_values(fixture[name])
            values.append([R.evaluate(fixture[name], args.view_coset ^ offset) for offset in range(32)] + novel[32:])
        expected_view[name] = encode_words(values)
    view_phase = np.logical_xor.reduce(expected_view['D'] & initial['probe_D'], axis=0)
    view_phase ^= np.logical_xor.reduce(expected_view['K'] & initial['probe_K'], axis=0)
    retained = 865

    def registers(builder):
        dr = builder.create_quantum_register(432, 'D')
        kr = builder.create_quantum_register(420, 'K')
        builder.create_quantum_register(13, 'dirty')
        mr = builder.create_classical_register(49140, 'masks')
        pd = builder.create_classical_register(432, 'probe_D')
        pk = builder.create_classical_register(420, 'probe_K')
        D = [dr[12*i:12*(i+1)] for i in range(36)]
        K = [kr[12*i:12*(i+1)] for i in range(35)]
        masks_view = [mr[12*i:12*(i+1)] for i in range(4095)]
        return dr, kr, D, K, masks_view, pd, pk

    def build_scan():
        builder = km.CircuitBuilder()
        _, _, D, K, mask_views, _, _ = registers(builder)
        record = New.emit(builder, D, K, mask_views, start_index=args.start_index, positions=args.positions)
        circuit = builder.finish_circuit()
        assert builder.num_allocated_qubits == retained
        assert circuit.num_qubits == retained+10
        assert circuit.operation_statistics().num_toffoli_like == 11*len(active) == record['static_T']
        return circuit, record

    def build_view(prefix_path=None):
        builder = km.CircuitBuilder()
        dr, kr, D, K, _, pd, pk = registers(builder)
        New.emit_basis(builder, D)
        New.emit_basis(builder, K)
        New.emit_coset_view(builder, D, args.view_coset)
        New.emit_coset_view(builder, K, args.view_coset)
        if prefix_path is not None:
            prefix = builder.finish_circuit()
            assert prefix.num_qubits == retained and prefix.operation_statistics().num_toffoli_like == 0
            prefix.to_file(prefix_path, format='kmb')
            del prefix
        builder.cz(pd, dr)
        builder.cz(pk, kr)
        New.emit_coset_view(builder, K, args.view_coset, inverse=True)
        New.emit_coset_view(builder, D, args.view_coset, inverse=True)
        New.emit_basis(builder, K, inverse=True)
        New.emit_basis(builder, D, inverse=True)
        circuit = builder.finish_circuit()
        assert builder.num_allocated_qubits == circuit.num_qubits == retained
        assert circuit.operation_statistics().num_toffoli_like == 0
        return circuit

    def simulate(circuit, seed, kind):
        simulator = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
        simulator.use_same_registers_as(circuit)
        for name, bits in initial.items():
            simulator.write_across_shots(circuit.register_data[name], bits)
        simulator.do(circuit)
        expected = dict(initial)
        phase = scan_phase if kind == 'scan' else view_phase if kind == 'view_pair' else np.zeros(cases, dtype=bool)
        if kind == 'view_prefix':
            expected.update(expected_view)
        errors = {}
        for name, bits in expected.items():
            actual = simulator.read_across_shots(circuit.register_data[name])
            if not np.array_equal(actual, bits):
                errors[name] = np.flatnonzero(np.any(actual != bits, axis=0)).tolist()
        if circuit.num_qubits > retained:
            if simulator.read_across_shots([km.q(k) for k in range(retained, circuit.num_qubits)]).any():
                errors['scratch'] = True
        phase_errors = np.flatnonzero(simulator.read_phase_flipped_across_shots() != phase).tolist()
        counted_T = simulator.operation_statistics().num_toffoli_like
        expected_T = scan_total_T if kind == 'scan' else 0
        result = dict(kind=kind, seed=seed, cases=cases, errors=errors,
                      phase_errors=phase_errors, total_T=counted_T,
                      exact_fixture_T=expected_T, measured_mean_T=counted_T/cases)
        assert not errors and not phase_errors and counted_T == expected_T, result
        del simulator
        gc.collect()
        return result

    paths = {name: args.output/(name+'.kmb') for name in ('scan-a', 'scan-b', 'view-prefix', 'view-a', 'view-b')}
    circuit, record = build_scan()
    scan_instruction_count = len(circuit)
    operation_counts = {str(k): int(v) for k, v in dict(circuit.operation_statistics()).items()}
    circuit.to_file(paths['scan-a'], format='kmb')
    scan_sha = sha(paths['scan-a'])
    scan_bytes = paths['scan-a'].stat().st_size
    runs = [simulate(circuit, seed, 'scan') for seed in args.seeds]
    del circuit
    gc.collect()
    circuit, repeated_record = build_scan()
    assert repeated_record == record
    circuit.to_file(paths['scan-b'], format='kmb')
    assert sha(paths['scan-b']) == scan_sha
    del circuit
    gc.collect()
    circuit = build_view(paths['view-prefix'])
    view_instruction_count = len(circuit)
    circuit.to_file(paths['view-a'], format='kmb')
    view_sha = sha(paths['view-a'])
    runs += [simulate(circuit, seed, 'view_pair') for seed in args.seeds]
    del circuit
    gc.collect()
    circuit = build_view()
    circuit.to_file(paths['view-b'], format='kmb')
    assert sha(paths['view-b']) == view_sha
    del circuit
    gc.collect()
    circuit = km.Circuit.from_file(paths['view-prefix'], format='kmb')
    runs += [simulate(circuit, seed, 'view_prefix') for seed in args.seeds]
    del circuit
    gc.collect()
    report = dict(status='PASS_NATIVE_ZERO_MASK_FULL_SCAN_COMPONENT_ONLY' if record['full_cycle'] else 'PASS_NATIVE_ZERO_MASK_PARTIAL_SCAN_COMPONENT_ONLY',
                  static_T=record['static_T'], Q=retained+10, retained=retained, helpers=10,
                  cases=cases, physical_cases=sum(bool(f.get('physical')) for f in fixtures),
                  physical_terminals=sorted({f['weight'] for f in fixtures if f.get('physical')}),
                  requested_physical_terminals=args.physical_terminals, physical_root_checks=physical_root_checks,
                  scan=record, two_identical_scan_builds=True, two_identical_view_builds=True,
                  scan_sha256=scan_sha, view_sha256=view_sha, scan_bytes=scan_bytes,
                  operation_counts=operation_counts, total_operations=sum(operation_counts.values()),
                  native_instruction_count=scan_instruction_count,
                  view_native_instruction_count=view_instruction_count,
                  measured_fixture_mean_T=scan_total_T/cases, view_static_T=0, view_Q=retained,
                  runs=runs, elapsed_seconds=time.monotonic()-started, census_draws=0,
                  source_sha256=sha(HERE/'zero_mask_scan.py'), checker_sha256=sha(Path(__file__)),
                  inherited_scan_sha256=sha(Path(New.Base.__file__)),
                  actual_finish_sha256=sha(Path(New.Finish.__file__)),
                  admitted_domain_change=False, official_verifier_run=False,
                  physical_fixture_sha256=sha(args.physical_fixtures),
                  limitations=['This is an isolated scan and public-view component, not an integrated decoder or official verification.',
                               'Measured means use the declared component fixtures, including zero masks; they are not official input-law means.',
                               'The old scan and all frozen census sources are unchanged.'])
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    if not args.keep_circuits:
        for path in paths.values():
            path.unlink()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
