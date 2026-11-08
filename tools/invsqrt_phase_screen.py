"""Screen dropped low phase bits against the frozen v3 table and full domain."""

import json
from functools import partial

import numpy as np
from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat, phase64
from qcompile.invsqrt.direct_screen import complete_cost, scan_phase
from qcompile.invsqrt.minimax import coefficient_table


def main() -> None:
    _, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    fmt = DirectFormat(10, 7, (29, 21, 14), True, True, True, True)
    table = coefficient_table(fmt)
    results = []
    for dropped in range(9):
        def evaluate(xs):
            phase = phase64(fmt, table, xs)
            shift = 64 - fmt.output_fractional + dropped
            return (phase >> np.uint64(shift)) << np.uint64(shift)
        margins = scan_phase(evaluate, spec.max_x, partial(official.reference_values, spec))
        passing = not margins["nonpositive_margins"] and not margins["above_90_percent"]
        cost = complete_cost(159, (3202, 1, 36 - dropped), margins["minimum_margin_phase64"]) if passing else None
        results.append({"dropped": dropped, "margins": margins, "cost": cost})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
