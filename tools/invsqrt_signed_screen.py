"""Screen the proposed signed-digit arithmetic model over the full control domain."""

import argparse
import json
from functools import partial
from pathlib import Path

from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat
from qcompile.invsqrt.direct_screen import scan_phase
from qcompile.invsqrt.minimax import coefficient_table
from qcompile.invsqrt.signed_model import signed_phase64


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    fmt = DirectFormat(10, 7, (29, 21, 14), True, True, True, True)
    table = coefficient_table(fmt)
    margins = scan_phase(partial(signed_phase64, fmt, table), spec.max_x,
                         partial(official.reference_values, spec))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"status": "model_only", "margins": margins}, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
