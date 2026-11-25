#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Native normalization94.75: exact data/conditional-HMR ANF proof."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import hashlib
import json
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
NARROW = HERE.parents[3]
assert resource.getrlimit(resource.RLIMIT_AS)[1] == 512*1024**2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for pin in json.loads((HERE/'SOURCE_READY.json').read_text())['files']:
    path = HERE/pin['path']
    assert path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], pin['path']
gate = NARROW/'arithmetic_round2/receipts/NORMALIZATION9475_PAPER_ACCEPTED.json'
assert sha(gate) == 'c6e795219c98415c078c010023004def1a76b2785779955c95d1f4f3c62f40bd'
assert json.loads(gate.read_text())['native_build_authorized'] is True
import normalization9475 as normalization
sys.path.insert(0, str(NARROW/'native/candidate01'))
from common import km, array, with_registers
import numpy as np
from branch_prover import Program, generated_text
from fourier_resource_expectation import exact_expectation
from stage94_normalization_proof import execute, leading_support, symbolic_witness, ZERO, ONE


def build(roundtrip, *, omit_final_helper_fix=False):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(48)
    x = list(builder.alloc_qubits(22))
    flags = list(builder.alloc_qubits(4))
    normalization.forward(builder, x, flags)
    if roundtrip:
        normalization.inverse(builder, x, flags, omit_final_helper_fix=omit_final_helper_fix)
    circuit = with_registers(builder.finish_circuit(), dict(x=x, flags=flags))
    assert builder.num_allocated_qubits == 26
    return circuit, x, flags


def native_symbolic(circuit, roundtrip):
    text = generated_text(circuit)
    program = Program(text)
    assert program.modulus == 2
    assert program.measurements == (30 if roundtrip else 20)
    rows = []
    for leading in range(22):
        inputs, nvars = leading_support(leading)
        initial = dict(zip(program.registers['x'], inputs))
        states, stats = execute(program, initial, {'end': len(program.operations)})
        state, phase = states['end']
        if phase != ZERO:
            raise AssertionError(dict(reason='native_phase', roundtrip=roundtrip,
                                      leading=leading, witness=symbolic_witness(phase, leading)))
        k = (21-leading)//2
        expected = inputs if roundtrip else [ZERO]*(2*k)+inputs[:22-2*k]
        for q, wanted in zip(program.registers['x'], expected):
            assert state[q] == wanted, ('native_data', roundtrip, leading, q)
        for bit, q in enumerate(program.registers['flags']):
            wanted = ZERO if roundtrip or not((k >> bit)&1) else ONE
            assert state[q] == wanted, ('native_flags', roundtrip, leading, q)
        keep = set(program.registers['x']+program.registers['flags'])
        for q in program.quantum_wires:
            if q not in keep:
                assert state[q] == ZERO, ('native_scratch', roundtrip, leading, q)
        rows.append(dict(leading=leading, independent_input_variables=nvars, **stats))
    return dict(status='PASS_EXACT_NATIVE_TEXT_ALL_INPUTS_ALL_ACTIVE_HMR_OUTCOMES',
                support_classes=22, syntactic_HMR_events=program.measurements,
                domain='Every positive x<3*2^20, a strict superset of the official domain',
                original_inputs_covered=3133452,
                conditional_HMR_destinations_follow_exact_inactive_write_semantics=True,
                original_forward_parity_symbols_expanded=True,
                every_active_HMR_assignment_proved=True,
                all_resets_checked_zero=True,
                expected_native_resources=exact_expectation(text), rows=rows)


def bits(values, width):
    return ((values[None, :] >> np.arange(width, dtype=np.uint64)[:, None])&1).astype(bool)


def read(simulator, wires):
    return (simulator.read_across_shots(array(wires)).astype(np.uint64) <<
            np.arange(len(wires), dtype=np.uint64)[:, None]).sum(axis=0)


