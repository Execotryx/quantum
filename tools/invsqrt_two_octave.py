"""Full-domain two-octave accuracy screen and coefficient lattice search."""

import argparse
import json
from functools import partial
from pathlib import Path

from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.invsqrt.two_octave import phase64, search_table, two_octave_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("fractional", type=int, nargs=3)
    args = parser.parse_args()
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    fmt = DirectFormat(10, 7, tuple(args.fractional), True, True, True, True)
    table = two_octave_table(fmt)
    target = partial(official.reference_values, spec)
    before = scan_phase(partial(phase64, fmt, table), spec.max_x, target)
    chosen, offsets = search_table(fmt, table, spec.max_x, target)
    after = scan_phase(partial(phase64, fmt, chosen), spec.max_x, target)
    if after["worst_tolerance_fraction"] > before["worst_tolerance_fraction"]:
        raise ValueError("lattice search increased the worst tolerance use")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"geometry": "128 per unit below 2, 64 per unit above 2",
                   "fractional": args.fractional, "before": before, "after": after,
                   "coefficients": chosen, "offsets": offsets}, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
