"""Bound and native mutation checks for the opt-in v4 width reduction."""

import json
from functools import partial
from importlib import import_module

import numpy as np
import pytest

from qcompile.invsqrt.direct import phase64
from qcompile.invsqrt.trimmed import TrimmedFormat, build_circuit, prove_chunk


def load_control(project_root):
    path = project_root / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    return tuple(tuple(row) for row in record["coefficients"])


def test_trimmed_bounds_and_control_phase(project_root):
    fmt = TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True)
    table = load_control(project_root)
    xs = np.asarray([1, 2, 3, 4, 15, 16, 17, 940030, 2416632, 3133452], dtype=np.int64)
    prove_chunk(fmt, table, xs)
    assert all(all(word < 1 << width for word, width in zip(row, fmt.widths, strict=True)) for row in table)


@pytest.mark.official
def test_trimmed_native_parity_and_high_bit_mutation(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    km, primitives, official = tool.backend()
    fmt = TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True)
    table = load_control(project_root)
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    circuit = build_circuit(km, primitives, fmt, table)
    points = [1, 2, 3, 4, 15, 16, 17, 940030, 2416632, spec.max_x]
    tool.native_smoke(km, official, circuit, spec, partial(phase64, fmt, table), points,
                      {"seed": 7701, "random_inputs": 0, "repeat": 16, "batch": 64})
    bad = ((table[0][0] | (1 << fmt.widths[0]), *table[0][1:]), *table[1:])
    with pytest.raises(ValueError, match="trimmed bit"):
        build_circuit(km, primitives, fmt, bad)
