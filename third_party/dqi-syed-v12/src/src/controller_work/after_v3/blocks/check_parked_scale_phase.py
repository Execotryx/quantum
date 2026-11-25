#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded direct parked-scale phase component gate.

The old decoded35-T phase seam and new23-T encoded seam are tested inside
a complete gauge park/unpark cycle. The actual HMR gauge masks are closed.
The878 retained bits include the real caller's persistent reciprocal and
local flag, so no new12-bit temporary can be hidden in the width ledger.
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
from pathlib import Path
import time

from accepted_runtime import load, recheck, digest, loaded_sources

RETAINED = 878
SEEDS = (35191, 36191, 37191)
PROBE_T = 3
km = np = Lender = Candidate = bit_matrix = None


def mul(a, b):
    a, b, out = int(a), int(b), 0
    while b:
        if b & 1:
            out ^= a
        a <<= 1
        b >>= 1
        if a & 4096:
            a ^= 0x1053
    return out


def fixtures(cases):
    rng = np.random.default_rng(202611111243)
    unit = 1+(np.arange(cases, dtype=np.int64)//2) % 4095
    gauge = np.arange(cases, dtype=np.int64) % 2
    other = rng.integers(0, 4096, cases, dtype=np.int64)
    other[gauge.astype(bool)] = 0
    target = rng.integers(0, 4096, cases, dtype=np.int64)
    masks = rng.integers(0, 4096, cases, dtype=np.int64)
    target[::17] = 0
    masks[::13] = 0
    dirty = rng.integers(0, 2, (RETAINED-37, cases), dtype=np.int8).astype(bool)
    arrays = dict(unit=bit_matrix(unit, 12), other=bit_matrix(other, 12),
                  target=bit_matrix(target, 12), gauge=bit_matrix(gauge, 1),
                  mask=bit_matrix(masks, 12), dirty=dirty)
    phase = np.array([(mul(t, r) & int(m)).bit_count() & 1
                      for t, r, m in zip(target, unit, masks)], dtype=bool)
    phase ^= ((unit & 1) != 0) & ((target & 2) != 0) & dirty[0]
    phase ^= ((other & 4) != 0) & ((target & 8) != 0) & dirty[1]
    phase ^= gauge.astype(bool) & ((unit & 16) != 0) & ((target & 32) != 0)
    return arrays, phase


def build(candidate):
    raw = km.CircuitBuilder()
    raw.set_max_qubits(889)
    unit = raw.create_quantum_register(12, 'unit')
    other = raw.create_quantum_register(12, 'other')
    target = raw.create_quantum_register(12, 'target')
    gauge = raw.create_quantum_register(1, 'gauge')
    mask_input = raw.create_classical_register(12, 'mask')
    dirty = raw.create_quantum_register(RETAINED-37, 'dirty')
    b = Lender.GaugeLender(raw, gauge[0])
    carrier = Lender.GaugeCarrier(b, gauge[0], other)
    mask = b.alloc_bits(12)
    b.bit_store(mask, False)
    b.cx(mask_input, mask)
    carrier.park(unit, 'component entry')
    if candidate:
        Candidate.repay_parked_scale(b, carrier, target, mask, 'component phase')
        assert carrier.parked_phase_payments == 1
        expected_parks = 1
    else:
        carrier.unpark('reference expose unit')
        Lender.repay_scale(b, target, unit, mask)
        carrier.park(unit, 'reference restore sentinel')
        expected_parks = 2
    carrier.assert_anchor(unit)
    assert b.enabled and b.idle and raw.num_allocated_qubits == RETAINED
    carrier.unpark('component exit')
    carrier.clean_boundary()
    assert (carrier.parks, carrier.unparks) == (expected_parks, expected_parks)
    raw.ccz(unit[0], target[1], dirty[0])
    raw.ccz(other[2], target[3], dirty[1])
    raw.ccz(gauge[0], unit[4], target[5])
    circuit = raw.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    assert raw.num_allocated_qubits == RETAINED
    assert static == (58 if candidate else 70)+PROBE_T, static
    assert circuit.num_qubits == RETAINED+10, circuit.num_qubits
    return circuit, dict(static_T=static, probe_T=PROBE_T,
                         complete_gauge_cycle_T=static-PROBE_T,
                         phase_seam_T=23 if candidate else 35,
                         retained_Q=RETAINED, Q=circuit.num_qubits,
                         phase_seam_extra_helpers=10,
                         park_unpark_pairs=expected_parks,
                         parked_phase_payments=int(candidate),
                         operations=len(circuit))


def simulate(circuit, arrays, phase, seed):
    count = arrays['unit'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    bad = {}
    for name, bits in arrays.items():
        observed = sim.read_across_shots(circuit.register_data[name])
        ids = np.flatnonzero(np.any(bits != observed, axis=0)).tolist()
        if ids:
            bad[name] = ids
    scratch_bad = bool(sim.read_across_shots(
        [km.q(i) for i in range(RETAINED, circuit.num_qubits)]).any())
    phase_bad = np.flatnonzero(sim.read_phase_flipped_across_shots() != phase).tolist()
    total = sim.operation_statistics().num_toffoli_like
    static = circuit.operation_statistics().num_toffoli_like
    result = dict(seed=seed, cases=count, input_errors=bad,
                  scratch_errors=scratch_bad, phase_error_case_ids=phase_bad,
                  total_T=total, measured_mean_T=total/count)
    assert not bad and not scratch_bad and not phase_bad and total == count*static, result
    del sim
    gc.collect()
    return result


def main():
    global km, np, Lender, Candidate, bit_matrix
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', type=int, default=8190)
    p.add_argument('--keep-circuits', action='store_true')
    args = p.parse_args()
    assert __debug__ and args.cases >= 2
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    runtime = load()
    km, np = importlib.import_module('kickmix'), importlib.import_module('numpy')
    Lender = importlib.import_module('gauge_park_lender')
    Candidate = importlib.import_module('parked_scale_phase')
    bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    arrays, phase = fixtures(args.cases)
    started = time.monotonic()
    report = dict(status='IN_PROGRESS_PARKED_SCALE_PHASE_COMPONENT',
                  cases=args.cases, seeds=list(SEEDS), rows=[],
                  exhaustive_unit_and_gauge_pairs=args.cases >= 8190,
                  source_sha256={str(Path(m.__file__).resolve()): digest(m.__file__)
                                 for m in (Lender, Candidate)},
                  production_integration=False, official_price_claimed=False)

    def save():
        temp = args.output/'report.json.tmp'
        temp.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        temp.replace(args.output/'report.json')

    save()
    for candidate in (False, True):
        label = 'candidate' if candidate else 'reference'
        paths = [args.output/f'{label}-{letter}.kmb' for letter in ('a', 'b')]
        circuit, metrics = build(candidate)
        circuit.to_file(paths[0], format='kmb')
        sha = digest(paths[0])
        runs = [simulate(circuit, arrays, phase, seed) for seed in SEEDS]
        del circuit
        gc.collect()
        second, second_metrics = build(candidate)
        second.to_file(paths[1], format='kmb')
        assert digest(paths[1]) == sha and metrics == second_metrics
        del second
        gc.collect()
        report['rows'].append(dict(implementation=label, metrics=metrics,
                                   sha256=sha, two_identical_builds=True, simulations=runs))
        save()
        print(json.dumps(dict(stage='panel_passed', implementation=label, metrics=metrics)), flush=True)
        if not args.keep_circuits:
            for path in paths:
                path.unlink()
    assert report['rows'][0]['metrics']['static_T']-report['rows'][1]['metrics']['static_T'] == 12
    report.update(status='PASS_NATIVE_PARKED_SCALE_PHASE_COMPONENT_ONLY',
                  elapsed_seconds=time.monotonic()-started,
                  accepted_source_preservation=recheck(runtime), loaded_sources=loaded_sources(),
                  exact_static_and_measured_delta_T=-12,
                  whole_preimage_two_occurrence_delta_T_model=-24,
                  limitations=['Unit parked anchor and sparse gauge chart are the existing caller domain.',
                               'Only the closed component is checked here; full caller remains a separate gate.',
                               'No optional zero-mask guard is enabled.'])
    save()
    print(json.dumps(dict(status=report['status'], cases=args.cases,
                          elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
