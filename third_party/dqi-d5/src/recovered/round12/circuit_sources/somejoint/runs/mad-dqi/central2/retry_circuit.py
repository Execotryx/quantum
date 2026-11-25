"""P1 first-gap repair by a controlled multiplication-by-x chart.

Barnett identity: Bez(P,xD)=Mx Bez(P,D). A first-order gap is repaired by
D->xD and by applying Mx to both RHS before the ordinary inverse solve.
One five-bit recursion pointer remembers the first active repair. Further
interior gaps and a coincident zero P(0) remain explicit approximations.

Controlled-scaling HMR identity is adapted from the fully read attributed
SomeJoint/ViberTeam `scale_active_reused_mask` routine. No syndrome is
measured; all predicate/history bits are reversibly restored.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import runtime
from border_circuit import Scaling, apply_border, GF, km
from half_circuit import transform, output_words
from forney_bezout import root_scan


def controlled_scale(scale, word, control, *, divide):
    b = scale.b
    factor, undo = ((scale.inverse, scale.pivot) if divide
                    else (scale.pivot, scale.inverse))
    b.ixor_gf2_mul(word, factor, target=scale.tmp, field=GF)
    b.cswap(control, word, scale.tmp)
    measured = b.alloc_bits(12)
    b.hmr(scale.tmp, measured)
    b.gf2_phase_by_product(word, factor, mask=measured, field=GF)
    b.init_and(control, word, scale.tmp)
    b.cx(undo, factor)
    b.gf2_phase_by_product(scale.tmp, factor, mask=measured, field=GF)
    b.cx(undo, factor)
    b.del_and(control, word, scale.tmp)
    b.free(measured)
    scale.counts["controlled_scales"] += 1


def rotate(b, words, flag, *, reverse=False):
    indices = range(len(words)-1) if reverse else reversed(range(len(words)-1))
    for i in indices:
        b.cswap(flag, words[i], words[i+1])


def companion(b, p, vectors, flag, counts, *, reverse=False, monic=False):
    n = len(vectors[0])
    assert all(len(v) == n for v in vectors)
    assert len(p) == n+(0 if monic else 1)

    def permutation(inv):
        for v in vectors:
            rotate(b, v, flag, reverse=inv)
            counts["controlled_word_swaps"] += n-1

    def leading_scale(inv):
        if monic:
            return
        scale = Scaling(b, p[-1], counts)
        for v in vectors:
            controlled_scale(scale, v[0], flag, divide=not inv)
        scale.close()

    def update(inv):
        for v in vectors:
            masked = b.alloc_qubits(12)
            b.init_and(flag, v[0], masked)
            counts["mask_ands"] += 12
            for i in range(1, n):
                b.ixor_gf2_mul(p[i], masked, target=v[i], field=GF)
                counts["companion_products"] += 1
            b.del_and(flag, v[0], masked)
            b.free(masked)

    def constant_scale(inv):
        scale = Scaling(b, p[0], counts)
        for v in vectors:
            controlled_scale(scale, v[0], flag, divide=inv)
        scale.close()

    actions = [permutation, leading_scale, update, constant_scale]
    for action in reversed(actions) if reverse else actions:
        action(reverse)


class FirstGap:
    def __init__(self, b, degree, counts):
        self.b, self.degree, self.counts = b, degree, counts
        self.pointer = b.alloc_qubits(degree.bit_length())

    def predicate(self, d, flag):
        b = self.b
        top, next_zero, empty, conjunction = [b.alloc_qubits(1)[0] for _ in range(4)]
        b.flip_if_equal(d[-1], 0, target=top)
        b.flip_if_equal(d[-2], 0, target=next_zero)
        b.x(next_zero)
        b.flip_if_equal(self.pointer, 0, target=empty)
        b.init_and(top, next_zero, conjunction)
        b.ccx(conjunction, empty, flag)
        b.del_and(top, next_zero, conjunction)
        b.flip_if_equal(self.pointer, 0, target=empty)
        b.x(next_zero)
        b.flip_if_equal(d[-2], 0, target=next_zero)
        b.flip_if_equal(d[-1], 0, target=top)
        b.free(km.array([top, next_zero, empty, conjunction]))
        self.counts["gap_predicates"] += 1

    def xor_code(self, flag, code):
        for bit, wire in enumerate(self.pointer):
            if code >> bit & 1:
                self.b.cx(flag, wire)

    def push(self, d, code):
        b = self.b
        flag = b.alloc_qubits(1)[0]
        self.predicate(d, flag)
        self.xor_code(flag, code)
        b.flip_if_equal(self.pointer, code, target=flag)
        b.free(flag)

    def pop(self, d, code):
        b = self.b
        flag = b.alloc_qubits(1)[0]
        b.flip_if_equal(self.pointer, code, target=flag)
        self.xor_code(flag, code)
        self.predicate(d, flag)
        b.free(flag)

    def read(self, code):
        flag = self.b.alloc_qubits(1)[0]
        self.b.flip_if_equal(self.pointer, code, target=flag)
        return flag

    def unread(self, code, flag):
        self.b.flip_if_equal(self.pointer, code, target=flag)
        self.b.free(flag)

    def run(self, b, p, d, vectors, counts, *, reverse=False, monic=False):
        n = len(d)
        if n == 1:
            return apply_border(b, p, d, vectors, counts, reverse=reverse, monic=monic)
        code = self.degree-n+1
        self.push(d, code)
        flag = self.read(code)
        rotate(b, d, flag)
        counts["controlled_word_swaps"] += n-1
        if not reverse:
            companion(b, p, vectors, flag, counts, monic=monic)
        self.unread(code, flag)
        apply_border(b, p, d, vectors, counts, reverse=reverse, monic=monic,
                     recurse=self.run)
        flag = self.read(code)
        if reverse:
            companion(b, p, vectors, flag, counts, reverse=True, monic=monic)
        rotate(b, d, flag, reverse=True)
        counts["controlled_word_swaps"] += n-1
        self.unread(code, flag)
        self.pop(d, code)

    def close(self):
        self.b.free(self.pointer)


def first_gap_border(b, p, d, vectors, counts, *, reverse=False, monic=False):
    repair = FirstGap(b, len(d), counts)
    repair.run(b, p, d, vectors, counts, reverse=reverse, monic=monic)
    repair.close()


def translate(b, words):
    """In-place x->x+1 Taylor shift over characteristic two, self-inverse."""
    bit = 1
    while bit < len(words):
        for i in range(len(words)):
            if not (i & bit) and i+bit < len(words):
                source, target = words[i+bit], words[i]
                assert not isinstance(target, int)
                if isinstance(source, int):
                    b.gf2_iadd(source, target=target, field=GF)
                else:
                    b.cx(source, target)
        bit *= 2


def translated_transform(b, numerator, denominator_tail, *, reverse=False,
                         counts=None):
    counts = Counter() if counts is None else counts
    s = list(reversed(denominator_tail))+[1]
    w = list(reversed(numerator))
    f = output_words(numerator)
    translate(b, s)
    translate(b, f if reverse else w)
    result = transform(b, numerator, denominator_tail, reverse=reverse,
                       border=first_gap_border, counts=counts)
    translate(b, s)
    translate(b, w if reverse else f)
    return result


def forney(b, numerator, denominator_tail, outcomes, *, field):
    counts = Counter()
    values = translated_transform(b, numerator, denominator_tail, counts=counts)
    root_scan(b, values, denominator_tail, outcomes, field=field)
    translated_transform(b, numerator, denominator_tail, reverse=True, counts=counts)
    b.bezout_phase_arithmetic = dict(counts)


def count(degree=17):
    start = time.monotonic()
    size = 2*degree+1
    b = runtime.make_builder()
    numerator = [b.create_quantum_register(12, name=f"o{i}") for i in range(size)]
    denominator = [b.create_quantum_register(12, name=f"s{i+1}") for i in range(size)]
    counts = Counter()
    translated_transform(b, numerator, denominator, counts=counts)
    circuit = b.finish_circuit()
    return dict(kind="native forward resource count, no correctness test",
                degree=degree, forward_toffolis=circuit.operation_statistics().num_toffoli_like,
                active_4025_phase_projection=2*circuit.operation_statistics().num_toffoli_like+4025*11,
                persistent_qubits=24*size, qubits=circuit.num_qubits,
                scratch_qubits=circuit.num_qubits-24*size,
                counts=dict(counts), instructions=len(circuit),
                seconds=time.monotonic()-start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--degree", type=int, default=17)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = count(args.degree)
    serialized = json.dumps(result, indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")
