from functools import partial

import numpy as np

from qcompile.invsqrt.direct import DirectFormat, phase64
from qcompile.invsqrt.direct_screen import beta_one_targets, scan_phase
from qcompile.invsqrt.lattice import search_table
from qcompile.invsqrt.minimax import coefficient_table


def test_lattice_uses_exact_model_and_improves_small_full_domain():
    fmt = DirectFormat(3, 2, (15, 12, 9))
    table = coefficient_table(fmt)
    same, zero = search_table(fmt, table, 147, beta_one_targets, radius=0)
    assert same == table
    assert all(offset == (0, 0, 0) for offset in zero)
    chosen, offsets = search_table(fmt, table, 147, beta_one_targets, radius=1)
    assert all(max(map(abs, offset)) <= 1 for offset in offsets)
    before = scan_phase(partial(phase64, fmt, table), 147)
    after = scan_phase(partial(phase64, fmt, chosen), 147)
    assert after["worst_tolerance_fraction"] <= before["worst_tolerance_fraction"]
    xs = np.arange(1, 148, dtype=np.int64)
    assert phase64(fmt, chosen, xs).shape == xs.shape
