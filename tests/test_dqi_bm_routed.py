"""Exhaustive small-field routing, reversal and independent BM comparison."""

import random
from itertools import combinations, product

import pytest

from qcompile.dqi.bm_reference import discrepancy
from qcompile.dqi.bm_reference import forward as reference_forward
from qcompile.dqi.bm_routed import History, State, forward, reverse, reverse_step, step
from qcompile.dqi.decoder import _add, bm_locator, syndrome
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
        assert value == 1 and all(index >= 0 for index in self.log[1:])

    @staticmethod
    def symbol(value):
        if type(value) is not int or not 0 <= value < 16:
            raise ValueError("invalid GF(16) symbol")
        return value


def normalized(state, field):
    inv = field.inv(state.sigma[0])
    return [field.mul(value, inv) for value in state.sigma]


def test_all_gf16_four_symbol_rounds_and_reverse():
    field = GF16()
    branches = {"zero": 0, "retain": 0, "replace": 0}
    valid = {}
    for weight in range(3):
        for positions in combinations(range(15), weight):
            for magnitudes in product(range(1, 16), repeat=weight):
                words = []
                for k in range(4):
                    value = 0
                    for j, magnitude in zip(positions, magnitudes, strict=True):
                        value ^= field.mul(magnitude, field.exp[(j * (k + 1)) % 15])
                    words.append(value)
                valid[tuple(words)] = reference_forward(words, field)[0]
    assert len(valid) == 23851
    max_sigma = [0] * 4
    max_tau = [0] * 4
    max_history = [0] * 4
    for symbols in product(range(16), repeat=4):
        values = list(symbols)
        state = State((1,), (1,), 0)
        history = []
        for index in range(4):
            before = state
            state, entry = step(state, values, index, field)
            assert reverse_step(state, entry, values, index, field) == before
            delta = discrepancy(list(before.sigma), values, index, field)
            old_delta = field.inv(before.sigma[0])
            if delta:
                alpha = field.div(delta, old_delta)
                shifted = [0, *before.tau]
                unscaled = _add(list(before.sigma), [field.mul(alpha, x) for x in shifted])
                inverse_constant = field.inv(unscaled[0])
                assert normalized(state, field) == [field.mul(x, inverse_constant) for x in unscaled]
            if entry.replace:
                assert field.mul(state.sigma[0], delta) == 1
                recovered_old_delta = field.mul(field.mul(state.sigma[0], field.inv(state.tau[0])), delta)
                assert recovered_old_delta == old_delta
            else:
                assert field.mul(state.sigma[0], old_delta) == 1
            branch = "replace" if entry.replace else "retain" if entry.retained_discrepancy else "zero"
            branches[branch] += 1
            history.append(entry)
            if symbols in valid:
                max_sigma[index] = max(max_sigma[index], len(state.sigma) - 1)
                max_tau[index] = max(max_tau[index], len(state.tau) - 1)
                max_history[index] = max(max_history[index], sum(bool(h.retained_discrepancy) for h in history))
                assert len(state.sigma) - 1 <= min(index + 1, 2)
        assert reverse(state, history, values, field) == State((1,), (1,), 0)
        if symbols in valid:
            assert normalized(state, field) == valid[symbols]
    assert all(branches.values())
    print(f"decodable per-round max sigma={max_sigma}, tau={max_tau}, retained={max_history}; branches={branches}")


def test_tie_policy_can_differ_outside_decoding_radius():
    field = GF16()
    values = [1, 0, 0, 1]
    routed, _ = forward(values, field)
    assert normalized(routed, field) == [1, 0, 1, 1]
    assert reference_forward(values, field)[0] == [1, 0, 0, 1]


@pytest.mark.parametrize("weight", range(36))
def test_pinned_field_locator_and_round_trip(weight):
    field = GF4096()
    rng = random.Random(2500 + weight)
    errors = {j: rng.randrange(1, 4096) for j in rng.sample(range(4095), weight)}
    values = syndrome(errors, field)
    state, history = forward(values, field)
    assert normalized(state, field) == bm_locator(values, field)
    assert reverse(state, history, values, field) == State((1,), (1,), 0)


def test_history_mutations_are_rejected():
    field = GF16()
    values = [1, 1, 2, 3]
    state, history = forward(values, field)
    changed = history[:]
    changed[-1] = History(not changed[-1].replace, changed[-1].retained_discrepancy)
    with pytest.raises(ValueError):
        reverse(state, changed, values, field)
