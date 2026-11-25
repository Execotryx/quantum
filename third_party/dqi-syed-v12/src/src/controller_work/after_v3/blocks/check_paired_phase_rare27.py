#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded forced-branch gate for the rare paired quotient phase.

The four fixtures explicitly force each classical mask branch. Full mode
visits every denominator, including zero, in each branch. These biased
fixtures validate the exact phase and execution count; they are not a fresh
HMR population sample. No production source or historical report is edited.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gc
import importlib
import json
from pathlib import Path
import time

from accepted_runtime import load, recheck, digest, loaded_sources

RETAINED = 867
PROBE_T = 3
SEEDS = (39191, 40191, 41191)
MODES = ('first_rhs_nonzero', 'only_second_rhs_nonzero',
         'only_inverse_mask_nonzero', 'all_masks_zero')
km = np = Reference = Candidate = bit_matrix = None
TOWER_ROWS = None


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


def inverse(value):
    base, exponent, result = int(value), 4094, 1
    while exponent:
        if exponent & 1:
            result = mul(result, base)
        base = mul(base, base)
        exponent >>= 1
    return result


def tower(value):
    # Public representation from the unchanged reciprocal-debt ABI. The
    # underlying field multiplication and inverse oracle above are independent.
    return sum(((int(value) & row).bit_count() & 1) << i
               for i, row in enumerate(TOWER_ROWS))


def fixtures(per_mode):
    rng = np.random.default_rng(202611111359)
    count = per_mode * len(MODES)
    mode = np.repeat(np.arange(len(MODES), dtype=np.int64), per_mode)
    factor = np.tile(np.arange(per_mode, dtype=np.int64) % 4096, len(MODES))
    x = rng.integers(0, 4096, count, dtype=np.int64)
    y = rng.integers(0, 4096, count, dtype=np.int64)
    xm = rng.integers(1, 4096, count, dtype=np.int64)
    ym = rng.integers(1, 4096, count, dtype=np.int64)
    im = rng.integers(1, 4096, count, dtype=np.int64)
    # Exercise every single-bit mask as well as general combinations.
    for start in range(0, count, per_mode):
        for j in range(min(per_mode, 12)):
            xm[start+j] = ym[start+j] = im[start+j] = 1 << j
    xm[mode >= 1] = 0
    ym[mode >= 2] = 0
    im[mode == 3] = 0
    ym[(mode == 0) & (np.arange(count) % 5 == 0)] = 0
    im[((mode == 0) | (mode == 1)) & (np.arange(count) % 7 == 0)] = 0
    x[::17] = 0
    y[::19] = 0
    dirty = rng.integers(0, 2, (RETAINED-36, count), dtype=np.int8).astype(bool)
    values = dict(factor=factor, x=x, y=y, xmask=xm, ymask=ym, inverse_mask=im)
    arrays = {name: bit_matrix(value, 12) for name, value in values.items()}
    arrays['dirty'] = dirty
    phase = np.array([
        ((int(a_mask) & mul(a, inverse(d))).bit_count()
         ^ (int(b_mask) & mul(b, inverse(d))).bit_count()
         ^ (int(i_mask) & tower(inverse(d))).bit_count()) & 1
        for d, a, b, a_mask, b_mask, i_mask
        in zip(factor, x, y, xm, ym, im)], dtype=bool)
    phase ^= ((factor & 1) != 0) & ((x & 2) != 0) & dirty[0]
    phase ^= ((y & 4) != 0) & ((x & 8) != 0) & dirty[1]
    phase ^= ((factor & 16) != 0) & ((y & 32) != 0) & dirty[2]
    return arrays, phase, mode


def build(candidate):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(889)
    factor = builder.create_quantum_register(12, 'factor')
    x = builder.create_quantum_register(12, 'x')
    y = builder.create_quantum_register(12, 'y')
    xm = builder.create_classical_register(12, 'xmask')
    ym = builder.create_classical_register(12, 'ymask')
    im = builder.create_classical_register(12, 'inverse_mask')
    dirty = builder.create_quantum_register(RETAINED-36, 'dirty')
    emitted = []
    old_hook = Candidate.record_uniform_hmr_event
    Candidate.record_uniform_hmr_event = lambda *row: emitted.append(tuple(row))
    try:
        provider = Candidate if candidate else Reference
        provider.quotient_phases(builder, factor, ((x, xm), (y, ym)), im)
    finally:
        Candidate.record_uniform_hmr_event = old_hook
    if candidate:
        assert emitted == [('paired_rare27_exclusive_overlap', 27, 0),
                           ('paired_rare27_rhs_zero', 38, 24),
                           ('paired_rare27_all_masks_zero', 27, 36)]
    else:
        assert not emitted
    builder.ccz(factor[0], x[1], dirty[0])
    builder.ccz(y[2], x[3], dirty[1])
    builder.ccz(factor[4], y[5], dirty[2])
    assert builder.num_allocated_qubits == RETAINED
    circuit = builder.finish_circuit()
    static = circuit.operation_statistics().num_toffoli_like
    assert static == (92 if candidate else 100)+PROBE_T, static
    assert circuit.num_qubits == RETAINED+22, circuit.num_qubits
    return circuit, dict(static_T=static-PROBE_T, circuit_static_T=static,
                         probe_T=PROBE_T, Q=circuit.num_qubits,
                         retained_Q=RETAINED, helpers=22,
                         events=[list(row) for row in emitted], operations=len(circuit))


