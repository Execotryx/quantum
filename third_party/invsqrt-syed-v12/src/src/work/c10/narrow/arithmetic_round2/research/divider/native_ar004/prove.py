#!/usr/bin/env python3
# Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Native AR004 actual-domain/all-HMR component proof; no official run."""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'
from pathlib import Path
import argparse, hashlib, json, resource, sys, time
import numpy as np

HERE = Path(__file__).resolve().parent
NARROW = HERE.parents[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


for _pin in json.loads((HERE/'SOURCE_READY.json').read_text())['files']:
    _path = HERE/_pin['path']
    assert _path.stat().st_size == _pin['bytes'] and sha(_path) == _pin['sha256'], _pin['path']
sys.path[:0] = [str(HERE), str(NARROW/'native/candidate02'), str(NARROW/'native/candidate01')]
import variant
import adapter
adapter.verify()
d = variant.install()
cleanup = adapter.bind(d)
from common import km, array, with_registers, MODEL, MODEL_SHA
from branch_prover import Program, generated_text
from fourier_resource_expectation import exact_expectation
import checker31


def atomic(name, data):
    path = HERE/name
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, default=str)+'\n')
    temporary.replace(path)


def restore31(builder, current, original):
    current, original = list(current), list(original)
    assert len(current) == len(original) == 31 and builder.num_allocated_qubits == 31
    spare = list(builder.alloc_qubits(17))
    all_wires = set(current+spare)
    assert len(all_wires) == 48 and set(original) <= all_wires
    swaps = []
    for i, target in enumerate(original):
        source = current[i]
        if source == target:
            continue
        builder.swap(source, target)
        swaps.append([str(source), str(target)])
        for j in range(i+1, 31):
            if current[j] == target:
                current[j] = source
        current[i] = target
    builder.free(array(sorted(all_wires-set(original), key=str)))
    assert builder.num_allocated_qubits == 31
    return swaps


class OmittedPhaseProxy:
    """Proof-only deliberate error; never used by the production adapter."""
    def __init__(self, builder, token, omission):
        self.builder, self.omission, self.skipped = builder, omission, 0
        self.stack = []
        self.retirement_pair = (token.v[10], token.history[13])
        self.old_outcome = next(debt for j, _, debt in token.rows if j == 13).measurements[1]
    def __getattr__(self, name):
        return getattr(self.builder, name)
    def push_condition(self, outcome):
        self.stack.append(outcome)
        return self.builder.push_condition(outcome)
    def pop_condition(self):
        self.stack.pop()
        return self.builder.pop_condition()
    def cz(self, a, b):
        if self.omission == 'retirement' and not self.skipped and (a, b) == self.retirement_pair:
            assert self.stack
            self.skipped += 1
        else:
            self.builder.cz(a, b)
    def z(self, target):
        if self.omission == 'original_carry' and not self.skipped and self.old_outcome in self.stack and isinstance(target, km.q):
            self.skipped += 1
        else:
            self.builder.z(target)


def build(omission=None):
    builder = km.CircuitBuilder()
    builder.set_max_qubits(48)
    v, P, flags = [list(builder.alloc_qubits(n)) for n in (12, 15, 4)]
    original = v+P+flags
    token = d.compute_divider(builder, v, P, flags)
    forward = with_registers(builder.finish_circuit(), {'x':original})
    endpoint = dict(v=list(v), flags=list(flags), u=list(token.u), history=dict(token.history))
    assert builder.num_allocated_qubits == 43
    proxy = OmittedPhaseProxy(builder, token, omission) if omission else builder
    current = cleanup(proxy, token)
    if omission:
        assert proxy.skipped == 1 and not proxy.stack
    assert all(debt.consumed and not debt.measurements for _, _, debt in token.rows)
    swaps = restore31(builder, v+current+flags, original)
    complete = with_registers(builder.finish_circuit(), {'x':original})
    return forward, complete, v, P, flags, endpoint, swaps


