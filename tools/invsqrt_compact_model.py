"""Bookkeeping bounds for a separately scoped compact-phasing tranche."""

import json

from invsqrt_opportunity import ROOT


def main() -> None:
    path = ROOT / "docs/evidence/invsqrt-lattice-20261108/native-28-20-14/result.json"
    control = json.loads(path.read_text(encoding="utf-8"))["cost"]
    output_width = 39  # 28 fractional coefficient bits + 10 scale bits + one integer bit.
    rotation_charge = (control["t_like"] + control["rotation_t"]) / 4
    equivalent = control["toffoli_like"] + rotation_charge
    result = {
        "status": "bookkeeping_only_no_prototype",
        "control_qubits": control["qubits"],
        "control_rotation_inclusive_toffoli_equivalent": equivalent,
        "target_qubits": 100, "target_toffoli_equivalent": 2000,
        "removed_output_qubits_assumed": output_width,
        "gradient_width_assumptions": [30, 36],
        "other_qubits_that_must_be_removed_after_output_replacement": [
            control["qubits"] - output_width + gradient - 100 for gradient in (30, 36)
        ],
        "control_direct_rotation_charge": rotation_charge,
        "toffolis_if_all_direct_rotation_charge_vanished": control["toffoli_like"],
        "additional_toffoli_reduction_needed_even_if_rotations_free": control["toffoli_like"] - 2000,
        "limitations": "Width is simple declared-register bookkeeping, not a lower bound on a redesigned "
                       "circuit; peak lifetimes can change. Gradient preparation, accumulation, "
                       "rounding and rotation costs are unmodeled. No predicted complete cost or gain.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
