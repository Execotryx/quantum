"""Price isolated C2a row fixtures before admitting a complete circuit."""

import json

from invsqrt_opportunity import backend, counts

from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.gated_row import add_row


def main() -> None:
    km, primitives, _ = backend()
    widths = (30, 21, 14)
    fractional = (29, 21, 14)
    totals = {"reference": 0, "gated": 0}
    rows = 0
    for stage in (1, 0):
        for inverse in (False, True):
            for bit in range(13):
                shift = fractional[stage] - fractional[stage + 1] + bit - 20
                indices = [(i, i + shift) for i in range(max(0, -shift),
                           min(widths[stage + 1], widths[stage] - shift))]
                if not indices:
                    continue
                rows += 1
                for label, operation in (("reference", primitives._add_row), ("gated", add_row)):
                    builder = km.CircuitBuilder()
                    control = builder.alloc_qubits(1)[0]
                    operand = builder.alloc_qubits(widths[stage + 1])
                    target = builder.alloc_qubits(widths[stage])
                    scratch = builder.alloc_qubits(max(widths))
                    terms = [(operand[i], column) for i, column in indices]
                    operation(builder, inverse, control, terms, target, scratch, subtract=True)
                    totals[label] += counts(builder.finish_circuit().operation_statistics())[0]
    extra = totals["gated"] - totals["reference"]
    optimistic = complete_cost(131, (3202 + extra, 1, 36), 181825093)
    print(json.dumps({"rows": rows, "isolated_row_toffolis": totals, "additional_toffolis": extra,
                      "optimistic_complete_cost_assuming_131_qubits": optimistic,
                      "control_cost": 548860.9216547348}, indent=2))


if __name__ == "__main__":
    main()
