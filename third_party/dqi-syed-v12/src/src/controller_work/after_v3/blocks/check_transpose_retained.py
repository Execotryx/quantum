#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-guarded native component panel for accepted-transpose flag retiming.

The original shared transpose and candidate use the same independent field
oracle, arbitrary dirty heads, all four modes, three HMR seeds and two builds.
Source-mask closure66T and three nonlinear probes are explicit test overhead.
No accepted source is changed or whole-decoder score claimed.
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
from pathlib import Path
import time

from accepted_runtime import load, recheck, loaded_sources, digest

RETAINED = 864
PROBE_T = 3
FLAG_CLOSURE_T = 66
SEEDS = (21901, 21902, 21903)
CANDIDATE_SHA = '5de6b48270d3098ca3ffa37474f2c10959d02ee3ccdb902e58b3ee8bcba129da'
km = np = toggle_zero = bit_matrix = None


def mul(a, b):
    """Independent multiplication in the actual 0x1053 polynomial basis."""
    a, b, out = int(a), int(b), 0
    while b:
        if b & 1:
            out ^= a
        b >>= 1
        a <<= 1
        if a & 4096:
            a ^= 0x1053
    return out


def polynomial(coefficients, point):
    answer = 0
    for coefficient in reversed(coefficients):
        answer = mul(answer, point) ^ int(coefficient)
    return answer


def unpack(words, m):
    p = 0
    F = words[p:p+m+2]
    p += m+2
    G = words[p:p+m+1]
    p += m+1
    q0, q1 = words[p:p+2]
    p += 2
    rhss = [words[p:p+m+3], words[p+m+3:p+2*(m+3)]]
    assert p+2*(m+3) == len(words)
    return F, G, q0, q1, rhss


def reference(row, m):
    """Independent original polynomial-transpose formula."""
    answer = list(map(int, row))
    F, G, q0, q1, rhss = unpack(answer, m)
    f, middle, third = int(q1 == 0), int(F[-1] == 0), int(G[-1] == 0)
    assert f+middle+third <= 1
    alpha = q0 if not f else 0
    weights = []
    for x in range(m):
        fv, gv = polynomial(F, x), polynomial(G, x)
        w3 = mul(gv, (1 ^ third) ^ (x if third else 0))
        w2 = (fv if not middle else 0) ^ (mul(gv, x) if middle else 0)
        p1 = (alpha if not middle else 0) ^ middle
        if not middle:
            p1 ^= mul(x, q1 ^ f)
        q1_form = 1 ^ f ^ middle
        if middle:
            q1_form ^= mul(x, alpha) ^ mul(mul(x, x), q1)
        w1 = mul(fv, p1) ^ mul(gv, q1_form)
        weights.append((w3, w2, w1))
    for r, rhs in enumerate(rhss):
        for head in range(3):
            for x, coefficients in enumerate(weights):
                answer[2*m+5+r*(m+3)+m+head] ^= mul(coefficients[head], rhs[x])
    return answer


def encode(values):
    values = np.asarray(values, dtype=np.int64)
    return np.vstack([bit_matrix(values[:, j], 12) for j in range(values.shape[1])])


def fixtures(m, per_mode):
    rng = np.random.default_rng(202611110941+m)
    count, fields = 4*per_mode, 4*m+11
    values = rng.integers(0, 4096, (count, fields), dtype=np.int64)
    witness_indices = (2*m+4, m+1, 2*m+2)
    modes = []
    for case in range(count):
        mode = case % 4
        flags = (int(mode == 1), int(mode == 2), int(mode == 3))
        modes.append(flags)
        for index, flag in zip(witness_indices, flags):
            values[case, index] = 0 if flag else int(rng.integers(1, 4096))
        if case % 13 == 0:
            values[case, 2*m+3] = 0
        if case % 17 == 0:
            values[case, 2*m+5:] = 0
    bits = encode(values)
    outside = rng.integers(0, 2, (RETAINED-12*fields, count), dtype=np.int8).astype(bool)
    probes = rng.integers(0, 2, bits.shape, dtype=np.int8).astype(bool)
    return values, modes, dict(data=bits, outside=outside, probes=probes)


def close_flag_debts(builder, witnesses, debts):
    """Pay all returned masks on restored physical witnesses: exactly66 T."""
    assert set(debts) == {0, 1, 2}
    for slot in range(3):
        flag = builder.alloc_qubits(1)
        toggle_zero(builder, witnesses[slot], flag[0])
        builder.cz(debts[slot], flag)
        builder.free(debts[slot])
        toggle_zero(builder, witnesses[slot], flag[0])
        builder.free(flag)


