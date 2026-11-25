#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Native first-two direct-carry panel on frozen C5 cases; root runs guard."""
from pathlib import Path
import argparse
import json
import ew_paths  # noqa: F401
import numpy as np
import check_extractor_width as Harness
import direct_carry_first2 as Extract

C5 = Harness.C5
ORIGINAL_FIXTURES = Harness.get_fixtures


def prefix_reference(raw, expected_heads, expected_flags, initial_carry=1):
    storage = list(raw)
    storage[0] = C5.value_at_node(C5.inverse(storage[0]), 0)
    r = C5.inverse(storage[1]) ^ C5.value_at_node(storage[0], 1)
    assert r
    difference = C5.Ref.KAPPAS[0] ^ C5.Ref.KAPPAS[1]
    storage[1] = C5.value_at_node(C5.scale(C5.inverse(r), difference), 1)
    assert storage[:2] == expected_heads[:2]
    assert expected_flags[:2] == [0, 0]
    carry = initial_carry
    for i in range(2, 35):
        n, d = (storage[i] if i == 2 else C5.multiply(carry, storage[i])), carry
        for old in range(i):
            p = C5.value_at_node(storage[old], i)
            difference = C5.Ref.KAPPAS[old] ^ C5.Ref.KAPPAS[i]
            n, d = C5.scale(d ^ C5.multiply(p, n), C5.Ref.INV[difference]), n
        assert n or d
        flag = int(n == 0)
        assert flag == expected_flags[i]
        if flag:
            n, d = d, n
        assert n
        storage[i] = C5.value_at_node(C5.multiply(d, C5.inverse(n)), i)
        assert storage[i] == expected_heads[i]
        carry = n
    return storage, carry


def get_fixtures(corpus, smoke, full_seed):
    source, old_cases, *_ = ORIGINAL_FIXTURES(corpus, smoke, full_seed)
    cases = []
    for old in old_cases:
        row = dict(old)
        storage, carry = prefix_reference(old['raw'], old['prefix_words'], old['flags'])
        row.update(initial_carry=1, old_C5_carry=old['prefix_carry'],
                   prefix_words=storage, prefix_carry=carry,
                   fixture_kind='immutable_C5_physical_input')
        cases.append(row)
    physical_count = len(cases)
    for weight in (16, 35):
        original = next(c for c in cases[:physical_count] if c['weight'] == weight)
        desired = (73+weight) << 12
        initial = C5.multiply(desired, C5.inverse(original['prefix_carry']))
        raw = list(original['raw'])
        raw[2] = C5.multiply(initial, raw[2])
        storage, carry = prefix_reference(raw, original['prefix_words'], original['flags'], initial)
        assert carry == desired
        row = dict(original)
        row.update(label='algebraic_initial_carry_extension:'+original['label'],
                   raw=raw, initial_carry=initial, prefix_words=storage, prefix_carry=carry,
                   fixture_kind='algebraic_initial_carry_extension',
                   extension_contract='word2=c*Y2; initialcarry=c unit; words0,1 raw; productionc=1')
        cases.append(row)
    for row in cases:
        if full_seed:
            words, carry, gauge = C5.seed_reference(
                row['prefix_words'], row['prefix_carry'], row['flags'][-1])
            control = gauge
        else:
            words, carry, gauge = row['prefix_words'], row['prefix_carry'], None
            control = row['flags'][-1]
        row.update(probe_words=words, probe_carry=carry, gauge=gauge, control=control)
    values = np.stack([C5.bits_of_data(c['raw'], c['initial_carry']) for c in cases], axis=1)
    prefix_values = np.stack([C5.bits_of_data(c['prefix_words'], c['prefix_carry'])
                              for c in cases], axis=1)
    probe_values = np.stack([C5.bits_of_data(c['probe_words'], c['probe_carry'])
                             for c in cases], axis=1)
    masks = np.random.default_rng(202611112701).integers(
        0, 2, size=values.shape, dtype=np.int8).astype(bool)
    phase = np.logical_xor.reduce(probe_values & masks, axis=0)
    phase ^= probe_values[0] & probe_values[47]
    phase ^= probe_values[181] & probe_values[863]
    phase ^= probe_values[11] & probe_values[425] & probe_values[841]
    phase ^= probe_values[7] & probe_values[528] & probe_values[852]
    phase ^= probe_values[19] & probe_values[577] & np.array([c['control'] for c in cases], bool)
    source.update(physical_cases=physical_count, algebraic_initial_carry_cases=2,
                  used_cases=len(cases),
                  count_scope='Physical C5 cases and two algebraic source-ABI cases are distinct.')
    return source, cases, values, prefix_values, probe_values, masks, phase


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--output', type=Path, required=True)
    args, _ = p.parse_known_args()
    Harness.Extract = Extract
    Harness.get_fixtures = get_fixtures
    Harness.main()
    path = args.output/'report.json'
    report = json.loads(path.read_text())
    report.update(variant='direct_unit_carry_with_public_first_two_charts',
                  expected_raw_arithmetic_static_T=149751,
                  C5_raw_arithmetic_static_T=154362,
                  expected_raw_arithmetic_static_delta_T=-4611,
                  expected_full_seam_static_delta_T=-4610,
                  first_two_inverse_domain='Exactly old activeN0,activeD1,activeN1 units',
                  final_carry_is_not_assumed_base_field=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(stage='first_two_report_complete',
                          component_static_T=report['metrics']['component_static_T'],
                          Q=report['metrics']['Q'], cases=report['cases'],
                          fixture_source=report['fixture_source']), indent=2), flush=True)


if __name__ == '__main__':
    main()
