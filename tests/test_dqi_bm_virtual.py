"""Virtual-template routing over every correctable four-syndrome GF(16) input."""

import random
from itertools import combinations, product

import pytest

from qcompile.dqi.bm_routed import State
from qcompile.dqi.bm_routed import step as material_step
from qcompile.dqi.bm_virtual import VirtualState, forward, reverse, reverse_step, step
from qcompile.dqi.decoder import bm_locator, syndrome
from qcompile.dqi.field import GF4096


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


def test_all_correctable_gf16_virtual_rounds():
    field = GF16()
    count = 0
    max_age = [0] * 4
    max_history = [0] * 4
    for weight in range(3):
        for positions in combinations(range(15), weight):
            for magnitudes in product(range(1, 16), repeat=weight):
                values = []
                for k in range(4):
                    value = 0
                    for j, magnitude in zip(positions, magnitudes, strict=True):
                        value ^= field.mul(magnitude, field.exp[(j * (k + 1)) % 15])
                    values.append(value)
                state = VirtualState((1,), (1,), 0, 0)
                material = State((1,), (1,), 0)
                history = []
                zeros = retained = 0
                for index in range(4):
                    old = state
                    state, entry = step(state, values, index, 2, field)
                    material, material_entry = material_step(material, values, index, field)
                    assert material_entry == entry
                    assert state.sigma == material.sigma
                    assert tuple([0] * state.age + list(state.base)) == material.tau
                    assert state.counter == material.counter
                    assert reverse_step(state, entry, values, index, 2, field) == old
                    assert len(state.sigma) - 1 <= 2 and len(state.base) - 1 <= 2
                    zeros += not entry.replace and not entry.retained_discrepancy
                    retained += bool(entry.retained_discrepancy)
                    assert zeros - retained >= abs(state.counter)
                    assert retained <= index // 2
                    max_age[index] = max(max_age[index], state.age)
                    max_history[index] = max(max_history[index], retained)
                    history.append(entry)
                assert reverse(state, history, values, 2, field) == VirtualState((1,), (1,), 0, 0)
                count += 1
    assert count == 23851
    print(f"virtual decodable max age={max_age}, retained={max_history}")


@pytest.mark.parametrize("weight", range(36))
def test_pinned_virtual_round_trip(weight):
    field = GF4096()
    rng = random.Random(3030 + weight)
    errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
    values = syndrome(errors, field)
    state, history = forward(values, 35, field)
    scale = field.inv(state.sigma[0])
    assert [field.mul(x, scale) for x in state.sigma] == bm_locator(values, field)
    assert reverse(state, history, values, 35, field) == VirtualState((1,), (1,), 0, 0)


def test_zero_path_is_virtual_and_out_of_domain_fails_closed():
    field = GF16()
    state, history = forward([0] * 4, 2, field)
    assert state == VirtualState((1,), (1,), 4, 4)
    assert reverse(state, history, [0] * 4, 2, field) == VirtualState((1,), (1,), 0, 0)
    with pytest.raises(ValueError, match="exceed locator radius"):
        forward([0, 0, 1, 0], 2, field)


def test_unrestricted_history_bound_is_tight_at_70_rounds():
    field = GF4096()
    state = State((1,), (1,), 0)
    values = []
    retained = 0
    # Force the next discrepancy by solving for its new syndrome coefficient.
    for target in [0] * 34 + [1] * 35 + [0]:
        index = len(values)
        previous_terms = 0
        for i in range(1, min(index, len(state.sigma) - 1) + 1):
            previous_terms ^= field.mul(state.sigma[i], values[index - i])
        values.append(field.div(target ^ previous_terms, state.sigma[0]))
        state, entry = material_step(state, values, index, field)
        retained += bool(entry.retained_discrepancy)
        assert retained <= index // 2
    assert retained == 34
