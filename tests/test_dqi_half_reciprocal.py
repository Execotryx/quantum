"""Half-degree reciprocal identity and exact Euclidean history replay."""

import random
from itertools import combinations

import pytest

from qcompile.dqi.decoder import _add, _divide, _multiply, bm_locator, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.half_reciprocal import bezout_reciprocal, reverse_remainders
from qcompile.dqi.scan import derivative_reciprocal


class GF16(GF4096):
    order = 15

    def __init__(self):
        self.exp = []
        self.log = [-1] * 16
        value = 1
        for index in range(15):
            self.exp.append(value)
            self.log[value] = index
            value <<= 1
            if value & 16:
                value ^= 0x13
        assert value == 1 and all(i >= 0 for i in self.log[1:])

    @staticmethod
    def symbol(value):
        if type(value) is not int or not 0 <= value < 16:
            raise ValueError("invalid GF(16) symbol")
        return value


def check(locator, field):
    result = bezout_reciprocal(locator, field)
    assert _add(_multiply(list(result.a), list(result.even), field),
                _multiply(list(result.b), list(result.odd), field)) == [1]
    assert reverse_remainders(result.gcd, result.quotients, field) == (list(result.even), list(result.odd))
    assert list(result.reciprocal) == derivative_reciprocal(locator, field)
    if len(locator) > 1:
        derivative = [locator[i] if i % 2 else 0 for i in range(1, len(locator))]
        assert _divide(_multiply(list(result.reciprocal), derivative, field), locator, field)[1] == [1]
    return result


def test_all_correctable_gf16_locators_and_scales():
    field = GF16()
    count = 0
    for weight in range(3):
        for positions in combinations(range(15), weight):
            locator = [1]
            for position in positions:
                locator = _multiply(locator, [1, field.exp[position]], field)
            for scale in range(1, 16):
                check([field.mul(value, scale) for value in locator], field)
                count += 1
    assert count == 1815


@pytest.mark.parametrize("weight", range(36))
def test_pinned_field_every_weight_and_rescaling(weight):
    field = GF4096()
    rng = random.Random(7159 + weight)
    errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
    locator = bm_locator(syndrome(errors, field), field)
    scale = rng.randrange(1, 4096)
    locator = [field.mul(value, scale) for value in locator]
    result = check(locator, field)
    assert len(result.even) - 1 <= weight // 2
    assert len(result.odd) - 1 <= max(0, (weight - 1) // 2)


def test_zero_case_repeated_root_and_missing_history():
    field = GF4096()
    result = check([1], field)
    assert result.reciprocal == (0,) and result.quotients == ()
    with pytest.raises(ValueError, match="not invertible"):
        bezout_reciprocal([1, 0, 1], field)
    sample = bezout_reciprocal([1, 1, 1, 2, 3], field)
    assert sample.quotients
    assert reverse_remainders(sample.gcd, sample.quotients[:-1], field) != (list(sample.even), list(sample.odd))
