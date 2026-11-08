"""Price the exact direct-phase compact proposal and inspect gradient feasibility."""

import argparse
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
from invsqrt_opportunity import ROOT, backend, counts

from qcompile.invsqrt.compact_phase import phase_product
from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.io import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    km, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    _, allowed = official.reference_values(spec, np.array([spec.max_x], dtype=np.int64))
    optimistic_margin = int(allowed[0])
    control_path = ROOT / "docs/evidence/invsqrt-trimmed-v4-20261108/development-a.json"
    control = json.loads(control_path.read_text(encoding="utf-8"))
    contract_path = ROOT / "contracts/contract.json"
    instructions = json.loads(contract_path.read_text(encoding="utf-8"))["fields"]["preflight.allowed_instructions"]["value"]
    basis_preserving = {"X", "CX", "CCX", "Z", "CZ", "CCZ", "Z_POW", "NEG", "SWAP", "CSWAP",
                        "R", "HMR", "BIT_INVERT", "BIT_STORE0", "BIT_STORE1", "PUSH_CONDITION",
                        "POP_CONDITION", "INFO_TAG", "DEBUG_PRINT"}
    if not set(instructions) <= basis_preserving:
        raise ValueError("allowed gate set changed; revisit phase-gradient feasibility")
    selectors = []
    for scale in range(11):
        builder = km.CircuitBuilder()
        count = builder.alloc_qubits(4)
        selected = builder.alloc_qubits(1)[0]
        builder.flip_if_equal(count, scale, target=selected)
        builder.flip_if_equal(count, scale, target=selected)
        circuit = builder.finish_circuit()
        selectors.append({"scale": scale, "counts": counts(circuit.operation_statistics()),
                          "declared_qubits": circuit.num_qubits})
    slices = []
    for product in (False, True):
        builder = km.CircuitBuilder()
        controls = builder.alloc_qubits(3)
        scratch = builder.alloc_qubits(2)
        phase_product(builder, controls[0], controls[1], controls[2] if product else None,
                      scratch, Fraction(1, 16))
        circuit = builder.finish_circuit()
        slices.append({"product": product, "counts": counts(circuit.operation_statistics()),
                       "declared_qubits": circuit.num_qubits})
    fractional = (28, 20, 14)
    coefficient_width, inner_width, low_width, output_fractional = 28, 19, 13, 38
    coefficient = [j + scale for scale in range(11) for j in range(coefficient_width)
                   if j + scale < output_fractional]
    products = [j + shift + scale for scale in range(11) for bit in range(low_width)
                for shift in (fractional[0] - fractional[1] + bit - 20,)
                for j in range(inner_width) if 0 <= j + shift < coefficient_width
                and j + shift + scale < output_fractional]
    fine = sum(power < output_fractional - 3 for power in coefficient + products)
    t_like = sum(power == output_fractional - 3 for power in coefficient + products)
    and_gates = len(coefficient) + 2 * len(products)
    # Deliberately optimistic: only 22 required input qubits, no selectors,
    # lookup, inner Horner, cleanup, or T charge, and the largest possible
    # full-domain margin (the tolerance at max_x).
    lower = complete_cost(spec.width, (and_gates, 0, fine), optimistic_margin)
    payload = {
        "status": "model_only_no_candidate", "control_sha256": control["sha256"],
        "control_cost": control["cost"]["score"], "contract_sha256": sha256(contract_path),
        "phase_source_sha256": sha256(ROOT / "src/qcompile/invsqrt/compact_phase.py"),
        "price_source_sha256": sha256(Path(__file__).resolve()),
        "phase_gradient": {"admissible_with_current_scratch_contract": False,
            "reason": "The pinned allowed gate set preserves computational-basis states branchwise; "
                      "no Hadamard or other superposition preparation exists, and all scratch starts at zero."},
        "direct_phase": {"precision_fractional_bits": output_fractional,
            "coefficient_bits": coefficient_width, "inner_bits": inner_width, "low_bits": low_width,
            "scale_values": 11, "coefficient_terms": len(coefficient), "product_terms": len(products),
            "fine_rotations": fine, "t_rotations": t_like, "phase_product_toffolis": and_gates,
            "selector_native_counts": selectors, "phase_slice_native_counts": slices,
            "optimistic_margin_phase64": optimistic_margin,
            "optimistic_cost_lower_bound": lower,
            "admitted_by_20_percent_gate": lower["score"] <= .8 * control["cost"]["score"],
            "limitations": "Bound applies only to the explicit per-term phase construction; "
                           "it excludes all selection, lookup, arithmetic and cleanup costs, "
                           "and assumes the largest possible tolerance margin."}}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
