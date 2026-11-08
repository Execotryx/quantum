"""Trace the exact frozen v4 control before the trimmed-width candidate."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from invsqrt_opportunity import ROOT, backend

from qcompile.invsqrt.direct import DirectFormat, build_circuit
from qcompile.io import sha256
from qcompile.liveness import LivenessBuilder, operation_intervals

CONTROL = "c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    table_path = ROOT / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json"
    record = json.loads(table_path.read_text(encoding="utf-8"))
    table = tuple(tuple(row) for row in record["coefficients"])
    fmt = DirectFormat(10, 7, (28, 20, 14), True, True, True, True)
    km, primitives, _ = backend()
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        proxy = LivenessBuilder(km.CircuitBuilder())
        traced = build_circuit(km, primitives, fmt, table, builder=proxy)
        plain = build_circuit(km, primitives, fmt, table)
        traced.to_file(str(root / "traced.kmb"), format="kmb")
        plain.to_file(str(root / "plain.kmb"), format="kmb")
        data = (root / "traced.kmb").read_bytes()
        if hashlib.sha256(data).hexdigest() != CONTROL or data != (root / "plain.kmb").read_bytes():
            raise ValueError("traced control differs from frozen v4 bytes")
        traced.to_file(str(root / "trace.kmx"), format="kmx")
        with (root / "trace.kmx").open() as stream:
            intervals = operation_intervals(stream, traced.num_qubits)
    payload = {"control_sha256": CONTROL, "table_sha256": sha256(table_path),
               "calls_sampled": proxy.calls, "public_allocation_peak": proxy.peak_event,
               "op_stream": intervals,
               "limitation": "Native calls may allocate and release workspace internally; "
                             "first-to-last-use interval overlap is a conservative upper bound."}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