def simulate(circuit, arrays, phase, mode, seed, candidate):
    count = arrays['factor'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in arrays.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    bad = {}
    for name, bits in arrays.items():
        actual = sim.read_across_shots(circuit.register_data[name])
        ids = np.flatnonzero(np.any(bits != actual, axis=0)).tolist()
        if ids:
            bad[name] = ids
    scratch_bad = bool(sim.read_across_shots(
        [km.q(i) for i in range(RETAINED, circuit.num_qubits)]).any())
    phase_bad = np.flatnonzero(sim.read_phase_flipped_across_shots() != phase).tolist()
    costs = (65, 65, 27, 0) if candidate else (65, 65, 35, 35)
    by_mode = {name: int(np.count_nonzero(mode == j)) for j, name in enumerate(MODES)}
    expected = sum(by_mode[name]*(costs[j]+PROBE_T) for j, name in enumerate(MODES))
    actual = sim.operation_statistics().num_toffoli_like
    result = dict(seed=seed, cases=count, cases_by_forced_mode=by_mode,
                  input_errors=bad, scratch_errors=scratch_bad,
                  phase_error_case_ids=phase_bad, total_T=actual,
                  independent_expected_total_T=expected,
                  measured_mean_T_excluding_probes=actual/count-PROBE_T)
    assert not bad and not scratch_bad and not phase_bad and actual == expected, result
    del sim
    gc.collect()
    return result


def main():
    global km, np, Reference, Candidate, bit_matrix, TOWER_ROWS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--per-mode', type=int, default=4096)
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert __debug__ and 1 <= args.per_mode <= 4096
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    runtime = load()
    km, np = importlib.import_module('kickmix'), importlib.import_module('numpy')
    Reference = importlib.import_module('gauge_park_paired')
    Candidate = importlib.import_module('paired_phase_rare27')
    bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    TOWER_ROWS = tuple(importlib.import_module('tower_inverse').quadratic_basis(12)['to_tower'])
    pinned = {str(Path(module.__file__).resolve()): digest(module.__file__)
              for module in (Reference, Candidate)}
    arrays, phase, mode = fixtures(args.per_mode)
    started = time.monotonic()
    report = dict(status='IN_PROGRESS_FORCED_RARE_PAIRED_PHASE_COMPONENT',
                  cases=args.per_mode*4, per_mode=args.per_mode,
                  exhaustive_denominators_per_branch=args.per_mode == 4096,
                  includes_zero_denominator=True, forced_modes=list(MODES),
                  fixture_masks_uniform_independent=False, seeds=list(SEEDS),
                  tower_mask_rows=list(TOWER_ROWS), source_sha256=pinned, rows=[],
                  full_preimage_checked=False, full_DQI_or_official_checked=False)

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
        runs = [simulate(circuit, arrays, phase, mode, seed, candidate) for seed in SEEDS]
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
    assert pinned == {path: digest(path) for path in pinned}
    expected_new = Candidate.expected_fresh_T()
    expected_old = Fraction(65)-Fraction(30, 1 << 24)
    assert expected_new == Fraction(65)-Fraction(38, 1 << 24)-Fraction(27, 1 << 36)
    report.update(status='PASS_NATIVE_FORCED_RARE_PAIRED_PHASE_COMPONENT_ONLY',
                  elapsed_seconds=time.monotonic()-started,
                  accepted_source_preservation=recheck(runtime), loaded_sources=loaded_sources(),
                  exact_static_delta_T_per_call=-8,
                  fresh_uniform_mask_expected_old_exact=str(expected_old),
                  fresh_uniform_mask_expected_new_exact=str(expected_new),
                  exact_uniform_fresh_mask_delta_T_per_call=str(expected_new-expected_old),
                  production_call_count_from_accepted_ledger=18,
                  full_preimage_static_delta_T_model=-144,
                  full_preimage_uniform_fresh_mask_delta_T_model_exact=str(18*(expected_new-expected_old)),
                  limitations=['Complete isolated phase component; no caller integration or whole decoder is asserted.',
                               'The inverse mask is in the unchanged public quadratic-tower coordinate convention.',
                               'The forced mask sample mean is not the fresh-HMR expectation.',
                               'All accepted and other prepared candidate sources remain unchanged.'])
    save()
    print(json.dumps(dict(status=report['status'], cases=report['cases'],
                          elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
