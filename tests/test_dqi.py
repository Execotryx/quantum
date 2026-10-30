import random

import pytest

from qcompile.dqi.decoder import decode, failure_summary, mask_parity, syndrome
from qcompile.dqi.field import GF4096
from qcompile.errors import ValidationError
from qcompile.reference import field as polynomial


@pytest.fixture(scope="module")
def field():
    return GF4096()


def test_all_unary_field_values_and_inverse_maps(field):
    for a in range(4096):
        assert field.mul(a, 1) == a
        assert field.mul(a, 0) == 0
        assert field.mul(a, a) == polynomial.multiply(a, a)
        assert field.apply_map(field.square_map(), a) == field.mul(a, a)
        assert field.apply_map(field.fixed_map(3791), a) == polynomial.multiply(a, 3791)
        if a:
            inverse = field.inv(a)
            assert polynomial.multiply(a, inverse) == 1
    with pytest.raises(ZeroDivisionError):
        field.inv(0)
    with pytest.raises(ZeroDivisionError):
        polynomial.inverse(0)


def test_random_multiplication_against_carryless_reference(field):
    rng = random.Random(412)
    for _ in range(3000):
        a, b = rng.randrange(4096), rng.randrange(4096)
        assert field.mul(a, b) == polynomial.multiply(a, b)


@pytest.mark.parametrize("weight", range(36))
def test_bm_and_eea_every_supported_weight(field, weight):
    rng = random.Random(913 + weight)
    positions = rng.sample(range(4095), weight)
    errors = {j: rng.randrange(1, 4096) for j in positions}
    values = syndrome(errors, field)
    assert decode(values, field, "bm") == errors
    assert decode(values, field, "eea") == errors
    mask1, mask2 = rng.getrandbits(49140), rng.getrandbits(49140)
    assert mask_parity(errors, mask1 ^ mask2) == mask_parity(errors, mask1) ^ mask_parity(errors, mask2)


@pytest.mark.parametrize("position", [0, 4094])
def test_endpoint_syndrome_independently_computed(field, position):
    errors = {position: 0x853}
    values = syndrome(errors, field)
    for i, value in enumerate(values):
        assert value == polynomial.multiply(0x853, polynomial.power(2, (i + 1) * position))
    assert decode(values, field) == errors


def test_masks_cannot_be_fixed():
    errors = {0: 1, 4094: 0x800}
    assert mask_parity(errors, 0) == 0
    assert mask_parity(errors, 1) == 1
    assert mask_parity(errors, 1 << (12 * 4094 + 11)) == 1
    assert mask_parity(errors, (1 << 49140) - 1) == 0
    with pytest.raises(ValidationError):
        mask_parity(errors, 1 << 49140)


def test_wrong_modulus_and_reversed_bits_are_detected(field):
    # An independently different irreducible-looking literal is not the contract field.
    assert any(field.mul(a, 3077) != polynomial.multiply(a, 3077, 0x1009) for a in range(1, 4096))
    assert syndrome({0: 1}, field) != syndrome({0: 0x800}, field)


def test_failure_categories_are_not_added_as_separate_trajectories():
    keys = ("decoder_disagreement", "wrong_phase", "register_corruption", "dirty_workspace")
    events = [
        dict.fromkeys(keys, False),
        dict(zip(keys, [True, False, False, False], strict=True)),
        dict(zip(keys, [True, True, False, True], strict=True)),
    ]
    result = failure_summary(events)
    assert result["completed"] == 3
    assert result["trajectory_failures"] == 1
    assert result["diagnostics"]["decoder_disagreement"] == 2
