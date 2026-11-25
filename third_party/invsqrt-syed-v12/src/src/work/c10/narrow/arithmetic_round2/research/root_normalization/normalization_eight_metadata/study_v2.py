#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Eight-coordinate inverse normalization: four exact symbolic branches."""
from pathlib import Path
from fractions import Fraction
import hashlib
import importlib.util
import json
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
NARROW = HERE.parents[3]
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
for pin in json.loads((HERE / 'INPUTS.json').read_text())['files']:
    data = (NARROW / pin['path']).read_bytes()
    assert len(data) == pin['bytes']
    assert hashlib.sha256(data).hexdigest() == pin['sha256'], pin['path']
spec = importlib.util.spec_from_file_location('_rn2f_pinned_rn2b_paper', PARENT / 'leading_one_normalization_v2.py')
baseline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = baseline
spec.loader.exec_module(baseline)
old, km = baseline.old, baseline.km
from thermometer_cleanup import thermometer_matrix, linear_frame

MASKS = tuple(range(1, 9))


def setup():
    original = thermometer_matrix(10)
    rows = [original[0] ^ original[8], original[1] ^ original[9]] + original[2:8]
    assert len(rows) == 8 and all(row < 256 for row in rows)
    frame = linear_frame(rows)
    monomials = [sum(int(k & m == m) << k for k in range(11)) for m in MASKS]
    thresholds = [sum(int(k >= j) << k for k in range(11)) for j in range(1, 11)]
    wanted = [thresholds[0] ^ thresholds[8], thresholds[1] ^ thresholds[9]] + thresholds[2:8]
    actual = list(monomials)
    for name, a, b in frame:
        if name == 'cx':
            actual[b] ^= actual[a]
        else:
            actual[a], actual[b] = actual[b], actual[a]
    assert actual == wanted
    controls = []
    for operation in old.operations(11):
        terms = [j for j in operation['prefix_terms'] if j <= 10]
        assert (1 in terms) == (9 in terms)
        assert (2 in terms) == (10 in terms)
        reduced = [j for j in terms if j not in (9, 10)]
        actual = 0
        for j in reduced:
            actual ^= wanted[j - 1]
        assert actual == operation['selector_truth'] & ((1 << 11) - 1)
        controls.append(dict(first=operation['first'], second=operation['second'], terms=reduced))
    assert len(controls) == 17
    return rows, frame, controls


ROWS, FRAME, CONTROLS = setup()


def prepare(builder, flags):
    monomials = {1 << i: q for i, q in enumerate(flags)}
    helpers = []
    for mask in MASKS:
        if mask in monomials:
            continue
        low = mask & -mask
        q = builder.alloc_qubits(1)[0]
        builder.ccx(monomials[mask ^ low], monomials[low], q)
        monomials[mask] = q
        helpers.append(q)
    assert len(helpers) == 4
    wires = [monomials[m] for m in MASKS]
    for name, a, b in FRAME:
        if name == 'cx':
            builder.cx(wires[a], wires[b])
        else:
            builder.swap(wires[a], wires[b])
    return dict(zip(range(1, 9), wires)), helpers


def measured(builder, q, role=None):
    outcome = builder.alloc_bits(1)[0]
    if role is not None and hasattr(builder, 'select_outcome'):
        builder.select_outcome(outcome, role)
    builder.hmr(q, outcome)
    return outcome


def prefix_phase(builder, outcome, previous, a, b):
    builder.push_condition(outcome)
    builder.z(previous)
    builder.cz(previous, a)
    builder.cz(previous, b)
    builder.ccz(previous, a, b)
    builder.pop_condition()


def joint_last_phase(builder, x, mB, m3, *, omit_final_helper_fix=False):
    # Both raw complement frames and the affine T1 frame are restored below.
    builder.cx(x[21], x[20])
    builder.x(x[20])
    for i in (18, 19, 16, 17):
        builder.x(x[i])
    a, t2 = list(builder.alloc_qubits(2))
    ma, mt = list(builder.alloc_bits(2))
    builder.bit_store(ma, False)
    builder.bit_store(mt, False)
    builder.push_condition(m3)
    builder.ccx(x[20], x[18], a)
    builder.ccx(a, x[19], t2)
    builder.push_condition(mB)
    builder.z(t2)
    builder.pop_condition()
    builder.ccz(t2, x[16], x[17])
    builder.hmr(t2, mt)
    builder.push_condition(mt)
    builder.cz(a, x[19])
    builder.pop_condition()
    builder.hmr(a, ma)
    builder.push_condition(ma)
    if not omit_final_helper_fix:
        builder.cz(x[20], x[18])
    builder.pop_condition()
    builder.pop_condition()
    builder.free(mt)
    builder.free(ma)
    builder.free(t2)
    builder.free(a)
    builder.x(m3)
    builder.push_condition(m3)
    builder.push_condition(mB)
    builder.ccz(x[20], x[18], x[19])
    builder.pop_condition()
    builder.pop_condition()
    builder.x(m3)
    for i in (17, 16, 19, 18):
        builder.x(x[i])
    builder.x(x[20])
    builder.cx(x[21], x[20])


