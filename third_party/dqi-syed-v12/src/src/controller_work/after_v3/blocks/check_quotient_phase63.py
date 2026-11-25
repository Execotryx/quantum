#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded native gate for the joint norm/relative-trace phase.

The phase oracle independently reduces the physical degree-twelve field.
The dual-number accumulator is also tested with arbitrary dirty targets.
No accepted source, source binding, or prior component receipt is changed.
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
from pathlib import Path
import time

from accepted_runtime import load, recheck, digest, loaded_sources

RETAINED = 867
PROBE_T = 3
SEEDS = (49191, 50191, 51191)
MODES = ('zero_numerator', 'unit_numerator', 'basis_numerator',
         'arbitrary_numerator', 'zero_denominator')
km = np = Reference = Candidate = Tensor = Accumulate = bit_matrix = None


def field_product(left, right, modulus=0x1053):
    """Oracle long multiplication, independent of all emitter field code."""
    degree = modulus.bit_length()-1
    left, right, result = int(left), int(right), 0
    while right:
        if right & 1:
            result ^= left
        right >>= 1
        left <<= 1
        if left & (1 << degree):
            left ^= modulus
    return result


def inverse(value):
    result, exponent, value = 1, 4094, int(value)
    while exponent:
        if exponent & 1:
            result = field_product(result, value)
        value = field_product(value, value)
        exponent >>= 1
    return result


def absolute_trace(value):
    value, result = int(value), 0
    for _ in range(12):
        result ^= value
        value = field_product(value, value)
    assert result in (0, 1)
    return result


def dual_oracle(left, right):
    a, u = int(left) & 63, int(left) >> 6
    b, v = int(right) & 63, int(right) >> 6
    lo = field_product(a, b, 0x43)
    hi = field_product(a, v, 0x43) ^ field_product(u, b, 0x43)
    return lo | (hi << 6)


def phase_fixtures(per_mode):
    rng = np.random.default_rng(202611111621)
    count = len(MODES)*per_mode
    denominator = np.tile(np.arange(per_mode, dtype=np.int64), len(MODES))
    numerator = rng.integers(0, 4096, count, dtype=np.int64)
    numerator[:per_mode] = 0
    numerator[per_mode:2*per_mode] = 1
    numerator[2*per_mode:3*per_mode] = 1 << (np.arange(per_mode) % 12)
    numerator[3*per_mode:4*per_mode:17] = denominator[3*per_mode:4*per_mode:17]
    denominator[4*per_mode:] = 0
    numerator[4*per_mode:] = np.arange(per_mode)
    phase_mask = rng.integers(0, 4096, count, dtype=np.int64)
    dirty = rng.integers(0, 2, (RETAINED-24, count), dtype=np.int8).astype(bool)
    reciprocal = {int(value): inverse(value) for value in denominator}
    quotient_phase = np.array([
        absolute_trace(field_product(x, reciprocal[int(d)]))
        for d, x in zip(denominator, numerator)], dtype=bool)
    probe = ((denominator & 1) != 0) & ((numerator & 2) != 0) & dirty[0]
    probe ^= ((denominator & 4) != 0) & ((numerator & 8) != 0) & dirty[1]
    probe ^= ((denominator & 16) != 0) & ((numerator & 32) != 0) & dirty[2]
    probe ^= np.array([(int(mask) & int(value)).bit_count() & 1
                       for mask, value in zip(phase_mask, numerator)], dtype=bool)
    arrays = {name: bit_matrix(value, 12) for name, value in
              dict(denominator=denominator, numerator=numerator,
                   phase_mask=phase_mask).items()}
    arrays['dirty'] = dirty
    return arrays, quotient_phase, probe


