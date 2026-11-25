#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded adaptive64 gauge/scan component; no decoder or census.

This source is prepared only. The author does not execute native work.
The field oracle constructs original masks from independent coefficient and
residual coordinates, computes the selector with ordinary integer counts,
and evaluates every scan polynomial directly. No selector network or emitter
interpolation rows are used by the oracle.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parent
WORK, ROOT = HERE.parents[2], HERE.parents[3]
for directory in (ROOT/'pro1_controller_bundle/1_task/official',
                  WORK/'work/round2/milestone152/source',
                  WORK/'night_schedule', WORK/'night_root', WORK/'night_converter',
                  WORK/'night_c27/arithmetic', WORK/'night_c27/synthesis',
                  WORK/'night_c27/census', WORK/'night_c27/mask_gauge',
                  WORK/'after_c5/arithmetic_t', WORK/'after_v3/scan'):
    sys.path.insert(0, str(directory))

import kickmix as km
import numpy as np
import reference as R
import adaptive_gauge64 as New

SEEDS = (3901, 4901, 5901)
FIXTURE_SEED = 202611113901
FULL_CASES = 80
MASK_BITS = 4095*12
RETAINED_Q = 865
PROBE_TRIPLES = ((0, 11, 257), (2, 601, 839))
PROBE_BITS = (2, 7, 11)
PROBE_SYNDROMES = (19, 449, 839)
CERTIFICATE = HERE.parent/'runs/adaptive-gauge-occupancy/paper_certificate.json'
CERTIFICATE_SHA = 'baa51690dae289f4bba81e53ca98c8c9db420a13dbd74f4c00beb281a9c4b627'
OLD_SOURCE_PINS = {
 'controller_work/night_c27/mask_gauge/mask_gauge_blocked.py':
 '0583bb931d91bb660108f815bb110d3885b713616b0b928bb3b385b22740a722',
 'controller_work/work/round2/milestone152/source/mask_gauge135.py':
 '8ccf4ef6589f54f5abab89dc21b791aef1991a1451cec0183ac4bcf35439caa5',
 'controller_work/night_c27/synthesis/public_geometry.py':
 'a6e410dd457679005c364d91ad191471086daf9f82ade0c9763d4ca13c016cf7',
 'controller_work/after_v3/scan/zero_mask_scan.py':
 'cacf6f97a639ff6b89d500e9cb9e2d427819ba461635cd6407a573d1668b53f1',
 'controller_work/night_schedule/scan10.py':
 '14a4e8e90dcc3b5f4b0dc3cc4ad5e306ebe55c87ca4185bc583f1ed9311f8b21',
 'controller_work/night_c27/census/reference.py':
 'a43a7dbf3ef0cb02f8660067a0067c603cf39fe7a552584c3fc9bc228f501aa6',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def bits(words):
    values = np.asarray(words, dtype=np.uint16)
    assert values.ndim == 2
    return (((values[:, :, None] >> np.arange(12,dtype=np.uint16)) & 1)
            .reshape(len(values), -1).astype(bool).T.copy())


def array_sha(values):
    return hashlib.sha256(memoryview(np.ascontiguousarray(values)).cast('B')).hexdigest()


def oracle_geometry():
    assert R.MODULUS == 0x1053 and New.F.modulus == R.MODULUS
    points = np.asarray(R.EXP[:4095], dtype=np.uint16)
    logs = np.asarray([0]+R.LOG[1:], dtype=np.int32)
    powers = np.asarray(R.EXP, dtype=np.uint16)

    def multiply(left, right):
        left, right = np.asarray(left,dtype=np.uint16), np.asarray(right,dtype=np.uint16)
        return np.where((left != 0) & (right != 0), powers[logs[left]+logs[right]], 0).astype(np.uint16)

    def evaluate(coefficients):
        answer = np.zeros(4095,dtype=np.uint16)
        for coefficient in reversed(coefficients):
            answer = multiply(answer, points) ^ int(coefficient)
        return answer

    gram_columns = [sum(R.trace(R.mul(1 << i, 1 << j)) << j for j in range(12))
                    for i in range(12)]
    gram = [0]*4096
    for value in range(1,4096):
        low = value & -value
        gram[value] = gram[value ^ low] ^ gram_columns[low.bit_length()-1]
    assert len(set(gram)) == 4096
    inverse = [0]*4096
    for value,image in enumerate(gram):
        inverse[image] = value
    gram, inverse = np.asarray(gram,dtype=np.uint16), np.asarray(inverse,dtype=np.uint16)
    polynomial = [0,1]
    for root in range(1,70):
        polynomial = R.product(polynomial,[root,1])
    g = evaluate(polynomial)
    selected = tuple(R.LOG[x] for x in range(1,71))
    chosen = frozenset(selected)
    residual = tuple(i for i in range(4095) if i not in chosen)
    fixed = frozenset(R.LOG[x] for x in range(1,70))
    pivot = R.LOG[70]
    assert tuple(New.geometry()['coefficients']) == tuple(polynomial[1:])
    assert tuple(New.geometry()['values']) == tuple(int(x) for x in g)
    assert tuple(New.geometry()['residual_indices']) == residual
    assert all((int(g[i]) == 0) == (i in fixed) for i in range(4095))
    U = [1]
    for factor in R.QUADRATICS:
        U = R.product(U,factor)
    M = [1]
    for index in range(35,51):
        kappa = R.KAPPA ^ R.mul(2*index,2*index) ^ (2*index)
        M = R.product(M,[kappa,1,1])
    assert tuple(U) == tuple(New.OriginalScan.geometry()['U'])
    assert tuple(M) == tuple(New.OriginalScan.Finish.geometry()['M'])
    denominator = multiply(points,multiply(evaluate(U),evaluate(M)))
    assert np.all(denominator)
    factors = np.asarray(R.INV,dtype=np.uint16)[denominator]
    return dict(points=points,multiply=multiply,evaluate=evaluate,gram=gram,inverse_gram=inverse,
                g=g,g_coefficients=np.asarray(polynomial[1:],dtype=np.uint16),
                selected=selected,residual=residual,fixed=fixed,pivot=pivot,factors=factors)


def make_fixtures(spec, limit):
    rng = np.random.default_rng(FIXTURE_SEED)
    count = FULL_CASES
    residual = spec['residual']
    labels = rng.integers(64,4096,(count,4025),dtype=np.uint16)
    names = []
    for candidate in range(64):
        labels[candidate,:9] = candidate
        names.append('forced_winner_'+str(candidate))
    labels[64].fill(0); names.append('all_residual_zero')
    labels[65].fill(63); names.append('all_residual_sixtythree')
    labels[66,:6] = 0; labels[66,6:18] = 2; names.append('zero_first_saturation')
    labels[67,0] = 0; labels[67,1:3] = 1; names.append('virtual_zero_tie')
    labels[68,:3] = 1; labels[68,3:6] = 2; names.append('first_nonzero_tie')
    labels[69,:7] = 3; labels[69,7:27] = 5; names.append('first_saturated_not_exact_mode')
    labels[70].fill(4095); names.append('no_eligible_residual')
    labels[71,:2] = 1; names.append('smallest_strict_improvement')
    labels[72:] = rng.integers(0,4096,(8,4025),dtype=np.uint16)
    names.extend('arbitrary_residual_'+str(i) for i in range(8))
    coefficients = rng.integers(0,4096,(count,70),dtype=np.uint16)
    syndromes = rng.integers(0,4096,(count,70),dtype=np.uint16)
    D = rng.integers(0,4096,(count,36),dtype=np.uint16)
    K = rng.integers(0,4096,(count,35),dtype=np.uint16)
    D[:64].fill(0)  # Exercise the weighted phase on every physical position.
    D[64].fill(0); K[64].fill(0)
    D[65].fill(0); D[65,0] = 1
    D[66].fill(0); D[66,:2] = [70,1]
    D[67].fill(0); D[67,:2] = [1,1]
    D[68].fill(0); D[68,:2] = [4095,1]
    for case in (69,70,71):
        polynomial = [1]
        roots = [70]+[71+offset+case for offset in range(34)]
        for root in roots:
            polynomial = R.product(polynomial,[root,1])
        D[case] = polynomial
    original = np.zeros((count,4095),dtype=np.uint16)
    old_opened = np.zeros_like(original)
    opened = np.zeros_like(original)
    chosen_labels = np.zeros(count,dtype=np.uint16)
    old_T,new_T = np.zeros(count,dtype=np.int64),np.zeros(count,dtype=np.int64)
    prefix_phase = np.zeros(count,dtype=bool)
    scan_phase = np.zeros(count,dtype=bool)
    parity = np.asarray([x.bit_count() & 1 for x in range(4096)],dtype=bool)
    scalar = spec['multiply']
    nonselected = np.asarray(residual,dtype=np.int32)
    for case in range(count):
        frequencies = np.bincount(labels[case],minlength=4096)
        baseline_zero = int(frequencies[0])+1
        scores = frequencies[:64].copy();scores[0] += 1
        chosen = int(np.argmax(np.minimum(scores,7)))
        chosen_labels[case] = chosen
        actual_zeros = int(frequencies[chosen])+int(chosen == 0)
        old_T[case] = 11*(4026-baseline_zero)
        new_T[case] = 11*(4026-actual_zeros)
        assert new_T[case] <= old_T[case]
        if case < 64:
            assert chosen == case
        Gvalues = spec['evaluate']([0]+coefficients[case].tolist())
        original[case] = spec['gram'][Gvalues]
        residual_field = scalar(spec['g'][nonselected], spec['inverse_gram'][labels[case]])
        old_opened[case,nonselected] = spec['gram'][residual_field]
        original[case,nonselected] ^= old_opened[case,nonselected]
        old_opened[case,list(spec['selected'])] = spec['gram'][coefficients[case]]
        opened[case] = old_opened[case]
        opened[case,nonselected] = labels[case] ^ chosen
        correction = scalar(spec['inverse_gram'][chosen], spec['g_coefficients'])
        combined = spec['gram'][coefficients[case] ^ correction]
        prefix_phase[case] = np.logical_xor.reduce(parity[combined & syndromes[case]])
        locator_values = spec['evaluate'](D[case])
        value_values = spec['evaluate'](K[case])
        weighted = scalar(value_values, scalar(spec['factors'],spec['g']))
        mask_values = np.zeros(4095,dtype=np.uint16)
        mask_values[nonselected] = labels[case] ^ chosen
        mask_values[spec['pivot']] = chosen
        terms = parity[mask_values & weighted] & (locator_values == 0)
        scan_phase[case] = np.logical_xor.reduce(terms)
    assert list(chosen_labels[64:72]) == [0,63,0,0,1,3,0,1]
    probes = (residual[0],residual[len(residual)//2],residual[-1])
    pair_phase = prefix_phase.copy()
    syndrome_bits = bits(syndromes)
    for triple in PROBE_TRIPLES:
        pair_phase ^= syndrome_bits[triple[0]] & syndrome_bits[triple[1]] & syndrome_bits[triple[2]]
    for position,bit,qubit in zip(probes,PROBE_BITS,PROBE_SYNDROMES):
        pair_phase ^= ((opened[:,position] >> bit) & 1).astype(bool) & syndrome_bits[qubit]
    retained = count if limit is None else limit
    assert 0 < retained <= count
    return dict(names=names[:retained],syndromes=syndromes[:retained],
        original=original[:retained],old_opened=old_opened[:retained],opened=opened[:retained],
        labels=chosen_labels[:retained],prefix_phase=prefix_phase[:retained],pair_phase=pair_phase[:retained],
        scan_phase=scan_phase[:retained],old_T=old_T[:retained],new_T=new_T[:retained],
        D=D[:retained],K=K[:retained],probes=probes,
        gauge_dirty=rng.integers(0,2,(25,retained),dtype=np.int8).astype(bool),
        scan_dirty=rng.integers(0,2,(13,retained),dtype=np.int8).astype(bool))


def dirty_reusable_classical(builder):
    """Explicitly dirty/free322 work bits, to test initial stores on reuse."""
    work = builder.alloc_bits(322)
    builder.bit_store(work,True)
    builder.free(work)
    return 322


def physical_indices(circuit, wires):
    lookup = {km.b(i):i for i in range(circuit.num_bits)}
    return [lookup[wire] for wire in wires]


def finish_metrics(builder, circuit, path, panel, record, *, source_expected, probes=0):
    assert builder.num_allocated_qubits == RETAINED_Q
    assert circuit.num_bits == MASK_BITS+322
    assert circuit.operation_statistics().num_toffoli_like == probes
    assert circuit.num_qubits == RETAINED_Q
    assert len(circuit) == source_expected
    circuit.to_file(path,format='kmb')
    return dict(panel=panel,sha256=sha(path),bytes=path.stat().st_size,
        instructions=len(circuit),source_expected_instructions=source_expected,
        Q=circuit.num_qubits,classical_bits=circuit.num_bits,
        selector_peak_classical_bits=322,gauge_additional_qubits=0,
        static_T=probes,probe_T=probes,
        pivot_indices=physical_indices(circuit,record.pivot),
        selector_ledger=record.selector_ledger,
        operations=dict(circuit.operation_statistics()))


def build_gauge(paths, data, ledger):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(RETAINED_Q)
    sr = builder.create_quantum_register(840,'syndromes')
    builder.create_quantum_register(25,'dirty')
    er = builder.create_classical_register(MASK_BITS,'masks')
    syndromes = [sr[12*i:12*(i+1)] for i in range(70)]
    masks = [er[12*i:12*(i+1)] for i in range(4095)]
    preparation = dirty_reusable_classical(builder)
    record = New.open_gauge(builder,syndromes,masks,
        stage=lambda row: print(json.dumps(row,sort_keys=True),flush=True))
    prefix = builder.finish_circuit()
    metrics = [finish_metrics(builder,prefix,paths[0],'gauge_prefix',record,
        source_expected=preparation+ledger['full_gauge_prefix_instructions'])]
    del prefix
    gc.collect()
    for triple in PROBE_TRIPLES:
        builder.ccz(*(sr[index] for index in triple))
    for point,bit,index in zip(data['probes'],PROBE_BITS,PROBE_SYNDROMES):
        builder.cz(masks[point][bit],sr[index])
    closure = New.close_gauge(builder,masks,record)
    pair = builder.finish_circuit()
    metrics.append(finish_metrics(builder,pair,paths[1],'gauge_pair',record,
        source_expected=preparation+ledger['full_gauge_pair_instructions']+5,
        probes=len(PROBE_TRIPLES)))
    assert record.closed and closure['all_owned_classical_bits_retired_zero']
    return metrics


def build_scan(path, ledger):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(RETAINED_Q+10)
    dr = builder.create_quantum_register(432,'D')
    kr = builder.create_quantum_register(420,'K')
    builder.create_quantum_register(13,'dirty')
    er = builder.create_classical_register(MASK_BITS,'masks')
    D = [dr[12*i:12*(i+1)] for i in range(36)]
    K = [kr[12*i:12*(i+1)] for i in range(35)]
    masks = [er[12*i:12*(i+1)] for i in range(4095)]
    preparation = dirty_reusable_classical(builder)
    record = New.open_transport(builder,masks)
    front = builder.finish_circuit()
    assert len(front) == preparation+ledger['transport_prefix_instructions']
    assert front.operation_statistics().num_toffoli_like == 0
    del front
    gc.collect()
    scan = New.emit_scan(builder,D,K,masks,record,
        stage=lambda row: print(json.dumps(row,sort_keys=True),flush=True))
    New.close_transport(builder,masks,record)
    circuit = builder.finish_circuit()
    assert builder.num_allocated_qubits == RETAINED_Q
    assert circuit.num_qubits == RETAINED_Q+10
    assert circuit.num_bits == MASK_BITS+322
    assert circuit.operation_statistics().num_toffoli_like == scan['static_T'] == 44286
    assert scan['point_tests'] == 4026 and scan['full_cycle'] and record.closed
    circuit.to_file(path,format='kmb')
    return dict(panel='transport_scan_pair',sha256=sha(path),bytes=path.stat().st_size,
        Q=circuit.num_qubits,classical_bits=circuit.num_bits,instructions=len(circuit),
        static_T=44286,pivot_indices=physical_indices(circuit,record.pivot),
        scan=scan,selector_ledger=record.selector_ledger,
        scan_instructions=len(circuit)-preparation-ledger['transport_prefix_instructions']-ledger['transport_close_instructions'],
        operations=dict(circuit.operation_statistics()))


def inspect_result(sim,circuit,expected,pivot,expected_label,phase,*,classical_clean):
    errors = {}
    for name,wanted in expected.items():
        actual = sim.read_across_shots(circuit.register_data[name])
        mismatch = np.any(actual != wanted,axis=0)
        if np.any(mismatch):
            errors[name] = np.flatnonzero(mismatch).tolist()
    pivot_actual = sim.read_across_shots([km.b(i) for i in pivot])
    pivot_wanted = bits(np.asarray(expected_label,dtype=np.uint16).reshape(-1,1))
    bad_pivot = np.any(pivot_actual != pivot_wanted,axis=0)
    if classical_clean:
        scratch = [km.b(i) for i in range(MASK_BITS,circuit.num_bits) if i not in pivot]
        bad_classical = np.any(sim.read_across_shots(scratch),axis=0)
    else:
        # Native scan HMR masks can reuse retired histogram bits. They are
        # not still owned by the selector. The live pivot must still reset.
        bad_classical = np.zeros(len(phase),dtype=bool)
    extra_q = [km.q(i) for i in range(RETAINED_Q,circuit.num_qubits)]
    bad_quantum = (np.any(sim.read_across_shots(extra_q),axis=0) if extra_q
                   else np.zeros(len(phase),dtype=bool))
    bad_phase = sim.read_phase_flipped_across_shots() != phase
    return dict(input_or_value_errors=errors,pivot_errors=np.flatnonzero(bad_pivot).tolist(),
        adaptive_classical_scratch_errors=np.flatnonzero(bad_classical).tolist(),
        quantum_scratch_errors=np.flatnonzero(bad_quantum).tolist(),
        phase_errors=np.flatnonzero(bad_phase).tolist(),
        all_retired_classical_bits_checked=classical_clean)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit-cases',type=int)
    parser.add_argument('--batch-size',type=int,default=80)
    parser.add_argument('--keep-circuits',action='store_true')
    args = parser.parse_args()
    assert __debug__ and sys.version_info[:2] == (3,13) and args.batch_size > 0
    assert args.limit_cases is None or 0 < args.limit_cases <= FULL_CASES
    output = args.output.resolve()
    assert output.is_relative_to(HERE/'runs') and not output.exists()
    assert all(sha(ROOT/name) == wanted for name,wanted in OLD_SOURCE_PINS.items())
    assert sha(CERTIFICATE) == CERTIFICATE_SHA
    certificate = json.loads(CERTIFICATE.read_bytes())
    exact = next(row for row in certificate['rows'] if row['candidates'] == 64)
    assert certificate['status'] == 'EXACT_FINITE_OCCUPANCY_PAPER_CERTIFICATE_NOT_NATIVE'
    assert exact['exact_expected_T_saving']['decimal_lower'] == '21.650726134792'
    output.mkdir(parents=True)
    started = time.monotonic()
    sources = dict(OLD_SOURCE_PINS)
    for path in (Path(__file__),Path(New.__file__),CERTIFICATE):
        sources[str(path.relative_to(ROOT))] = sha(path)
    report = dict(status='RUNNING_ADAPTIVE64_COMPONENT',source_sha256=sources,
        fixture_seed=FIXTURE_SEED,seeds=list(SEEDS),runs=[],
        native_scope='Separate gauge and arbitrary-polynomial scan components; no joined decoder or official price.',
        population_draws=0,population_event_changed=False,
        old_selected_sources_modified=False,native_components_only=True,
        expectation_certificate_sha256=CERTIFICATE_SHA,
        exact_uniform_mask_saving=exact['exact_expected_T_saving'],
        initial_classical_store_addendum=129,
        official_mean_T=None,banked_whole_decoder_gain=None)
    paths = [[output/f'{name}-{suffix}.kmb' for name in ('gauge-prefix','gauge-pair','transport-scan')]
             for suffix in ('a','b')]
    try:
        spec = oracle_geometry()
        data = make_fixtures(spec,args.limit_cases)
        ledger = New.source_ledger()
        count = len(data['names'])
        report.update(cases=count,full_cases=FULL_CASES,all64_winners_checked=count>=64,
            adversarial_policy_cases_checked=count>=72,source_ledger=ledger,
            oracle='Independent field Horner/trace Gram, integer capped counts, complete scan polynomial evaluation',
            fixture_array_sha256={name:array_sha(data[name]) for name in
                ('syndromes','original','old_opened','opened','labels','prefix_phase','pair_phase','scan_phase','D','K')},
            fixture_labels=data['names'],selected_labels=data['labels'].tolist(),
            per_case_old_scan_T=data['old_T'].tolist(),per_case_new_scan_T=data['new_T'].tolist(),
            pointwise_no_scan_T_loss=bool(np.all(data['new_T'] <= data['old_T'])))
        atomic_json(output/'report.json',report)
        builds = []
        for triple in paths:
            metrics = build_gauge(triple[:2],data,ledger)
            gc.collect()
            metrics.append(build_scan(triple[2],ledger))
            builds.append(metrics)
            gc.collect()
        assert builds[0] == builds[1], 'Two native component builds differ'
        report['two_identical_builds'] = True
        report['builds'] = builds[0]
        for panel,path,metric in zip(('gauge_prefix','gauge_pair','transport_scan_pair'),paths[0],builds[0]):
            circuit = km.Circuit.from_file(path,format='kmb')
            for offset in range(0,count,args.batch_size):
                end = min(count,offset+args.batch_size)
                part = slice(offset,end)
                scan = panel == 'transport_scan_pair'
                initial = ({'D':bits(data['D'][part]),'K':bits(data['K'][part]),
                            'dirty':data['scan_dirty'][:,part], 'masks':bits(data['old_opened'][part])}
                           if scan else
                           {'syndromes':bits(data['syndromes'][part]),
                            'dirty':data['gauge_dirty'][:,part], 'masks':bits(data['original'][part])})
                expected = dict(initial)
                if panel == 'gauge_prefix':
                    expected['masks'] = bits(data['opened'][part])
                phase = data['scan_phase' if scan else 'prefix_phase' if panel=='gauge_prefix' else 'pair_phase'][part]
                label = data['labels'][part] if panel=='gauge_prefix' else np.zeros(end-offset,dtype=np.uint16)
                expected_T = int(np.sum(data['new_T'][part])) if scan else metric['static_T']*(end-offset)
                for seed in SEEDS:
                    simulator = km.Simulator(batch_size=end-offset,seed=seed,counting_operations=True)
                    simulator.use_same_registers_as(circuit)
                    for name,value in initial.items():
                        simulator.write_across_shots(circuit.register_data[name],value)
                    simulator.do(circuit)
                    checked = inspect_result(simulator,circuit,expected,metric['pivot_indices'],label,phase,
                                             classical_clean=not scan)
                    row = dict(panel=panel,offset=offset,cases=end-offset,seed=seed,**checked,
                        actual_total_T=simulator.operation_statistics().num_toffoli_like,
                        independently_expected_total_T=expected_T)
                    report['runs'].append(row)
                    report['elapsed_seconds'] = time.monotonic()-started
                    atomic_json(output/'report.json',report)
                    print(json.dumps(row,sort_keys=True),flush=True)
                    assert not any(checked[key] for key in ('input_or_value_errors','pivot_errors',
                        'adaptive_classical_scratch_errors','quantum_scratch_errors','phase_errors')),row
                    assert row['actual_total_T'] == expected_T,row
                    del simulator
                    gc.collect()
            del circuit
            gc.collect()
        assert all(sha(ROOT/name) == wanted for name,wanted in sources.items())
        report['status'] = ('PASS_NATIVE_ADAPTIVE64_GAUGE_AND_SCAN_COMPONENTS' if count==FULL_CASES
                            else 'PASS_NATIVE_ADAPTIVE64_REDUCED_FIXTURE_SMOKE')
        report['gauge_additional_quantum_bits'] = 0
        report['maximum_adaptive_classical_bits'] = 322
        report['original_masks_restored'] = True
        report['joined_decoder_and_officials_required'] = True
    except BaseException as error:
        report['status'] = 'FAIL_OR_INTERRUPTED_ADAPTIVE64_COMPONENT'
        report['failure'] = repr(error)
        report['elapsed_seconds'] = time.monotonic()-started
        atomic_json(output/'report.json',report)
        raise
    report['elapsed_seconds'] = time.monotonic()-started
    atomic_json(output/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','source_sha256')},sort_keys=True),flush=True)
    if not args.keep_circuits:
        for triple in paths:
            for path in triple:
                path.unlink()


if __name__ == '__main__':
    main()
