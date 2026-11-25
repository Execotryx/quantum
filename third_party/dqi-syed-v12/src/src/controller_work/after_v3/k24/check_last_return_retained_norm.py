#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded old/new final-return value, phase, restoration and count panel."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import time
import last_return_retained_norm as New
import kickmix as km
import numpy as np
from quantum_reciprocal import bit_matrix

Old, A = New.Original, New.A
SEEDS = (35301, 35302, 35303)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def fixtures(cases, retained):
    rng = np.random.default_rng(202611120104)
    source = rng.integers(1, 1 << 24, cases, dtype=np.int64)
    for i in range(min(cases, 8190)):
        source[i] = i+1 if i < 4095 else (i-4094) << 12
    value = rng.integers(0, 1 << 24, cases, dtype=np.int64)
    value[::17] = 0
    probe = rng.integers(0, 1 << 24, cases, dtype=np.int64)
    quotient = np.array([A.mul24(int(v), A.inverse24(int(s)))
                         for s, v in zip(source, value)], dtype=np.int64)
    phases = np.array([(int(v)&int(m)).bit_count() & 1
                       for v, m in zip(quotient, probe)], dtype=bool)
    phases ^= (((source >> 2)&1) & ((quotient >> 13)&1)).astype(bool)
    arrays = dict(source=bit_matrix(source, 24), value=bit_matrix(value, 24),
                  probe=bit_matrix(probe, 24),
                  dirty=rng.integers(0, 2, (retained-48, cases), dtype=np.int8).astype(bool))
    return arrays, quotient, phases


def build(retained, candidate):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(retained+24)
    source = builder.create_quantum_register(24, 'source')
    value = builder.create_quantum_register(24, 'value')
    probe = builder.create_classical_register(24, 'probe')
    builder.create_quantum_register(retained-48, 'dirty')
    record = Old.divide_deferred(builder, source, value)
    prefix = builder.finish_circuit()
    assert prefix.operation_statistics().num_toffoli_like == 291
    builder.cz(probe, value)
    builder.cz(source[2], value[13])
    operation = New.restore_with_shared_norm if candidate else Old.restore_with_shared_norm
    operation(builder, source, value, record)
    assert record.closed and builder.num_allocated_qubits == retained
    circuit = builder.finish_circuit()
    static = 643 if candidate else 651
    assert circuit.operation_statistics().num_toffoli_like == static
    assert circuit.num_qubits <= retained+24
    mean = static-84/(1 << 24)-(19/64 if candidate else 27/4096)
    return circuit, prefix, dict(static_T=static, Q=circuit.num_qubits,
        helpers=circuit.num_qubits-retained, instructions=len(circuit),
        prefix_static_T=291, uniform_HMR_mean_T=mean,
        mean_scope='Fresh24-bit head mask and final fresh6/12-bit mask; exact source model.')


def simulate(circuit, arrays, quotient, phases, retained, seed, prefix=False):
    cases = arrays['source'].shape[1]
    sim = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    errors = {}
    for name, bits in arrays.items():
        expected = bit_matrix(quotient, 24) if prefix and name == 'value' else bits
        bad = np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name]) != expected, axis=0)).tolist()
        if bad:
            errors[name] = bad
    scratch = bool(sim.read_across_shots([km.q(i) for i in range(retained, circuit.num_qubits)]).any())
    phase_errors = None if prefix else np.flatnonzero(sim.read_phase_flipped_across_shots() != phases).tolist()
    row = dict(seed=seed, cases=cases, prefix_values_only=prefix, input_errors=errors,
               scratch_errors=scratch, phase_errors=phase_errors,
               observed_mean_T=sim.operation_statistics().num_toffoli_like/cases)
    assert not errors and not scratch and not phase_errors, row
    del sim
    gc.collect()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=8192)
    parser.add_argument('--retained', type=int, default=865)
    args = parser.parse_args()
    assert __debug__ and 0 < args.cases <= 8192 and args.retained >= 48
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True, exist_ok=True)
    # Match selected v3 providers within this isolated checker process only.
    Old.A = A
    Old.Prior = New.Nested
    sources = [Path(__file__), Path(New.__file__), Path(Old.__file__),
               Path(A.__file__), Path(New.Nested.__file__)]
    before = {str(path.resolve()):sha(path) for path in sources}
    report = dict(status='IN_PROGRESS_LAST_RETURN_COMPONENTS', cases=args.cases,
                  source_sha256=before, source_ledger=New.source_ledger(),
                  production_integration=False, new_population_draws=False, rows=[])
    save(args.output/'report.json', report)
    arrays, quotient, phases = fixtures(args.cases, args.retained)
    started = time.monotonic()
    for candidate in (False, True):
        name = 'retained_child_candidate' if candidate else 'nested_reference'
        paths = [args.output/f'{name}-{suffix}.kmb' for suffix in ('a', 'b')]
        circuit, prefix, metrics = build(args.retained, candidate)
        circuit.to_file(paths[0], format='kmb')
        runs = [simulate(circuit, arrays, quotient, phases, args.retained, seed) for seed in SEEDS]
        runs += [simulate(prefix, arrays, quotient, phases, args.retained, seed, True) for seed in SEEDS]
        del circuit, prefix
        gc.collect()
        circuit, prefix, again = build(args.retained, candidate)
        circuit.to_file(paths[1], format='kmb')
        assert sha(paths[0]) == sha(paths[1]) and again == metrics
        report['rows'].append(dict(component=name, status='PASS_ISOLATED_LAST_RETURN',
            metrics=metrics, sha256=sha(paths[0]), identical_builds=True, runs=runs,
            all4095_units_on_both_coordinate_axes=args.cases >= 8190))
        save(args.output/'report.json', report)
        del circuit, prefix
        gc.collect()
    assert before == {str(path.resolve()):sha(path) for path in sources}
    report.update(status='PASS_ISOLATED_LAST_RETURN_COMPONENTS',
                  elapsed_seconds=time.monotonic()-started,
                  no_source_changes_during_test=True)
    save(args.output/'report.json', report)
    print(json.dumps({key:report[key] for key in ('status','cases','elapsed_seconds')}, sort_keys=True))


if __name__ == '__main__':
    main()
