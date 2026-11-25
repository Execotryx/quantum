#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Caller-guarded native panels for C2.7 arithmetic; never a full decoder.

The root agent must run this under the shared runtime memory guard.
Each component builds twice, tests three HMR seeds, checks arbitrary dirty
retained words, value, source/restoration, nonlinear phase, clean scratch,
static counts and peak width. Prefix checks do not claim a settled phase
when the prefix deliberately returns outstanding HMR masks.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import random
import sys
import time
import c27_paths  # noqa: F401
import kickmix as km
import numpy as np
import gf24_arithmetic as New
import phase_inverse12 as Phase12
import narrow_field130 as Narrow
import scalar_inverse_phase as Scalar
from quantum_reciprocal import bit_matrix


COMPONENTS = ('phase12', 'inverse195', 'affine264', 'unit462', 'guarded483',
              'boundary1050', 'unit462zero')
SEEDS = (271, 1271, 2271)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mask_dot(mask, value):
    return (int(mask) & int(value)).bit_count() & 1


def install_events(events):
    def record(name, conditional_t, bits):
        events.append(dict(name=name, conditional_T=conditional_t, mask_bits=bits,
                           uniform_discount=conditional_t / 2**bits))
    New.record_uniform_hmr_event = record
    Phase12.record_uniform_hmr_event = record
    Narrow.record_uniform_hmr_event = record
    original = Scalar.phase_inverse_six
    def scalar(*args, **kwargs):
        record('scalar_inverse_six', 4, 6)
        return original(*args, **kwargs)
    for module in list(sys.modules.values()):
        if getattr(module, 'phase_inverse_six', None) is original:
            setattr(module, 'phase_inverse_six', scalar)


