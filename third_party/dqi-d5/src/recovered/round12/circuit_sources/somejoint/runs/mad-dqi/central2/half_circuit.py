"""Fixed-grade P1 half-Forney transform and native microcheck.

The interior-gap chart is intentionally not claimed correct here. Quantum
phase and restoration are checked against the exact implemented extension;
root-level mathematical agreement is reported separately. This is not the
official DQI verifier. R42/R43 half-degree identity and final factorization
are credited to the repository's earlier Astra phase work.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import runtime
import bezout_model as model
from border_circuit import apply_border, fixed_model, km, GF
import inplace_poly as poly
import numpy as np


def output_words(numerator):
    c = list(reversed(numerator))[::2]
    d = list(reversed(numerator))[1::2]
    out = []
    even, odd = [c[-1]]+d, c[:-1]
    for i in range(len(odd)):
        out.extend([even[i], odd[i]])
    out.append(even[-1])
    return out


def transform(b, numerator, denominator_tail, *, reverse=False,
              border=apply_border, counts=None):
    """Overwrite Omega by the fixed-reversal Forney polynomial.

    Locator coefficients are restored before returning. The result's natural
    coefficient order is returned as wire references, not extra registers.
    """
    size = len(numerator)
    assert size % 2 == 1 and len(denominator_tail) == size
    n = size//2
    assert n >= 1
    if counts is None:
        counts = Counter()
    a = list(reversed(denominator_tail))[::2]
    bb = list(reversed(denominator_tail))[1::2]  # Monic leading 1 is implicit.
    c = list(reversed(numerator))[::2]
    dd = list(reversed(numerator))[1::2]
    assert len(a) == len(c) == n+1 and len(bb) == len(dd) == n
    h0, h1, scalar = c[:-1], dd, c[-1]

    def root_basis(inv):
        # Both directions begin by square-rooting their current raw words and
        # end by squaring: these are inverse GF(2)-linear coordinate changes.
        for word in [*a, *bb, *c, *dd]:
            poly.transform_word(b, word, frobenius=2 if inv else 2048)

    def reduce_a():
        for i in range(n):
            b.ixor_gf2_mul(a[-1], bb[i], target=a[i], field=GF)
            counts["outer_products"] += 1

    def reduce_c():
        for i in range(n):
            b.ixor_gf2_mul(scalar, bb[i], target=h0[i], field=GF)
            counts["outer_products"] += 1

    def border_stage(inv):
        border(b, bb, a[:-1], [h0, h1], counts, reverse=inv, monic=True)

    def barnett_stage(inv):
        for words in (h0, h1):
            counts["outer_products"] += poly.barnett(b, bb, words, reverse=inv)

    def final_stage(inv):
        counts["outer_products"] += poly.final_map(b, a, bb, scalar, h0, h1, reverse=inv)

    root_basis(False)
    if not reverse:
        reduce_a()
        reduce_c()
        border_stage(False)
        barnett_stage(False)
        reduce_a()
        final_stage(False)
    else:
        final_stage(True)
        reduce_a()
        barnett_stage(True)
        border_stage(True)
        reduce_c()
        reduce_a()
    root_basis(True)
    return output_words(numerator)


def scalar_transform(original_sigma, original_omega, size):
    sigma = list(original_sigma)+[0]*(size+1-len(original_sigma))
    omega = list(original_omega)+[0]*(size-len(original_omega))
    s, w = list(reversed(sigma)), list(reversed(omega))
    a = [model.sqrt(v) for v in s[::2]]
    b = [model.sqrt(v) for v in s[1::2]]
    c = [model.sqrt(v) for v in w[::2]]
    d = [model.sqrt(v) for v in w[1::2]]
    n = size//2
    assert b[-1] == 1
    aa = [v ^ model.mul(a[-1], u) for v, u in zip(a[:-1], b[:-1])]
    cc = [v ^ model.mul(c[-1], u) for v, u in zip(c[:-1], b[:-1])]
    z0 = fixed_model(b[:-1], aa, cc, monic=True)
    z1 = fixed_model(b[:-1], aa, d, monic=True)
    h0 = model.matvec(model.bezout(b, [1]), z0)
    h1 = model.matvec(model.bezout(b, [1]), z1)
    q0 = model.pdiv(model.pmul(a, h0), b)[0]
    q1 = model.pdiv(model.pmul(a, h1), b)[0]
    even = model.padd(model.padd(q0, [c[-1]]), [0]+h1)
    odd = model.padd(h0, q1)
    out = [0]*size
    for i, value in enumerate(even):
        out[2*i] = model.mul(value, value)
    for i, value in enumerate(odd):
        out[2*i+1] = model.mul(value, value)
    return out


def check(degree=4, shots=256, seed=2026102521):
    start = time.monotonic()
    size = 2*degree+1
    rng = random.Random(seed)
    b = runtime.make_builder()
    numerator = [b.create_quantum_register(12, name=f"o{i}") for i in range(size)]
    denominator = [b.create_quantum_register(12, name=f"s{i+1}") for i in range(size)]
    words = numerator+denominator
    mask = b.create_classical_register(12*size, name="mask")
    counts = Counter()
    result_words = transform(b, numerator, denominator, counts=counts)
    forward_t = b.finish_circuit().operation_statistics().num_toffoli_like
    forward_counts = dict(counts)
    b.cz(mask, km.array([q for word in result_words for q in word]))
    transform(b, numerator, denominator, reverse=True, counts=counts)
    circuit = b.finish_circuit()
    build_seconds = time.monotonic()-start
    values = np.zeros((2*size, shots), dtype=np.uint16)
    masks = np.array([[rng.randrange(4096) for _ in range(shots)] for _ in range(size)], dtype=np.uint16)
    expected = []
    failures = []
    weights = Counter()
    for shot in range(shots):
        weight = shot % (size+1)
        weights[weight] += 1
        roots = rng.sample(range(1, 4096), weight)
        sigma = [1]
        for root in roots:
            sigma = model.pmul(sigma, [1, model.inv(root)])
        omega = [rng.randrange(4096) for _ in range(weight)]
        values[:len(omega), shot] = omega
        values[size:size+len(sigma)-1, shot] = sigma[1:]
        ff = scalar_transform(sigma, omega, size)
        expected.append(sum((v & int(m)).bit_count() for v, m in zip(ff, masks[:, shot])) & 1)
        derivative = [v if i % 2 else 0 for i, v in enumerate(sigma)][1:]
        correct = all(model.mul(root, model.peval(ff, model.inv(root))) ==
                      model.div(model.peval(omega, root), model.peval(derivative, root))
                      for root in roots)
        if not correct:
            failures.append(dict(shot=shot, weight=weight))
    sim = km.Simulator(batch_size=shots, seed=seed)
    sim.use_same_registers_as(circuit)
    bits = np.arange(12, dtype=np.uint16)[:, None]
    for i, word in enumerate(words):
        sim.write_across_shots(word, ((values[i][None, :] >> bits) & 1).astype(bool))
    sim.write_across_shots(mask, ((masks[:, None, :] >> bits[None, :, :]) & 1).reshape(-1, shots).astype(bool))
    sim.do(circuit)
    got = sim.read_phase_flipped_across_shots()
    assert np.array_equal(got, np.array(expected, dtype=bool)), {
        "phase_bad": np.flatnonzero(got != np.array(expected, dtype=bool)).tolist()}
    for i, word in enumerate(words):
        assert np.array_equal(sim.read_across_shots(word), ((values[i][None, :] >> bits) & 1).astype(bool)), i
    persistent = 24*size
    assert not sim.read_across_shots(km.array([km.q(i) for i in range(persistent, circuit.num_qubits)])).any()
    return dict(status="PASS", scope="exact implemented-chart phase/restoration, not official DQI verification",
                degree=degree, fixed_locator_grade=size, shots=shots, seed=seed,
                weights=dict(sorted(weights.items())), semantic_failures=failures,
                forward_toffolis=forward_t,
                roundtrip_toffolis=circuit.operation_statistics().num_toffoli_like,
                forward_arithmetic=forward_counts,
                qubits=circuit.num_qubits, persistent_qubits=persistent,
                scratch_qubits=circuit.num_qubits-persistent,
                instructions=len(circuit), build_seconds=build_seconds,
                total_seconds=time.monotonic()-start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.degree, args.shots)
    serialized = json.dumps(result, indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")
