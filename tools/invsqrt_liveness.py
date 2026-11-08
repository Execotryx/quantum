"""Reproduce the frozen v3 control and report public allocator/serialized liveness."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from invsqrt_opportunity import backend, counts

from qcompile.invsqrt.direct import DirectFormat, build_circuit
from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.minimax import coefficient_table
from qcompile.liveness import LivenessBuilder, operation_intervals

CONTROL = "ce8a58b65ee2d89457de655565a22b68ffc2d7dc68befc764a99410b3285f5b4"
MARGIN = 181825093


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    km, primitives, _ = backend()
    fmt = DirectFormat(10, 7, (29, 21, 14), True, True, True, True)
    table = coefficient_table(fmt)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proxy = LivenessBuilder(km.CircuitBuilder())
        circuit = build_circuit(km, primitives, fmt, table, builder=proxy)
        plain = build_circuit(km, primitives, fmt, table)
        circuit.to_file(str(root / "traced.kmb"), format="kmb")
        plain.to_file(str(root / "plain.kmb"), format="kmb")
        digest = hashlib.sha256((root / "traced.kmb").read_bytes()).hexdigest()
        if digest != CONTROL or (root / "traced.kmb").read_bytes() != (root / "plain.kmb").read_bytes():
            raise ValueError("traced circuit differs from frozen control")
        circuit.to_file(str(root / "trace.kmx"), format="kmx")
        with (root / "trace.kmx").open() as stream:
            intervals = operation_intervals(stream, circuit.num_qubits)
        ladder = []
        for cap in (159, 158, 155, 150, 145, 140, 135, 132, 131):
            builder = km.CircuitBuilder()
            builder.set_max_qubits(cap)
            capped = build_circuit(km, primitives, fmt, table, builder=builder)
            resources = counts(capped.operation_statistics())
            ladder.append({"cap": cap, "projected_cost": complete_cost(capped.num_qubits, resources, MARGIN)})
        counting = {}
        for label, last in (("dense", 2), ("sparse", 100)):
            builder = km.CircuitBuilder()
            for qubit in (0, 1, last):
                builder.x(km.q(qubit))
            counting[label] = builder.finish_circuit().num_qubits
        result = {"control_sha256": digest, "calls_sampled": proxy.calls,
                  "public_allocation_peak": proxy.peak_event, "op_stream": intervals,
                  "counting_fixtures": counting, "native_width_cap_ladder": ladder,
                  "limitation": "Native methods can allocate and free workspace within a single call; "
                                "capped scores assume the control margin and have not passed native parity."}
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")


if __name__ == "__main__":
    main()
