"""Resource model checks against independent pinned circuit receipts."""

import json
from pathlib import Path

import pytest

from qcompile.invsqrt.costmodel import predict
from qcompile.invsqrt.direct import DirectFormat
from qcompile.invsqrt.trimmed import TrimmedFormat


@pytest.mark.parametrize("receipt,trimmed", [
    ("docs/evidence/invsqrt-direct-20261107/direct-control/attempt.json", False),
    ("docs/evidence/invsqrt-direct-20261107/quartic/attempt.json", False),
    ("docs/evidence/invsqrt-direct-20261107/combined/attempt.json", False),
    ("docs/evidence/next-hybrid-20261108/invsqrt/minimax-quadratic.json", False),
    ("docs/evidence/advance-hybrid-20261108/invsqrt/attempt-combined-v3.json", False),
    ("docs/evidence/invsqrt-v4-screen-20261108/attempt-combined-lattice.json", False),
    ("docs/evidence/invsqrt-trimmed-v4-20261108/development-a.json", True),
])
def test_resource_model_matches_retained_native_counts(project_root: Path, receipt: str, trimmed: bool):
    record = json.loads((project_root / receipt).read_text(encoding="utf-8"))
    params = record.get("parameters", {"fractional": [28, 20, 14], "segment_bits": 7,
                                          "fused": True, "reuse_lookup": True,
                                          "binary_normalization": True, "measurement_unlookup": True})
    fmt = DirectFormat(10, params["segment_bits"], tuple(params["fractional"]),
                       params.get("fused", False), params.get("reuse_lookup", False),
                       params.get("binary_normalization", False), params.get("measurement_unlookup", False))
    estimate = predict(fmt, record["margins"]["minimum_margin_phase64"], trimmed=trimmed)["cost"]
    actual = record["cost"]
    assert (estimate["qubits"], estimate["toffoli_like"], estimate["t_like"], estimate["fine_rotations"]) == (
        actual["qubits"], actual["toffoli_like"], actual["t_like"], actual["fine_rotations"])
    assert estimate["score"] == pytest.approx(actual["score"], rel=1e-12)


def test_out_of_scope_and_unproven_layout_rejected():
    with pytest.raises(ValueError, match="calibrated only"):
        predict(DirectFormat(3, 2, (13, 9, 5)), 1)
    with pytest.raises(ValueError, match="trimmed model requires"):
        predict(DirectFormat(10, 7, (28, 20, 14)), 1, trimmed=True)
    with pytest.raises(ValueError, match="trimmed model requires"):
        predict(DirectFormat(10, 7, (28, 20, 14), True, False, True, True), 1, trimmed=True)
    with pytest.raises(ValueError, match="unmodified DirectFormat"):
        predict(TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True), 1, trimmed=True)
