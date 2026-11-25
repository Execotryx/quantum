#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Four-fixture, pure-stdlib exact check of unit rather than reciprocal carry.

No native library, circuit builder, sampler or census is imported.  This is
an algebraic screen, not a complete validation or an official verification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
MODULUS, DELTA = 0x1053, 2048


def mul(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & 4096:
            a ^= MODULUS
    return result


def power(a, n):
    result = 1
    while n:
        if n & 1:
            result = mul(result, a)
        a = mul(a, a)
        n >>= 1
    return result


def kmul(a, b):
    a0, a1, b0, b1 = a & 4095, a >> 12, b & 4095, b >> 12
    aa, bb = mul(a0, b0), mul(a1, b1)
    return (aa ^ mul(DELTA, bb)) | ((mul(a0 ^ a1, b0 ^ b1) ^ aa) << 12)


def kinverse(a):
    assert a
    x, y = a & 4095, a >> 12
    norm = mul(x, x) ^ mul(x, y) ^ mul(DELTA, mul(y, y))
    assert norm
    inv = power(norm, 4094)
    out = mul(x ^ y, inv) | (mul(y, inv) << 12)
    assert kmul(a, out) == 1
    return out


def kscale(a, scale):
    return mul(a & 4095, scale) | (mul(a >> 12, scale) << 12)


def node_value(head, i):
    return (head & 4095) ^ mul(2*i, head >> 12) | (head & (4095 << 12))


def run_row(row):
    old = row['boundary_oracle']
    raw, heads = old['raw_queries'], old['heads']
    kappas = [DELTA ^ mul(2*i, 2*i) ^ 2*i for i in range(35)]
    inverses = {(a, b):power(kappas[a] ^ kappas[b], 4094)
                for b in range(35) for a in range(b)}
    old_carry = direct_carry = 1
    steps = []
    for i in range(35):
        pairs = []
        for carry in (old_carry, direct_carry):
            n, d = kmul(carry, raw[i]), carry
            for j in range(i):
                n, d = kscale(d ^ kmul(node_value(heads[j], i), n),
                              inverses[j, i]), n
            assert n or d
            flag = int(n == 0)
            if flag:
                n, d = d, n
            assert n
            head = kmul(d, kinverse(n))
            assert node_value(head, i) == heads[i]
            assert flag == old['tail_flags'][i]
            pairs.append((n, d, flag))
        ratio = kmul(direct_carry, kinverse(old_carry))
        assert pairs[1][0] == kmul(ratio, pairs[0][0])
        assert pairs[1][1] == kmul(ratio, pairs[0][1])
        old_carry = kinverse(pairs[0][0])
        direct_carry = pairs[1][0]
        steps.append(dict(index=i, old_carry=old_carry, direct_carry=direct_carry,
                          direct_is_base_field=direct_carry < 4096,
                          tail_flag=pairs[1][2]))
    assert old_carry == old['raw_carry']
    low, high = direct_carry & 4095, direct_carry >> 12
    gauge = int(low == 0)
    selected = high if gauge else low
    assert selected
    return dict(label=row['label'], weight=row['weight'],
                old_carry=old_carry, direct_carry=direct_carry,
                direct_low=low, direct_high=high,
                final_direct_carry_is_base_field=(high == 0),
                old_gauge=old['gauge'], direct_gauge=gauge,
                direct_selected_lambda=selected,
                old_selected_lambda=old['selected_lambda'],
                selected_scale_ratio=mul(selected, power(old['selected_lambda'], 4094)),
                all_heads_and_flags_equal=True, all_source_units=True, steps=steps)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    started = time.monotonic()
    path = WORK/'night_c27/arithmetic/panel_audit/key-boundary-full/fixtures.json'
    rows = json.loads(path.read_text())
    indices = {next(i for i, r in enumerate(rows) if r['weight'] == j)
               for j in (15, 16, 35)}
    indices.update(i for i, r in enumerate(rows) if r['boundary_oracle']['gauge'] == 1)
    assert len(indices) == 4
    result = [run_row(rows[i]) for i in sorted(indices)]
    report = dict(status='PASS_FOUR_FIXTURE_SCALAR_CARRY_EQUIVALENCE_ONLY',
                  fixture_path=str(path),
                  fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  modulus=MODULUS, delta=DELTA, cases=result,
                  final_carry_always_base_field_screen=all(
                      r['final_direct_carry_is_base_field'] for r in result),
                  native_check=False, official_verifier=False,
                  elapsed_seconds=time.monotonic()-started)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in report.items() if k != 'cases'},
                      'cases':[{k:v for k,v in row.items() if k != 'steps'} for row in result]},
                     indent=2))


if __name__ == '__main__':
    main()
