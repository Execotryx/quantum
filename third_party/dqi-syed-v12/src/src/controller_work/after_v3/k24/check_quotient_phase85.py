#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded native panel for the isolated85-T quotient phase.

No production source is rebound. Run only under the team's heavy-job guard.
Both old/new phase and old/new K24 inverse-pair circuits get independent
field oracles, three HMR seeds, exact count checks and two identical builds.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import time
import k24_paths  # noqa: F401
import kickmix as km
import numpy as np
import narrow_field130 as Original
import gf24_nested_norm as Arithmetic
import quotient_phase85 as New
from quantum_reciprocal import bit_matrix

SEEDS = (35201, 35202, 35203)
KINDS = ('phase88', 'phase85', 'inverse472', 'inverse469')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def fixtures(kind, cases, retained):
    rng = np.random.default_rng(202611120015)
    scalar = kind.startswith('phase')
    values = np.arange(cases, dtype=np.int64) % 4096
    if scalar:
        masks = rng.integers(0, 4096, (3, cases), dtype=np.int64)
        targets = rng.integers(0, 4096, (3, cases), dtype=np.int64)
        masks[:, ::13] = 0
        targets[:, ::17] = 0
        arrays = dict(source=bit_matrix(values, 12),
                      dirty=rng.integers(0, 2, (retained-48, cases), dtype=np.int8).astype(bool))
        for j in range(3):
            arrays[f'value{j}'] = bit_matrix(targets[j], 12)
            arrays[f'mask{j}'] = bit_matrix(masks[j], 12)
        phases = []
        for i, value in enumerate(values):
            inv = Arithmetic.FIELD.invert(int(value)) if value else 0
            terms = [Arithmetic.FIELD.mul(int(targets[j, i]),
                        Arithmetic.FIELD.pow(inv, power)) for j, power in enumerate((1, 2, 4))]
            phases.append(sum((term & int(masks[j, i])).bit_count()
                              for j, term in enumerate(terms)) & 1)
        return arrays, np.array(phases, dtype=bool), None
    # Exercise zero and both coordinate axes, including source low half=0.
    values = rng.integers(0, 1 << 24, cases, dtype=np.int64)
    values[::4] = np.arange(cases, dtype=np.int64)[::4] % 4096
    values[1::4] = (1 + np.arange(cases, dtype=np.int64)[1::4] % 4095) << 12
    values[0] = 0
    masks = rng.integers(0, 1 << 24, cases, dtype=np.int64)
    inverses = np.array([Arithmetic.inverse24(int(value)) for value in values], dtype=np.int64)
    phases = np.array([(int(value)&int(mask)).bit_count() & 1
                       for value, mask in zip(inverses, masks)], dtype=bool)
    phases ^= (((inverses >> 2)&1) & ((inverses >> 13)&1)).astype(bool)
    arrays = dict(source=bit_matrix(values, 24), probe=bit_matrix(masks, 24),
                  dirty=rng.integers(0, 2, (retained-24, cases), dtype=np.int8).astype(bool))
    return arrays, phases, inverses


def build(kind, retained):
    builder = km.CircuitBuilder()
    if kind.startswith('phase'):
        source = builder.create_quantum_register(12, 'source')
        words = [builder.create_quantum_register(12, f'value{j}') for j in range(3)]
        masks = [builder.create_classical_register(12, f'mask{j}') for j in range(3)]
        builder.create_quantum_register(retained-48, 'dirty')
        operation = Original.phase_quotients12 if kind == 'phase88' else New.phase_quotients12
        operation(builder, source, list(zip(words, masks, (1, 2, 4))))
        expected, helpers = (88 if kind == 'phase88' else 85), 12
        prefix = None
    else:
        source = builder.create_quantum_register(24, 'source')
        probe = builder.create_classical_register(24, 'probe')
        builder.create_quantum_register(retained-24, 'dirty')
        record = Arithmetic.inverse_deferred(builder, source)
        prefix = builder.finish_circuit()
        assert prefix.operation_statistics().num_toffoli_like == 192
        builder.cz(probe, source)
        builder.cz(source[2], source[13])
        operation = Arithmetic.inverse_closed if kind == 'inverse472' else New.inverse_closed
        operation(builder, source)
        Arithmetic.repay_source_masks(builder, source, record)
        assert record.closed
        expected, helpers = (472 if kind == 'inverse472' else 469), 24
    circuit = builder.finish_circuit()
    assert builder.num_allocated_qubits == retained
    assert circuit.operation_statistics().num_toffoli_like == expected
    assert circuit.num_qubits <= retained+helpers
    metrics = dict(static_T=expected, Q=circuit.num_qubits,
                   helpers=circuit.num_qubits-retained, retained=retained,
                   instructions=len(circuit), uniform_HMR_mean_T=expected-4/64,
                   mean_scope='One final GF64 inverse-phase mask; fresh uniform six bits.')
    return circuit, prefix, metrics


