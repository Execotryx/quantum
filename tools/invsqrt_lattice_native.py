"""Check a searched table against the official native simulator fixtures."""

import argparse
import json
from functools import partial
from pathlib import Path

from invsqrt_direct import emit, fixture_inputs, native_smoke
from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat, build_circuit, phase64
from qcompile.invsqrt.direct_screen import complete_cost, scan_phase
from qcompile.invsqrt.minimax import coefficient_table
from qcompile.io import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("search", type=Path)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args()
    result = json.loads(args.search.read_text(encoding="utf-8"))
    margin = result["after"]
    if margin["nonpositive_margins"] or margin["above_90_percent"]:
        raise ValueError("search result does not pass the full-domain phase gate")
    fmt = DirectFormat(10, 7, tuple(result["fractional"]), True, True, True, True)
    table = tuple(tuple(row) for row in result["coefficients"])
    km, primitives, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    base = coefficient_table(fmt)
    if len(table) != len(base) or any(
        len(row) != len(original) or any(abs(a - b) > 2 for a, b in zip(row, original, strict=True))
        for row, original in zip(table, base, strict=True)
    ):
        raise ValueError("table is outside the registered coefficient lattice")
    model = partial(phase64, fmt, table)
    if scan_phase(model, spec.max_x, partial(official.reference_values, spec)) != margin:
        raise ValueError("full-domain result does not match searched table")
    args.output.mkdir(parents=True, exist_ok=False)
    circuit, digest = emit(km, build_circuit(km, primitives, fmt, table), official, args.output / "invsqrt.kmb")
    policy = {"seed": 2026110701, "random_inputs": 256, "repeat": 4, "batch": 64}
    points = fixture_inputs(spec.max_x, fmt.segment_bits, margin, policy)
    native = native_smoke(km, official, circuit, spec, model, points, policy)
    score = complete_cost(circuit.num_qubits, native["counts"], margin["minimum_margin_phase64"])
    with (args.output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump({"sha256": digest, "search_sha256": sha256(args.search),
                   "native": native, "cost": score}, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
