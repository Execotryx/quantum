from functools import partial

import numpy as np
import pytest

from qcompile.invsqrt.direct import DirectFormat, coefficient_table, phase64
from qcompile.invsqrt.direct_screen import beta_one_targets, complete_cost, scan_phase
from qcompile.reference.invsqrt import circular_units, phase_nearest_even


def test_exact_coefficients_and_power_of_four_phases():
    fmt = DirectFormat(10, 6, (33, 28, 23, 18))
    table = coefficient_table(fmt)
    assert table[0] == (1 << 33, 1 << 27, 3 << 20, 5 << 14)
    assert len(table) == 192
    xs = np.asarray([4**e for e in range(11)], dtype=np.int64)
    expected, _ = beta_one_targets(xs)
    assert expected[0] == 0
    assert np.array_equal(phase64(fmt, table, xs), expected)


def test_phase64_wrap_and_tolerance_edges():
    def targets(xs):
        return np.zeros_like(xs, dtype=np.uint64), np.full_like(xs, 10, dtype=np.uint64)

    def evaluate(xs):
        values = [2**64 - 9, 10, 2**63, 1]
        return np.asarray([values[x - 1] for x in xs.tolist()], dtype=np.uint64)

    margins = scan_phase(evaluate, 4, targets, chunk=3)
    assert margins["input_count"] == 4
    assert margins["failed_inputs"] == 1
    assert margins["nonpositive_margins"] == 2
    assert margins["above_90_percent"] == 2
    assert margins["minimum_margin_x"] == margins["worst_x"] == 3
    assert margins["minimum_margin_phase64"] == 10 - 2**63
    with pytest.raises(ValueError, match="incomplete"):
        scan_phase(lambda xs: evaluate(xs[:-1]), 4, targets)


def test_rounding_and_rotation_charge():
    xs = np.array([1, 2, 3, 65535, 1048576, 3133452], dtype=np.int64)
    target, _ = beta_one_targets(xs)
    assert all(
        circular_units(int(word), phase_nearest_even(x)) == 0
        for x, word in zip(xs.tolist(), target, strict=True)
    )
    assert complete_cost(2, (2, 4, 0), 1)["score"] == 6
    assert complete_cost(2, (2, 4, 1), 1)["score"] > 6
    with pytest.raises(ValueError, match="positive margin"):
        complete_cost(2, (2, 4, 0), 0)


@pytest.mark.slow
def test_independent_direct_control_covers_domain():
    fmt = DirectFormat(10, 6, (33, 28, 23, 18))
    result = scan_phase(partial(phase64, fmt, coefficient_table(fmt)), 3_133_452)
    assert result["input_count"] == 3_133_452
    assert result["nonpositive_margins"] == result["above_90_percent"] == 0
    assert result["worst_tolerance_fraction"] < 0.30
