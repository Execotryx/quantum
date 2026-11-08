from qcompile.liveness import operation_intervals


def test_intervals_include_reset_points_and_overlap():
    lines = ["APPEND_TO_REGISTER q0 r0", "X q0", "R q1", "CX q0 q1", "HMR q1 b0", "X q2"]
    result = operation_intervals(lines, 3)
    assert result["intervals"] == {"0": [0, 2], "1": [1, 3], "2": [4, 4]}
    assert result["resets"] == {"1": [1, 3]}
    assert result["maximum_interval_overlap"] == 2
    assert result["max_id_plus_one"] == 3