def fixtures(component, cases, retained, delta):
    rng = random.Random(202611111950 + COMPONENTS.index(component))
    arrays = {}
    if component == 'phase12':
        source = np.array([i % 4096 for i in range(cases)], dtype=np.int64)
        mask = np.array([0 if i % 11 == 0 else rng.randrange(4096)
                         for i in range(cases)], dtype=np.int64)
        arrays.update(source=bit_matrix(source, 12), mask=bit_matrix(mask, 12))
        target = source.copy()
        phase = np.array([mask_dot(m, New.FIELD.invert(int(s)) if s else 0)
                          for s, m in zip(source, mask)], dtype=bool)
        dirty_size = retained - 12
    else:
        source, x, y = [], [], []
        for i in range(cases):
            a = 0 if i % 5 == 0 else rng.randrange(1, 4096)
            b = rng.randrange(1, 4096) if not a else (0 if i % 5 == 1 else rng.randrange(4096))
            s = a | (b << 12)
            if component == 'inverse195' and i == 0:
                s = 0  # Explicit extra probe of the inherited zero extension.
            if 0 < i <= 24:
                s = 1 << (i - 1)
            v = 0 if i % 11 == 0 else rng.randrange(1 << 24)
            if component in ('guarded483', 'unit462zero') and i % 7 == 0:
                s, v = 0, 0
            source.append(s)
            x.append(v)
            y.append(rng.randrange(1 << 24))
        source, x, y = [np.array(z, dtype=np.int64) for z in (source, x, y)]
        arrays['source'] = bit_matrix(source, 24)
        if component == 'inverse195':
            target = np.array([New.inverse24(int(s), delta) for s in source], dtype=np.int64)
            dirty_size = retained - 24
            probe = np.array([rng.randrange(1 << 24) for _ in range(cases)], dtype=np.int64)
            arrays['probe'] = bit_matrix(probe, 24)
            phase = np.array([mask_dot(m, t) ^ (((int(t) >> 2) & 1) & ((int(t) >> 13) & 1))
                              for t, m in zip(target, probe)], dtype=bool)
        elif component == 'boundary1050':
            arrays['first'] = bit_matrix(x, 24)
            arrays['second'] = bit_matrix(y, 24)
            inv = np.array([New.inverse24(int(s), delta) for s in source], dtype=np.int64)
            first = np.array([New.mul24(int(v), int(s), delta)
                              for v, s in zip(x, inv)], dtype=np.int64)
            second = np.array([New.mul24(int(v), int(s), delta)
                               for v, s in zip(y, inv)], dtype=np.int64)
            target = dict(source=inv, first=first, second=second)
            masks = [np.array([rng.randrange(1 << 24) for _ in range(cases)],
                              dtype=np.int64) for _ in range(3)]
            for name, mask in zip(('probe_source', 'probe_first', 'probe_second'), masks):
                arrays[name] = bit_matrix(mask, 24)
            phase = np.array([
                mask_dot(m0, s) ^ mask_dot(m1, v) ^ mask_dot(m2, w) ^
                ((int(s) & 1) & ((int(v) >> 3) & 1)) ^
                (((int(v) >> 7) & 1) & ((int(w) >> 19) & 1))
                for s, v, w, m0, m1, m2 in zip(inv, first, second, *masks)
            ], dtype=bool)
            dirty_size = retained - 72
        elif component == 'affine264':
            arrays['first'] = bit_matrix(x, 24)
            arrays['second'] = bit_matrix(y, 24)
            m0 = np.array([rng.randrange(1 << 24) for _ in range(cases)], dtype=np.int64)
            m1 = np.array([0 if i % 9 == 0 else rng.randrange(1 << 24)
                           for i in range(cases)], dtype=np.int64)
            m2 = np.array([0 if i % 9 == 0 else rng.randrange(1 << 24)
                           for i in range(cases)], dtype=np.int64)
            for name, mask in [('constant', m0), ('mask_first', m1), ('mask_second', m2)]:
                arrays[name] = bit_matrix(mask, 24)
            target = None
            phase = np.array([
                mask_dot(a, New.inverse24(int(s), delta)) ^
                mask_dot(b, New.mul24(int(v), New.inverse24(int(s), delta), delta)) ^
                mask_dot(c, New.mul24(int(w), New.inverse24(int(s), delta), delta))
                for s, v, w, a, b, c in zip(source, x, y, m0, m1, m2)
            ], dtype=bool)
            dirty_size = retained - 72
        else:
            arrays['value'] = bit_matrix(x, 24)
            target = np.array([New.mul24(int(s), int(v), delta)
                               for s, v in zip(source, x)], dtype=np.int64)
            probe = np.array([rng.randrange(1 << 24) for _ in range(cases)], dtype=np.int64)
            arrays['probe'] = bit_matrix(probe, 24)
            phase = np.array([
                mask_dot(m, t) ^ ((int(s) & 1) & ((int(t) >> 1) & 1)) ^
                (((int(t) >> 2) & 1) & ((int(t) >> 13) & 1))
                for s, t, m in zip(source, target, probe)
            ], dtype=bool)
            dirty_size = retained - 48
    r = np.random.default_rng(202611111960 + COMPONENTS.index(component))
    arrays['dirty'] = r.integers(0, 2, size=(dirty_size, cases), dtype=np.int8).astype(bool)
    return arrays, target, phase


