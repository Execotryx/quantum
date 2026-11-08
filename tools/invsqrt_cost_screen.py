"""Apply the calibrated model to a searched, potentially trimmed table."""

import argparse
import json
from pathlib import Path

from invsqrt_opportunity import ROOT

from qcompile.invsqrt.costmodel import predict
from qcompile.invsqrt.direct import DirectFormat
from qcompile.io import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    calibration_path = ROOT / "docs/evidence/invsqrt-costmodel-20261108/calibration-final-v2.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if calibration["status"] != "calibrated" or calibration["model_sha256"] != sha256(
        ROOT / "src/qcompile/invsqrt/costmodel.py"
    ):
        raise ValueError("resource model is not calibrated for these source bytes")
    record = json.loads(args.table.read_text(encoding="utf-8"))
    margins = record["after"]
    if margins["nonpositive_margins"] or margins["above_90_percent"]:
        raise ValueError("table fails the full-domain phase gate")
    fmt = DirectFormat(10, 7, tuple(record["fractional"]), True, True, True, True)
    widths = tuple(width - 1 for width in fmt.widths)
    if len(record["coefficients"]) != 3 * (1 << fmt.segment_bits) or any(
        len(row) != len(widths) or any(word < 0 or word >= 1 << width
                                       for word, width in zip(row, widths, strict=True))
        for row in record["coefficients"]
    ):
        raise ValueError("table does not fit the proposed trimmed widths")
    control_path = ROOT / "docs/evidence/invsqrt-trimmed-v4-20261108/development-a.json"
    control = json.loads(control_path.read_text(encoding="utf-8"))["cost"]["score"]
    result = predict(fmt, margins["minimum_margin_phase64"], trimmed=True)
    gain = 1 - result["cost"]["score"] / control
    payload = {"status": "model_only", "table_sha256": sha256(args.table),
               "calibration_sha256": sha256(calibration_path), "control_receipt_sha256": sha256(control_path),
               "control_cost": control, "full_domain_margins": margins, "predicted": result,
               "gain_fraction": gain, "admitted_by_5_percent_cost_gate": gain >= .05,
               "limitations": "Unseen trimmed precision is an extrapolation. Table fit alone does not "
                              "prove intermediate zero-bit invariants, quantum phases, or native parity."}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
