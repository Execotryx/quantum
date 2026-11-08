"""Price a passing two-octave table using measured native primitives."""

import argparse
import json
from pathlib import Path

from invsqrt_opportunity import backend, counts

from qcompile.invsqrt.direct import DirectFormat, build_circuit
from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.minimax import coefficient_table
from qcompile.invsqrt.two_octave_mapping import permute_address


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = json.loads(args.table.read_text(encoding="utf-8"))
    margins = result["after"]
    if margins["nonpositive_margins"] or margins["above_90_percent"]:
        raise ValueError("two-octave table fails the full-domain phase gate")
    km, primitives, _ = backend()
    fmt = DirectFormat(10, 7, tuple(result["fractional"]), True, True, True, True)
    baseline = build_circuit(km, primitives, fmt, coefficient_table(fmt))
    original = counts(baseline.operation_statistics())
    builder = km.CircuitBuilder()
    x = builder.create_quantum_register(22, "x")
    permute_address(builder, x, 7)
    permute_address(builder, x, 7, inverse=True)
    mapping = counts(builder.finish_circuit().operation_statistics())
    row_costs = []
    row_qubits = []
    for stage in (1, 0):
        builder = km.CircuitBuilder()
        x = builder.alloc_qubits(22)
        builder.alloc_qubits(4)
        output = builder.alloc_qubits(fmt.output_fractional + 1)
        c1 = builder.alloc_qubits(fmt.widths[1])
        c2 = builder.alloc_qubits(fmt.widths[2])
        scratch = builder.alloc_qubits(max(fmt.widths))
        target, operand = (c1, c2) if stage == 1 else (output[:fmt.widths[0]], c1)
        bit = 2 * fmt.n_p - fmt.segment_bits
        shift = fmt.fractional[stage] - fmt.fractional[stage + 1] + bit - 2 * fmt.n_p
        terms = [(operand[i], i + shift) for i in range(max(0, -shift),
                 min(len(operand), len(target) - shift))]
        flag = builder.alloc_qubits(1)[0]
        # After the in-place mapping, x[20] carries the extra low bit in the
        # upper octave and x[21] is its flag.
        builder.init_and(x[20], x[21], flag)
        primitives._add_row(builder, False, flag, terms, target, scratch, subtract=True)
        builder.del_and(x[20], x[21], flag)
        circuit = builder.finish_circuit()
        row_costs.append(counts(circuit.operation_statistics()))
        row_qubits.append(circuit.num_qubits)
    extra_toffoli = 2 * sum(row[0] for row in row_costs)
    # Calibrated existing 384-row lookup/repair trees cost 766+56;
    # the full 256-row trees cost 508+39 (see model-only-screens.json).
    saved = (766 + 56) - (508 + 39)
    projected_counts = (original[0] - saved + extra_toffoli + mapping[0], original[1], original[2])
    projected_width = max(baseline.num_qubits, *row_qubits)
    score = complete_cost(projected_width, projected_counts, margins["minimum_margin_phase64"])
    control = 509471.48180735623
    payload = {"fractional": result["fractional"], "full_domain_margins": margins,
               "uniform_baseline_counts": original, "uniform_baseline_qubits": baseline.num_qubits,
               "mapping_counts": mapping, "extra_row_counts": row_costs,
               "extra_row_qubits": row_qubits, "lookup_and_repair_saved": saved,
               "projected_cost": score, "control_cost": control,
               "projected_gain_fraction": 1 - score["score"] / control,
               "limitations": "Tree savings are structural estimates; the full two-octave circuit has "
                              "not been emitted or native-verified. Declared width is a peak estimate."}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
