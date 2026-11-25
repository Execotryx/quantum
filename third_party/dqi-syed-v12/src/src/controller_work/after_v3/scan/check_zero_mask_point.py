#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Caller-guarded exhaustive-mask native point-cell qualification.

All 4096 masks are tested on root and nonroot inputs. All 4096 locator
values are additionally tested with zero and all-one masks. Each complete
panel is split into batches, with exact value/phase/restoration/T checks.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
ROOT = WORK.parent
sys.path.insert(0, str(WORK/'after_c5/release_v3'))
from build_release import load_fixed_runtime
load_fixed_runtime()
import integrated_pipeline as Pipeline
Pipeline.configure(Pipeline.Options(True, True, True, True))
sys.path.insert(0, str(HERE))
import zero_mask_scan as New
import kickmix as km
import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def bits(values, width):
    a = np.asarray(values, dtype=np.uint16)
    return ((a[None, :] >> np.arange(width)[:, None]) & 1).astype(bool)


def build(kind):
    b = km.CircuitBuilder()
    b.set_max_qubits(47)
    D = b.create_quantum_register(12, 'D')
    K = b.create_quantum_register(12, 'K')
    b.create_quantum_register(13, 'dirty')
    mask = b.create_classical_register(12, 'mask')
    b.create_classical_register(19, 'classical_dirty')
    ladder = b.alloc_qubits(10)
    (New.point_cell if kind == 'candidate' else New.Base.point_cell)(b, D, K, mask, ladder)
    b.free(ladder)
    assert b.num_allocated_qubits == 37
    circuit = b.finish_circuit()
    assert circuit.num_qubits == 47
    assert circuit.operation_statistics().num_toffoli_like == 11
    return circuit


def fixture_groups():
    all_words = np.arange(4096, dtype=np.uint16)
    rng = np.random.default_rng(202611110947)
    values = rng.integers(0, 4096, 4096, dtype=np.uint16)
    return [
        ('all_masks_root', np.zeros(4096, dtype=np.uint16), values, all_words),
        ('all_masks_nonroot', (1 << (all_words % 12)).astype(np.uint16), values, all_words),
        ('all_locators_zero_mask', all_words, values, np.zeros(4096, dtype=np.uint16)),
        ('all_locators_one_mask', all_words, values, np.full(4096, 4095, dtype=np.uint16)),
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--batch-size', type=int, default=256)
    args = p.parse_args()
    assert 0 < args.batch_size <= 256
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True, exist_ok=True)
    source_paths = [Path(__file__).resolve(), Path(New.__file__).resolve(),
                    Path(New.Base.__file__).resolve(),
                    WORK/'night_schedule/scan10.py',
                    WORK/'work/round2/milestone152/source/narrow_field130.py']
    source_bindings = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    started = time.monotonic()
    circuits = {}
    for kind in ('baseline', 'candidate'):
        c = build(kind)
        target = args.output/(kind+'-a.kmb')
        c.to_file(target, format='kmb')
        circuits[kind] = dict(sha256=digest(target), bytes=target.stat().st_size,
                              Q=c.num_qubits, static_T=11, operations=len(c))
        del c
        gc.collect()
    c = build('candidate')
    second = args.output/'candidate-b.kmb'
    c.to_file(second, format='kmb')
    assert digest(second) == circuits['candidate']['sha256']
    del c
    gc.collect()
    rows = []
    for kind in ('baseline', 'candidate'):
        c = km.Circuit.from_file(args.output/(kind+'-a.kmb'), format='kmb')
        for group, locators, values, masks in fixture_groups():
            for seed in (147, 1147, 2147):
                total = 0
                for start in range(0, 4096, args.batch_size):
                    stop = min(start+args.batch_size, 4096)
                    size = stop-start
                    rng = np.random.default_rng(202611110948+start)
                    initial = dict(D=bits(locators[start:stop], 12),
                                   K=bits(values[start:stop], 12),
                                   mask=bits(masks[start:stop], 12),
                                   dirty=rng.integers(0, 2, (13, size), dtype=np.int8).astype(bool),
                                   classical_dirty=rng.integers(0, 2, (19, size), dtype=np.int8).astype(bool))
                    expected_phase = np.asarray([
                        d == 0 and bool((int(k)&int(m)).bit_count()&1)
                        for d, k, m in zip(locators[start:stop], values[start:stop], masks[start:stop])
                    ], dtype=bool)
                    sim = km.Simulator(batch_size=size, seed=seed, counting_operations=True)
                    sim.use_same_registers_as(c)
                    for name, value in initial.items():
                        sim.write_across_shots(c.register_data[name], value)
                    sim.do(c)
                    for name, value in initial.items():
                        assert np.array_equal(sim.read_across_shots(c.register_data[name]), value), (kind, group, seed, start, name)
                    assert not sim.read_across_shots([km.q(i) for i in range(37, 47)]).any(), (kind, group, seed, start, 'scratch')
                    assert np.array_equal(sim.read_phase_flipped_across_shots(), expected_phase), (kind, group, seed, start, 'phase')
                    active = int(np.count_nonzero(masks[start:stop]))
                    expected_T = 11*active if kind == 'candidate' else 10*size+active
                    counted = sim.operation_statistics().num_toffoli_like
                    assert counted == expected_T, (kind, group, seed, start, counted, expected_T)
                    total += counted
                    del sim
                row = dict(kind=kind, panel=group, seed=seed, cases=4096,
                           total_T=total, measured_mean_T=total/4096,
                           value_errors=0, phase_errors=0, scratch_errors=0,
                           mask_restoration_errors=0, status='PASS')
                rows.append(row)
                save(args.output/'progress.json', dict(status='RUNNING_COMPONENT_CHECK', completed=rows))
                print(json.dumps(row), flush=True)
        del c
        gc.collect()
    assert source_bindings == {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    uniform = [row for row in rows if row['panel']=='all_masks_root']
    means = {kind: {row['measured_mean_T'] for row in uniform if row['kind']==kind}
             for kind in ('baseline', 'candidate')}
    assert means == {'baseline': {10+4095/4096}, 'candidate': {11*4095/4096}}
    report = dict(status='PASS_EXHAUSTIVE_MASK_NATIVE_POINT_COMPONENT_ONLY',
                  circuit_records=circuits, two_candidate_builds_identical=True,
                  distinct_fixture_cases=16384, cases_per_kind_per_seed=16384,
                  seeds=[147, 1147, 2147], maximum_batch_size=args.batch_size,
                  all_4096_masks_root_and_nonroot=True,
                  all_4096_locators_zero_and_nonzero_masks=True,
                  total_native_case_shots=2*3*16384,
                  uniform_mask_measured_old_mean_T=10+4095/4096,
                  uniform_mask_measured_new_mean_T=11*4095/4096,
                  exact_per_point_mean_saving=10/4096,
                  full4025_scan_mean_saving_model=4025*10/4096,
                  component_Q=47, component_static_T=11,
                  admitted_domain_change=False, official_verifier_run=False,
                  full_decoder_gain_claimed=False, source_bindings=source_bindings,
                  runs=rows, elapsed_seconds=time.monotonic()-started)
    save(args.output/'report.json', report)
    print(json.dumps({k:v for k,v in report.items() if k!='runs'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
