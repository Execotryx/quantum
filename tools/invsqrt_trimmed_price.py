"""Price isolated row and shift effects of removing zero high bits."""

import json

from invsqrt_opportunity import ROOT, backend, counts

from qcompile.invsqrt.direct import DirectFormat, _binary_shift
from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.trimmed import TrimmedFormat


def main() -> None:
    km, primitives, _ = backend()
    table_path = ROOT / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json"
    record = json.loads(table_path.read_text(encoding="utf-8"))
    margin = record["after"]["minimum_margin_phase64"]
    totals = {}
    for trimmed in (False, True):
        cls = TrimmedFormat if trimmed else DirectFormat
        fmt = cls(10, 7, (28, 20, 14), True, True, True, True)
        row_count = 0
        row_peak = 0
        for stage in (1, 0):
            for inverse in (False, True):
                for bit in range(13):
                    builder = km.CircuitBuilder()
                    x = builder.alloc_qubits(22)
                    builder.alloc_qubits(4)
                    output = builder.alloc_qubits(fmt.output_fractional + (0 if trimmed else 1))
                    c1 = builder.alloc_qubits(fmt.widths[1])
                    c2 = builder.alloc_qubits(fmt.widths[2])
                    scratch = builder.alloc_qubits(max(fmt.widths))
                    target, operand = (c1, c2) if stage == 1 else (output[:fmt.widths[0]], c1)
                    shift = fmt.fractional[stage] - fmt.fractional[stage + 1] + bit - 20
                    terms = [(operand[i], i + shift) for i in range(max(0, -shift),
                             min(len(operand), len(target) - shift))]
                    if terms:
                        primitives._add_row(builder, inverse, x[bit], terms, target, scratch, subtract=True)
                    circuit = builder.finish_circuit()
                    row_count += counts(circuit.operation_statistics())[0]
                    row_peak = max(row_peak, circuit.num_qubits)
        builder = km.CircuitBuilder()
        flags = builder.alloc_qubits(4)
        output = builder.alloc_qubits(fmt.output_fractional + (0 if trimmed else 1))
        _binary_shift(builder, False, flags, output)
        _binary_shift(builder, True, flags, output)
        shift_count = counts(builder.finish_circuit().operation_statistics())[0]
        totals["trimmed" if trimmed else "control"] = {"row_toffolis": row_count,
                                                        "row_peak": row_peak,
                                                        "output_shift_toffolis": shift_count}
    difference = (totals["trimmed"]["row_toffolis"] - totals["control"]["row_toffolis"]
                  + totals["trimmed"]["output_shift_toffolis"] - totals["control"]["output_shift_toffolis"])
    predicted = complete_cost(totals["trimmed"]["row_peak"], (3046 + difference, 1, 35), margin)
    print(json.dumps({"slices": totals, "projected_cost": predicted,
                      "control_cost": 509471.48180735623,
                      "projected_gain_fraction": 1 - predicted["score"] / 509471.48180735623,
                      "limitations": "Row peak and unchanged non-row costs are estimates. "
                                     "Full-domain bit identity and native parity are not established."},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
