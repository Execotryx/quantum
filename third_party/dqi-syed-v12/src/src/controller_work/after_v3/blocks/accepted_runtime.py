# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed accepted-v3 import boundary for root-run block panels.

Importing this file uses only the standard library. ``load`` imports the
supplied native runtime and must run under the root engineer's memory guard.
No accepted source or historical source-binding receipt is changed.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
ROOT = WORK.parent
AFTER = WORK/'after_c5'
RELEASE = AFTER/'release_v3'
BOOTSTRAP_SHA = '10777a00500b4af810213a994d416ac79f28a9d6925262a6bd318645c286f4f4'
PINS = {
    RELEASE/'build_release.py': BOOTSTRAP_SHA,
    RELEASE/'normalized/window_tensor_shared.py':
        '683d02a8640cbcca0013ca685d00a8212b035c31915779fcbe16110514e24ae8',
    RELEASE/'normalized/local_flag_window.py':
        'bd58bbb619c4cf27ad28cec0443a3305b1e3db2af93638c31d09c86e8284dd41',
    RELEASE/'normalized/direct_carry_first2.py':
        'fdb519bd501df5df70bd3571742964496e622951290d92f5479b4380c832772e',
    AFTER/'integration_v3/integrated_pipeline.py':
        '0ddd3ececf5738594636a486dfbc211388dfed872fc8dba97fd573c45b64d5c9',
}
_loaded = None


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pinned_sources():
    answer = {}
    for path, expected in PINS.items():
        observed = digest(path)
        assert observed == expected, (str(path), observed, expected)
        answer[str(path.relative_to(ROOT))] = observed
    return answer


def load():
    """Load exactly the accepted all-four-options normalized production ABI."""
    global _loaded
    assert __debug__ and sys.version_info[:2] == (3, 13)
    if _loaded is not None:
        return _loaded
    before = pinned_sources()
    spec = importlib.util.spec_from_file_location(
        'accepted_v3_release_bootstrap', RELEASE/'build_release.py')
    assert spec is not None and spec.loader is not None
    bootstrap = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bootstrap
    spec.loader.exec_module(bootstrap)
    builder, normalized, derivation = bootstrap.load_fixed_runtime()
    pipeline = importlib.import_module('integrated_pipeline')
    assert Path(pipeline.__file__).resolve() == AFTER/'integration_v3/integrated_pipeline.py'
    pipeline.configure(pipeline.Options(
        first_two_charts=True, nested_norm=True,
        finish_seam=True, infinity3_finish=True))
    reference, window, first_two = normalized
    assert pipeline.Window is window
    assert pipeline.Window.tensor is pipeline.SharedTensor is reference
    assert pipeline.Extractor is first_two
    transpose = pipeline.Window.transpose_tensor
    assert Path(transpose.__file__).resolve() == AFTER/'arithmetic_t/window_transpose_shared.py'
    binding = importlib.import_module('source_binding')
    assert Path(binding.__file__).resolve() == AFTER/'integration_v3/source_binding.py'
    baseline_binding = binding.verify_accepted_sources()
    assert before == pinned_sources()
    _loaded = SimpleNamespace(
        bootstrap=bootstrap, builder=builder, pipeline=pipeline,
        reference=reference, transpose=transpose, binding=binding,
        baseline_binding=baseline_binding, derivation=derivation,
        pinned_sources=before, original_runtime=pipeline.runtime_bindings())
    return _loaded


def recheck(runtime):
    assert pinned_sources() == runtime.pinned_sources
    assert runtime.bootstrap.validate_normalization() == runtime.derivation
    assert runtime.binding.verify_accepted_sources() == runtime.baseline_binding
    assert runtime.pipeline.Window.transpose_tensor is runtime.transpose
    return dict(pins=runtime.pinned_sources,
                unchanged_original_gate=runtime.baseline_binding,
                normalization_derivation=runtime.derivation)


def loaded_sources():
    """Hash the actual local modules loaded by a completed panel process."""
    answer = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if path.suffix == '.pyc':
            path = Path(importlib.util.source_from_cache(str(path))).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            continue
        key = str(path.relative_to(ROOT))
        row = answer.setdefault(key, dict(path=key, bytes=path.stat().st_size,
                                         sha256=digest(path), modules=[]))
        row['modules'].append(name)
    for row in answer.values():
        row['modules'].sort()
    return answer
