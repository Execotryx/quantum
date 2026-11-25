"""P1 reversible ordinary-border microcircuit; not a full DQI decoder.

The rank-one Bezoutian schedule is independently implemented here. Arithmetic
comes through the parent's reviewed Apache-2.0 paired-v6 adapter; see its
NOTICE. Low-space inverse implementation is ViberTeam's norm-recycling/HMR
method, read in full before reuse. Every pivot uses a reversible zero-to-one
extension. This does not claim interior degree-gap correctness.
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

runtime.make_builder()  # Import reviewed builder dependencies and native ABI.
from common import km
from smallspace_inverse import init_smallspace_inverse, clear_inverse_hmr
import numpy as np

GF = km.GF2Field(12)


class Scaling:
    """Low-space shared pivot inverse; one field product per scaled word."""
    def __init__(self, b, pivot, counts):
        self.b, self.pivot, self.counts = b, pivot, counts
        self.zero = b.alloc_qubits(1)[0]
        b.flip_if_equal(pivot, 0, target=self.zero)
        b.cx(self.zero, pivot[0])
        self.inverse = init_smallspace_inverse(b, pivot, field=GF)
        self.tmp = b.alloc_qubits(12)
        counts["inverse_groups"] += 1

    def apply(self, word, divide):
        b = self.b
        factor, undo = ((self.inverse, self.pivot) if divide
                        else (self.pivot, self.inverse))
        b.ixor_gf2_mul(word, factor, target=self.tmp, field=GF)
        b.swap(word, self.tmp)
        b.del_gf2_mul(word, undo, target=self.tmp, field=GF)
        self.counts["scales"] += 1

    def close(self):
        b = self.b
        b.free(self.tmp)
        clear_inverse_hmr(b, self.pivot, self.inverse, field=GF)
        b.free(self.inverse)
        b.cx(self.zero, self.pivot[0])
        b.flip_if_equal(self.pivot, 0, target=self.zero)
        b.free(self.zero)


def product(b, lhs, rhs, target, counts):
    b.ixor_gf2_mul(lhs, rhs, target=target, field=GF)
    counts["products"] += 1


def divide_locator(b, p, d, scale, counts, *, reverse=False, monic=False):
    """P -> [r_low,q0,q1], or [r_low,q0] if its leading 1 is implicit."""
    n = len(d)
    assert len(p) == n + (0 if monic else 1)
    q1 = scale.inverse if monic else p[n]

    def high_scale():
        if not monic:
            scale.apply(p[n], divide=not reverse)

    def shifted_update():
        for i in range(1, n):
            product(b, q1, d[i-1], p[i], counts)

    def constant_scale():
        scale.apply(p[n-1], divide=not reverse)

    def constant_update():
        for i in range(n-1):
            product(b, p[n-1], d[i], p[i], counts)

    actions = [high_scale, shifted_update, constant_scale, constant_update]
    for action in reversed(actions) if reverse else actions:
        action()


def apply_border(b, p, d, vectors, counts, *, reverse=False, monic=False, recurse=None):
    """Apply inverse Bezoutian on fixed-size ordinary/terminal-zero chart."""
    n = len(d)
    assert len(p) == n + (0 if monic else 1)
    assert all(len(v) == n for v in vectors)
    if n == 1:
        # Two serial scalar groups avoid a held 12-bit product pivot.
        pivots = [d[0]] if monic else [p[1], d[0]]
        for pivot in reversed(pivots) if reverse else pivots:
            scale = Scaling(b, pivot, counts)
            for v in vectors:
                scale.apply(v[0], divide=not reverse)
            scale.close()
        return

    def low_update():
        for v in vectors:
            for i in range(n-1):
                product(b, d[i], v[n-1], v[i], counts)

    def high_update():
        for v in vectors:
            for i in range(n-1):
                product(b, d[i], v[i], v[n-1], counts)

    def enter(inv):
        scale = Scaling(b, d[n-1], counts)
        if not inv:
            for v in vectors:
                scale.apply(v[n-1], divide=True)
            low_update()
            divide_locator(b, p, d, scale, counts, monic=monic)
            if monic:
                for v in vectors:
                    scale.apply(v[n-1], divide=False)
        else:
            if monic:
                for v in vectors:
                    scale.apply(v[n-1], divide=True)
            divide_locator(b, p, d, scale, counts, reverse=True, monic=monic)
            low_update()
            for v in vectors:
                scale.apply(v[n-1], divide=False)
        scale.close()

    def quotient_scale(inv):
        if monic:
            return
        scale = Scaling(b, p[n], counts)
        for v in vectors:
            scale.apply(v[n-1], divide=not inv)
        scale.close()

    def descend(inv):
        child = apply_border if recurse is None else recurse
        child(b, d, p[:n-1], [v[:n-1] for v in vectors], counts, reverse=inv)

    def leave(inv):
        scale = Scaling(b, d[n-1], counts)
        if not inv:
            high_update()
            for v in vectors:
                scale.apply(v[n-1], divide=True)
            divide_locator(b, p, d, scale, counts, reverse=True, monic=monic)
        else:
            divide_locator(b, p, d, scale, counts, monic=monic)
            for v in vectors:
                scale.apply(v[n-1], divide=False)
            high_update()
        scale.close()

    actions = [enter, quotient_scale, descend, leave]
    for action in reversed(actions) if reverse else actions:
        action(reverse)


def fixed_model(p, d, rhs, *, monic=False):
    """Literal scalar version of this reversible extension, on all inputs."""
    p, d, rhs = list(p), list(d), list(rhs)
    n = len(d)
    assert len(p) == n + (0 if monic else 1)
    if n == 1:
        value = rhs[0]
        if not monic:
            value = model.div(value, p[1] or 1)
        return [model.div(value, d[0] or 1)]
    den = d[-1] or 1
    hi = model.div(rhs[-1], den)
    low = [v ^ model.mul(c, hi) for v, c in zip(rhs[:-1], d[:-1])]
    q1 = model.inv(den) if monic else model.div(p[-1], den)
    for i in range(1, n):
        p[i] ^= model.mul(q1, d[i-1])
    q0 = model.div(p[n-1], den)
    for i in range(n-1):
        p[i] ^= model.mul(q0, d[i])
    hi = model.mul(hi, den) if monic else model.div(hi, q1 or 1)
    low = fixed_model(d, p[:n-1], low)
    hi ^= model.xor(model.mul(c, v) for c, v in zip(d[:-1], low))
    return low+[model.div(hi, den)]


def check(degree=4, shots=128, monic=True, seed=2026102520, *,
          kernel=apply_border, scalar=fixed_model, forced_gaps=False):
    start = time.monotonic()
    rng = random.Random(seed)
    b = runtime.make_builder()
    p = [b.create_quantum_register(12, name=f"p{i}")
         for i in range(degree + (0 if monic else 1))]
    d = [b.create_quantum_register(12, name=f"d{i}") for i in range(degree)]
    vectors = [[b.create_quantum_register(12, name=f"v{k}_{i}")
                for i in range(degree)] for k in range(2)]
    words = p+d+vectors[0]+vectors[1]
    mask = b.create_classical_register(24*degree, name="mask")
    counts = Counter()
    kernel(b, p, d, vectors, counts, monic=monic)
    forward_stats = b.finish_circuit().operation_statistics()
    forward_t = forward_stats.num_toffoli_like
    forward_counts = dict(counts)
    b.cz(mask, km.array([q for v in vectors for word in v for q in word]))
    kernel(b, p, d, vectors, counts, reverse=True, monic=monic)
    circuit = b.finish_circuit()
    build_seconds = time.monotonic()-start
    data = np.array([[rng.randrange(4096) for _ in range(shots)] for _ in words], dtype=np.uint16)
    masks = np.array([[rng.randrange(4096) for _ in range(shots)]
                      for _ in range(2*degree)], dtype=np.uint16)
    # Structured zero-pivot inputs test the unit extension rather than merely
    # assuming that random nonzero pivots cover HMR cleanup.
    data[:, 0] = 0
    for shot in range(1, min(shots, degree+2)):
        k = shot % (degree+1)
        data[:k, shot] = 0
        data[len(p):len(p)+k, shot] = 0
        data[len(p)+len(d):len(p)+len(d)+k, shot] = 0
        data[len(p)+len(d)+degree:len(p)+len(d)+degree+k, shot] = 0
    if forced_gaps:
        assert degree >= 2
        for shot in range(shots):
            if shot % 2:
                data[len(p)+len(d)-1, shot] = 0
                data[len(p)+len(d)-2, shot] = rng.randrange(1, 4096)
            if shot % 8 == 0:
                data[0, shot] = 0
    expected = []
    semantic_cases = 0
    for shot in range(shots):
        pp = [int(v) for v in data[:len(p), shot]]
        dd = [int(v) for v in data[len(p):len(p)+len(d), shot]]
        out = []
        for k in range(2):
            begin = len(p)+len(d)+k*degree
            vv = [int(v) for v in data[begin:begin+degree, shot]]
            zz = scalar(pp, dd, vv, monic=monic)
            out += zz
            full_p = pp+[1] if monic else pp
            if model.matvec(model.bezout(full_p, dd), zz) == vv:
                semantic_cases += 1
        expected.append(sum((x & int(y)).bit_count() for x, y in zip(out, masks[:, shot])) & 1)
    sim = km.Simulator(batch_size=shots, seed=seed)
    sim.use_same_registers_as(circuit)
    bit_indices = np.arange(12, dtype=np.uint16)[:, None]
    for i, word in enumerate(words):
        sim.write_across_shots(word, ((data[i][None, :] >> bit_indices) & 1).astype(bool))
    sim.write_across_shots(mask, ((masks[:, None, :] >> bit_indices[None, :, :]) & 1).reshape(-1, shots).astype(bool))
    sim.do(circuit)
    actual = sim.read_phase_flipped_across_shots()
    assert np.array_equal(actual, np.array(expected, dtype=bool)), {
        "phase_bad": np.flatnonzero(actual != np.array(expected, dtype=bool)).tolist()}
    for i, word in enumerate(words):
        assert np.array_equal(sim.read_across_shots(word), ((data[i][None, :] >> bit_indices) & 1).astype(bool)), i
    persistent = 12*len(words)
    scratch = km.array([km.q(i) for i in range(persistent, circuit.num_qubits)])
    assert not sim.read_across_shots(scratch).any()
    return dict(status="PASS", scope="fixed-chart microcircuit, not official DQI verification",
                degree=degree, monic=monic, shots=shots, seed=seed,
                semantic_rhs_cases=semantic_cases, total_rhs_cases=2*shots,
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
    parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--nonmonic", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.degree, args.shots, not args.nonmonic)
    serialized = json.dumps(result, indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")