def inverse(builder, x, flags, *, omit_final_helper_fix=False):
    x, flags = list(x), list(flags)
    T, helpers = prepare(builder, flags)
    for operation in reversed(CONTROLS):
        terms = operation['terms']
        control, others = T[terms[0]], [T[j] for j in terms[1:]]
        for q in others:
            builder.cx(q, control)
        for lane in range(2):
            builder.cswap(control, x[2*operation['first'] + lane], x[2*operation['second'] + lane])
        for q in reversed(others):
            builder.cx(q, control)
    A = T.pop(1)
    builder.x(A)
    builder.cx(x[20], A)
    builder.cx(x[21], A)
    T[9] = A
    mB = measured(builder, T.pop(2), 'B')
    prefix_phase(builder, mB, T[9], x[2], x[3])
    for j in reversed(range(4, 10)):
        outcome = measured(builder, T[j])
        prefix_phase(builder, outcome, T[j-1], x[22-2*j], x[23-2*j])
        builder.free(outcome)
    m3 = measured(builder, T[3], 'T3')
    builder.free(km.array(helpers))
    joint_last_phase(builder, x, mB, m3, omit_final_helper_fix=omit_final_helper_fix)
    builder.free(mB)
    builder.free(m3)


class BranchBuilder(old.TruthPhaseBuilder):
    """Keep every other outcome symbolic; branch only on the two selected bits."""
    def __init__(self, full, valid, branch):
        super().__init__(48, full, valid)
        self.branch = dict(B=branch[0], T3=branch[1])
        self.classical = {}
        self.selected = {}
        self.active_symbols = 0
        self.inactive_measurements = 0

    def alloc_bits(self, n):
        result = super().alloc_bits(n)
        for bit in result:
            self.classical[bit] = (0, 0)
        return result

    def bit_store(self, bit, value):
        assert not self.stack and value is False
        self.classical[bit] = (0, 0)

    def select_outcome(self, outcome, role):
        assert role not in self.selected.values()
        self.selected[outcome] = role

    def _active_data(self):
        for bit in set(self.stack):
            mask, constant = self.classical[bit]
            assert mask == 0, 'Data mutation is controlled only by the two fixed branch outcomes.'
            if constant == 0:
                return False
        return True

    def free(self, value):
        if isinstance(value, km.b):
            self.classical.pop(value, None)
        return super().free(value)

    def _condition(self, extra=None):
        conditions = set(self.stack)
        if extra is not None:
            conditions.add(extra)
        symbolic = set()
        for bit in conditions:
            mask, constant = self.classical[bit]
            if mask == 0:
                if not constant:
                    return False, set()
            else:
                assert constant == 0 and mask.bit_count() == 1
                symbolic.add(mask.bit_length()-1)
        assert len(symbolic) <= 1
        return True, symbolic

    def _phase(self, value, extra=None):
        active, symbolic = self._condition(extra)
        if active:
            key = next(iter(symbolic)) if symbolic else None
            self.phases[key] = self.phases.get(key, 0) ^ value

    def _charge(self, n=1):
        active, symbolic = self._condition()
        if active:
            self.count += Fraction(n, 1 << len(symbolic))

    def x(self, q):
        if isinstance(q, km.b):
            assert not self.stack
            mask, constant = self.classical[q]
            self.classical[q] = (mask, constant ^ 1)
        elif self._active_data():
            self.values[q] ^= self.full

    def cx(self, a, target):
        assert isinstance(target, km.q)
        if self._active_data():
            self.values[target] ^= self.value(a)

    def ccx(self, a, b, target):
        self._charge()
        if self._active_data():
            self.values[target] ^= self.value(a) & self.value(b)

    def cswap(self, c, a, b):
        self._charge()
        if self._active_data():
            delta = self.value(c) & (self.value(a) ^ self.value(b))
            self.values[a] ^= delta
            self.values[b] ^= delta

    def hmr(self, q, outcome):
        event = self.measurements
        self.measurements += 1
        if not self._active_data():
            assert self.classical[outcome] == (0, 0)
            assert self.value(q) & self.valid == 0
            self.inactive_measurements += 1
            return
        if outcome in self.selected:
            value = self.branch[self.selected[outcome]]
            self.classical[outcome] = (0, value)
            if value:
                self.phases[None] = self.phases.get(None, 0) ^ self.value(q)
        else:
            self.classical[outcome] = (1 << event, 0)
            self.phases[event] = self.phases.get(event, 0) ^ self.value(q)
            self.active_symbols += 1
        self.values[q] = 0


