#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only native gate for the explicit transpose third-flag handoff.

Uses the frozen independent polynomial oracle and fixtures from the retimed
transpose checker. It also observes the returned quantum bit at the prefix
boundary, probes it nonlinearly, and rejects duplicate/wrong-witness claims.
Caller-query savings are not inferred from artificial fixture closure.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import importlib
import json
from pathlib import Path
import time

import check_transpose_retained as Oracle
from accepted_runtime import load, recheck, digest, loaded_sources

RETAINED = 864
PROBE_T = 3
SEEDS = (22901, 22902, 22903)
CANDIDATE_SHA = 'bb8423494ded91d4b42e83b147de4d45cf5bdb87695788ea66ef73cc3f817b21'
ORACLE_SHA = 'fa9355de142e7c3b3b2265063e1891167bdec10ef7634b7b9a5adfe60a24803b'
km = np = Candidate = toggle_zero = None


def build(m, pair):
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    fields = 4*m+11
    data = b.create_quantum_register(12*fields, 'data')
    outside = b.create_quantum_register(RETAINED-12*fields, 'outside')
    probes = b.create_classical_register(12*fields, 'probes')
    words = [data[12*j:12*(j+1)] for j in range(fields)]
    F, G, low_head, high_head, rhss = Oracle.unpack(words, m)
    calls = []

    def paid_one():
        # Merge each logical source witness's masks, then pay them on
        # restored inputs. The final third predicate is already available.
        debts, slots = {}, []

        def record(slot, mask):
            assert slot in (0, 1, 2) and len(mask) == 1
            slots.append(slot)
            if slot in debts:
                b.cx(mask, debts[slot])
                b.free(mask)
            else:
                debts[slot] = mask

        handoff = Candidate.emit(b, F, G, low_head, high_head, rhss, record)
        assert isinstance(handoff, Candidate.ThirdFlagHandoff)
        assert b.num_allocated_qubits == RETAINED+1
        assert Counter(slots) == {0: 5, 1: 5, 2: 3}, slots
        assert handoff.witness == tuple(G[-1]) and not handoff.claimed
        for builder, witness in ((object(), G[-1]), (b, G[0])):
            try:
                handoff.claim(builder, witness)
            except AssertionError:
                pass
            else:
                raise AssertionError('invalid flag claim accepted')
            assert not handoff.claimed
        flag = handoff.claim(b, G[-1])
        assert handoff.claimed and len(flag) == 1
        assert flag[0] not in set(data) | set(outside)
        try:
            handoff.claim(b, G[-1])
        except AssertionError:
            pass
        else:
            raise AssertionError('duplicate flag claim accepted')
        third_mask = debts.pop(2)
        b.cz(third_mask, flag)
        b.free(third_mask)
        for slot, witness in enumerate((high_head, F[-1])):
            temporary = b.alloc_qubits(1)
            toggle_zero(b, witness, temporary[0])
            source_mask = debts.pop(slot)
            b.cz(source_mask, temporary)
            b.free(source_mask)
            toggle_zero(b, witness, temporary[0])
            b.free(temporary)
        assert not debts and b.num_allocated_qubits == RETAINED+1
        calls.append(dict(source_mask_slot_counts=dict(Counter(slots)),
                          returned_flag=True, invalid_claims_rejected=3))
        return flag

    flag = paid_one()
    if pair:
        b.cz(probes, data)
        b.ccz(data[0], data[-1], outside[0])
        b.ccz(data[12], data[-13], data[-25])
        b.ccz(flag[0], data[25], data[-14])
        toggle_zero(b, G[-1], flag[0])
        b.free(flag)
        flag = paid_one()
        toggle_zero(b, G[-1], flag[0])
        b.free(flag)
        flag = None
    circuit = b.finish_circuit()
    core = 168*m+876
    closure = 55 if pair else 44
    static = circuit.operation_statistics().num_toffoli_like
    assert static == (2 if pair else 1)*(core+closure)+(PROBE_T if pair else 0)
    assert b.num_allocated_qubits == RETAINED+int(not pair)
    assert circuit.num_qubits == RETAINED+25
    return circuit, flag, dict(static_T=static, Q=circuit.num_qubits,
                               core_T_per_call=core, fixture_closure_T_per_call=closure,
                               probe_T=PROBE_T if pair else 0, calls=calls,
                               live_output_flags=int(not pair), operations=len(circuit))


