"""Run a full-domain independent coefficient lattice search for one format."""

import argparse
import json
from functools import partial
from pathlib import Path

from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat, phase64
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.invsqrt.lattice import search_table
from qcompile.invsqrt.minimax import coefficient_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("fractional", type=int, nargs=3)
    args = parser.parse_args()
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    fmt = DirectFormat(10, 7, tuple(args.fractional), True, True, True, True)
    table = coefficient_table(fmt)
    target = partial(official.reference_values, spec)
    chosen, offsets = search_table(fmt, table, spec.max_x, target)
    before = scan_phase(partial(phase64, fmt, table), spec.max_x, target)
    after = scan_phase(partial(phase64, fmt, chosen), spec.max_x, target)
    if after["worst_tolerance_fraction"] > before["worst_tolerance_fraction"]:
        raise ValueError("search increased worst tolerance use")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"fractional": args.fractional, "before": before, "after": after,
                   "coefficients": chosen, "offsets": offsets}, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