def simulate(circuit, arrays, phases, retained, seed, prefix_inverse=None):
    cases = arrays['source'].shape[1]
    sim = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    errors = {}
    for name, bits in arrays.items():
        expected = bit_matrix(prefix_inverse, 24) if name == 'source' and prefix_inverse is not None else bits
        mismatches = np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name]) != expected, axis=0)).tolist()
        if mismatches:
            errors[name] = mismatches
    scratch_bad = bool(sim.read_across_shots([km.q(i) for i in range(retained, circuit.num_qubits)]).any())
    phase_bad = None if prefix_inverse is not None else np.flatnonzero(sim.read_phase_flipped_across_shots() != phases).tolist()
    row = dict(seed=seed, cases=cases, input_errors=errors, scratch_errors=scratch_bad,
               phase_errors=phase_bad, prefix_value_only=prefix_inverse is not None,
               observed_mean_T=sim.operation_statistics().num_toffoli_like/cases)
    assert not errors and not scratch_bad and not phase_bad, row
    del sim
    gc.collect()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=4096)
    parser.add_argument('--retained', type=int, default=865)
    parser.add_argument('--components', nargs='+', choices=KINDS, default=list(KINDS))
    args = parser.parse_args()
    assert args.cases > 0 and args.retained >= 48
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists()
    sources = [Path(__file__), Path(New.__file__), Path(Original.__file__),
               Path(Arithmetic.__file__), Path(New.Nested.__file__)]
    report = dict(status='IN_PROGRESS_ISOLATED_QUOTIENT_PHASE85', cases=args.cases,
                  source_sha256={str(path.resolve()):sha(path) for path in sources},
                  new_population_draws=False, production_integration=False, rows=[])
    save(args.output/'report.json', report)
    started = time.monotonic()
    for kind in args.components:
        arrays, phases, inverses = fixtures(kind, args.cases, args.retained)
        paths = [args.output/f'{kind}-{label}.kmb' for label in ('a', 'b')]
        circuit, prefix, metrics = build(kind, args.retained)
        circuit.to_file(paths[0], format='kmb')
        runs = [simulate(circuit, arrays, phases, args.retained, seed) for seed in SEEDS]
        if prefix is not None:
            runs += [simulate(prefix, arrays, phases, args.retained, seed, inverses) for seed in SEEDS]
        del circuit, prefix
        gc.collect()
        again, prefix, again_metrics = build(kind, args.retained)
        again.to_file(paths[1], format='kmb')
        assert sha(paths[0]) == sha(paths[1]) and metrics == again_metrics
        row = dict(status='PASS_ISOLATED_COMPONENT', component=kind, metrics=metrics,
                   sha256=sha(paths[0]), identical_builds=True, runs=runs,
                   exhaustive_F12_sources=kind.startswith('phase') and args.cases >= 4096)
        report['rows'].append(row)
        save(args.output/'report.json', report)
        del again, prefix
        gc.collect()
    report.update(status='PASS_REQUESTED_QUOTIENT_PHASE85_COMPONENTS',
                  elapsed_seconds=time.monotonic()-started)
    save(args.output/'report.json', report)
    print(json.dumps({key:report[key] for key in ('status','cases','elapsed_seconds')}, sort_keys=True))


if __name__ == '__main__':
    main()
