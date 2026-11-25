#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Native real-CRT raw-query panels; root must run under the memory guard.

Fixture inputs are derived from actual nonzero physical positions/magnitudes,
their seventy syndromes, the public Hankel map H(U), and quadratic CRT.  The
circuit receives the resulting raw residues, never a supplied head or tail
profile.  A short --slots panel checks the same emitter's initial stages.
The full35 panel includes the actual gauge, scalar seed and tail seed seam.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import random
import sys
import time
import c27_paths
import kickmix as km
import numpy as np
import raw_query_extractor as Extract
import rolling_tail as Tail
import scalar_seed as Seed
from quantum_reciprocal import bit_matrix
from check_arithmetic import install_events

sys.path.insert(0, str(c27_paths.WORK/'night_c27/census'))
import reference as Ref

SEEDS = (317, 1317, 2317)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pack(pair):
    return pair[0] | (pair[1] << 12)


def unpack(value):
    return value & 4095, value >> 12


def multiply(a, b):
    return pack(Ref.quadratic_mul(unpack(a), unpack(b), 2048))


def inverse(a):
    return pack(Ref.quadratic_div((1, 0), unpack(a), 2048))


def value_at_node(coefficient_word, index):
    a, b = unpack(coefficient_word)
    return (a ^ Ref.mul(2*index, b)) | (b << 12)


def scale(value, factor):
    a, b = unpack(value)
    return Ref.mul(a, factor) | (Ref.mul(b, factor) << 12)


def public_modulus():
    out = [1]
    for q in Ref.QUADRATICS:
        out = Ref.product(out, q)
    assert len(out) == 71 and out[-1] == 1
    return out


def raw_from_syndromes(roots, magnitudes, modulus):
    syndromes = [0]*70
    for a, e in zip(roots, magnitudes):
        power = a
        for k in range(70):
            syndromes[k] ^= Ref.mul(e, power)
            power = Ref.mul(power, a)
    transformed = [0]*70
    for i in range(70):
        for j in range(70-i):
            transformed[i] ^= Ref.mul(modulus[i+j+1], syndromes[j])
    raw = [value_at_node(pack(Ref.quadratic_remainder(transformed, k)), i)
           for i, k in enumerate(Ref.KAPPAS)]
    numerator, denominator = Ref.physical_pair(roots, magnitudes)
    for i, k in enumerate(Ref.KAPPAS):
        n = Ref.quadratic_remainder(numerator, k)
        d = Ref.quadratic_remainder(denominator, k)
        want = value_at_node(pack(Ref.quadratic_div(n, d, k)), i)
        assert raw[i] == want, ('syndrome_CRT_identity', i)
    return raw, syndromes, numerator, denominator


def prefix_reference(raw, weight, stop, j_min):
    storage, heads, flags, carry, previous = list(raw), [], [], 1, 0
    for i in range(stop):
        n, d = multiply(carry, storage[i]), carry
        for old in range(i):
            p = value_at_node(heads[old], i)
            difference = Ref.KAPPAS[old] ^ Ref.KAPPAS[i]
            n, d = scale(d ^ multiply(p, n), Ref.INV[difference]), n
        assert n or d
        flag = int(n == 0)
        if i < weight:
            assert not flag, ('active_numerator_pole', i)
        if flag:
            assert i >= j_min
            n, d = d, n
        carry = inverse(n)
        p = multiply(d, carry)
        if i < weight:
            assert p, ('active_zero_head', i)
        else:
            assert p == 0
        assert int(p == 0) == (previous ^ flag)
        previous = flag
        heads.append(value_at_node(p, i))
        storage[i] = heads[-1]
        flags.append(flag)
    return storage, carry, flags


def seed_reference(storage, carry, flag):
    output = list(storage)
    a, b = unpack(carry)
    gauge = int(a == 0)
    if gauge:
        a, b = b, a
    assert a
    p0, p1 = unpack(output[34])
    d0, d1 = Ref.mul(a, p0), Ref.mul(a, p1)
    if flag:
        assert d1 == 0
        a, d1 = d1, a
    output[34] = d0 | (d1 << 12)
    return output, a | (b << 12), gauge


def bits_of_data(words, carry):
    return np.concatenate([bit_matrix(np.array([x], dtype=np.int64), 24)
                           for x in (*words, carry)], axis=0)[:, 0]