def build(module, m, pair, candidate):
    b = km.CircuitBuilder()
    b.set_max_qubits(889)
    fields = 4*m+11
    data = b.create_quantum_register(12*fields, 'data')
    outside = b.create_quantum_register(RETAINED-12*fields, 'outside')
    probes = b.create_classical_register(12*fields, 'probes')
    words = [data[12*j:12*(j+1)] for j in range(fields)]
    F, G, q0, q1, rhss = unpack(words, m)

    def one():
        debts = {}

        def record(slot, mask):
            assert slot in (0, 1, 2) and len(mask) == 1
            if slot in debts:
                b.cx(mask, debts[slot])
                b.free(mask)
            else:
                debts[slot] = mask

        module.emit(b, F, G, q0, q1, rhss, record)
        assert b.num_allocated_qubits == RETAINED
        close_flag_debts(b, (q1, F[-1], G[-1]), debts)
        assert b.num_allocated_qubits == RETAINED

    one()
    if pair:
        b.cz(probes, data)
        b.ccz(data[0], data[-1], outside[0])
        b.ccz(data[12], data[-13], data[-25])
        b.ccz(outside[1], data[25], data[-14])
        one()
    circuit = b.finish_circuit()
    assert b.num_allocated_qubits == RETAINED
    core = 168*m+(876 if candidate else 964)
    expected = (2 if pair else 1)*(core+FLAG_CLOSURE_T)+(PROBE_T if pair else 0)
    assert circuit.operation_statistics().num_toffoli_like == expected
    assert circuit.num_qubits == RETAINED+25, circuit.num_qubits
    return circuit


def check_rejections(candidate):
    """Invalid aliases/types must fail before a gate or helper is emitted."""
    checked = []
    for name in ('source_alias', 'head_target_alias', 'repeated_bit',
                 'short_word', 'classical_source', 'wrong_rhs_count'):
        b = km.CircuitBuilder()
        data = b.create_quantum_register(12*15, 'data')
        classical = b.create_classical_register(12, 'classical')
        words = [data[12*j:12*(j+1)] for j in range(15)]
        F, G, q0, q1, rhss = unpack(words, 1)
        if name == 'source_alias':
            F[0] = G[0]
        elif name == 'head_target_alias':
            rhss[0][0] = rhss[1][-1]
        elif name == 'repeated_bit':
            F[0] = km.array([F[0][0], F[0][0], *F[0][2:]])
        elif name == 'short_word':
            q0 = q0[:-1]
        elif name == 'classical_source':
            q1 = classical
        else:
            rhss = rhss[:1]
        before = b.finish_circuit()
        before_ops = len(before)
        before_q = b.num_allocated_qubits
        del before
        try:
            candidate.emit(b, F, G, q0, q1, rhss, lambda *_: None)
        except AssertionError:
            pass
        else:
            raise AssertionError(('invalid view accepted', name))
        after = b.finish_circuit()
        assert len(after) == before_ops and b.num_allocated_qubits == before_q
        assert after.operation_statistics().num_toffoli_like == 0
        checked.append(name)
    return checked


