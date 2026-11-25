#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-run exact finite occupancy certificate for a classical gauge proposal.

Standard library only. No project/native imports, random draws, circuit,
sampler, census, or statistical confidence calculation. The physical model
is4025 independent uniform12-bit residual labels plus one fixed zero pivot.
The capped chooser includes label0 first and caps all histogram counters at7.
All large rational integers are encoded in hexadecimal or powers of two.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import product
import json
from math import comb, factorial
from pathlib import Path
import time

Q = 4096
N = 4025
CAP = 7
BITS = 12


def convolve(left, right):
    out = [0]*(len(left)+len(right)-1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i+j] += a*b
    return out


def bounded_egf(cutoff, scale):
    """Integer coefficients of scale*sum_{j=0}^cutoff z^j/j!."""
    assert cutoff >= 0
    return [scale//factorial(j) for j in range(cutoff+1)]


def count_words(n, coefficients, denominator, unrestricted_labels):
    """Exact weighted word count from an exponential generating polynomial.

    n!*[z^n] (P(z)/denominator)*exp(unrestricted_labels*z).
    Every caller supplies integer category weights, so division is exact.
    This evaluates one polynomial of degree at most383 for the actual case.
    """
    assert n >= 0 and denominator > 0 and unrestricted_labels >= 0
    coefficients = coefficients[:n+1]
    degree = len(coefficients)-1
    falling = 1
    total = coefficients[0]
    for j in range(1, degree+1):
        falling *= n-j+1
        total = total*unrestricted_labels + coefficients[j]*falling
    total *= unrestricted_labels**(n-degree)
    quotient, remainder = divmod(total, denominator)
    assert remainder == 0
    return quotient


def capped_gain(n, q, candidates, cap):
    """Exact E[chosen multiplicity-(1+old zero count)].

    Counts come from n iid uniform q-letter labels. Only the first K labels
    are considered. The zero label has a fixed extra pivot occurrence.
    Highest capped count wins; ties use the earliest label, with zero first.
    """
    assert 1 <= candidates <= q and n >= 1 and cap >= 2
    denominator = q**n
    capped_numerator = 0
    cdf_rows = []
    for k in range(2, cap+1):
        scale = factorial(k-1)
        first = bounded_egf(k-2, scale)
        ordinary = bounded_egf(k-1, scale)
        polynomial = first
        for _ in range(candidates-1):
            polynomial = convolve(polynomial, ordinary)
        base_count = count_words(n, first, scale, q-1)
        joint_count = count_words(n, polynomial, scale**candidates, q-candidates)
        assert 0 <= joint_count <= base_count <= denominator
        capped_numerator += base_count-joint_count
        cdf_rows.append(dict(threshold=k, polynomial_degree=len(polynomial)-1,
                             probability_gap_numerator_hex=hex(base_count-joint_count)))

    # Above-cap excess is owned by the first nonzero label reaching the cap.
    # A_i is: N0<=cap-2 and each earlier nonzero count<=cap-1.
    # E[(Ni-cap)+ 1(A_i)] is calculated with a first-moment shift and a
    # bounded correction. All three integer counts share denominator q**n.
    scale = factorial(cap-1)
    polynomial = bounded_egf(cap-2, scale)
    ordinary = bounded_egf(cap-1, scale)
    weighted = [(cap-j)*coefficient for j, coefficient in enumerate(ordinary)]
    normalization = scale
    excess_numerator = 0
    excess_rows = []
    for index in range(1, candidates):
        whole = count_words(n, polynomial, normalization, q-index)
        shifted = count_words(n-1, polynomial, normalization, q-index)
        bounded = count_words(n, convolve(polynomial, weighted),
                              normalization*scale, q-index-1)
        excess = n*shifted-cap*whole+bounded
        assert excess >= 0
        excess_numerator += excess
        excess_rows.append(dict(candidate_index=index,
                                excess_numerator_hex=hex(excess)))
        polynomial = convolve(polynomial, ordinary)
        normalization *= scale

    tail_numerator = n*q**(n-1)-cap*denominator
    for count in range(min(cap, n+1)):
        tail_numerator += ((cap-count)*comb(n, count)*(q-1)**(n-count))
    assert tail_numerator >= 0
    assert excess_numerator <= (candidates-1)*tail_numerator
    gain = Fraction(capped_numerator+excess_numerator, denominator)
    return gain, dict(capped_numerator_hex=hex(capped_numerator),
                      excess_numerator_hex=hex(excess_numerator),
                      common_denominator_power_of_two=(BITS*n if q == Q else None),
                      common_denominator_hex=None if q == Q else hex(denominator),
                      first_candidate_excess_rows=excess_rows,
                      capped_cdf_rows=cdf_rows,
                      capped_only_lower=Fraction(capped_numerator, denominator),
                      elementary_upper=Fraction(capped_numerator+(candidates-1)*tail_numerator,
                                                denominator))


def decimal_bound(value, digits=12, *, upper=False):
    scaled = value.numerator*10**digits
    integer = (-((-scaled)//value.denominator) if upper else scaled//value.denominator)
    sign = '-' if integer < 0 else ''
    whole, fractional = divmod(abs(integer), 10**digits)
    return f'{sign}{whole}.{fractional:0{digits}d}'


def encode_fraction(value):
    denominator = value.denominator
    assert denominator > 0 and denominator & (denominator-1) == 0
    return dict(numerator_hex=hex(value.numerator),
                denominator_power_of_two=denominator.bit_length()-1,
                decimal_lower=decimal_bound(value),
                decimal_upper=decimal_bound(value, upper=True),
                directed_decimal_digits=12)


def counter_step(value, enable):
    bits = [(value >> j) & 1 for j in range(3)]
    c1 = enable & bits[0]
    c2 = c1 & bits[1]
    c3 = c2 & bits[2]
    bits[0] ^= enable ^ c3
    bits[1] ^= c1 ^ c3
    bits[2] ^= c2 ^ c3
    return sum(bit << j for j, bit in enumerate(bits))


def compare_three(left, right):
    equal, greater = 1, 0
    for bit in reversed(range(3)):
        a, b = (left >> bit) & 1, (right >> bit) & 1
        difference = a ^ b
        greater |= equal & a & (b ^ 1)
        equal &= difference ^ 1
    return greater


def tiny_checks():
    for value in range(8):
        for enable in range(2):
            assert counter_step(value, enable) == min(7, value+enable)
    for left in range(8):
        for right in range(8):
            assert compare_three(left, right) == (left > right)
    rows, checked_words = [], 0
    for n in range(1, 6):
        for candidates in (1, 2, 4):
            total = 0
            for word in product(range(4), repeat=n):
                counts = Counter(word)
                multiplicities = [counts[i]+int(i == 0) for i in range(candidates)]
                chosen = max(range(candidates), key=lambda i: min(3, multiplicities[i]))
                saving = multiplicities[chosen]-multiplicities[0]
                assert saving >= 0
                total += saving
                checked_words += 1
            exact, _ = capped_gain(n, 4, candidates, 3)
            assert exact == Fraction(total, 4**n)
            rows.append(dict(n=n, q=4, candidates=candidates, cap=3,
                             expected_gain=str(exact)))
    return dict(saturated_increment_truth_cases=16, comparator_truth_cases=64,
                exhaustive_small_alphabet_words=checked_words,
                exact_distribution_checks=rows)


def classical_ledger(candidates):
    assert candidates in (1, 2, 4, 8, 16, 32, 64)
    label_bits = candidates.bit_length()-1
    per_word = 25*candidates+7-label_bits
    selection = 6*candidates+19+(candidates-1)*(46+label_bits)
    return dict(candidate_labels=list(range(candidates)),
        candidate_label_bits=label_bits, counter_bits=3*candidates,
        histogram_instructions_per_word=per_word,
        histogram_instructions=N*per_word,
        initialize_select_and_retire_instructions_upper=selection,
        classical_scratch_peak_upper=max(5*candidates+2,3*candidates+18),
        retained_virtual_pivot_classical_bits=12,
        shift_unshift_instructions=2*label_bits*N,
        original_syndrome_compensation_CZ_upper=70*12*label_bits,
        normalization_pair_classical_instructions_upper=330*N,
        replacement_scan_mask_scaling_instructions_upper=330*(N+1),
        old_scan_mask_scaling_subtraction_credited=0,
        quantum_scratch=0, additional_non_scan_T=0,
        new_scan_static_T=11*(N+1), old_scan_static_T=11*N,
        native_instruction_measurement=False,
        scope='Explicit histogram instruction ledger; public linear-map terms are conservative upper bounds, not native size results.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidates', type=int, nargs='+', default=[2, 8, 16, 32, 64])
    args = parser.parse_args()
    assert __debug__
    assert len(set(args.candidates)) == len(args.candidates)
    assert all(k in (1, 2, 4, 8, 16, 32, 64) for k in args.candidates)
    assert not args.output.exists(), 'Use a new output directory.'
    started = time.monotonic()
    tests = tiny_checks()
    old_mean = Fraction(11*N*(Q-1), Q)
    rows = []
    for candidates in args.candidates:
        gain, witness = capped_gain(N, Q, candidates, CAP)
        lower = witness.pop('capped_only_lower')
        upper = witness.pop('elementary_upper')
        assert lower <= gain <= upper
        rows.append(dict(candidates=candidates, cap=CAP,
            exact_expected_additional_zeros=encode_fraction(gain),
            exact_expected_T_saving=encode_fraction(11*gain),
            exact_new_scan_mean_T=encode_fraction(old_mean-11*gain),
            capped_only_lower_T_saving=encode_fraction(11*lower),
            elementary_upper_T_saving=encode_fraction(11*upper),
            exact_integer_witness=witness,
            classical_source_ledger=classical_ledger(candidates)))
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = dict(format='DQI_ADAPTIVE_GAUGE_CAPPED_OCCUPANCY_V1',
        status='EXACT_FINITE_OCCUPANCY_PAPER_CERTIFICATE_NOT_NATIVE',
        source_sha256=source_sha, q=Q, independent_residual_labels=N,
        fixed_zero_pivot_labels=1, cap=CAP, zero_first_tie_policy=True,
        old_scan_mean_T=encode_fraction(old_mean), rows=rows, tiny_checks=tests,
        sampler_draws=0, population_census_runs=0, project_imports=0,
        native_builds=0, native_simulations=0,
        exact_modal_selector=False, all_input_pointwise_no_T_loss=True,
        admission_changed=False, measured_official_gain=None,
        elapsed_seconds=time.monotonic()-started)
    args.output.mkdir(parents=True, exist_ok=False)
    target = args.output/'paper_certificate.json'
    target.write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], source_sha256=source_sha,
        elapsed_seconds=report['elapsed_seconds'],
        rows=[dict(candidates=row['candidates'],
                   T_saving_lower=row['exact_expected_T_saving']['decimal_lower'],
                   T_saving_upper=row['exact_expected_T_saving']['decimal_upper'],
                   histogram_instructions=row['classical_source_ledger']['histogram_instructions'])
              for row in rows]),sort_keys=True),flush=True)


if __name__ == '__main__':
    main()
