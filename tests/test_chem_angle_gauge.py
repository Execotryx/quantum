import math

import numpy as np
import pytest

from qcompile.chemistry.angle_gauge import recode_cosine_signs
from qcompile.chemistry.representation import reconstruct


@pytest.mark.parametrize("brot", [2, 7, 16])
def test_recode_assigns_markers_and_preserves_the_real_projector(brot):
    # Includes zero parent and child branches, non-root vertex labels, and unequal paths.
    edges = [[2, 1], [2, 3], [1, 0], [1, 4], [3, 5], [0, 6]]
    rng = np.random.default_rng(34)
    turn = 1 << brot
    words = rng.integers(0, turn, (64, 6))
    words[:16, :4] = rng.integers(0, 4, (16, 4)) * (turn // 4)
    requested = rng.integers(0, 2, words.shape).astype(bool)
    recoded = recode_cosine_signs(words, edges, brot, requested, root=2)
    assert np.array_equal((recoded >> (brot - 2) ^ recoded >> (brot - 1)) & 1, requested)
    assert np.all((0 <= recoded) & (recoded < turn))
    for original, new in zip(words, recoded, strict=True):
        before = reconstruct(original, brot, edges, 7, 2, radians_per_unit=math.pi)
        after = reconstruct(new, brot, edges, 7, 2, radians_per_unit=math.pi)
        assert np.allclose(np.outer(after, after), np.outer(before, before), atol=1e-14, rtol=0)