def save(name, circuit, expected):
    kmb, kmx = HERE/(name+'.kmb'), HERE/(name+'.kmx')
    assert not kmb.exists() and not kmx.exists()
    circuit.to_file(str(kmb), format='kmb')
    text = generated_text(circuit)
    kmx.write_text(text)
    counts = exact_expectation(text)
    assert counts['mean_numeric'] == {'toffoli_like':float(expected), 'T':0.0, 'generic_rotations':0.0}, counts
    return dict(Q=circuit.num_qubits, native_expected_counts=counts, kmb_sha256=sha(kmb), kmx_sha256=sha(kmx))


def encode(v, P, flags):
    return np.asarray(v, dtype=np.uint64) | (np.asarray(P, dtype=np.uint64) << np.uint64(12)) | (np.asarray(flags, dtype=np.uint64) << np.uint64(27))


def model_input(xs):
    xs = np.asarray(xs, dtype=np.int64)
    assert np.all((1 <= xs) & (xs <= 3133452))
    leading = np.searchsorted(1 << np.arange(22, dtype=np.int64), xs, side='right')-1
    flags = (21-leading)//2
    n = xs << (2*flags)
    Q = np.sqrt(n << 4).astype(np.int64)
    assert np.all(Q*Q <= n << 4) and np.all((Q+1)*(Q+1) > n << 4)
    v, dd = Q-4096, 2*Q+1
    h = ((n << 6)-dd*dd)//64
    C, seed = np.asarray(MODEL['C'], dtype=np.int64)[v], np.asarray(MODEL['U0'], dtype=np.int64)[v]
    q, total = h+512, np.zeros(len(xs), dtype=np.int64)
    for i in range(10):
        shift = 8-i
        term = (C+(1 << (shift-1))) >> shift if shift > 0 else C if shift == 0 else 2*C+1
        total += (2*((q >> i) & 1)-1)*term
    U = seed-total//2
    assert np.all((-16384 <= U) & (U < 16384))
    return v, U & 32767, flags


def endpoint_values(v, P):
    v, P = np.asarray(v, dtype=np.int64), np.asarray(P, dtype=np.int64)
    V = 4096+v
    u = 4094-3*v+((P >> 13) & 1)-2*((P >> 14) & 1)+((P >> 12) & 1)
    u = ((u+8192) & 16383)-8192
    history = {}
    for j in range(12, 36):
        sign = (u < 0).astype(np.int64)
        if j <= 24:
            history[j] = sign.copy()
            previous = (P >> (24-j)) & 1
            current = (P >> (23-j)) & 1 if j < 24 else np.zeros_like(P)
            nxt = 2*u+(2*sign-1)*V+sign+current-previous
        else:
            k = j-26 if j >= 28 else 0
            A = (((V >> (k+1))+((V >> k) & 1)) << (k+1))-(V & 1) if k else V
            nxt = 2*u+sign+(2*sign-1)*A
        u = ((nxt+8192) & 16383)-8192
    return u & 16383, history


def sample_xs(seed):
    roots = np.arange(4096, 8192, dtype=np.int64)
    low_n = (roots*roots+15)//16
    high_n = ((roots+1)*(roots+1)+15)//16-1
    low_x, high_x = (low_n+3)//4, high_n//4
    assert np.array_equal(model_input(low_x)[0], roots-4096)
    assert np.array_equal(model_input(high_x)[0], roots-4096)
    random = np.random.default_rng(seed+47004).integers(1, 3133453, size=8192, dtype=np.int64)
    boundary = [max(1, min(3133452, (1 << i)+a)) for i in range(22) for a in (-1, 0, 1)] + [3133452]
    random[:len(boundary)] = boundary
    return np.concatenate((low_x, high_x, random))


def bits(values, width):
    return ((np.asarray(values, dtype=np.uint64)[None, :] >> np.arange(width, dtype=np.uint64)[:, None]) & 1).astype(bool)


def read(simulator, wires):
    return (simulator.read_across_shots(array(wires)).astype(np.uint64) << np.arange(len(wires), dtype=np.uint64)[:, None]).sum(axis=0)