def build(component, retained, delta, events, prefix_path=None):
    events.clear()
    b = km.CircuitBuilder()
    source = b.create_quantum_register(12 if component == 'phase12' else 24, 'source')
    prefix = None
    if component == 'phase12':
        mask = b.create_classical_register(12, 'mask')
        b.create_quantum_register(retained - 12, 'dirty')
        Phase12.phase_inverse_twelve_polynomial(b, source, mask)
        expected_static, helpers, prefix_static = 27, 12, None
    elif component == 'inverse195':
        probe = b.create_classical_register(24, 'probe')
        b.create_quantum_register(retained - 24, 'dirty')
        rec = New.inverse_deferred(b, source, delta)
        prefix = b.finish_circuit()
        prefix_static = 195
        assert prefix.operation_statistics().num_toffoli_like == prefix_static
        if prefix_path is not None:
            prefix.to_file(prefix_path, format='kmb')
        del prefix
        b.cz(probe, source)
        b.cz(source[2], source[13])
        New.inverse_closed(b, source, delta)
        New.repay_source_masks(b, source, rec)
        expected_static, helpers = 478, 24
    elif component == 'boundary1050':
        first = b.create_quantum_register(24, 'first')
        second = b.create_quantum_register(24, 'second')
        probes = [b.create_classical_register(24, name)
                  for name in ('probe_source', 'probe_first', 'probe_second')]
        b.create_quantum_register(retained - 72, 'dirty')
        inverse_forward = New.inverse_deferred(b, source, delta)
        product_forward = [New.emit_prefix(b, source, word, delta)
                           for word in (first, second)]
        prefix = b.finish_circuit()
        prefix_static = 393
        assert prefix.operation_statistics().num_toffoli_like == prefix_static
        if prefix_path is not None:
            prefix.to_file(prefix_path, format='kmb')
        del prefix
        for probe, word in zip(probes, (source, first, second)):
            b.cz(probe, word)
        b.cz(source[0], first[3])
        b.cz(first[7], second[19])
        inverse_return = New.inverse_deferred(b, source, delta)
        product_return = [New.emit_prefix(b, source, word, delta)
                          for word in (first, second)]
        # At this exact seam the source is u, and both targets are their
        # restored entry values. One oracle pays all fresh reciprocal debts.
        New.phase_affine_quotient(
            b, source,
            [(word, rec.old_target_mask)
             for word, rec in zip((first, second), product_return)],
            New.source_mask(inverse_return), delta)
        New.free_source_masks(b, inverse_return)
        for rec in product_return:
            New.free_product_mask(b, rec)
        New.repay_source_masks(b, source, inverse_forward)
        for word, rec in zip((first, second), product_forward):
            New.repay_product_input(b, word, rec)
        expected_static, helpers = 1050, 24
    elif component == 'affine264':
        first = b.create_quantum_register(24, 'first')
        second = b.create_quantum_register(24, 'second')
        masks = [b.create_classical_register(24, name)
                 for name in ('constant', 'mask_first', 'mask_second')]
        b.create_quantum_register(retained - 72, 'dirty')
        New.phase_affine_quotient(b, source, [(first, masks[1]), (second, masks[2])], masks[0], delta)
        expected_static, helpers, prefix_static = 264, 24, None
    else:
        value = b.create_quantum_register(24, 'value')
        probe = b.create_classical_register(24, 'probe')
        b.create_quantum_register(retained - 48, 'dirty')
        record = New.emit_prefix(b, source, value, delta, guarded=component == 'guarded483')
        prefix = b.finish_circuit()
        prefix_static = 99
        assert prefix.operation_statistics().num_toffoli_like == prefix_static
        if prefix_path is not None:
            prefix.to_file(prefix_path, format='kmb')
        del prefix
        b.cz(probe, value)
        b.cz(source[0], value[1])
        b.cz(value[2], value[13])
        New.emit_closing(b, source, value, record)
        expected_static, helpers = (483, 25) if component == 'guarded483' else (462, 24)
    circuit = b.finish_circuit()
    assert b.num_allocated_qubits == retained, (component, b.num_allocated_qubits, retained)
    static = circuit.operation_statistics().num_toffoli_like
    assert static == expected_static, (component, static, expected_static)
    assert circuit.num_qubits == retained + helpers, (component, circuit.num_qubits, retained + helpers)
    metric = dict(component=component, static_T=static,
                  uniform_mask_HMR_mean_T=static-sum(e['uniform_discount'] for e in events),
                  Q=circuit.num_qubits, retained=retained, peak_helpers=helpers,
                  prefix_static_T=prefix_static, events=list(events),
                  mean_scope='Exact event model when recorded classical masks are independent uniform; samples include deliberate zero masks.')
    return circuit, metric


