#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only native third-chart test, with forced raw-zero and affine cases.

The prefix is explicitly phase-open. The matched pair preserves both earlier
heads, arbitrary dirty bystanders, the owned norm bank and all scratch, and
checks diagonal/nonlinear phases. Real HMR masks are observed classically to
check every executed nonlinear count. No source-value probability is used.
"""
from __future__ import annotations
import argparse
from functools import cache
import gc
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORK = PROJECT.parent
RETAINED = 864
SEEDS = (59191, 60191, 61191)
MODES = ('base_axis', 'extension_axis', 'arbitrary_K24', 'forced_zero', 'zero_cross_coefficient')
km = np = Candidate = bit_matrix = None


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mul(a, b):
    result, a, b = 0, int(a), int(b)
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & 4096:
            a ^= 0x1053
    return result


@cache
def inv(value):
    answer, value, exponent = 1, int(value), 4094
    while exponent:
        if exponent & 1:
            answer = mul(answer, value)
        value = mul(value, value)
        exponent >>= 1
    return answer


def kmul(a, b):
    x, y, u, v = int(a) & 4095, int(a) >> 12, int(b) & 4095, int(b) >> 12
    return (mul(x, u) ^ mul(2048, mul(y, v))) | ((mul(x, v) ^ mul(y, u) ^ mul(y, v)) << 12)


def kinv(value):
    x, y = int(value) & 4095, int(value) >> 12
    factor = inv(mul(x, x) ^ mul(x, y) ^ mul(2048, mul(y, y)))
    return mul(x ^ y, factor) | (mul(y, factor) << 12)


def scale(value, coefficient):
    return mul(int(value) & 4095, coefficient) | (mul(int(value) >> 12, coefficient) << 12)


def coefficient_view(value):
    return (int(value) & 4095) ^ mul(int(value) >> 12, 4) | (int(value) & (4095 << 12))


def fixtures(per_mode):
    rng = np.random.default_rng(202611111932)
    firsts, seconds, values, answers, modes = [], [], [], [], []
    for mode in MODES:
        for index in range(per_mode):
            value = (index if mode == 'base_axis' else index << 12 if mode == 'extension_axis'
                     else 0 if mode == 'forced_zero' else int(rng.integers(0, 1 << 24)))
            while True:
                first = int(rng.integers(1, 1 << 24))
                denominator = 1 ^ kmul(first, value)
                if denominator:
                    break
            if mode == 'zero_cross_coefficient':
                second = scale(kinv(first), 20)
                assert kmul(first, second) == 20
            else:
                while True:
                    second = int(rng.integers(1, 1 << 24))
                    if scale(value, 20) ^ kmul(second, denominator):
                        break
            # Independent two query matrices, without the inversion-chain formula.
            n, d = scale(1 ^ kmul(first, value), inv(20)), value
            n, d = scale(d ^ kmul(second, n), inv(18)), n
            assert n and d
            answer = kmul(d, kinv(n))
            assert answer
            firsts.append(coefficient_view(first)); seconds.append(coefficient_view(second))
            values.append(value); answers.append(answer); modes.append(mode)
    count = len(values)
    dirty = rng.integers(0, 2, (RETAINED-96, count), dtype=np.int8).astype(bool)
    probe = rng.integers(0, 2, (RETAINED, count), dtype=np.int8).astype(bool)
    arrays = dict(first=bit_matrix(np.array(firsts), 24), second=bit_matrix(np.array(seconds), 24),
                  current=bit_matrix(np.array(values), 24), clean=np.zeros((24, count), dtype=bool),
                  dirty=dirty, probe=probe)
    boundary = np.vstack((arrays['first'], arrays['second'], bit_matrix(np.array(answers), 24),
                          arrays['clean'], dirty))
    phase = np.logical_xor.reduce(boundary & probe, axis=0)
    phase ^= boundary[1] & boundary[48+13] & boundary[96]
    phase ^= boundary[24+9] & boundary[48+3] & boundary[98]
    phase ^= boundary[0] & boundary[24+16] & boundary[48+18]
    return arrays, bit_matrix(np.array(answers), 24), phase, dict(
        cases=count, per_mode=per_mode, modes=list(MODES),
        actual_raw_zero_cases=sum(value == 0 for value in values),
        zero_cross_coefficient_cases=modes.count('zero_cross_coefficient'),
        all_existing_third_pivot_coordinates_nonzero=True,
        physical_syndrome_claim=False)


class ObserveMasks:
    def __init__(self, builder, clean, child_masks, flag_masks):
        self.builder = builder
        self.child = tuple(clean[12:18])
        self.child_masks, self.flag_masks = child_masks, flag_masks
        self.children = self.flags = 0

    def __getattr__(self, name):
        return getattr(self.builder, name)

    def hmr(self, source, mask):
        self.builder.hmr(source, mask)
        if tuple(source) == self.child:
            assert len(mask) == 6 and 6*(self.children+1) <= len(self.child_masks)
            self.builder.cx(mask, self.child_masks[6*self.children:6*(self.children+1)])
            self.children += 1
        elif len(source) == 1:
            assert len(mask) == 1 and self.flags < len(self.flag_masks)
            self.builder.cx(mask[0], self.flag_masks[self.flags])
            self.flags += 1


def build(pair):
    b = km.CircuitBuilder(); b.set_max_qubits(889)
    first = b.create_quantum_register(24, 'first')
    second = b.create_quantum_register(24, 'second')
    current = b.create_quantum_register(24, 'current')
    clean = b.create_quantum_register(24, 'clean')
    dirty = b.create_quantum_register(RETAINED-96, 'dirty')
    probe = b.create_classical_register(RETAINED, 'probe')
    children = b.create_classical_register(36 if pair else 18, 'child_masks')
    flags = b.create_classical_register(2 if pair else 1, 'flag_masks')
    spy = ObserveMasks(b, clean, children, flags)
    owned_flag = b.alloc_qubits(1)
    record = Candidate.emit_prefix(spy, (first, second), current, clean, owned_flag[0])
    assert record.prefix_static_T == 620 and not record.closed and record.zero_mask is not None
    assert b.num_allocated_qubits == RETAINED+1
    # Model the prefix owner relinquishing its now-zero predicate before return.
    b.free(owned_flag)
    receipt = None
    if pair:
        boundary = km.array([*first, *second, *current, *clean, *dirty])
        b.cz(probe, boundary)
        b.ccz(first[1], current[13], dirty[0])
        b.ccz(second[9], current[3], dirty[2])
        b.ccz(first[0], second[16], current[18])
        receipt = Candidate.emit_closing(spy, (first, second), current, clean, record)
        assert record.closed and record.zero_mask is None and all(row.closed for row in record.inverses)
        assert receipt['prefix_zero_mask_paid'] and receipt['return_zero_flag_retired']
        assert receipt['closed_inverse_calls'] == len(receipt['inverse_receipts']) == 3
        assert all(row['all_owned_storage_bits_reset'] and row['deferred_prefix_mask_paid']
                   for row in receipt['inverse_receipts'])
    assert b.num_allocated_qubits == RETAINED
    assert (spy.children, spy.flags) == ((6, 2) if pair else (3, 1))
    circuit = b.finish_circuit()
    static, probes = (1274, 3) if pair else (620, 0)
    assert circuit.operation_statistics().num_toffoli_like == static+probes
    assert circuit.num_qubits == 889
    return circuit, dict(component_static_T=static, probe_T=probes,
        circuit_static_T=static+probes, Q=889, retained_Q=RETAINED,
        child_mask_count=spy.children, flag_mask_count=spy.flags,
        return_child_mask_indices=[3, 4, 5] if pair else [],
        return_flag_mask_index=1 if pair else None,
        phase_checked=pair, owned_clean_bank_bits=24,
        borrowed_prefix_predicate_reset_without_free=True,
        return_predicate_separately_allocated=True, receipt=receipt)


def simulate(circuit, arrays, expected, phase, seed, metrics):
    count = arrays['dirty'].shape[1]
    sim = km.Simulator(batch_size=count, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    for name, value in arrays.items():
        sim.write_across_shots(circuit.register_data[name], value)
    for name, width in (('child_masks', 6*metrics['child_mask_count']), ('flag_masks', metrics['flag_mask_count'])):
        sim.write_across_shots(circuit.register_data[name], np.zeros((width, count), dtype=bool))
    sim.do(circuit)
    errors = {}
    for name, value in expected.items():
        ids = np.flatnonzero(np.any(sim.read_across_shots(circuit.register_data[name]) != value, axis=0)).tolist()
        if ids:
            errors[name] = ids
    scratch = bool(sim.read_across_shots([km.q(i) for i in range(RETAINED, 889)]).any())
    phase_bad = (np.flatnonzero(sim.read_phase_flipped_across_shots() != phase).tolist()
                 if metrics['phase_checked'] else None)
    children = sim.read_across_shots(circuit.register_data['child_masks'])
    flags = sim.read_across_shots(circuit.register_data['flag_masks'])
    child_zeros = [int(np.count_nonzero(~np.any(children[6*i:6*(i+1)], axis=0)))
                   for i in range(metrics['child_mask_count'])]
    flag_zeros = [int(np.count_nonzero(~flags[i])) for i in range(metrics['flag_mask_count'])]
    wanted = count*metrics['circuit_static_T']-4*sum(child_zeros[i] for i in metrics['return_child_mask_indices'])
    if metrics['return_flag_mask_index'] is not None:
        wanted -= 22*flag_zeros[metrics['return_flag_mask_index']]
    actual = sim.operation_statistics().num_toffoli_like
    row = dict(seed=seed, cases=count, value_error_case_ids=errors, scratch_errors=scratch,
               phase_error_case_ids=phase_bad, observed_child_zero_masks=child_zeros,
               observed_flag_zero_masks=flag_zeros, total_T=actual,
               independently_recomputed_total_T=wanted,
               measured_mean_T_excluding_probes=actual/count-metrics['probe_T'])
    assert not errors and not scratch and not phase_bad and actual == wanted, row
    del sim; gc.collect()
    return row


def reject_contracts():
    results = []
    for name in ('short_head', 'bank_alias', 'flag_alias', 'classical_current'):
        b = km.CircuitBuilder()
        first = b.create_quantum_register(24, 'first'); second = b.create_quantum_register(24, 'second')
        current = b.create_quantum_register(24, 'current'); clean = b.create_quantum_register(24, 'clean')
        flag = b.alloc_qubits(1)[0]
        heads = [first, second]
        if name == 'short_head': heads[0] = first[:23]
        if name == 'bank_alias': clean = km.array([current[0], *clean[1:]])
        if name == 'flag_alias': flag = current[1]
        if name == 'classical_current': current = b.create_classical_register(24, 'classical')
        try:
            Candidate.emit_prefix(b, heads, current, clean, flag)
        except (ValueError, TypeError): results.append(name)
        else: raise AssertionError(('invalid prefix accepted', name))
        assert b.finish_circuit().operation_statistics().num_toffoli_like == 0
    for name in ('closed_record', 'wrong_builder', 'wrong_current', 'wrong_heads'):
        b = km.CircuitBuilder()
        first = b.create_quantum_register(24, 'first'); second = b.create_quantum_register(24, 'second')
        current = b.create_quantum_register(24, 'current'); clean = b.create_quantum_register(24, 'clean')
        mask = b.create_classical_register(1, 'old_zero_mask')
        record = Candidate.Record(id(b), tuple(current), (tuple(first), tuple(second)), (), mask, None)
        if name == 'closed_record': record.closed = True
        if name == 'wrong_builder': record.builder_id = -1
        if name == 'wrong_current': record.source = tuple(reversed(current))
        if name == 'wrong_heads': record.heads = (tuple(second), tuple(first))
        try:
            Candidate.emit_closing(b, (first, second), current, clean, record)
        except (ValueError, TypeError): results.append(name)
        else: raise AssertionError(('invalid return accepted', name))
        assert b.finish_circuit().operation_statistics().num_toffoli_like == 0
    return results


def main():
    global km, np, Candidate, bit_matrix
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--per-mode', type=int, default=4096)
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert __debug__ and sys.version_info[:2] == (3, 13) and 1 <= args.per_mode <= 4096
    assert not (args.output/'report.json').exists()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(PROJECT/'integration_v4'))
    import v4_pipeline as V4
    from v4_binding import verify_preservation
    V4.configure(); preserved = verify_preservation(V4.Runtime)
    sys.path.insert(0, str(HERE))
    km = importlib.import_module('kickmix'); np = importlib.import_module('numpy')
    Candidate = importlib.import_module('third_pivot_chart')
    bit_matrix = importlib.import_module('quantum_reciprocal').bit_matrix
    assert Candidate.Base is V4.P.Extractor and Candidate.Norm.Arithmetic is V4.P.Arithmetic
    assert Candidate.Tail is V4.P.Tail
    assert digest(Candidate.Norm.__file__) == '8cb8eaee9312acc81a3048072ec3ddf721399ba8ccdd7eac94002f9d4ec2da46'
    from accepted_runtime import loaded_sources
    arrays, outputs, phase, fixture_scope = fixtures(args.per_mode)
    pins = {str(Path(path).resolve()): digest(path) for path in
            (Path(__file__), Candidate.__file__, Candidate.Norm.__file__, Candidate.Base.__file__, Candidate.Tail.__file__)}
    report = dict(status='IN_PROGRESS_THIRD_PIVOT_COMPONENT', fixture_scope=fixture_scope,
                  seeds=list(SEEDS), source_sha256=pins, rows=[],
                  rejected_contracts=reject_contracts(), production_or_official_checked=False)
    def save():
        temporary = args.output/'report.json.tmp'
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        temporary.replace(args.output/'report.json')
    started = time.monotonic(); save()
    for pair in (False, True):
        name = 'matched_pair' if pair else 'open_prefix'
        paths = [args.output/f'{name}-{label}.kmb' for label in ('a', 'b')]
        circuit, metrics = build(pair)
        circuit.to_file(paths[0], format='kmb'); tape_sha = digest(paths[0])
        expected = dict(arrays)
        if not pair: expected['current'] = outputs
        runs = [simulate(circuit, arrays, expected, phase, seed, metrics) for seed in SEEDS]
        del circuit; gc.collect()
        second, repeated = build(pair)
        second.to_file(paths[1], format='kmb')
        assert metrics == repeated and digest(paths[1]) == tape_sha
        del second; gc.collect()
        report['rows'].append(dict(panel=name, metrics=metrics, runs=runs,
                                  circuit_sha256=tape_sha, two_identical_builds=True))
        save(); print(json.dumps(dict(stage='panel_passed', panel=name, metrics=metrics)), flush=True)
        if not args.keep_circuits:
            for path in paths: path.unlink()
    V4.assert_bindings(); assert preserved == verify_preservation(V4.Runtime)
    assert pins == {path: digest(path) for path in pins}
    report.update(status='PASS_THIRD_PIVOT_ZERO_REPAIRED_COMPONENT_ONLY',
                  loaded_sources=loaded_sources(), elapsed_seconds=time.monotonic()-started,
                  exact_fresh_mask_mean_T='1274-12/64-22/2',
                  no_new_domain_condition=True, frozen_sources_unchanged=True,
                  production_carry_and_boundary_scale_gate_separate=True)
    save(); print(json.dumps(dict(status=report['status'], elapsed_seconds=report['elapsed_seconds'])), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