def native_samples(forward, circuit, v, P, flags, endpoint):
    rows, original = [], v+P+flags
    for seed in (0, 1, 2, 3):
        xs = sample_xs(seed)
        vv, pp, ff = model_input(xs)
        expected_u, expected_history = endpoint_values(vv, pp)
        for mode, current in (('forward_data', forward), ('roundtrip', circuit)):
            sim = km.Simulator(batch_size=256, seed=seed, counting_operations=True)
            keep = set(endpoint['v']+endpoint['flags']+endpoint['u']+list(endpoint['history'].values())) if mode == 'forward_data' else set(original)
            scratch = [km.q(i) for i in range(current.num_qubits) if km.q(i) not in keep]
            for first in range(0, len(xs), 256):
                stop = first+256
                sim.clear_for_shot()
                for wires, values in ((v, vv), (P, pp), (flags, ff)):
                    sim.write_across_shots(array(wires), bits(values[first:stop], len(wires)))
                sim.do(current)
                assert np.array_equal(read(sim, v), vv[first:stop].astype(np.uint64))
                assert np.array_equal(read(sim, flags), ff[first:stop].astype(np.uint64))
                if mode == 'forward_data':
                    assert np.array_equal(read(sim, endpoint['u']), expected_u[first:stop].astype(np.uint64))
                    for j, wire in endpoint['history'].items():
                        assert np.array_equal(read(sim, [wire]), expected_history[j][first:stop].astype(np.uint64))
                else:
                    assert np.array_equal(read(sim, P), pp[first:stop].astype(np.uint64))
                    assert all(sim.read_shot_phase(i) % 2 == 0 for i in range(256))
                assert not sim.read_across_shots(array(scratch)).any()
            rows.append(dict(seed=seed, mode=mode, valid_original_inputs=len(xs), root_boundary_inputs=8192,
                original_x_digest=hashlib.sha256(xs.astype('<u4').tobytes()).hexdigest(),
                exact_endpoint_data=mode == 'forward_data', exact_zero_roundtrip_phase=mode == 'roundtrip',
                forward_carry_phases_intentionally_deferred=mode == 'forward_data',
                sampled_mean_Toffolis=sim.operation_statistics().num_toffoli_like/len(xs)))
    return rows


