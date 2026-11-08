"""Algebraic preservation and bounded-search controls for GF(64)."""

import random

import pytest

from qcompile.dqi.bilinear_search import basis_tensor, expand, flip, reduce_terms, search, verify
from qcompile.dqi.tower import tower


def test_flips_preserve_tensor_and_reductions():
    terms = reduce_terms(tower().subfield_terms)
    expected = basis_tensor(terms)
    rng = random.Random(880)
    terms = expand(terms, rng)
    for _ in range(3000):
        candidate = flip(terms, rng)
        if candidate is None:
            terms = expand(reduce_terms(terms), rng)
            continue
        terms = candidate
        assert basis_tensor(terms) == expected
        if _ % 20 == 19:
            terms = reduce_terms(terms)
    verify(terms, exhaustive=True)


def test_reject_mutated_tensor():
    terms = list(tower().subfield_terms)
    a, b, out = terms[0]
    terms[0] = (a, b, out ^ 1)
    with pytest.raises(ValueError, match="tensor"):
        verify(tuple(terms), exhaustive=True)


def test_bounded_search_registers_exact_result():
    first = search(27, 250, 60, 100)
    second = search(27, 250, 60, 100)
    assert first["steps_completed"] == second["steps_completed"]
    assert first["steps_completed"] > 0
    assert first["terms"] == second["terms"]
    assert first["best_rank"] <= first["initial_rank"]
    verify(first["terms"], exhaustive=True)
    with pytest.raises(ValueError, match="positive"):
        search(0, 0, 1, 1)
