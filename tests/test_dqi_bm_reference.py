"""Roundwise normalized BM history recovery against the independent oracle."""

import random
from dataclasses import replace
from itertools import product

import pytest

from qcompile.dqi.bm_reference import forward, reverse
from qcompile.dqi.decoder import bm_locator, syndrome
from qcompile.dqi.field import GF4096


@pytest.mark.parametrize("weight", range(36))
def test_normalized_bm_round_trip_all_weights(weight):
    field = GF4096()
    rng = random.Random(3309 + weight)
    errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
    syndromes = syndrome(errors, field)
    locator, auxiliary, degree, history = forward(syndromes, field)
    assert locator == bm_locator(syndromes, field)
    assert reverse(syndromes, locator, auxiliary, degree, history, field) == ([1], [0, 1], 0)


def test_history_mutation_detected():
    field = GF4096()
    values = syndrome({2: 5, 17: 7}, field)
    locator, auxiliary, degree, history = forward(values, field)
    index = next(i for i, entry in enumerate(history) if not entry.replace)
    history[index] = replace(history[index], retained_discrepancy=1)
    with pytest.raises(ValueError, match="history"):
        reverse(values, locator, auxiliary, degree, history, field)


def test_zero_syndrome_demonstrates_unbounded_auxiliary_degree():
    locator, auxiliary, degree, history = forward([0] * 70, GF4096())
    assert locator == [1] and degree == 0
    assert auxiliary == [0] * 71 + [1]
    assert len(history) == 70


class GF16(GF4096):
    order = 15

    def __init__(self):
        self.exp = []
        self.log = [-1] * 16
        value = 1
        for index in range(self.order):
            self.exp.append(value)
            self.log[value] = index
            value <<= 1
            if value & 16:
                value ^= 0x13
        assert value == 1 and all(index >= 0 for index in self.log[1:])

    @staticmethod
    def symbol(value):
        if type(value) is not int or not 0 <= value < 16:
            raise ValueError("invalid GF(16) symbol")
        return value


def test_exhaustive_gf16_four_symbol_histories():
    field = GF16()

    def oracle(symbols):
        size = len(symbols)
        current, previous = [1] + [0] * size, [1] + [0] * size
        degree, offset, last = 0, 1, 1
        for index, value in enumerate(symbols):
            delta = value
            for i in range(1, degree + 1):
                delta ^= field.mul(current[i], symbols[index - i])
            if not delta:
                offset += 1
                continue
            old = current[:]
            ratio = field.div(delta, last)
            for i in range(size + 1 - offset):
                current[i + offset] ^= field.mul(ratio, previous[i])
            if 2 * degree <= index:
                degree, previous, last, offset = index + 1 - degree, old, delta, 1
            else:
                offset += 1
        while len(current) > 1 and current[-1] == 0:
            current.pop()
        return current

    for symbols in product(range(16), repeat=4):
        syndromes = list(symbols)
        locator, auxiliary, degree, history = forward(syndromes, field)
        assert reverse(syndromes, locator, auxiliary, degree, history, field) == ([1], [0, 1], 0)
        for index in range(1, 5):
            assert forward(syndromes[:index], field)[0] == oracle(syndromes[:index])
