# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact owned/serialized classical allocation contract for the new checker.

This module imports no provider or native engine. The original emitter is
unchanged. Native point-cell scratch is distinguished from explicitly owned
selector bits using the completed root-only allocation probe.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGINAL = HERE.parent/'adaptive_gauge'
INPUT_BITS = 4095*12
SELECTOR_BITS = 322
PIVOT_BITS = 12
SCAN_EXPLICIT_LIVE_BITS = 24
NATIVE_POINT_SCRATCH_BITS = 1
GAUGE_SERIALIZED_BITS = INPUT_BITS+SELECTOR_BITS
SCAN_SERIALIZED_BITS = GAUGE_SERIALIZED_BITS+NATIVE_POINT_SCRATCH_BITS
EVIDENCE_PINS = {
 'controller_work/after_v3/k24/adaptive_gauge/adaptive_gauge64.py':
 '3299627d63c20cf1223dc782cc6d48728f328a237d420f76f2d9260811bc7e5d',
 'controller_work/after_v3/k24/adaptive_gauge/check_adaptive_gauge64.py':
 '2210560abbd36e6bb8320afbc31afc77c86dad38a00b495962c530e1bd3fa3d1',
 'controller_work/after_v3/k24/adaptive_gauge/runs/smoke/report.json':
 '5f3e1b96974e199aad34d81fa09bcd79eae9235ddb8647f900bc7a2e610f1aee',
 'controller_work/after_v3/k24/adaptive_gauge/runs/smoke.guard.json':
 'e7bf91c000a59a16ec1373bb30331ade7502dcbff611e8936d06017d933b6c33',
 'controller_work/after_v3/k24/adaptive_gauge/runs/smoke.stdout':
 '5cd14589eb99e13258068d566f2ec33dd95523859f94106eb542b47c58b0f829',
 'controller_work/after_v3/k24/adaptive_gauge_allocation_probe.py':
 'b3d3cefefecae8550eafa2009ae80ea608b7ffbf255e890a55c88655617e8922',
 'controller_work/after_v3/k24/runs/adaptive-allocation-probe/receipt.json':
 'f82009246d8b897a9e5ef0410b3860030a2b8edc0127f30574cb7ebd1912247e',
 'controller_work/after_v3/k24/runs/adaptive-allocation-probe.guard.json':
 '6494cccbeb8aa57d98eab8a32906a350718bdcfe1a5e2359f4c3e8da664c6eb5',
 'controller_work/work/round2/milestone152/source/narrow_field130.py':
 'f021152bc598f334d854bfba13b9f228cd6a0b751010dde10c9341203bd49bf6',
 'pro1_controller_bundle/1_task/official/kickmix.so':
 'c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_evidence():
    """Read exact completed evidence; never rerun the native diagnostic."""
    for name, expected in EVIDENCE_PINS.items():
        assert sha(ROOT/name) == expected, name
    receipt_path = HERE.parent/'runs/adaptive-allocation-probe/receipt.json'
    guard_path = HERE.parent/'runs/adaptive-allocation-probe.guard.json'
    receipt = json.loads(receipt_path.read_bytes())
    guard = json.loads(guard_path.read_bytes())
    assert receipt['status'] == 'OBSERVED_TINY_NATIVE_POINT_ALLOCATION_ONLY'
    assert receipt['source_sha256'] == EVIDENCE_PINS[
        'controller_work/after_v3/k24/adaptive_gauge_allocation_probe.py']
    assert receipt['native_simulations'] == receipt['decoder_builds'] == 0
    assert receipt['selector_executed'] is receipt['component_correctness_claim'] is False
    assert receipt['changed_existing_files'] is False
    assert guard['status'] == 'complete' and type(guard['exit_code']) is int
    assert guard['exit_code'] == 0 and guard['stopped'] is False
    assert Path(guard['cwd']).resolve() == ROOT
    assert guard['command'] == [
        '/usr/bin/python3.13', '-B',
        'controller_work/after_v3/k24/adaptive_gauge_allocation_probe.py',
        '--output', 'controller_work/after_v3/k24/runs/adaptive-allocation-probe/receipt.json']
    for name, expected in receipt['input_sources'].items():
        assert sha(ROOT/name) == expected, name
    rows = receipt['rows']
    expected = {
        'plain_baseline':(INPUT_BITS+12, 11, 18368),
        'plain_conditional':(INPUT_BITS+13, 12, 19392),
        'pool_baseline':(SCAN_SERIALIZED_BITS, SELECTOR_BITS, 19039),
        'pool_conditional':(SCAN_SERIALIZED_BITS, SELECTOR_BITS, 20063),
    }
    assert len(rows) == len(expected) and {row['mode'] for row in rows} == set(expected)
    for row in rows:
        bits, owned_peak, operations = expected[row['mode']]
        assert row['point_cells'] == 64 and row['static_T'] == 704 and row['Q'] == 34
        assert row['num_bits'] == bits and row['instructions'] == operations
        points = [stage for stage in row['stages'] if stage['stage'].startswith('point_')]
        assert [stage['stage'] for stage in points] == [
            'point_1','point_2','point_4','point_8','point_16','point_32','point_64']
        assert all(stage['num_bits'] == bits and stage['explicit_workspace_peak'] == owned_peak
                   for stage in points)
        assert row['stages'][-1]['explicit_live_workspace'] == 0
        if row['mode'].startswith('pool_'):
            before = row['stages'][1]
            assert before['stage'] == 'selector_topology_only_label_live'
            assert before['num_bits'] == GAUGE_SERIALIZED_BITS
            assert before['explicit_live_workspace'] == PIVOT_BITS
            assert all(stage['explicit_live_workspace'] == PIVOT_BITS for stage in points)
    failed = json.loads((ORIGINAL/'runs/smoke/report.json').read_bytes())
    failed_guard = json.loads((ORIGINAL/'runs/smoke.guard.json').read_bytes())
    assert failed['status'] == 'FAIL_OR_INTERRUPTED_ADAPTIVE64_COMPONENT' and failed['runs'] == []
    assert failed_guard['status'] == 'complete' and failed_guard['exit_code'] == 1
    assert failed_guard['stopped'] is False
    return dict(
        status='EXACT_COMPLETED_NATIVE_ALLOCATION_PROBE_BOUND',
        receipt=receipt_path.relative_to(ROOT).as_posix(), receipt_sha256=sha(receipt_path),
        guard=guard_path.relative_to(ROOT).as_posix(), guard_sha256=sha(guard_path),
        selector_owned_peak_bits=SELECTOR_BITS, retained_pivot_bits=PIVOT_BITS,
        conditional_scan_owned_live_peak_bits=SCAN_EXPLICIT_LIVE_BITS,
        inherited_native_point_scratch_bits=NATIVE_POINT_SCRATCH_BITS,
        gauge_serialized_bits=GAUGE_SERIALIZED_BITS, scan_serialized_bits=SCAN_SERIALIZED_BITS,
        observed_probe_points=[1,2,4,8,16,32,64],
        full4026_count_is_a_new_exact_native_assertion=True,
        original_failed_smoke_preserved=True, original_emitter_unchanged=True)


class OwnedClassicalTracker:
    """Delegate gates verbatim while accounting for explicit alloc/free only.

    Native del_and remains delegated and may use the separately measured
    engine scratch bit. The tracker makes no assertion that free native HMR
    history is zero. The unchanged simulation checks own/input restoration.
    """
    def __init__(self, builder, bit_type):
        self.builder = builder
        self.bit_type = bit_type
        self.live = set()
        self.peak = 0
        self.phase_peak = 0
        self.alloc_calls = 0
        self.free_calls = 0

    def __getattr__(self, name):
        return getattr(self.builder, name)

    def alloc_bits(self, count):
        value = self.builder.alloc_bits(count)
        wires = set(value)
        assert len(wires) == count and not (wires & self.live)
        assert all(isinstance(wire, self.bit_type) for wire in wires)
        self.live.update(wires)
        self.peak = max(self.peak, len(self.live))
        self.phase_peak = max(self.phase_peak, len(self.live))
        self.alloc_calls += 1
        return value

    def free(self, wires):
        values = tuple(wires)
        if values and isinstance(values[0], self.bit_type):
            assert all(isinstance(wire, self.bit_type) for wire in values)
            current = set(values)
            assert len(current) == len(values) and current <= self.live
            self.live.difference_update(current)
            self.free_calls += 1
        return self.builder.free(wires)

    def start_phase(self):
        self.phase_peak = len(self.live)

    def snapshot(self):
        return dict(owned_live_bits=len(self.live), owned_peak_bits=self.peak,
                    phase_owned_peak_bits=self.phase_peak,
                    explicit_alloc_calls=self.alloc_calls, explicit_free_calls=self.free_calls)
