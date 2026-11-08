"""Regression tests for the next-tranche algebra and reversible ablations."""

from functools import partial
from importlib import import_module
import sys

import numpy as np
import pytest

from qcompile.dqi.decoder import bm_locator, recover_forney, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.tower import linear, tower
from qcompile.chemistry.factorization import (
    direct_residual, gram_residual, rank_lower_bound, shifted_target, svec,
)
from qcompile.invsqrt.direct import DirectFormat, build_circuit, coefficient_table, phase64
from qcompile.invsqrt.unlookup import repair_table


def test_tower_roundtrip_bilinearity_and_trace_dual():
    field, model = GF4096(), tower()
    assert len(model.terms) == 54
    for value in range(4096):
        assert linear(model.basis, linear(model.coordinates, value)) == value
    for i in range(12):
        for j in range(12):
            assert model.multiply(1 << i, 1 << j) == field.mul(1 << i, 1 << j)
        for value in (0, 1, 0x400, 0x801, 4095):
            term = field.mul(model.trace_dual[i], value)
            trace = term
            for _ in range(11):
                term = field.mul(term, term)
                trace ^= term
            assert trace == value >> i & 1


@pytest.mark.parametrize("weight", [0, 1, 8, 35])
def test_independent_forney_recovery(weight):
    field = GF4096()
    errors = {int(j): 1 + i * 113 for i, j in enumerate(np.linspace(0, 4094, weight, dtype=int))}
    values = syndrome(errors, field)
    locator = bm_locator(values, field)
    assert recover_forney(values, locator, field) == errors


def test_anf_repair_matches_each_address_and_measurement_mask():
    rows = (0, 0, 0, 0, 7, 2, 5, 6, 7, 1, 3, 4, 1, 4, 7, 2)
    table = repair_table(rows, 2)
    for address, target in enumerate(rows):
        for mask in range(8):
            actual = 0
            for subset, word in enumerate(table[address >> 2]):
                if subset & address == subset:
                    actual ^= (word & mask).bit_count() & 1
            assert actual == (target & mask).bit_count() & 1


def test_shifted_symmetric_gram_and_gradient():
    rng = np.random.default_rng(5)
    factors = rng.normal(size=(3, 4, 4))
    factors = factors + factors.swapaxes(-1, -2)
    tei = np.einsum("apq,ars->pqrs", factors, factors)
    shift = np.diag([1.0, 0.3, -0.1, 0.0])
    rows = svec(factors)
    target = shifted_target(tei, shift)
    ident = np.eye(4)
    dense_shift = (np.einsum("pq,rs->pqrs", shift, ident)
                   + np.einsum("pq,rs->pqrs", ident, shift)) / 2
    assert direct_residual(target, rows) == pytest.approx(np.linalg.norm(dense_shift))
    norm = float(np.vdot(target, target))
    squared, grad = gram_residual(target, rows, norm)
    assert squared == pytest.approx(float(np.vdot(dense_shift, dense_shift)))
    direction = rng.normal(size=rows.shape)
    plus = gram_residual(target, rows + direction * 1e-6, norm)[0]
    minus = gram_residual(target, rows - direction * 1e-6, norm)[0]
    assert (plus - minus) / 2e-6 == pytest.approx(float(np.vdot(grad, direction)), abs=2e-6)
    assert rank_lower_bound(np.array([-2.0, -1.0, 0, 3, 5]), 1) == pytest.approx(np.sqrt(14.0))


@pytest.mark.official
@pytest.mark.parametrize("binary,measurement", [(True, False), (False, True), (True, True)])
def test_native_invsqrt_ablations(monkeypatch, project_root, tmp_path, binary, measurement):
    if not sys.platform.startswith("linux"):
        pytest.skip("pinned native Linux backend required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    tool = import_module("invsqrt_direct")
    km, primitives, official = tool.backend()
    fmt = DirectFormat(3, 2, (13, 9, 5), fused=True, reuse_lookup=True,
                       binary_normalization=binary, measurement_unlookup=measurement)
    table = coefficient_table(fmt)
    circuit, _ = tool.emit(km, build_circuit(km, primitives, fmt, table), official, tmp_path / "invsqrt.kmb")
    spec = official.ProblemSpecInvSqrt.for_n_p(3)
    tool.native_smoke(km, official, circuit, spec, partial(phase64, fmt, table),
                      list(range(1, spec.max_x + 1)), {"batch": 64, "repeat": 4, "seed": 884})
