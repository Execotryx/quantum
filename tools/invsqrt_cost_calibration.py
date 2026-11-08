"""Calibrate the direct resource model against every retained comparable attempt."""

import json
from pathlib import Path

from invsqrt_opportunity import ROOT

from qcompile.invsqrt.costmodel import predict
from qcompile.invsqrt.direct import DirectFormat
from qcompile.io import sha256


def main() -> None:
    paths = (list((ROOT / "docs/evidence/invsqrt-direct-20261107").glob("*/attempt.json"))
             + list((ROOT / "docs/evidence/advance-hybrid-20261108/invsqrt").glob("attempt-*.json"))
             + list((ROOT / "docs/evidence/next-hybrid-20261108/invsqrt").glob("*.json"))
             + list((ROOT / "docs/evidence/invsqrt-v4-screen-20261108").glob("attempt-*.json")))
    cases = []
    for path in sorted(paths):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            continue
        params = record.get("parameters", {})
        measured = record.get("cost")
        if not measured or "fractional" not in params:
            continue
        fmt = DirectFormat(10, params["segment_bits"], tuple(params["fractional"]),
                           params.get("fused", False), params.get("reuse_lookup", False),
                           params.get("binary_normalization", False), params.get("measurement_unlookup", False))
        predicted = predict(fmt, record["margins"]["minimum_margin_phase64"])
        got = predicted["cost"]
        cases.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                      "parameters": params, "actual": measured, "predicted": predicted,
                      "toffoli_relative_error": abs(got["toffoli_like"] - measured["toffoli_like"]) / measured["toffoli_like"],
                      "width_error": got["qubits"] - measured["qubits"],
                      "t_error": got["t_like"] - measured["t_like"],
                      "rotation_error": got["fine_rotations"] - measured["fine_rotations"]})
    path = ROOT / "docs/evidence/invsqrt-trimmed-v4-20261108/development-a.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    fmt = DirectFormat(10, 7, (28, 20, 14), True, True, True, True)
    predicted = predict(fmt, record["margins"]["minimum_margin_phase64"], trimmed=True)
    measured = record["cost"]
    cases.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                  "parameters": {"fractional": [28, 20, 14], "segment_bits": 7, "trimmed": True},
                  "actual": measured, "predicted": predicted,
                  "toffoli_relative_error": abs(predicted["cost"]["toffoli_like"] - measured["toffoli_like"]) / measured["toffoli_like"],
                  "width_error": predicted["cost"]["qubits"] - measured["qubits"],
                  "t_error": predicted["cost"]["t_like"] - measured["t_like"],
                  "rotation_error": predicted["cost"]["fine_rotations"] - measured["fine_rotations"]})
    report = {"status": "calibrated" if cases and all(c["width_error"] == 0 and c["t_error"] == 0
                                                      and c["rotation_error"] == 0 and c["toffoli_relative_error"] <= .02
                                                      for c in cases) else "uncalibrated",
              "cases": cases,
              "model_sha256": sha256(ROOT / "src/qcompile/invsqrt/costmodel.py"),
              "calibration_tool_sha256": sha256(Path(__file__).resolve()),
              "backend_sha256": sha256(ROOT / "vendor/backend.json"),
              "dependency_lock_sha256": sha256(ROOT / "uv.lock"),
              "note": "Only scored direct-circuit receipts are comparable; reference Newton circuits and failed or missing-cost lanes are excluded. The model does not establish accuracy, quantum phase correctness or zero-bit invariants."}
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
