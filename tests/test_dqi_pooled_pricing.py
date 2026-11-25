import pytest

from qcompile.dqi.pooled_pricing import pooled_failures


@pytest.mark.parametrize(
    ("failures", "expected"),
    [
        ([0, 0], 2),
        ([0] * 8, 1),
        ([2] + [0] * 7, 1),
        ([2] * 8, 4),
    ],
)
def test_pooled_failure_examples(failures: list[int], expected: int) -> None:
    assert pooled_failures(failures) == expected
