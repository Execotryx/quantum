"""Exhaustive decodable GF(16) domain for the two-bank end-state map."""

import random
from itertools import combinations, product

import pytest

from qcompile.dqi.decoder import syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.inplace import degree_bits, pack, transfer_forward, transfer_reverse, unpack


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


def test_all_decodable_gf16_n4_end_states_and_transfers():
    field = GF16()
    count = 0
    seen_syndromes = set()
    seen_states = set()
    for weight in range(3):
        for positions in combinations(range(15), weight):
            for magnitudes in product(range(1, 16), repeat=weight):
                errors = dict(zip(positions, magnitudes, strict=True))
                values = []
                for k in range(4):
                    value = 0
                    for j, magnitude in errors.items():
                        value ^= field.mul(magnitude, field.exp[(j * (k + 1)) % 15])
                    values.append(value)
                clean, encoded_weight, bank = transfer_forward(values, field)
                assert clean == [0] * 4 and encoded_weight == weight
                restored, cleared_weight, cleared_bank = transfer_reverse(clean, encoded_weight, bank, field)
                assert restored == values and cleared_weight == 0 and cleared_bank == [0] * 4
                assert not any(bank[2 * weight:])
                locator = [1, *bank[:weight]]
                g = bank[weight:2 * weight]
                for position, magnitude in errors.items():
                    root = field.exp[-position % 15]
                    assert field.evaluate(locator, root) == 0
                    assert field.evaluate(g, root) == magnitude
                    assert (field.evaluate(g, root) & 15).bit_count() % 2 == magnitude.bit_count() % 2
                seen_syndromes.add(tuple(values))
                seen_states.add((encoded_weight, *bank))
                count += 1
    assert degree_bits(4) == 2
    assert count == len(seen_syndromes) == len(seen_states) == 23851


def test_weight_zero_and_invalid_encodings():
    field = GF16()
    assert pack([0] * 4, field) == (0, [0] * 4)
    assert unpack(0, [0] * 4, field) == [0] * 4
    with pytest.raises(ValueError, match="unused"):
        unpack(0, [1, 0, 0, 0], field)
    with pytest.raises(ValueError, match="lower degree"):
        unpack(2, [1, 0, 0, 0], field)
    with pytest.raises(ValueError, match="invertible"):
        unpack(2, [0, 1, 1, 0], field)
    with pytest.raises(ValueError, match="clean source"):
        transfer_reverse([1, 0, 0, 0], 0, [0] * 4, field)


@pytest.mark.parametrize("weight", range(36))
def test_pinned_field_end_state_all_weights(weight):
    field = GF4096()
    rng = random.Random(879 + weight)
    errors = {position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)}
    values = syndrome(errors, field)
    clean, actual_weight, bank = transfer_forward(values, field)
    assert actual_weight == weight and clean == [0] * 70
    assert transfer_reverse(clean, actual_weight, bank, field) == (values, 0, [0] * 70)
    g = bank[weight:2 * weight]
    for position, magnitude in errors.items():
        assert field.evaluate(g, field.exp[-position % 4095]) == magnitude
    assert degree_bits(70) == 6
