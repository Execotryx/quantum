"""Independent runtime-mask identity against Forney recovery."""

import random

import pytest

from qcompile.dqi.decoder import bm_locator, recover_forney, syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.tower import linear, tower


def trace(field, value):
    result = value
    for _ in range(11):
        value = field.mul(value, value)
        result ^= value
    return result


@pytest.mark.parametrize("weight", range(36))
def test_runtime_mask_trace_identity_all_weights(weight):
    field = GF4096()
    dual = tower().trace_dual
    rng = random.Random(6821 + weight)
    errors = {position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)}
    values = syndrome(errors, field)
    recovered = recover_forney(values, bm_locator(values, field), field)
    assert recovered == errors
    for symbol in recovered.values():
        for mask in (0, 4095, rng.randrange(4096)):
            assert trace(field, field.mul(linear(dual, mask), symbol)) == (mask & symbol).bit_count() % 2
