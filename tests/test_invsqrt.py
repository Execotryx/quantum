import random
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from qcompile.errors import ValidationError
from qcompile.invsqrt.fixed import Format, polynomial_model
from qcompile.reference.invsqrt import (
    MAX_INPUT,
    circular_units,
    decimal_margin,
    phase_floor,
    phase_nearest_even,
    scan,
)


def boundary_inputs():
    values = {1, 2, 3, MAX_INPUT - 1, MAX_INPUT}
    for k in range(1, 22):
        values.update(x for x in (2**k - 1, 2**k, 2**k + 1) if x <= MAX_INPUT)
    values.update(random.Random(2718).sample(range(1, MAX_INPUT + 1), 64))
    return sorted(values)


@pytest.mark.parametrize("x", boundary_inputs())
def test_integer_bracket_against_independent_decimal(x):
    with localcontext() as ctx:
        ctx.prec = 100
        target = Decimal(2**64) / Decimal(x).sqrt()
        assert phase_floor(x) == int(target)
        assert phase_nearest_even(x) == int(target.to_integral_value(rounding="ROUND_HALF_EVEN"))


def test_circular_phase_and_wrap_mutation():
    assert circular_units(0, 2**64) == 0
    assert circular_units(0, 2**64 - 1) == 1
    assert circular_units(2**63, 0) == -(2**63)
    assert decimal_margin(1, 0) == Decimal(2) ** -24
    assert decimal_margin(1, 2**63) < 0


def test_scan_visits_every_input_and_last_partial_chunk():
    visited = []

    def model(x):
        visited.append(x)
        return phase_floor(x) % 2**64

    result = scan(model, first=1, last=101, chunk_size=13)
    assert visited == list(range(1, 102))
    assert result["completed"] == result["expected"] == 101
    assert result["nonpositive_margin_count"] == 0
    assert sum(result["margin_histogram_eighths_of_tolerance"]) == 101
    assert result["minimum_margin_turns"] > 0
    assert result["official_compatible"] is False


def test_deliberate_phase_error_detected():
    result = scan(
        lambda x: ((phase_floor(x) % 2**64) + (2**40 if x == 7 else 0)) % 2**64, last=9, chunk_size=3
    )
    assert result["nonpositive_margin_count"] == 1
    assert result["worst_input"] == 7


@pytest.mark.parametrize("first,last,chunk", [(0, 10, 3), (9, 8, 3), (1, MAX_INPUT + 1, 3), (1, 10, 0)])
def test_bad_scan_domain(first, last, chunk):
    with pytest.raises(ValidationError):
        scan(lambda x: 0, first=first, last=last, chunk_size=chunk)


@pytest.mark.parametrize("word", [-1, 2**64, 1.5, True])
def test_scan_rejects_invalid_words(word):
    with pytest.raises(ValidationError, match="phase word"):
        scan(lambda x: word, last=1)


def test_explicit_rounding_and_overflow():
    even = Format(8, 2, signed=True)
    assert even.encode(Fraction(5, 8)) == 2
    assert even.encode(Fraction(7, 8)) == 4
    assert Format(8, 2, True, "floor").encode(Fraction(-1, 8)) == -1
    assert Format(8, 2, True, "toward_zero").encode(Fraction(-1, 8)) == 0
    with pytest.raises(ValidationError, match="overflow"):
        Format(4, 0, True).encode(8)
    assert Format(4, 0, True, overflow="wrap").encode(8) == -8
    assert Format(4, 0, False, overflow="wrap").encode(-1) == 15


def test_finite_width_model_scaling_and_invalid_initial_model():
    model = polynomial_model(
        {
            "format": {"width": 68, "fractional": 60, "signed": True},
            "coefficients": [["1/2"]],
            "newton_steps": 0,
        }
    )
    assert model(1) == 2**63
    assert model(4) == 2**62
    assert model(16) == 2**61
    assert scan(model, last=32)["nonpositive_margin_count"] > 0


@pytest.mark.slow
def test_complete_domain_rigorous_numerical_harness():
    # Harness control only. The target is deliberately fed back, not a candidate proof.
    result = scan(lambda x: phase_floor(x) % 2**64)
    assert result["completed"] == 3_133_452
    assert result["full_domain"] is True
    assert result["nonpositive_margin_count"] == 0
    assert result["minimum_margin_turns"] > 0