def simulator_checks(circuit, x, flags):
    checks = []
    count = 32768
    for seed in (0, 1, 2, 3):
        simulator = km.Simulator(batch_size=256, counting_operations=True, seed=seed)
        rng = np.random.default_rng(947500+seed)
        for first in range(0, count, 256):
            xs = rng.integers(1, normalization.MAX_X+1, 256, dtype=np.uint64)
            if first == 0:
                xs[:44] = [value for bit in range(22) for value in
                           (1 << bit, min(normalization.MAX_X, (1 << bit)+1))]
            simulator.clear_for_shot()
            simulator.write_across_shots(array(x), bits(xs, 22))
            simulator.do(circuit)
            assert np.array_equal(read(simulator, x), xs)
            assert not simulator.read_across_shots(array(flags)).any()
            scratch = [km.q(i) for i in range(circuit.num_qubits) if km.q(i) not in x]
            assert not simulator.read_across_shots(array(scratch)).any()
            assert all(simulator.read_shot_phase(i)%2 == 0 for i in range(256))
        stats = simulator.operation_statistics()
        checks.append(dict(seed=seed, shots=count, status='PASS',
                           sampled_mean_Toffolis=stats.num_toffoli_like/count))
    return checks


def save(name, circuit):
    binary, text = HERE/(name+'.kmb'), HERE/(name+'.kmx')
    assert not binary.exists() and not text.exists()
    circuit.to_file(binary, format='kmb')
    text.write_text(generated_text(circuit))
    return dict(kmb_sha256=sha(binary), kmx_sha256=sha(text), actual_native_Q=circuit.num_qubits)


def main():
    began = time.monotonic()
    target = HERE/'NATIVE_PROOF.json'
    assert not target.exists()
    forward, x, flags = build(False)
    fresource = save('normalization9475_forward', forward)
    fproof = native_symbolic(forward, False)
    roundtrip, xx, ff = build(True)
    rresource = save('normalization9475_roundtrip', roundtrip)
    rproof = native_symbolic(roundtrip, True)
    assert forward.num_qubits == roundtrip.num_qubits == 46
    assert fproof['expected_native_resources']['mean_numeric'] == dict(toffoli_like=51.5, T=0.0, generic_rotations=0.0)
    assert rproof['expected_native_resources']['mean_numeric'] == dict(toffoli_like=94.75, T=0.0, generic_rotations=0.0)
    wrong, _, _ = build(True, omit_final_helper_fix=True)
    negative_text = generated_text(wrong)
    negative_path = HERE/'negative_omitted_helper_fix.kmx'
    assert not negative_path.exists()
    negative_path.write_text(negative_text)
    try:
        native_symbolic(wrong, True)
    except AssertionError as error:
        assert 'native_phase' in str(error), ('Negative failed outside its intended phase check', str(error))
        negative = dict(status='REJECTED_MISSING_CONDITIONAL_HELPER_PHASE',
                        error=str(error), native_text_sha256=sha(negative_path))
    else:
        raise AssertionError('Missing helper phase was not rejected.')
    samples = simulator_checks(roundtrip, xx, ff)
    result = dict(status='PASS_NATIVE_NORMALIZATION9475_COMPONENT_NOT_OFFICIAL',
                  component='RN2-D forward parity plus RN2-F eight inverse coordinates',
                  actual_native_Q=46, forward_E=51.5, inverse_expected_E=43.25,
                  roundtrip_expected_E=94.75, saving_vs_original_normalizer_E=2.75,
                  additional_saving_vs_RN2B_E=1.75, T=0, R=0,
                  forward_resource=fresource, roundtrip_resource=rresource,
                  forward_symbolic=fproof, roundtrip_symbolic=rproof,
                  negative_omitted_helper_fix=negative, simulator=samples,
                  source_sha256=sha(HERE/'normalization9475.py'),
                  proof_source_sha256=sha(Path(__file__)),
                  inputs_sha256=sha(HERE/'INPUTS.json'),
                  source_ready_sha256=sha(HERE/'SOURCE_READY.json'),
                  paper_acceptance_sha256=sha(gate),
                  complete_math_certificate_sha256=sha(HERE.parent/'normalization9475_combined/study.json'),
                  all_original_input_owners_restored=True, all_scratch_flags_zero=True,
                  all_active_HMR_transcripts_proved=True,
                  inactive_helper_measurement_destinations_explicitly_initialized=True,
                  inherited_sources_and_modules_unchanged=True,
                  normalization95_fallback_preserved=True,
                  complete_fusion_qualification=False, official_verifier_run=False,
                  seconds=time.monotonic()-began,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, indent=2, default=str)+'\n')
    temporary.replace(target)
    print(json.dumps({key:value for key,value in result.items()
                      if key not in ('forward_symbolic','roundtrip_symbolic')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
