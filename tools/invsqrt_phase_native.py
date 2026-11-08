"""Emit and native-check the independently modeled low-phase-bit variant."""

import argparse
import json
from fractions import Fraction
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from invsqrt_direct import emit, fixture_inputs, native_smoke
from invsqrt_opportunity import backend

from qcompile.invsqrt.direct import DirectFormat, build_circuit, phase64
from qcompile.invsqrt.direct_screen import complete_cost, scan_phase
from qcompile.invsqrt.minimax import coefficient_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--drop", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.drop <= 36:
        raise ValueError("drop must remove only fine-rotation bits")
    km, primitives, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    fmt = DirectFormat(10, 7, (29, 21, 14), True, True, True, True)
    table = coefficient_table(fmt)

    def phase_by_bits(builder, output):
        width = len(output)
        for j in range(args.drop, width):
            builder.z_pow(output[j], Fraction(2) ** (j - width + 1))

    def model(xs):
        shift = 64 - fmt.output_fractional + args.drop
        return (phase64(fmt, table, xs) >> np.uint64(shift)) << np.uint64(shift)

    margins = scan_phase(model, spec.max_x, partial(official.reference_values, spec))
    if margins["nonpositive_margins"] or margins["above_90_percent"]:
        raise ValueError("phase-bit model fails the full-domain gate")
    predicted = complete_cost(159, (3202, 1, 36 - args.drop), margins["minimum_margin_phase64"])
    if predicted["score"] >= 548860.9216547348:
        raise ValueError("phase-bit model does not improve the frozen control cost")
    api = SimpleNamespace(**{name: getattr(primitives, name) for name in
                             ("_normalize", "_denormalize", "_add_row")}, _phase_by_bits=phase_by_bits)
    args.output.mkdir(parents=True, exist_ok=False)
    circuit, digest = emit(km, build_circuit(km, api, fmt, table), official, args.output / "invsqrt.kmb")
    policy = {"seed": 2026110701, "random_inputs": 256, "repeat": 4, "batch": 64}
    points = fixture_inputs(spec.max_x, fmt.segment_bits, margins, policy)
    native = native_smoke(km, official, circuit, spec, model, points, policy)
    cost = complete_cost(circuit.num_qubits, native["counts"], margins["minimum_margin_phase64"])
    if cost != predicted:
        raise ValueError("emitted phase-bit cost differs from its pre-emission model")
    with (args.output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump({"drop": args.drop, "sha256": digest, "margins": margins,
                   "native": native, "cost": cost}, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
