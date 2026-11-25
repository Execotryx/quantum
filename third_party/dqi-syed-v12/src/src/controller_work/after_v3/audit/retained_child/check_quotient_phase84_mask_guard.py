#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded component gate for the whole phase84 zero-mask bypass.

This is a new isolated checker. The unchanged phase85 checker supplies
deterministic fixtures and its independent physical-field oracle only.
No production module is rebound. All native work belongs to the root queue.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import time

import quotient_phase84_mask_guard as New
import check_quotient_phase85 as PriorCheck
import kickmix as km
import numpy as np

Base = New.Base
Original = New.Original
Arithmetic = New.Arithmetic
SEEDS = PriorCheck.SEEDS
KINDS = ('phase85_reference', 'phase84_candidate',
         'inverse469_reference', 'inverse468_candidate')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def public_contraction_check():
    """Compare every nonzero embedded weight with direct field arithmetic.

    The expected columns do not use partial_inverse_product_terms or its
    bilinear tensor. This also checks the source/output-basis orientation.
    """
    field = Arithmetic.FIELD
    rows = Original.quadratic_basis(12)['from_tower']
    checked = 0
    for component in (0, 1):
        for power in (1, 2, 4):
            for weight in range(1, 64):
                tower_word = weight << (6*component)
                embedded = sum(((row & tower_word).bit_count() & 1) << i
                               for i, row in enumerate(rows))
                factor = field.pow(embedded, power)
                expected = tuple(field.mul(1 << i, factor) for i in range(12))
                actual = New.target_mask_rows(component, power, weight)
                assert actual == expected, (component, power, weight, actual, expected)
                assert New._rank(actual) == 12
                checked += 12
    return dict(status='PASS_PUBLIC_CONTRACTION_COLUMNS',
                nonzero_weights=63, components=2, frobenius_powers=[1, 2, 4],
                checked_binary_columns=checked,
                expected_source='Direct physical GF4096 multiplication and tower embedding')


def build(kind, retained):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(retained+24)
    candidate = kind.endswith('candidate')
    prefix = None
    if kind.startswith('phase'):
        source = builder.create_quantum_register(12, 'source')
        values = [builder.create_quantum_register(12, f'value{j}') for j in range(3)]
        masks = [builder.create_classical_register(12, f'mask{j}') for j in range(3)]
        builder.create_quantum_register(retained-48, 'dirty')
        operation = New.phase_quotients12 if candidate else Base.phase_quotients12
        operation(builder, source, list(zip(values, masks, (1, 2, 4))))
        static, helpers = (84 if candidate else 85), 12
        mean = static-(84/(1 << 36) if candidate else 4/64)
        scope = ('Independent uniform supplied36-bit target-mask tuple' if candidate
                 else 'One independent fresh6-bit final HMR mask')
    else:
        source = builder.create_quantum_register(24, 'source')
        probe = builder.create_classical_register(24, 'probe')
        builder.create_quantum_register(retained-24, 'dirty')
        record = Arithmetic.inverse_deferred(builder, source)
        prefix = builder.finish_circuit()
        assert prefix.operation_statistics().num_toffoli_like == 192
        builder.cz(probe, source)
        builder.cz(source[2], source[13])
        operation = New.inverse_closed if candidate else Base.inverse_closed
        operation(builder, source)
        Arithmetic.repay_source_masks(builder, source, record)
        assert record.closed
        static, helpers = (468 if candidate else 469), 24
        mean = static-(84/(1 << 24) if candidate else 4/64)
        scope = ('The two fresh12-bit target HMR masks of the closed inverse' if candidate
                 else 'One independent fresh6-bit final HMR mask')
    circuit = builder.finish_circuit()
    assert builder.num_allocated_qubits == retained
    assert circuit.operation_statistics().num_toffoli_like == static
    assert circuit.num_qubits <= retained+helpers <= retained+24
    return circuit, prefix, dict(static_T=static, Q=circuit.num_qubits,
        retained=retained, helpers=circuit.num_qubits-retained,
        instructions=len(circuit), source_expected_mean_T=mean,
        mean_scope=scope, official_measured_mean=False)


def phase_fixtures(cases, retained, panel):
    assert panel in ('random', 'zero', 'ones')
    arrays, expected, _ = PriorCheck.fixtures('phase85', cases, retained)
    if panel != 'random':
        for j in range(3):
            arrays[f'mask{j}'][:] = panel == 'ones'
        expected = np.zeros(cases, dtype=bool)
        for i in range(cases):
            source = sum(int(bit) << k for k, bit in enumerate(arrays['source'][:, i]))
            inv = Arithmetic.FIELD.invert(source) if source else 0
            for j, power in enumerate((1, 2, 4)):
                value = sum(int(bit) << k for k, bit in enumerate(arrays[f'value{j}'][:, i]))
                mask = sum(int(bit) << k for k, bit in enumerate(arrays[f'mask{j}'][:, i]))
                product = Arithmetic.FIELD.mul(value, Arithmetic.FIELD.pow(inv, power))
                expected[i] ^= bool((product & mask).bit_count() & 1)
    active = np.any(np.concatenate([arrays[f'mask{j}'] for j in range(3)], axis=0), axis=0)
    return arrays, expected, int(np.count_nonzero(active))