def prove_branch(source, full, valid, branch, *, omit_final_helper_fix=False):
    builder = BranchBuilder(full, valid, branch)
    x = list(builder.alloc_qubits(22))
    flags = list(builder.alloc_qubits(4))
    for q, value in zip(x, source):
        builder.values[q] = value
    baseline.forward(builder, x, flags)
    builder.check_phase()
    expected = [0] * 22
    expected_flags = [0] * 4
    for k in range(11):
        lo = 1 << (20 - 2*k)
        hi = min(old.MAX_X + 1, 1 << (22 - 2*k))
        support = (1 << hi) - (1 << lo) if hi > lo else 0
        for bit in range(2*k, 22):
            expected[bit] ^= support & source[bit - 2*k]
        for bit in range(4):
            if (k >> bit) & 1:
                expected_flags[bit] ^= support
    assert all((builder.value(q) ^ value) & valid == 0 for q, value in zip(x, expected))
    assert all((builder.value(q) ^ value) & valid == 0 for q, value in zip(flags, expected_flags))
    assert builder.num_allocated_qubits == 26
    before = float(builder.count)
    fp = builder.peak
    builder.peak = 26
    inverse(builder, x, flags, omit_final_helper_fix=omit_final_helper_fix)
    assert all((builder.value(q) ^ value) & valid == 0 for q, value in zip(x, source))
    assert all(builder.value(q) & valid == 0 for q in flags)
    assert builder.num_allocated_qubits == 26
    unpaid = [key for key, value in builder.phases.items() if value & valid]
    if omit_final_helper_fix:
        assert branch[1] == 1 and len(unpaid) == 1
    else:
        builder.check_phase()
        assert not unpaid
    return dict(branch=dict(mB=branch[0], m3=branch[1]), forward_E=before,
                inverse_E=float(builder.count)-before, total_E=float(builder.count),
                modeled_forward_peak=fp, modeled_inverse_peak=builder.peak,
                static_HMR_events=builder.measurements, active_independent_HMR_symbols=builder.active_symbols,
                inactive_HMR_destinations_remain_zero=builder.inactive_measurements,
                unpaid_HMR_symbols=unpaid, all_input_owners_restored=True,
                all_flags_scratch_zero=True)


def main():
    began = time.monotonic()
    full = (1 << (1 << 22)) - 1
    valid = (1 << (old.MAX_X + 1)) - 2
    source = old.input_truths()
    rows = []
    for mB, m3 in ((0, 0), (1, 0), (0, 1), (1, 1)):
        if time.monotonic() - began > 20:
            raise TimeoutError('Bound reached before a complete four-branch certificate.')
        rows.append(prove_branch(source, full, valid, (mB, m3)))
    negative = prove_branch(source, full, valid, (0, 1), omit_final_helper_fix=True)
    average = sum(row['inverse_E'] for row in rows) / 4
    assert average == 43.25 and all(row['forward_E'] == 52 for row in rows)
    assert all(row['modeled_inverse_peak'] == 30 for row in rows)
    assert all(row['modeled_forward_peak'] == 46 for row in rows)
    result = dict(status='PASS_EXACT_EIGHT_COORDINATE_NORMALIZATION_PAPER_NOT_NATIVE',
                  original_inputs_per_branch=old.MAX_X, selected_outcomes_exhaustive=True,
                  selected_outcomes_are_distinct_unconditional_HMR=True, branch_weights=[0.25]*4,
                  every_other_active_HMR_symbol_independent=True, rows=rows,
                  negative_missing_helper_fix_detected=negative, metadata_monomials=MASKS,
                  metadata_basis_rows=ROWS, metadata_Clifford_frame=FRAME, route_controls=CONTROLS,
                  forward_E=52, inverse_expected_E=average, full_component_E=52+average,
                  change_vs_RN2B=-1.25, additional_change_vs_RN2C=-0.25,
                  complete_Q=48, complete_Toffolis_vs_candidate09=1567.25,
                  complete_expected_cost=48*(1567.25+1+230.84805946161188),
                  T_change=0, R_change=0, numerical_error_change=0,
                  RN2D_combination_not_executed_or_credited=True,
                  native_execution=False, official_execution=False,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  inputs_sha256=hashlib.sha256((HERE/'INPUTS.json').read_bytes()).hexdigest(),
                  seconds=time.monotonic()-began,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    with (HERE/'study.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('metadata_Clifford_frame', 'route_controls')}, indent=2))


if __name__ == '__main__':
    main()