def selftest():
    header = '\n'.join([f'APPEND_TO_REGISTER q{i} 0' for i in range(31)]+['REGISTER 0 x'])+'\n'
    xs, zero = np.arange(1, 18, dtype=np.uint64), np.zeros(17, dtype=np.uint64)
    good = [header+'CX q0 q31\nHMR q31 b0\nZ q0 if b0\nR q31\n',
        header+'X q31\nHMR q31 b0\nZ b0\nR q31\n',
        header+'HMR q31 b0\nCCX q0 q1 q32 if b0\nHMR q32 b1 if b0\nPUSH_CONDITION if b0\nCZ q0 q1 if b1\nPOP_CONDITION\nR q32\n']
    for text in good:
        checker31.prove_native_chunk(Program(text), xs, zero)
    bad = [('missing HMR phase', header+'CX q0 q31\nHMR q31 b0\n'),
        ('dirty reset', header+'X q31\nR q31\n'), ('wrong input', header+'X q0\n'), ('wrong phase', header+'Z q0\n')]
    for label, text in bad:
        try:
            checker31.prove_native_chunk(Program(text), xs, zero)
        except AssertionError:
            pass
        else:
            raise AssertionError(label)
    return dict(positive=3, negative=4, native_phase_modulus=2, input_register_bits=31,
        checker_sha256=sha(HERE/'checker31.py'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk', type=int, default=65536)
    args = parser.parse_args()
    assert 1 <= args.chunk <= 65536 and not (HERE/'NATIVE_PROOF.json').exists()
    began = time.monotonic()
    checks = selftest()
    forward, circuit, v, P, flags, endpoint, swaps = build()
    original_forward = HERE.parent/'native_ar003/forward_endpoint.kmx'
    assert generated_text(forward) == original_forward.read_text()
    resources = dict(forward=save('forward_endpoint', forward, 270), roundtrip=save('divider_roundtrip', circuit, 578))
    assert circuit.num_qubits == 48
    negative_inputs = encode(*model_input(sample_xs(0)))
    negatives = []
    for omission in ('retirement', 'original_carry'):
        _, wrong, *_ = build(omission)
        wrong_text = generated_text(wrong)
        (HERE/f'negative_{omission}.kmx').write_text(wrong_text)
        try:
            checker31.prove_native_chunk(Program(wrong_text), negative_inputs, np.zeros(len(negative_inputs), dtype=np.uint64))
        except AssertionError as error:
            assert 'phase' in str(error).lower(), ('Negative probe failed outside its intended phase check', omission, str(error))
            negatives.append(dict(omitted=omission, rejected=True, error=str(error), native_text_sha256=hashlib.sha256(wrong_text.encode()).hexdigest()))
        else:
            raise AssertionError('Native negative phase probe passed:'+omission)
    samples = native_samples(forward, circuit, v, P, flags, endpoint)
    program = Program(generated_text(circuit))
    assert program.measurements == 583
    rows, digest = [], hashlib.sha256()
    for first in range(1, 3133453, args.chunk):
        xs = np.arange(first, min(3133453, first+args.chunk), dtype=np.uint64)
        inputs = encode(*model_input(xs))
        digest.update(inputs.astype('<u8').tobytes())
        receipt = checker31.prove_native_chunk(program, inputs, np.zeros(len(xs), dtype=np.uint64))
        rows.append(dict(original_first=first, original_stop=int(xs[-1])+1, **receipt))
        atomic('all_inputs.partial.json', dict(status='PARTIAL_NOT_COMPLETE', proved_inputs=sum(r['inputs'] for r in rows), chunks=rows))
        if len(rows) % 12 == 0:
            print(json.dumps(dict(progress='AR004_native_all_input_HMR', inputs=sum(r['inputs'] for r in rows), seconds=time.monotonic()-began)), flush=True)
    assert sum(r['inputs'] for r in rows) == 3133452
    frozen_baseline = json.loads((HERE.parent/'native_ar003/NATIVE_PROOF.json').read_text())
    assert digest.hexdigest() == frozen_baseline['component_input_digest']
    result = dict(status='PASS_NATIVE_AR004_DIVIDER_COMPONENT_NOT_OFFICIAL', resources=resources,
        forward_native_text_identical_to_candidate07_arithmetic=True, frozen_forward_native_sha256=sha(original_forward),
        unchanged_endpoint_owners=43, inverse_intermediate_data_owners=42, restoration_Toffolis=1,
        negative_phase_probes=negatives, native_simulator=samples, all_original_inputs=3133452,
        every_HMR_transcript_proved=True, independent_HMR_variables=program.measurements,
        exact_zero_roundtrip_phase=True, original_input_values_and_all_scratch_restored=True,
        all_resets_provably_zero=True, original_input_interval=[1, 3133453], end_exclusive=True,
        phase_modulus=2, component_input_digest=digest.hexdigest(), frozen_AR003_input_digest_matched=True, chunks=rows,
        proof_fixture_layout_swaps=swaps, original_divider_E=587.5, new_divider_E=578.0,
        saving_E=9.5, saving_over_AR003_E=8.5, all24_CarryDebts_consumed=True,
        unrestricted_root_product_promise_not_claimed=True,
        endpoint_phase_model_and_all_frozen_sources_unchanged=True, model_sha256=MODEL_SHA,
        adapter_sha256=sha(HERE/'adapter.py'), kernel_sha256=sha(adapter.KERNEL),
        proof_sha256=sha(Path(__file__)), checker_sha256=sha(HERE/'checker31.py'),
        source_ready_sha256=sha(HERE/'SOURCE_READY.json'), inputs_sha256=sha(HERE/'INPUTS.json'),
        acceptance_sha256=adapter.ACCEPTANCE_SHA, checker_selftest=checks,
        whole_fusion_native_or_official_qualification=False, official_verifier_run=False,
        seconds=time.monotonic()-began, peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    atomic('NATIVE_PROOF.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('chunks', 'native_simulator')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
