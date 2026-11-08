"""Check batched depth statistics against the scalar routed BM oracle."""

import numpy as np

from qcompile.dqi.bm_routed import State, step
from qcompile.dqi.decoder import syndrome
from qcompile.dqi.field import GF4096
from qcompile.dqi.history_sampling import history_statistics


def scalar_statistics(rows, field):
    n = rows.shape[1]
    histogram, maximum, shifted_max = [0] * (n + 1), [0] * n, 0
    for shot, row in enumerate(rows):
        state = State((1,), (1,), 0)
        retains = 0
        sequence = row.tolist()
        for j in range(n):
            previous = state
            state, history = step(previous, sequence, j, field)
            degree = len(state.sigma) - 1
            shifted = len(previous.tau) if history.replace or history.retained_discrepancy else 0
            if degree > min(j + 1, 35) or shifted > 35:
                return {"status": "degree_violation", "shot": shot, "round": j + 1,
                        "degree": degree, "shifted_degree": shifted}
            retains += bool(history.retained_discrepancy)
            maximum[j] = max(maximum[j], degree)
            shifted_max = max(shifted_max, shifted)
        histogram[retains] += 1
    return {"status": "complete", "shots": len(rows), "histogram": histogram,
            "max_degree_by_round": maximum, "max_active_shifted_degree": shifted_max}


def test_history_batches_match_scalar_for_every_weight():
    field = GF4096()
    rng = np.random.default_rng(2026110801)
    rows = []
    for weight in list(range(36)) * 5:
        locations = rng.choice(4095, size=weight, replace=False).tolist()
        values = rng.integers(1, 4096, size=weight).tolist()
        rows.append(syndrome(dict(zip(locations, values, strict=True)), field))
    data = np.asarray(rows, dtype=np.int64)
    expected = scalar_statistics(data, field)
    assert expected["status"] == "complete"
    assert history_statistics(data, field, block_size=37) == expected


def test_history_batches_keep_first_violation_in_shot_order():
    field = GF4096()
    data = np.zeros((3, 70), dtype=np.int64)
    data[1, 69] = data[2, 37] = 1
    expected = scalar_statistics(data, field)
    assert expected["shot"] == 1 and expected["round"] == 70
    assert history_statistics(data, field) == expected