def simulate_phase(circuit, arrays, expected, active, retained, seed, candidate):
    cases = arrays['source'].shape[1]
    sim = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    errors = {}
    for name, bits in arrays.items():
        bad = np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name]) != bits, axis=0)).tolist()
        if bad:
            errors[name] = bad
    scratch = bool(sim.read_across_shots([km.q(i) for i in range(retained, circuit.num_qubits)]).any())
    phase_errors = np.flatnonzero(sim.read_phase_flipped_across_shots() != expected).tolist()
    measured = sim.operation_statistics().num_toffoli_like
    exact = 84*active if candidate else None
    row = dict(seed=seed, cases=cases, input_errors=errors, scratch_errors=scratch,
               phase_errors=phase_errors, actual_T=measured,
               exact_fixture_T=exact, nonzero_target_mask_tuples=active,
               observed_fixture_mean_T=measured/cases)
    assert not errors and not scratch and not phase_errors, row
    if exact is not None:
        assert measured == exact, row
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
    assert __debug__ and 0 < args.cases <= 4096 and args.retained >= 48
    assert len(args.components) == len(set(args.components))
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = [Path(__file__), Path(New.__file__), Path(Base.__file__),
               Path(PriorCheck.__file__), Path(Original.__file__),
               Path(Arithmetic.__file__), Path(New.Nested.__file__), Path(New.Unguarded.__file__)]
    before = {str(path.resolve()):sha(path) for path in sources}
    report = dict(status='IN_PROGRESS_RETAINED_CHILD_ZERO_MASK_GUARD',
                  cases=args.cases, seeds=list(SEEDS), source_sha256=before,
                  production_integration=False, official_verifier_run=False,
                  new_population_draws=False, source_ledger=New.source_ledger(), rows=[])
    save(args.output/'report.json', report)
    started = time.monotonic()
    report['public_matrix_audit'] = public_contraction_check()
    save(args.output/'report.json', report)
    for kind in args.components:
        paths = [args.output/f'{kind}-{suffix}.kmb' for suffix in ('a', 'b')]
        circuit, prefix, metrics = build(kind, args.retained)
        circuit.to_file(paths[0], format='kmb')
        runs = []
        if kind.startswith('phase'):
            for panel in ('random', 'zero', 'ones'):
                arrays, phases, active = phase_fixtures(args.cases, args.retained, panel)
                for seed in SEEDS:
                    row = simulate_phase(circuit, arrays, phases, active,
                                         args.retained, seed, kind.endswith('candidate'))
                    row['panel'] = panel
                    runs.append(row)
        else:
            arrays, phases, inverses = PriorCheck.fixtures('inverse469', args.cases, args.retained)
            runs = [PriorCheck.simulate(circuit, arrays, phases, args.retained, seed) for seed in SEEDS]
            runs += [PriorCheck.simulate(prefix, arrays, phases, args.retained, seed, inverses) for seed in SEEDS]
        del circuit, prefix
        gc.collect()
        again, prefix, again_metrics = build(kind, args.retained)
        again.to_file(paths[1], format='kmb')
        assert sha(paths[0]) == sha(paths[1]) and metrics == again_metrics
        report['rows'].append(dict(status='PASS_ISOLATED_COMPONENT', component=kind,
            metrics=metrics, sha256=sha(paths[0]), identical_builds=True, runs=runs,
            exhaustive_F12_sources=kind.startswith('phase') and args.cases == 4096,
            K24_source_scope=('Zero, both coordinate axes and deterministic general fixtures; not exhaustive K24'
                              if not kind.startswith('phase') else None)))
        save(args.output/'report.json', report)
        del again, prefix
        gc.collect()
    assert before == {str(path.resolve()):sha(path) for path in sources}
    report.update(status='PASS_REQUESTED_RETAINED_CHILD_ZERO_MASK_GUARD_COMPONENTS',
                  elapsed_seconds=time.monotonic()-started,
                  no_source_changes_during_test=True)
    save(args.output/'report.json', report)
    print(json.dumps({key:report[key] for key in ('status','cases','elapsed_seconds')}, sort_keys=True))


if __name__ == '__main__':
    main()
