"""Check the proposed compact phase recurrence against every control input."""

import argparse
import json
from pathlib import Path

import numpy as np
from invsqrt_opportunity import ROOT, backend

from qcompile.invsqrt.compact_phase import phase_accumulation
from qcompile.invsqrt.direct import phase64
from qcompile.invsqrt.trimmed import TrimmedFormat
from qcompile.io import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    table_path = ROOT / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json"
    table = tuple(tuple(row) for row in json.loads(table_path.read_text(encoding="utf-8"))["coefficients"])
    fmt = TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True)
    for start in range(1, spec.max_x + 1, 65536):
        xs = np.arange(start, min(start + 65536, spec.max_x + 1), dtype=np.int64)
        if not np.array_equal(phase_accumulation(fmt, table, xs), phase64(fmt, table, xs)):
            raise ValueError(f"phase recurrence mismatch in chunk starting {start}")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"status": "model_only", "exact_matches": spec.max_x,
                   "table_sha256": sha256(table_path),
                   "source_sha256": sha256(ROOT / "src/qcompile/invsqrt/compact_phase.py"),
                   "limitation": "Equality of integer models does not prove a complete circuit or all measurement branches."},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
