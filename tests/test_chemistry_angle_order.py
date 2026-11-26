"""Check a rank-lowering Givens move and its decoded vectors."""

import numpy as np

from qcompile.chemistry.angle_order import search_angle_order
from qcompile.chemistry.representation import reconstruct


def test_commuting_givens_move_lowers_mixed_rank():
    addresses = np.arange(16)
    first = ((addresses & 1) != 0) & ((addresses & 4) != 0)
    second = ((addresses & 2) != 0) & ((addresses & 4) != 0)
    angles = np.column_stack((first, first, second, second)).astype(np.int64)
    edges = np.array([[0, 1], [0, 2], [1, 3], [2, 4]])
    order, before, after = search_angle_order(angles, edges, brot=2, batch=2, low_bits=2,
                                              seed=71, proposals=100)
    assert before == 3 and after == 2
    assert order == (0, 2, 1, 3)
    for row in angles:
        original = reconstruct(row, 2, edges, 5, 0, radians_per_unit=np.pi)
        reordered = reconstruct(row[list(order)], 2, edges[list(order)], 5, 0, radians_per_unit=np.pi)
        np.testing.assert_array_equal(original, reordered)
