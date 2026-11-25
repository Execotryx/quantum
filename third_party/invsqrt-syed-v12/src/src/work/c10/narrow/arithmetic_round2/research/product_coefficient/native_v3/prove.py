#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Bounded exact native proof of accepted AR005 with all seed/product HMRs."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import hashlib
import json
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
OWN = HERE.parent
NARROW = HERE.parents[3]
assert resource.getrlimit(resource.RLIMIT_AS)[1] == 512 * 1024 ** 2, 'Fresh strict guard required.'
resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
AUTH = NARROW / 'arithmetic_round2/receipts/PRODUCT_V3_PAPER_ACCEPTED.json'
AUTH_SHA = '72fe5dcd5afb57baea23099619bcec05d4ca738a6787d289bd0badfb0ec6b80f'
assert hashlib.sha256(AUTH.read_bytes()).hexdigest() == AUTH_SHA
assert json.loads(AUTH.read_text())['native_build_authorized'] is True
for row in json.loads((HERE / 'SOURCE_READY.json').read_text())['files']:
    raw = (NARROW / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
inherited = json.loads((NARROW / 'native/candidate07/INPUTS.json').read_text())['files']
assert len(inherited) == 304
for row in inherited:
    raw = (NARROW / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
sys.path[:0] = [str(NARROW / 'native/candidate01'), str(OWN), str(HERE)]
import common
import lifecycle as baseline
from branch_prover import Program, generated_text
from fourier_resource_expectation import exact_expectation
from component_text_proof import prove_native_text
from adapter import product_inverse
import numpy as np

km, array = common.km, common.array
COUNT = 4096 * 1024
D_TABLE = np.asarray(common.MODEL['D'], dtype=np.int64)
SEED_TABLE = np.asarray(common.MODEL['U0'], dtype=np.int64)


def restore_fixture_layout(builder, current, original):
    """Proof-only Clifford restoration of arbitrary-length input metadata."""
    current, original = list(current), list(original)
    n = len(current)
    assert n == len(original) == 38
    assert len(set(current)) == len(set(original)) == n
    assert builder.num_allocated_qubits == n
    spare = list(builder.alloc_qubits(48 - n))
    all_wires = set(current + spare)
    assert len(all_wires) == 48 and set(original) <= all_wires
    swaps = []
    for bit, target in enumerate(original):
        source = current[bit]
        if source == target:
            continue
        builder.swap(source, target)
        swaps.append((str(source), str(target)))
        for other in range(bit + 1, n):
            if current[other] == target:
                current[other] = source
        current[bit] = target
    assert current == original
    builder.free(array(sorted(all_wires - set(original), key=str)))
    assert builder.num_allocated_qubits == n
    return swaps


def seed_records(token):
    return tuple(tuple(sorted(debt.measurements.items())) for debt in token.rows)


def build(**negative):
    b = km.CircuitBuilder()
    b.set_max_qubits(48)
    D = list(b.alloc_qubits(13))
    h = list(b.alloc_qubits(10))
    low = list(b.alloc_qubits(4))
    inputs = D + h + low
    spectators = list(b.alloc_qubits(11))
    idle = b.alloc_qubits(1)[0]
    # v4, R, raw_a5 and the eight other entry spectators are arbitrary.
    v = low + [spectators[0], None, None, None, spectators[1], None, spectators[2], None]
    assert b.num_allocated_qubits == 39 and len(v) == 12
    seed, stoken = baseline.seed_forward(b, v, D)
    records = seed_records(stoken)
    assert len(stoken.rows) == 3 and sum(map(len, records)) == 6
    assert b.num_allocated_qubits == 45
    seed_prefix = b.finish_circuit()
    word, ptoken = baseline.product_forward(b, D, seed, h)
    product_prefix = b.finish_circuit()
    b.free(idle)
    assert b.num_allocated_qubits == 44
    dirty = low + spectators
    trace = []
    recovered_seed, recovered_h = product_inverse(
        b, v, D, word, ptoken, dirty, baseline=baseline, trace=trace, **negative)
    assert recovered_seed == seed and recovered_h == h
    assert b.num_allocated_qubits == 44 and v[3] is not None
    assert seed_records(stoken) == records and all(not x.consumed for x in stoken.rows)
    assert all(x.consumed and not x.measurements for x in ptoken.rows)
    baseline.seed_cleanup(b, v, D, recovered_seed, stoken)
    assert all(x.consumed and not x.measurements for x in stoken.rows)
    assert b.num_allocated_qubits == 38
    swaps = restore_fixture_layout(b, D + h + v[:4] + spectators, inputs + spectators)
    circuit = common.with_registers(b.finish_circuit(), dict(inputs=inputs, spectators=spectators))
    assert circuit.num_qubits == 48
    return dict(circuit=circuit, inputs=inputs, spectators=spectators,
                seed_prefix=seed_prefix, product_prefix=product_prefix,
                seed=seed, word=word, trace=trace, layout_swaps=swaps,
                current_v3_before_layout=str(v[3]), original_v3=str(low[3]))


def values(indices):
    index = np.asarray(indices, dtype=np.uint64)
    assert np.all(index < COUNT)
    v = (index >> np.uint64(10)).astype(np.int64)
    h = index & np.uint64(1023)
    words = D_TABLE[v].astype(np.uint64) | (h << np.uint64(13)) | ((v.astype(np.uint64) & 15) << np.uint64(23))
    return words, v, h


def bit_functions(words, width=27):
    return [int.from_bytes(np.packbits(((words >> np.uint64(i)) & 1).astype(np.uint8),
                                      bitorder='little').tobytes(), 'little')
            for i in range(width)]


def bits(words, width):
    return ((np.asarray(words, dtype=np.uint64)[None, :] >>
             np.arange(width, dtype=np.uint64)[:, None]) & 1).astype(bool)


def read(sim, wires):
    return (sim.read_across_shots(array(wires)).astype(np.uint64) <<
            np.arange(len(wires), dtype=np.uint64)[:, None]).sum(axis=0)


def product_value(v, h):
    """Independent finite-width signed-row value, valid for every h pattern."""
    C = 2 * D_TABLE[v]
    q = h.astype(np.int64) ^ 512
    value = SEED_TABLE[v].copy()
    total = np.zeros(len(v), dtype=np.int64)
    for i in range(10):
        shift = 8 - i
        term = ((C + (1 << (shift - 1))) >> shift) if shift > 0 else C if shift == 0 else 2 * C + 1
        total += (2 * ((q >> i) & 1) - 1) * term
    value -= total // 2
    return ((value + 32768) & 65535).astype(np.uint64)


def native_diagnostics(fixture):
    checks = []
    root = np.tile(np.arange(4096, dtype=np.uint64), 2)
    residual = (np.arange(8192, dtype=np.uint64) * 317 + 29) & 1023
    indices = (root << 10) | residual
    words, v, h = values(indices)
    expected_word = product_value(v, h)
    expected_seed = (SEED_TABLE[v] & 63).astype(np.uint64)
    for random_seed in range(4):
        sim = km.Simulator(batch_size=256, counting_operations=True, seed=random_seed)
        front_seed = km.Simulator(batch_size=256, seed=random_seed + 101)
        front_product = km.Simulator(batch_size=256, seed=random_seed + 201)
        for start in range(0, 8192, 256):
            w = words[start:start + 256]
            ss = (np.arange(start, start + 256, dtype=np.uint64) * 4051 + random_seed * 1771) & 2047
            for obj in (sim, front_seed, front_product):
                obj.clear_for_shot()
                obj.write_across_shots(array(fixture['inputs']), bits(w, 27))
                obj.write_across_shots(array(fixture['spectators']), bits(ss, 11))
            front_seed.do(fixture['seed_prefix'])
            assert np.array_equal(read(front_seed, fixture['seed']), expected_seed[start:start + 256]), 'Seed value mismatch.'
            front_product.do(fixture['product_prefix'])
            assert np.array_equal(read(front_product, fixture['word']), expected_word[start:start + 256]), 'Product value mismatch.'
            sim.do(fixture['circuit'])
            assert np.array_equal(read(sim, fixture['inputs']), w)
            assert np.array_equal(read(sim, fixture['spectators']), ss)
            kept = set(fixture['inputs'] + fixture['spectators'])
            scratch = [km.q(i) for i in range(fixture['circuit'].num_qubits) if km.q(i) not in kept]
            assert not sim.read_across_shots(array(scratch)).any()
            assert all(sim.read_shot_phase(i) % 2 == 0 for i in range(256))
        checks.append(dict(seed=random_seed, shots=8192, all4096_roots_covered_twice=True,
                           status='PASS', sampled_mean_Toffolis=sim.operation_statistics().num_toffoli_like / 8192))
    return checks


def write_atomic(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def main():
    began = time.monotonic()
    out = HERE / 'result'
    out.mkdir(exist_ok=False)
    fixture = build()
    text = generated_text(fixture['circuit'])
    fixture['circuit'].to_file(str(out / 'seed_product_v3_roundtrip.kmb'), format='kmb')
    (out / 'seed_product_v3_roundtrip.kmx').write_text(text)
    expectation = exact_expectation(text)
    assert expectation['mean_numeric'] == dict(toffoli_like=246.0, T=0.0, generic_rotations=0.0), expectation
    words, _, _ = values(np.arange(1024, dtype=np.uint64))
    diagnostic = prove_native_text(text, bit_functions(words), 1024)
    print(json.dumps(dict(event='diagnostic1024_passed', seconds=diagnostic['seconds'],
                          maximum_terms=diagnostic['maximum_polynomial_terms'])), flush=True)
    words, _, _ = values(np.arange(65536, dtype=np.uint64))
    truths = bit_functions(words)
    negatives = []
    cases = [('omitted_new_v3_phase', dict(omit_v3_phase=True), 'phase'),
             ('omitted_old_row9_carry13_phase', dict(omit_original_debt=(9, 13)), 'phase'),
             ('omitted_recovery_linear_v2', dict(omit_linear_c=True), 'data')]
    for label, kwargs, kind in cases:
        bad = generated_text(build(**kwargs)['circuit'])
        try:
            prove_native_text(bad, truths, 65536)
        except AssertionError as error:
            message = str(error)
            if kind == 'phase':
                assert 'phase' in message.lower(), message
            else:
                assert 'mismatch' in message.lower() or 'reset' in message.lower(), message
            negatives.append(dict(case=label, status='REJECTED_' + kind.upper(), message=message,
                                  data_scratch_preserved_before_phase_check=(kind == 'phase')))
        else:
            raise AssertionError(('Omission negative unexpectedly passed', label))
    chunks, digest, maximum = [], hashlib.sha256(), 0
    for first in range(0, COUNT, 65536):
        last = min(first + 65536, COUNT)
        words, _, _ = values(np.arange(first, last, dtype=np.uint64))
        receipt = prove_native_text(text, bit_functions(words), last - first)
        maximum = max(maximum, receipt['maximum_polynomial_terms'])
        digest.update(words.astype('<u8').tobytes())
        receipt.update(first_chart_index=first, last_chart_index=last - 1)
        chunks.append(receipt)
        write_atomic(out / 'PROOF.partial.json', dict(
            status='PARTIAL_ALL_HMR_MODEL_ROOT_RESIDUAL_PROOF', expected_inputs=COUNT,
            completed_inputs=sum(row['care_inputs'] for row in chunks), chunks=chunks))
        print(json.dumps(dict(event='chunk_passed', first=first, last=last - 1,
                              inputs=last - first, seconds=receipt['seconds'])), flush=True)
    assert sum(row['care_inputs'] for row in chunks) == COUNT
    diagnostics = native_diagnostics(fixture)
    result = dict(
        status='PASS_NATIVE_AR005_COMPONENT_ALL_MODEL_ROOT_RESIDUAL_SPECTATORS_AND_HMR_NOT_FULL_INVSQRT',
        authorization_sha256=AUTH_SHA,
        paper_sha256=hashlib.sha256((OWN / 'V3_SEED_RETIREMENT_PAPER.json').read_bytes()).hexdigest(),
        adapter_sha256=hashlib.sha256((HERE / 'adapter.py').read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256((OWN / 'component_text_proof.py').read_bytes()).hexdigest(),
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_ready_sha256=hashlib.sha256((HERE / 'SOURCE_READY.json').read_bytes()).hexdigest(),
        input_model_sha256=common.MODEL_SHA, inherited_pins_checked=len(inherited),
        inputs=COUNT, first_chart_index=0, last_chart_index=COUNT - 1,
        chart='index=(root_v<<10)|residual_pattern; inputs=D[v]13,h10,raw_v_low4',
        coverage='All4096 model roots times all1024 residual bit patterns; includes every original normalized chart.',
        input_chart_sha256=digest.hexdigest(), chunks=chunks, diagnostic1024=diagnostic,
        arbitrary_spectator_variables=11, all_HMR_outcomes=True,
        all_data_restored=True, all_scratch_zero=True, all_resets_zero=True,
        all10_original_product_CarryDebts_consumed=True,
        all3_seed_CarryDebts_and6_original_records_preserved_until_unchanged_cleanup=True,
        all_original_seed_measurement_signs_repaid=True,
        new_v3_measurement_paid_once=True, fresh_v3_logical_owner=True,
        proof_only_Clifford_final_layout=fixture['layout_swaps'],
        original_v3=fixture['original_v3'], current_v3_before_layout=fixture['current_v3_before_layout'],
        no_new_table_debt=True, no_original_high_root_outcome_changes=True,
        native_HMR_variables=Program(text).measurements,
        maximum_polynomial_terms=maximum, negative_controls=negatives,
        native_diagnostics=diagnostics, exact_native_expectation=expectation,
        production_Q=48, production_entry_data=44, production_inverse_data=43,
        production_return_data=44, trace=fixture['trace'],
        expected_fixture_Toffolis=246, unchanged_seed_E=17.5,
        product_forward_E=103, product_inverse_E=124.5, v3_restoration_E=1,
        product_and_restoration_E=228.5, AR002_comparator_E=238, saving_E=9.5,
        T=0, R=0, phase_model_unchanged=True, protected_blocks_unchanged=True,
        full_invsqrt_native_qualified=False, official_verifier=False,
        elapsed_seconds=time.monotonic() - began,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result['files'] = [dict(path=p.name, bytes=p.stat().st_size,
                            sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                       for p in sorted(out.iterdir()) if p.is_file()]
    write_atomic(out / 'PROOF.json', result)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('chunks', 'exact_native_expectation', 'files')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
