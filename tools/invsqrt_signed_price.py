"""Price Booth-row slices at the frozen control widths before full emission."""

import json

from invsqrt_opportunity import backend, counts

from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.signed_row import signed_row


def main() -> None:
    km, _, _ = backend()
    fractional = (29, 21, 14)
    totals = [0, 0, 0]
    declared = 0
    rows = []
    for stage in (1, 0):
        for subtract in (True, False):
            for digit in range(7):
                shift = fractional[stage] - fractional[stage + 1] + 2 * digit - 20
                builder = km.CircuitBuilder()
                x = builder.alloc_qubits(22)
                builder.alloc_qubits(4)
                output = builder.alloc_qubits(40)
                c1 = builder.alloc_qubits(21)
                c2 = builder.alloc_qubits(14)
                scratch = builder.alloc_qubits(30)
                target, operand = (c1, c2) if stage == 1 else (output[:30], c1)
                # Independent zero-state stand-ins preserve declared cost for
                # edge digit bits; the full circuit must bind them to constants.
                signed_row(builder, x[0], x[1], x[2], operand, target, scratch, shift, subtract=subtract)
                circuit = builder.finish_circuit()
                resources = counts(circuit.operation_statistics())
                totals = [a + b for a, b in zip(totals, resources, strict=True)]
                declared = max(declared, circuit.num_qubits)
                rows.append({"stage": stage, "subtract": subtract, "digit": digit,
                             "shift": shift, "qubits": circuit.num_qubits, "counts": resources})
    # 1,846 is the independently measured native count for the 52 original
    # controlled rows. Other control counts and rotation classes are unchanged
    # only under the proposed replacement and must be confirmed by emission.
    predicted_counts = (3202 - 1846 + totals[0], 1 + totals[1], 36 + totals[2])
    predicted = complete_cost(max(131, declared), predicted_counts, 367941604)
    print(json.dumps({"status": "isolated_slice_projection", "rows": rows,
                      "row_counts": totals, "projected": predicted,
                      "control_cost": 548860.9216547348,
                      "limitations": "Boundary constants are stand-ins; this is not an emitted full circuit."},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
