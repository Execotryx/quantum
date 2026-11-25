# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Pure source/evidence binding for the new public transpose14 placement.

This helper never emits or simulates a circuit. Native component checkers
call it before and after their work; the old v4 files stay byte-identical.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORK = PROJECT.parent
ROOT = WORK.parent
BLOCKS = PROJECT/'blocks'
V4 = PROJECT/'integration_v4'
BASELINE_REPORT = BLOCKS/'runs/quotient63-preimage-full/report.json'
BASELINE_REPORT_SHA = '461bb69e8825e211ae7ba7a547fe92ce4a4969361c140b52ee71f8bf416d8ebb'
FROZEN_V4 = {
    'v4_paths.py': '04a6fe260b7ee4d82b0eaea4e84cb6ca36afcaf27f273315128a2409117a7f82',
    'v4_binding.py': 'ab35fa3ff1c81677bc5ca2b03cd8e84c186033d86a6483b83291e87b01583dbb',
    'v4_pipeline.py': '24d48d2d02f555b1dff03732f96b1fb9ca564a6bacece36142e53086288e40eb',
    'v4_events.py': 'e88c35391485c80f0127408e1988ebe68523b854c348a6fecf16ed17c3a4ba96',
    'NATIVE_COMPONENT_GATES.json': 'd6918c9937e961a5610423012713ef65edcd7fe545ad19e4612cce922144dc1c',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def enable_import_paths():
    for path in (V4, BLOCKS, HERE):
        name = str(path)
        if name in sys.path:
            sys.path.remove(name)
        sys.path.insert(0, name)


def baseline_metrics():
    assert digest(BASELINE_REPORT) == BASELINE_REPORT_SHA
    report = json.loads(BASELINE_REPORT.read_text())
    assert report['status'] == 'PASS_NATIVE_JOINT63_HANDOFF_PREIMAGE_COMPONENT_ONLY'
    assert report['fixtures'] == 256 and report['two_identical_builds'] is True
    metrics = report['metrics']
    assert (metrics['static_T'], metrics['prefix_static_T'], metrics['Q']) == (115081, 57053, 889)
    return metrics


def verify_frozen_v4():
    """Check the exact selected v4 files and all17 existing native gates."""
    for name, wanted in FROZEN_V4.items():
        assert digest(V4/name) == wanted, name
    if str(V4) not in sys.path:
        sys.path.insert(0, str(V4))
    import v4_binding
    assert Path(v4_binding.__file__).resolve() == V4/'v4_binding.py'
    gates = v4_binding.verify_components()
    assert gates['component_count'] == 17 and gates['pinned_files'] == 163
    baseline_metrics()
    return dict(files=dict(FROZEN_V4), selected_component_gate=gates,
                baseline_report=str(BASELINE_REPORT.relative_to(ROOT)),
                baseline_report_sha256=BASELINE_REPORT_SHA)


def verify_derivation():
    """Reproduce the explicit literal copies, without importing the copies."""
    path = HERE/'SOURCE_DERIVATION.json'
    record = json.loads(path.read_text())
    assert record['format'] == 'DQI_PUBLIC_TRANSPOSE14_EXACT_LITERAL_COPIES_V1'
    assert record['admitted_domain_change'] is False
    expected = {'transpose14_core.py', 'transpose14_window.py', 'check_transpose14_preimage.py'}
    assert {row['new_name'] for row in record['copies']} == expected
    results = {}
    for row in record['copies']:
        old = (ROOT/row['old_path']).resolve()
        new = HERE/row['new_name']
        assert old.is_relative_to(BLOCKS) and old.is_file()
        assert new.parent == HERE and new.is_file()
        original = old.read_bytes()
        assert hashlib.sha256(original).hexdigest() == row['old_sha256']
        text = original.decode()
        for edit in row['edits']:
            assert text.count(edit['before']) == edit['occurrences']
            text = text.replace(edit['before'], edit['after'])
        emitted = text.encode()
        assert emitted == new.read_bytes()
        actual = hashlib.sha256(emitted).hexdigest()
        assert actual == row['new_sha256']
        ast.parse(emitted, filename=str(new))
        results[row['new_name']] = actual
    assert len(record['copies'][0]['edits']) == 1
    assert len(record['copies'][1]['edits']) == 2
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                actual_copy_sha256=results, no_native_execution=True)


def source_snapshot():
    result = {}
    for path in sorted(HERE.iterdir()):
        if path.is_file() and path.suffix in ('.py', '.json', '.md'):
            result[path.name] = dict(sha256=digest(path), bytes=path.stat().st_size)
    return result
