"""Native all-input and measurement-trajectory checks for the gated row."""

from functools import partial
from importlib import import_module
from types import SimpleNamespace

import pytest


@pytest.mark.official
def test_gated_row_native_all_small_inputs(monkeypatch, project_root):
    pytest.importorskip("resource")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    from qcompile.invsqrt.direct import DirectFormat, build_circuit, coefficient_table, phase64
    from qcompile.invsqrt.gated_row import add_row

    km, primitives, official = tool.backend()
    fmt = DirectFormat(3, 2, (13, 9, 5), fused=True, reuse_lookup=True)
    table = coefficient_table(fmt)
    api = SimpleNamespace(**{name: getattr(primitives, name) for name in
                             ("_normalize", "_denormalize", "_phase_by_bits")}, _add_row=add_row)
    circuit = build_circuit(km, api, fmt, table)
    spec = official.ProblemSpecInvSqrt.for_n_p(3)
    tool.native_smoke(km, official, circuit, spec, partial(phase64, fmt, table),
                      list(range(1, spec.max_x + 1)),
                      {"batch": 64, "repeat": 16, "seed": 131})