def fixtures(weights, per_weight, stop, j_min, full_seed):
    rng = random.Random(202611112700)
    modulus = public_modulus()
    cases, rejected = [], []
    for weight in weights:
        assert j_min <= weight <= 35
        kept = 0
        attempts = 0
        while kept < per_weight:
            attempts += 1
            assert attempts < 10000
            roots = rng.sample(range(1, 4096), weight)
            magnitudes = [rng.randrange(1, 4096) for _ in roots]
            raw, syndromes, n, d = raw_from_syndromes(roots, magnitudes, modulus)
            active = Ref.active_profile(n, d, weight)
            if active['bad']:
                rejected.append(dict(weight=weight, attempt=attempts, active=active))
                continue
            storage, carry, flags = prefix_reference(raw, weight, stop, j_min)
            if stop == 35:
                assert flags[-1] == int(weight % 2 == 0)
            if full_seed:
                probe_words, probe_carry, gauge = seed_reference(storage, carry, flags[-1])
            else:
                probe_words, probe_carry, gauge = storage, carry, None
            cases.append(dict(weight=weight, roots=roots, magnitudes=magnitudes,
                              syndromes=syndromes, raw=raw, prefix_words=storage,
                              prefix_carry=carry, flags=flags,
                              probe_words=probe_words, probe_carry=probe_carry,
                              gauge=gauge,
                              converter_half=Ref.half_profile(Ref.product(d, Ref.PADDING[weight]))))
            kept += 1
    values = np.stack([bits_of_data(c['raw'], 1) for c in cases], axis=1)
    prefix_values = np.stack([bits_of_data(c['prefix_words'], c['prefix_carry'])
                              for c in cases], axis=1)
    probe_values = np.stack([bits_of_data(c['probe_words'], c['probe_carry'])
                             for c in cases], axis=1)
    masks = np.random.default_rng(202611112701).integers(
        0, 2, size=values.shape, dtype=np.int8).astype(bool)
    phase = np.logical_xor.reduce(probe_values & masks, axis=0)
    phase ^= probe_values[0] & probe_values[47]
    phase ^= probe_values[181] & probe_values[863]
    return cases, rejected, values, prefix_values, probe_values, masks, phase


def build(stop, j_min, full_seed, events, *, prefix_path=None, seam_path=None,
          label='build'):
    events.clear()
    b = km.CircuitBuilder()
    data = b.create_quantum_register(864, 'data')
    probe = b.create_classical_register(864, 'probe')
    words = [data[24*i:24*(i+1)] for i in range(35)]
    carry = data[840:864]
    def stage(message):
        if message.endswith(('04', '09', '14', '19', '24', '29', '34', '00')):
            print(json.dumps(dict(stage=message, build=label)), flush=True)
    record = Extract.emit_prefix(b, words, carry, j_min=j_min, stop_index=stop, stage=stage)
    prefix_flag = record.tail.current if record.tail is not None else None
    if record.tail is not None:
        record.tail.release_spare()
    front = b.finish_circuit()
    prefix_static = front.operation_statistics().num_toffoli_like
    if prefix_path is not None:
        front.to_file(prefix_path, format='kmb')
    del front
    gauge = seed = None
    if full_seed:
        gauge = Tail.gauge_prefix(b, carry)
        seed = Seed.emit_prefix(b, carry[:12], words[34])
        record.tail.seed_prefix(carry[:12], words[34][12:])
        if seam_path is not None:
            seam = b.finish_circuit()
            seam.to_file(seam_path, format='kmb')
            del seam
    b.cz(probe, data)
    b.cz(data[0], data[47])
    b.cz(data[181], data[863])
    if full_seed:
        record.tail.seed_return(carry[:12], words[34][12:])
        Seed.emit_closing(b, carry[:12], words[34], seed)
        events.append(dict(name='scalar_seed_inverse_phase', conditional_T=27,
                           mask_bits=12, uniform_discount=27/4096))
        Tail.gauge_return(b, carry, gauge)
    if record.tail is not None:
        record.tail.resume_return()
    Extract.emit_closing(b, words, carry, record, stage=stage)
    circuit = b.finish_circuit()
    ledger = Extract.source_ledger(stop, j_min, full_seed_seam=full_seed)
    static = circuit.operation_statistics().num_toffoli_like
    assert static == ledger['total_pair_T'], (static, ledger)
    assert circuit.num_qubits == ledger['peak_Q'], (circuit.num_qubits, ledger)
    assert b.num_allocated_qubits == 864 and record.closed
    expected_prefix = ledger['arithmetic_prefix_T']
    if stop > j_min:
        expected_prefix += 69*(stop-j_min)-22
    assert prefix_static == expected_prefix, (prefix_static, expected_prefix)
    metrics = dict(static_T=static, Q=circuit.num_qubits, retained_data=864,
                   prefix_static_T=prefix_static,
                   uniform_HMR_mean_T=static-sum(e['uniform_discount'] for e in events),
                   uniform_HMR_events=list(events), source_ledger=ledger)
    return circuit, metrics, prefix_flag, None if gauge is None else gauge.flag


