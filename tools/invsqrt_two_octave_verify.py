"""Revalidate retained two-octave tables and their full-domain model receipts."""

import argparse
import json
from functools import partial
from pathlib import Path

from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.invsqrt.two_octave import phase64, two_octave_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tables", type=Path, nargs="+")
    args = parser.parse_args()
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    for path in args.tables:
        record = json.loads(path.read_text(encoding="utf-8"))
        fmt = DirectFormat(10, 7, tuple(record["fractional"]), True, True, True, True)
        original = two_octave_table(fmt)
        selected = tuple(tuple(row) for row in record["coefficients"])
        offsets = tuple(tuple(row) for row in record["offsets"])
        if len(selected) != len(original) or len(offsets) != len(original):
            raise ValueError(f"incomplete table in {path}")
        for before, after, delta in zip(original, selected, offsets, strict=True):
            if tuple(a - b for a, b in zip(after, before, strict=True)) != delta or any(abs(x) > 2 for x in delta):
                raise ValueError(f"invalid lattice offset in {path}")
        observed = scan_phase(partial(phase64, fmt, selected), spec.max_x,
                              partial(official.reference_values, spec))
        if observed != record["after"]:
            raise ValueError(f"full-domain results differ for {path}")
        print(f"validated {path}: {observed['failed_inputs']} failures, "
              f"worst tolerance {observed['worst_tolerance_fraction']:.9f}", flush=True)


if __name__ == "__main__":
    main()
