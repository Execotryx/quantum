import math
from decimal import Decimal, localcontext

import mpmath as mp
import pytest

from qcompile.errors import ValidationError
from qcompile.reference.scoring import (
    DELTA,
    aggregate,
    chemistry_cost,
    cp_upper,
    dqi_cost,
    log_binomial_cdf_decimal,
    repetition,
    rotation_price,
)


def test_zero_failure_cp_is_not_empirical_rate():
    p = cp_upper(0, 102400)
    assert p == pytest.approx(0.0008660587301657926, rel=2e-15)
    assert repetition(p) == pytest.approx(1.1912604648115832, rel=2e-15)
    assert 1 - DELTA == 1  # Documents why inverse-CDF(1-delta) is invalid.
    assert repetition(0) == 1
    assert dqi_cost(1893, 5725461, 0, 102400)["cost"] > 1893**2 * 5725461


@pytest.mark.parametrize("k", [0, 1, 7, 150, 4500, 5000, 5500, 6000])
def test_extreme_tail_independent_decimal_residual(k):
    p = cp_upper(k, 102400)
    actual = log_binomial_cdf_decimal(k, 102400, p)
    with localcontext() as ctx:
        ctx.prec = 90
        target = -128 * Decimal(2).ln()
        assert abs(actual - target) < Decimal("2e-9")


def test_small_sample_against_high_precision_polynomial_cdf():
    with mp.workdps(90):
        n, k = 100, 3
        p = cp_upper(k, n)
        cdf = mp.fsum(mp.binomial(n, j) * mp.mpf(p) ** j * (1 - mp.mpf(p)) ** (n - j) for j in range(k + 1))
        assert abs(mp.log(cdf) + 128 * mp.log(2)) < mp.mpf("1e-11")


def test_cp_monotonicity_and_rejection_threshold():
    ks = [0, 1, 10, 100, 1000, 4500, 5500, 6000, 102399, 102400]
    bounds = [cp_upper(k, 102400) for k in ks]
    assert bounds == sorted(bounds)
    assert len(set(bounds[:-1])) >= len(bounds) - 1
    assert cp_upper(102400, 102400) == 1
    with pytest.raises(ValidationError, match="1/16"):
        dqi_cost(1, 1, 102400, 102400)
    with pytest.raises(ValidationError, match="1/16"):
        repetition(1 / 16)
    epsilon = math.nextafter(1 / 16, 0)
    with mp.workdps(90):
        expected = mp.log(2) / -mp.log(mp.mpf(".5") + 2 * mp.sqrt(mp.mpf(epsilon)))
        # Rationalizing the distance to the cutoff avoids amplified cancellation.
        assert repetition(epsilon) == pytest.approx(float(expected), rel=1e-14)
        assert repetition(epsilon) > 1e15
        regular = 0.062499
        want = mp.log(2) / -mp.log(mp.mpf(".5") + 2 * mp.sqrt(mp.mpf(regular)))
        assert repetition(regular) == pytest.approx(float(want), rel=2e-11)
        assert expected > 0


@pytest.mark.parametrize(
    "k,n,delta",
    [
        (-1, 10, DELTA),
        (11, 10, DELTA),
        (0, 0, DELTA),
        (False, 10, DELTA),
        (1, True, DELTA),
        (0, 10, 0),
        (0, 10, float("nan")),
    ],
)
def test_invalid_counts(k, n, delta):
    with pytest.raises(ValidationError):
        cp_upper(k, n, delta)


def test_rotation_price_independent_high_precision_units_and_no_double_count():
    with mp.workdps(90):
        margin = mp.mpf("3.1e-12")
        n = 37
        expected = 0.56 * mp.log(n / (mp.pi * margin), 2) + mp.mpf("5.3")
        result = rotation_price(float(margin), n, 7735, 1)
        assert result["T_per_fine_rotation"] == pytest.approx(float(expected), rel=1e-14)
        assert result["C"] == pytest.approx(7735 + (1 + n * float(expected)) / 4)
        assert result["allocated_error_radians"] == pytest.approx(float(mp.pi * margin / n))
        assert result["kind"] == "estimate"
    assert rotation_price(1e-12, 0, 11, 4)["C"] == 12
    assert rotation_price(1e-12, 0, 11, 4)["allocated_error_radians"] is None


@pytest.mark.parametrize("margin", [0, -1, float("nan"), float("inf")])
def test_invalid_rotation_margin(margin):
    with pytest.raises(ValidationError):
        rotation_price(margin, 1, 1, 1)


def test_aggregate_all_components_and_finiteness():
    refs = {"invsqrt": 8, "dqi": 27, "dfthcsos": 64}
    costs = {"invsqrt": 1, "dqi": 1, "dfthcsos": 1}
    assert aggregate(refs, costs) == pytest.approx(24)
    assert aggregate(refs, refs) == 1
    with pytest.raises(ValidationError):
        aggregate(refs, {"invsqrt": 1})
    with pytest.raises(ValidationError):
        aggregate(refs, {**costs, "dqi": float("nan")})


def good_chemistry(**changes):
    return (
        dict(
            residual1=0.01,
            residual2=0.017,
            normalization=50,
            e_sos=-22145.27335,
            q_total=1000,
            t_total=2000,
            max_angle_width=128,
        )
        | changes
    )


def test_chemistry_complete_cost_not_capped_at_128():
    result = chemistry_cost(**good_chemistry())
    assert result["gap"] == 5
    assert result["cost"] == pytest.approx(math.sqrt(5 * 95) * 1000 * 2000)


@pytest.mark.parametrize(
    "changes",
    [
        dict(normalization=49),
        dict(max_angle_width=129),
        dict(residual1=0.02001),
        dict(residual2=-0.1),
        dict(e_sos=-22140.27335),
        dict(e_sos=-22240.27335),
        dict(residual1=float("nan")),
        dict(e_sos=0),
    ],
)
def test_chemistry_negative_controls(changes):
    with pytest.raises(ValidationError):
        chemistry_cost(**good_chemistry(**changes))