def simulate(circuit, values, masks, expected_values, expected_phase, seed,
             *, live_flag=None, flag_values=None, label='pair'):
    cases = values.shape[1]
    sim = km.Simulator(batch_size=cases, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circuit)
    registers = circuit.register_data
    sim.write_across_shots(registers['data'], values)
    sim.write_across_shots(registers['probe'], masks)
    sim.do(circuit)
    actual = sim.read_across_shots(registers['data'])
    errors = np.flatnonzero(np.any(actual != expected_values, axis=0)).tolist()
    assert not errors, dict(panel=label, value_errors=errors)
    assert np.array_equal(sim.read_across_shots(registers['probe']), masks)
    scratch = [km.q(i) for i in range(864, circuit.num_qubits)
               if live_flag is None or km.q(i) != live_flag]
    assert not sim.read_across_shots(scratch).any(), (label, 'dirty_scratch')
    if live_flag is not None:
        assert np.array_equal(sim.read_across_shots([live_flag])[0], flag_values)
    phase_errors = None
    if expected_phase is not None:
        phase_errors = np.flatnonzero(
            sim.read_phase_flipped_across_shots() != expected_phase).tolist()
        assert not phase_errors, dict(panel=label, phase_errors=phase_errors, seed=seed)
    return dict(panel=label, seed=seed, cases=cases, status='PASS',
                phase_errors=phase_errors,
                sampled_mean_T=sim.operation_statistics().num_toffoli_like/cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slots', type=int, default=35)
    parser.add_argument('--j-min', type=int, default=15)
    parser.add_argument('--weights', default='15,25,35')
    parser.add_argument('--per-weight', type=int, default=1)
    parser.add_argument('--without-seed', action='store_true')
    parser.add_argument('--keep-circuits', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert 1 <= args.slots <= 35 and 0 <= args.j_min < 35 and args.per_weight > 0
    full_seed = args.slots == 35 and not args.without_seed
    weights = [int(v) for v in args.weights.split(',')]
    args.output.mkdir(parents=True, exist_ok=True)
    events = []
    install_events(events)
    started = time.monotonic()
    cases, rejected, values, prefix_values, probe_values, masks, phase = fixtures(
        weights, args.per_weight, args.slots, args.j_min, full_seed)
    fixture_path = args.output/'fixtures.json'
    fixture_path.write_text(json.dumps(dict(cases=cases, rejected=rejected), indent=2)+'\n')
    print(json.dumps(dict(stage='fixtures_ready', cases=len(cases), weights=weights,
                          rejected=len(rejected), slots=args.slots)), flush=True)
    prefix_path, seam_path = args.output/'prefix.kmb', args.output/'seam.kmb'
    first_path, second_path = args.output/'build-a.kmb', args.output/'build-b.kmb'
    circuit, metrics, prefix_flag, seam_flag = build(
        args.slots, args.j_min, full_seed, events,
        prefix_path=prefix_path, seam_path=seam_path, label='first')
    circuit.to_file(first_path, format='kmb')
    sha = digest(first_path)
    runs = [simulate(circuit, values, masks, values, phase, seed) for seed in SEEDS]
    del circuit
    gc.collect()
    circuit, again, _, _ = build(args.slots, args.j_min, full_seed, events, label='second')
    circuit.to_file(second_path, format='kmb')
    assert metrics == again and sha == digest(second_path)
    del circuit
    gc.collect()
    circuit = km.Circuit.from_file(prefix_path, format='kmb')
    flags = np.array([bool(c['flags'][-1]) for c in cases]) if prefix_flag is not None else None
    runs += [simulate(circuit, values, masks, prefix_values, None, seed,
                      live_flag=prefix_flag, flag_values=flags, label='raw_prefix')
             for seed in SEEDS]
    del circuit
    gc.collect()
    if full_seed:
        circuit = km.Circuit.from_file(seam_path, format='kmb')
        gauges = np.array([bool(c['gauge']) for c in cases])
        runs += [simulate(circuit, values, masks, probe_values, None, seed,
                          live_flag=seam_flag, flag_values=gauges, label='seed_prefix')
                 for seed in SEEDS]
        del circuit
        gc.collect()
    report = dict(status='PASS_NATIVE_RAW_QUERY_EXTRACTOR_COMPONENT', slots=args.slots,
                  j_min=args.j_min, weights=weights, cases=len(cases), full_seed_seam=full_seed,
                  metrics=metrics, two_identical_builds=True, sha256=sha,
                  fixture_sha256=digest(fixture_path), circuit_bytes=first_path.stat().st_size,
                  runs=runs, elapsed_seconds=time.monotonic()-started,
                  scope='Actual syndrome-generated rawCRT inputs; fixed quantum queries/tail flags; component only, no complete decoder or failure certificate.')
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    if not args.keep_circuits:
        for path in (prefix_path, seam_path, first_path, second_path):
            if path.exists():
                path.unlink()


if __name__ == '__main__':
    main()
