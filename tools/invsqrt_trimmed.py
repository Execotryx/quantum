"""Prove, emit and native-check the opt-in trimmed v4 control."""

import argparse
import json
from functools import partial
from pathlib import Path

import numpy as np
from invsqrt_direct import emit, fixture_inputs, native_smoke
from invsqrt_opportunity import ROOT, backend

from qcompile.invsqrt.direct import phase64
from qcompile.invsqrt.direct_screen import complete_cost, scan_phase
from qcompile.invsqrt.trimmed import TrimmedFormat, build_circuit, prove_chunk
from qcompile.io import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    table_path = ROOT / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json"
    price_path = ROOT / "docs/evidence/invsqrt-trimmed-v4-20261108/price.json"
    record = json.loads(table_path.read_text(encoding="utf-8"))
    price = json.loads(price_path.read_text(encoding="utf-8"))
    if price["projected_cost"]["score"] > 0.95 * price["control_cost"]:
        raise ValueError("trimmed slice model fails the 5% pre-emission gate")
    table = tuple(tuple(row) for row in record["coefficients"])
    fmt = TrimmedFormat(10, 7, (28, 20, 14), True, True, True, True)
    km, primitives, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    for start in range(1, spec.max_x + 1, 65536):
        xs = np.arange(start, min(start + 65536, spec.max_x + 1), dtype=np.int64)
        prove_chunk(fmt, table, xs)
    model = partial(phase64, fmt, table)
    margins = scan_phase(model, spec.max_x, partial(official.reference_values, spec))
    if margins != record["after"]:
        raise ValueError("trimmed full-domain model differs from frozen table receipt")
    args.output.mkdir(parents=True, exist_ok=False)
    circuit, digest = emit(km, build_circuit(km, primitives, fmt, table), official, args.output / "invsqrt.kmb")
    stats = circuit.operation_statistics()
    resource_counts = (int(stats.num_toffoli_like), int(stats.num_t_like),
                       int(stats.num_z_pow(min_clifford_hierarchy_level=4)))
    score = complete_cost(circuit.num_qubits, resource_counts, margins["minimum_margin_phase64"])
    if score != price["projected_cost"]:
        raise ValueError("emitted cost differs from pre-emission slice model")
    policy = {"seed": 2026110701, "random_inputs": 256, "repeat": 4, "batch": 64}
    points = fixture_inputs(spec.max_x, fmt.segment_bits, margins, policy)
    native = native_smoke(km, official, circuit, spec, model, points, policy)
    with (args.output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump({"sha256": digest, "table_sha256": sha256(table_path),
                   "price_sha256": sha256(price_path), "margins": margins,
                   "intermediate_bounds_checked": spec.max_x, "native": native, "cost": score,
                   "control_cost": 509471.48180735623,
                   "gain_fraction": 1 - score["score"] / 509471.48180735623},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