def simulate(component, circuit, arrays, target, expected_phase, retained, seed, prefix=False):
    cases = arrays['source'].shape[1]
    sim = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    registers = circuit.register_data
    for name, values in arrays.items():
        sim.write_across_shots(registers[name], values)
    sim.do(circuit)
    errors = []
    for name, values in arrays.items():
        if prefix and component == 'boundary1050' and name in target:
            values = bit_matrix(target[name], 24)
        elif prefix and name == ('source' if component == 'inverse195' else 'value'):
            values = bit_matrix(target, 24)
        actual = sim.read_across_shots(registers[name])
        if not np.array_equal(actual, values):
            errors.append(dict(register=name,
                               shots=np.flatnonzero(np.any(actual != values, axis=0)).tolist()))
    scratch = [km.q(i) for i in range(retained, circuit.num_qubits)]
    if scratch and sim.read_across_shots(scratch).any():
        errors.append(dict(register='scratch'))
    phase_errors = [] if prefix else np.flatnonzero(
        sim.read_phase_flipped_across_shots() != expected_phase).tolist()
    row = dict(seed=seed, prefix=prefix, cases=cases,
               value_restoration_errors=errors, phase_errors=None if prefix else phase_errors,
               sampled_mean_T=sim.operation_statistics().num_toffoli_like/cases)
    assert not errors and not phase_errors, row
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', choices=(*COMPONENTS, 'all'), default='all')
    parser.add_argument('--cases', type=int, default=4096)
    parser.add_argument('--retained', type=int, default=865)
    parser.add_argument('--delta', type=int, default=2048)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--keep-circuits', action='store_true')
    args = parser.parse_args()
    assert args.cases > 0 and args.retained >= 72
    args.output.mkdir(parents=True, exist_ok=True)
    events = []
    install_events(events)
    components = COMPONENTS if args.component == 'all' else (args.component,)
    started = time.monotonic()
    reports = []
    for component in components:
        folder = args.output / component
        folder.mkdir(parents=True, exist_ok=True)
        arrays, target, phases = fixtures(component, args.cases, args.retained, args.delta)
        prefix_path = folder/'prefix.kmb'
        path_a, path_b = folder/'build-a.kmb', folder/'build-b.kmb'
        circuit, metric = build(component, args.retained, args.delta, events, prefix_path)
        circuit.to_file(path_a, format='kmb')
        sha = digest(path_a)
        runs = [simulate(component, circuit, arrays, target, phases, args.retained, seed)
                for seed in SEEDS]
        del circuit
        gc.collect()
        circuit, again = build(component, args.retained, args.delta, events)
        circuit.to_file(path_b, format='kmb')
        assert metric == again and sha == digest(path_b), component
        del circuit
        gc.collect()
        if prefix_path.exists():
            circuit = km.Circuit.from_file(prefix_path, format='kmb')
            runs += [simulate(component, circuit, arrays, target, phases, args.retained, seed, True)
                     for seed in SEEDS]
            del circuit
            gc.collect()
        report = dict(status='PASS_NATIVE_C27_ARITHMETIC_COMPONENT', component=component,
                      metrics=metric, cases=args.cases, two_identical_builds=True,
                      sha256=sha, circuit_bytes=path_a.stat().st_size, runs=runs,
                      scope='Component only; not a joined extractor, DQI circuit, failure census or official verifier.')
        (folder/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        reports.append(report)
        print(json.dumps(report, indent=2), flush=True)
        if not args.keep_circuits:
            for path in (prefix_path, path_a, path_b):
                if path.exists():
                    path.unlink()
    (args.output/'summary.json').write_text(json.dumps(dict(
        status='PASS_REQUESTED_COMPONENT_PANELS', reports=reports,
        elapsed_seconds=time.monotonic()-started), indent=2)+'\n')


if __name__ == '__main__':
    main()