def simulate(circuit, initial, expected, seed, pair):
    count = initial['data'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, bits in initial.items():
        sim.write_across_shots(circuit.register_data[name], bits)
    sim.do(circuit)
    wanted_data = initial['data'] if pair else expected
    wanted_phase = np.zeros(count, dtype=bool)
    if pair:
        wanted_phase = np.logical_xor.reduce(expected & initial['probes'], axis=0)
        wanted_phase ^= expected[0] & expected[-1] & initial['outside'][0]
        wanted_phase ^= expected[12] & expected[-13] & expected[-25]
        wanted_phase ^= initial['outside'][1] & expected[25] & expected[-14]
    errors = {}
    for name, bits in dict(initial, data=wanted_data).items():
        observed = sim.read_across_shots(circuit.register_data[name])
        bad = np.flatnonzero(np.any(observed != bits, axis=0)).tolist()
        if bad:
            errors[name] = bad
    scratch = [km.q(i) for i in range(RETAINED, circuit.num_qubits)]
    if sim.read_across_shots(scratch).any():
        errors['scratch'] = True
    phase_bad = np.flatnonzero(sim.read_phase_flipped_across_shots() != wanted_phase).tolist()
    total = sim.operation_statistics().num_toffoli_like
    static = circuit.operation_statistics().num_toffoli_like
    row = dict(seed=seed, cases=count, pair=pair, errors=errors,
               phase_error_case_ids=phase_bad, total_T=total,
               measured_mean_T=total/count, static_T=static)
    assert not errors and not phase_bad and total == count*static, row
    del sim
    gc.collect()
    return row


def main():
    global km, np, toggle_zero, bit_matrix
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--sizes', type=int, nargs='+', default=[1, 3, 11, 14])
    p.add_argument('--per-mode', type=int, default=64)
    p.add_argument('--keep-circuits', action='store_true')
    args = p.parse_args()
    assert __debug__ and args.per_mode > 0
    assert args.sizes and len(args.sizes) == len(set(args.sizes))
    assert all(1 <= m <= 14 for m in args.sizes)
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists(), 'Use a new output directory'
    runtime = load()
    km, np = importlib.import_module('kickmix'), importlib.import_module('numpy')
    toggle_zero = importlib.import_module('coherent_border').toggle_zero
    bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    candidate = importlib.import_module('window_transpose_retained')
    assert Path(candidate.__file__).resolve() == Path(__file__).with_name('window_transpose_retained.py')
    reference_module = runtime.transpose
    assert digest(candidate.__file__) == CANDIDATE_SHA
    started = time.monotonic()
    report = dict(
        status='IN_PROGRESS_ISOLATED_RETIMED_TRANSPOSE_COMPONENT',
        input_cases_per_size=4*args.per_mode, sizes=args.sizes,
        modes=['000', '100', '010', '001'], seeds=list(SEEDS),
        retained_data_qubits=RETAINED, flag_debt_closure_T_per_call=FLAG_CLOSURE_T,
        nonlinear_probe_T_per_pair=PROBE_T, panels=[],
        invalid_view_rejections=check_rejections(candidate),
        reference_source_sha256=digest(reference_module.__file__),
        candidate_source_sha256=digest(candidate.__file__),
        expected_delta_per_core_call=-88,
        joined_preimage_checked=False, full_DQI_or_official_checked=False)

    def save():
        temp = args.output/'report.json.tmp'
        temp.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        temp.replace(args.output/'report.json')

    save()
    for m in args.sizes:
        values, modes, initial = fixtures(m, args.per_mode)
        fixture_path = args.output/f'fixtures-m{m}.json'
        fixture_path.write_text(json.dumps(dict(m=m, values=values.tolist(), modes=modes))+'\n')
        expected = encode([reference(row, m) for row in values])
        # The exact source map is an XOR shear and hence its own inverse.
        assert all(reference(reference(row, m), m) == list(map(int, row)) for row in values)
        counts = {}
        for label, module in (('reference', reference_module), ('candidate', candidate)):
            for pair in (False, True):
                name = f'm{m}-{label}-'+('pair' if pair else 'prefix')
                paths = [args.output/(name+f'-{letter}.kmb') for letter in ('a', 'b')]
                first = build(module, m, pair, label == 'candidate')
                first.to_file(paths[0], format='kmb')
                sha = digest(paths[0])
                static, Q, ops = first.operation_statistics().num_toffoli_like, first.num_qubits, len(first)
                simulations = [simulate(first, initial, expected, seed, pair) for seed in SEEDS]
                del first
                gc.collect()
                second = build(module, m, pair, label == 'candidate')
                second.to_file(paths[1], format='kmb')
                assert digest(paths[1]) == sha
                assert (second.operation_statistics().num_toffoli_like, second.num_qubits, len(second)) == (static, Q, ops)
                del second
                gc.collect()
                calls = 2 if pair else 1
                core_static = (static-(PROBE_T if pair else 0))//calls-FLAG_CLOSURE_T
                counts[(label, pair)] = static
                report['panels'].append(dict(
                    m=m, implementation=label, pair=pair, static_T=static, Q=Q,
                    core_static_T_per_call=core_static,
                    measured_core_mean_T_per_call=core_static,
                    instructions=ops, sha256=sha, identical_builds=True,
                    fixture_sha256=digest(fixture_path), simulations=simulations))
                save()
                print(json.dumps(dict(stage='panel_passed', name=name, static_T=static,
                                      Q=Q, core_T_per_call=core_static)), flush=True)
                if not args.keep_circuits:
                    for path in paths:
                        path.unlink()
        for pair in (False, True):
            assert counts[('reference', pair)]-counts[('candidate', pair)] == 88*(2 if pair else 1)
    assert digest(candidate.__file__) == CANDIDATE_SHA
    report.update(
        status='PASS_NATIVE_RETIMED_TRANSPOSE_COMPONENT_ONLY',
        elapsed_seconds=time.monotonic()-started,
        accepted_source_preservation=recheck(runtime), loaded_sources=loaded_sources(),
        predicted_two_call_preimage_delta_T=-176,
        model_scope='Two accepted transpose calls at m14, each saving88; joined caller and complete decoder are separate gates.',
        limitations=['Only four admitted local modes; no claim for two simultaneous local gaps.',
                     'Only flag lifetimes change; no borrowed-transpose arithmetic or global width improvement is included.',
                     'The66-T test closure is excluded from the reported core count.'])
    save()
    print(json.dumps(dict(status=report['status'], sizes=args.sizes,
                          cases_per_size=report['input_cases_per_size'],
                          elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