def tensor_fixtures(count):
    rng = np.random.default_rng(202611111622)
    left = rng.integers(0, 4096, count, dtype=np.int64)
    right = rng.integers(0, 4096, count, dtype=np.int64)
    target = rng.integers(0, 4096, count, dtype=np.int64)
    for index in range(min(count, 144)):
        left[index] = 1 << (index//12)
        right[index] = 1 << (index % 12)
    left[144::31] = 0
    right[145::37] = 0
    phase_mask = rng.integers(0, 4096, count, dtype=np.int64)
    dirty = rng.integers(0, 2, (RETAINED-36, count), dtype=np.int8).astype(bool)
    output = target ^ np.array([dual_oracle(a, b) for a, b in zip(left, right)], dtype=np.int64)
    probe = ((left & 1) != 0) & ((output & 2) != 0) & dirty[0]
    probe ^= ((right & 4) != 0) & ((output & 8) != 0) & dirty[1]
    probe ^= ((output & 16) != 0) & ((left & 32) != 0) & dirty[2]
    probe ^= np.array([(int(mask) & int(value)).bit_count() & 1
                       for mask, value in zip(phase_mask, output)], dtype=bool)
    arrays = {name: bit_matrix(value, 12) for name, value in
              dict(left=left, right=right, target=target, phase_mask=phase_mask).items()}
    arrays['dirty'] = dirty
    return arrays, bit_matrix(output, 12), probe


def build(kind, paired):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(889)
    if kind == 'tensor':
        left = builder.create_quantum_register(12, 'left')
        right = builder.create_quantum_register(12, 'right')
        target = builder.create_quantum_register(12, 'target')
        phase_mask = builder.create_classical_register(12, 'phase_mask')
        dirty = builder.create_quantum_register(RETAINED-36, 'dirty')

        def action():
            Accumulate(builder, left, right, target, Tensor.multiplication_tensor())

        action()
        builder.ccz(left[0], target[1], dirty[0])
        builder.ccz(right[2], target[3], dirty[1])
        builder.ccz(target[4], left[5], dirty[2])
        builder.cz(phase_mask, target)
        base, helpers = 42, 0
    else:
        denominator = builder.create_quantum_register(12, 'denominator')
        numerator = builder.create_quantum_register(12, 'numerator')
        phase_mask = builder.create_classical_register(12, 'phase_mask')
        dirty = builder.create_quantum_register(RETAINED-24, 'dirty')
        provider = Candidate if kind == 'candidate' else Reference

        def action():
            provider.phase_inverse_trace_twelve(builder, denominator, numerator)

        action()
        builder.ccz(denominator[0], numerator[1], dirty[0])
        builder.ccz(denominator[2], numerator[3], dirty[1])
        builder.ccz(denominator[4], numerator[5], dirty[2])
        builder.cz(phase_mask, numerator)
        base, helpers = (63, 18) if kind == 'candidate' else (65, 22)
    if paired:
        action()
    assert builder.num_allocated_qubits == RETAINED
    circuit = builder.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    expected = base*(2 if paired else 1)+PROBE_T
    assert static == expected, (kind, paired, static, expected)
    assert circuit.num_qubits == RETAINED+helpers, (kind, circuit.num_qubits)
    return circuit, dict(static_T=static-PROBE_T, circuit_static_T=static,
                         probe_T=PROBE_T, Q=circuit.num_qubits,
                         retained_Q=RETAINED, helpers=helpers,
                         operations=len(circuit), action_count=2 if paired else 1)


def simulate(circuit, arrays, expected_arrays, phase, seed, metrics):
    count = arrays['dirty'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    bad = {}
    for name, bits in expected_arrays.items():
        observed = sim.read_across_shots(circuit.register_data[name])
        ids = np.flatnonzero(np.any(bits != observed, axis=0)).tolist()
        if ids:
            bad[name] = ids
    scratch_ids = [km.q(i) for i in range(RETAINED, circuit.num_qubits)]
    scratch_bad = bool(sim.read_across_shots(scratch_ids).any()) if scratch_ids else False
    phase_bad = np.flatnonzero(sim.read_phase_flipped_across_shots() != phase).tolist()
    actual = sim.operation_statistics().num_toffoli_like
    expected = count*metrics['circuit_static_T']
    result = dict(seed=seed, cases=count, value_error_case_ids=bad,
                  scratch_errors=scratch_bad, phase_error_case_ids=phase_bad,
                  total_T=actual, independent_expected_total_T=expected,
                  measured_mean_T_excluding_probes=actual/count-PROBE_T)
    assert not bad and not scratch_bad and not phase_bad and actual == expected, result
    del sim
    gc.collect()
    return result


def rejection_panel():
    rejected = []
    for kind in ('same_word', 'one_wire_overlap', 'duplicate_wire', 'classical_word'):
        builder = km.CircuitBuilder()
        left = builder.create_quantum_register(12, 'left')
        right = builder.create_quantum_register(12, 'right')
        if kind == 'same_word':
            right = left
        elif kind == 'one_wire_overlap':
            right = km.array([left[0], *right[1:]])
        elif kind == 'duplicate_wire':
            right = km.array([right[1], *right[1:]])
        else:
            right = builder.create_classical_register(12, 'classical')
        try:
            Candidate.phase_inverse_trace_twelve(builder, left, right)
        except (ValueError, TypeError):
            rejected.append(kind)
        else:
            raise AssertionError(('invalid contract accepted', kind))
        assert builder.num_allocated_qubits == 24
        assert builder.finish_circuit().operation_statistics().num_toffoli_like == 0
    assert len(rejected) == 4
    return rejected


def main():
    global km, np, Reference, Candidate, Tensor, Accumulate, bit_matrix
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--per-mode', type=int, default=4096)
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert __debug__ and 1 <= args.per_mode <= 4096
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a fresh output directory'
    runtime = load()
    km, np = importlib.import_module('kickmix'), importlib.import_module('numpy')
    Reference = importlib.import_module('cubic_inverse130')
    Candidate = importlib.import_module('quotient_phase63')
    Tensor = importlib.import_module('dual64_tensor')
    Accumulate = importlib.import_module('field_tensor').accumulate_product
    bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    pins = {str(Path(module.__file__).resolve()): digest(module.__file__)
            for module in (Reference, Candidate, Tensor)}
    arrays, quotient, probe = phase_fixtures(args.per_mode)
    tensor_arrays, tensor_output, tensor_probe = tensor_fixtures(args.per_mode*len(MODES))
    certificate = Tensor.certificate()
    started = time.monotonic()
    report = dict(status='IN_PROGRESS_JOINT_NORM_QUOTIENT_PHASE_COMPONENT',
                  cases=args.per_mode*len(MODES), per_mode=args.per_mode,
                  fixture_modes=list(MODES), seeds=list(SEEDS),
                  full_denominator_range_per_mode=args.per_mode == 4096,
                  full_numerator_range_at_zero_denominator=args.per_mode == 4096,
                  algebra_certificate=certificate, source_sha256=pins,
                  rejected_contracts=rejection_panel(), rows=[],
                  full_preimage_checked=False, full_DQI_or_official_checked=False)

    def save():
        temporary = args.output/'report.json.tmp'
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        temporary.replace(args.output/'report.json')

    save()
    for kind in ('tensor', 'reference', 'candidate'):
        for paired in (False, True):
            label = f'{kind}-'+('pair' if paired else 'prefix')
            paths = [args.output/f'{label}-{letter}.kmb' for letter in ('a', 'b')]
            circuit, metrics = build(kind, paired)
            circuit.to_file(paths[0], format='kmb')
            sha = digest(paths[0])
            if kind == 'tensor':
                source = tensor_arrays
                expected_arrays = dict(tensor_arrays)
                expected_arrays['target'] = tensor_arrays['target'] if paired else tensor_output
                phase = tensor_probe
            else:
                source = expected_arrays = arrays
                phase = probe if paired else probe ^ quotient
            simulations = [simulate(circuit, source, expected_arrays, phase, seed, metrics)
                           for seed in SEEDS]
            del circuit
            gc.collect()
            second, second_metrics = build(kind, paired)
            second.to_file(paths[1], format='kmb')
            assert digest(paths[1]) == sha and metrics == second_metrics
            del second
            gc.collect()
            report['rows'].append(dict(implementation=kind,
                                       panel='pair' if paired else 'prefix',
                                       metrics=metrics, sha256=sha,
                                       two_identical_builds=True, simulations=simulations))
            save()
            print(json.dumps(dict(stage='panel_passed', label=label, metrics=metrics)), flush=True)
            if not args.keep_circuits:
                for path in paths:
                    path.unlink()
    assert pins == {path: digest(path) for path in pins}
    report.update(status='PASS_NATIVE_JOINT_NORM_QUOTIENT_PHASE_COMPONENT_ONLY',
                  elapsed_seconds=time.monotonic()-started,
                  accepted_source_preservation=recheck(runtime),
                  loaded_sources=loaded_sources(),
                  measured_single_phase_delta_T=-2,
                  measured_helper_delta=-4,
                  full_preimage_static_delta_model=-36,
                  full_preimage_mean_delta_model_exact='-301989870/8388608',
                  full_preimage_delta_is_conditional_on_18_paid_nonzero_mask_branches=True,
                  limitations=['Only the isolated phase and dual accumulator are measured here.',
                               'The component is exact on every input; the 18-call caller has a separately priced classical branch.',
                               'All full preimage, whole decoder, and official results require separate integrations.',
                               'Prior accepted and prepared candidate source bytes remain unchanged.'])
    save()
    print(json.dumps(dict(status=report['status'], elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