def simulate(circuit, flag, initial, expected, m, pair, seed):
    count = initial['data'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in initial.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    desired = initial['data'] if pair else expected
    offset = 12*(2*m+2)
    wanted_flag = ~np.any(initial['data'][offset:offset+12], axis=0)
    wanted_phase = np.zeros(count, dtype=bool)
    if pair:
        wanted_phase = np.logical_xor.reduce(expected & initial['probes'], axis=0)
        wanted_phase ^= expected[0] & expected[-1] & initial['outside'][0]
        wanted_phase ^= expected[12] & expected[-13] & expected[-25]
        wanted_phase ^= wanted_flag & expected[25] & expected[-14]
    errors = {}
    for name, bits in dict(initial, data=desired).items():
        actual = sim.read_across_shots(circuit.register_data[name])
        bad = np.flatnonzero(np.any(actual != bits, axis=0)).tolist()
        if bad:
            errors[name] = bad
    if flag is not None:
        actual = sim.read_across_shots(flag)[0]
        bad = np.flatnonzero(actual != wanted_flag).tolist()
        if bad:
            errors['returned_flag'] = bad
    excluded = set(() if flag is None else flag)
    scratch = [km.q(i) for i in range(RETAINED, circuit.num_qubits) if km.q(i) not in excluded]
    if sim.read_across_shots(scratch).any():
        errors['scratch'] = True
    phase_bad = np.flatnonzero(sim.read_phase_flipped_across_shots() != wanted_phase).tolist()
    total = sim.operation_statistics().num_toffoli_like
    static = circuit.operation_statistics().num_toffoli_like
    result = dict(seed=seed, cases=count, pair=pair, errors=errors,
                  phase_error_case_ids=phase_bad, returned_flag_observed=not pair,
                  total_T=total, static_T=static, measured_mean_T=total/count)
    assert not errors and not phase_bad and total == count*static, result
    del sim
    gc.collect()
    return result


def main():
    global km, np, Candidate, toggle_zero
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', type=int, nargs='+', default=[14])
    parser.add_argument('--per-mode', type=int, default=64)
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert __debug__ and args.per_mode > 0
    assert args.sizes and len(args.sizes) == len(set(args.sizes))
    assert all(1 <= m <= 14 for m in args.sizes)
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    runtime = load()
    km, np = importlib.import_module('kickmix'), importlib.import_module('numpy')
    Candidate = importlib.import_module('window_transpose_handoff')
    toggle_zero = importlib.import_module('coherent_border').toggle_zero
    Oracle.km, Oracle.np, Oracle.toggle_zero = km, np, toggle_zero
    Oracle.bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    assert digest(Candidate.__file__) == CANDIDATE_SHA
    assert digest(Oracle.__file__) == ORACLE_SHA
    start = time.monotonic()
    report = dict(status='IN_PROGRESS_NATIVE_TRANSPOSE_FLAG_HANDOFF_COMPONENT',
                  sizes=args.sizes, cases_per_size=4*args.per_mode,
                  modes=['000', '100', '010', '001'], seeds=list(SEEDS),
                  source_sha256={str(Path(module.__file__).resolve()): digest(module.__file__)
                                 for module in (Candidate, Oracle)}, panels=[],
                  invalid_views_rejected=Oracle.check_rejections(Candidate),
                  full_preimage_checked=False, full_DQI_or_official_checked=False)

    def save():
        temporary = args.output/'report.json.tmp'
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        temporary.replace(args.output/'report.json')

    save()
    for m in args.sizes:
        values, modes, initial = Oracle.fixtures(m, args.per_mode)
        expected = Oracle.encode([Oracle.reference(row, m) for row in values])
        fixture = args.output/f'fixtures-m{m}.json'
        fixture.write_text(json.dumps(dict(m=m, values=values.tolist(), modes=modes))+'\n')
        for pair in (False, True):
            name = f'm{m}-'+('pair' if pair else 'prefix')
            paths = [args.output/f'{name}-{letter}.kmb' for letter in ('a', 'b')]
            circuit, flag, metrics = build(m, pair)
            circuit.to_file(paths[0], format='kmb')
            sha = digest(paths[0])
            simulations = [simulate(circuit, flag, initial, expected, m, pair, seed) for seed in SEEDS]
            del circuit
            gc.collect()
            second, second_flag, second_metrics = build(m, pair)
            second.to_file(paths[1], format='kmb')
            assert metrics == second_metrics and digest(paths[1]) == sha
            assert flag is None if pair else tuple(flag) == tuple(second_flag)
            del second
            gc.collect()
            report['panels'].append(dict(m=m, pair=pair, metrics=metrics,
                                          circuit_sha256=sha, two_identical_builds=True,
                                          fixture_sha256=digest(fixture), simulations=simulations))
            save()
            print(json.dumps(dict(stage='panel_passed', panel=name, metrics=metrics)), flush=True)
            if not args.keep_circuits:
                for path in paths:
                    path.unlink()
    assert digest(Candidate.__file__) == CANDIDATE_SHA and digest(Oracle.__file__) == ORACLE_SHA
    report.update(status='PASS_NATIVE_TRANSPOSE_FLAG_HANDOFF_COMPONENT_ONLY',
                  elapsed_seconds=time.monotonic()-start,
                  accepted_source_preservation=recheck(runtime), loaded_sources=loaded_sources(),
                  caller_two_occurrence_static_and_mean_delta_T_model=-22,
                  limitations=['The tensor core count is unchanged; only a later actual caller query can be removed.',
                               'Fixture closures are44 T with a live returned flag,55 T when closing that bit.',
                               'Only the four unchanged admitted local modes are covered.',
                               'No complete preimage or official score is inferred by this isolated gate.'])
    save()
    print(json.dumps(dict(status=report['status'], elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
