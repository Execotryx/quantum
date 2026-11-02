"""Independent integer cost equations with exhaustive QROM block selection."""

import json
import math
import sys
from fractions import Fraction
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from qcompile.io import read_json
from qcompile.official import validate_backend


def qr(length, width):
    choices = [(Fraction(length, 2**k) + width * (2**k - 1), k) for k in range(length.bit_length() + 1)]
    cost, k = min(choices)
    return k, math.ceil(cost)


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    official = import_module("dfthcsos.verify")
    circuit_module = import_module("dfthcsos.scoreinfra.circuits")
    directory = root / "vendor/official/sample_submission/dfthcsos"
    with np.load(directory / "submission.npz") as arrays:
        w = arrays["W"].copy()
    r, b, c = w.shape
    n, beta, chi = 76, 12, official.KEEP_BITS

    def bits(value):
        return (value - 1).bit_length()

    rc, outer = r * c, n + r * c
    width1, width2 = bits(outer) + chi, bits(b) + chi + 1
    k1, qrom1 = qr(outer, width1)
    _, inverse1 = qr(outer, 1)
    k2, _ = qr(rc * b, width2)
    k2 = next(
        k
        for k in range(k2, -1, -1)
        if bits(rc * math.ceil(Fraction(b, 2**k))) + (2**k - 1) * width2 < beta * (n - 1)
    )
    toffoli_k2 = min(k2, b.bit_length() - 1)
    outer_t = 8 * bits(outer) + qrom1 + inverse1 + 2 * width1 + 1
    inner_t = (
        rc * math.ceil(Fraction(b + 1, 2**toffoli_k2))
        + 2**toffoli_k2 * width2
        + qr(rc, b + 1)[1]
        + b
        + 1
        + n
        + width2
        + 8 * bits(b + 1)
    )
    outer_p = width1 + chi + bits(outer) + 2
    outer_temp = bits(math.ceil(Fraction(outer, 2**k1))) + 2**k1 * width1 + max(0, bits(outer) - 2)
    inner_p = width2 + chi + bits(r) + 2 + bits(b + 1) + 2
    inner_temp = max(0, bits(b + 1) - 2) + bits(rc * math.ceil(Fraction(b + 1, 2**k2))) + (2**k2 - 1) * width2
    circuits = circuit_module.load_circuits(directory)
    layout = circuit_module.register_layout(circuits)
    angles_width = max(circuit.num_qubits for circuit in circuits)
    angles_p = layout.batch_size * beta
    angles_temp = angles_width - len(layout.selection) - angles_p
    angles_t = read_json(root / "docs/evidence/step3-chemistry-words.json")["forward_reverse_mean_toffoli"]
    calculated = {
        "outer_state_prep_toffoli": outer_t,
        "inner_state_prep_toffoli": inner_t,
        "givens_rotations_toffoli": 2 * (n - 1) * (2 * beta - 1),
        "outer_state_prep_persistent_qubits": outer_p,
        "outer_state_prep_temporary_qubits": outer_temp,
        "inner_state_prep_persistent_qubits": inner_p,
        "inner_state_prep_temporary_qubits": inner_temp,
        "persistent_qubits": outer_p + inner_p + angles_p,
        "temporary_qubits": max(outer_temp, inner_temp, angles_temp),
    }
    calculated["toffoli"] = angles_t + outer_t + inner_t + calculated["givens_rotations_toffoli"]
    calculated["qubits"] = calculated["persistent_qubits"] + calculated["temporary_qubits"]
    expected = official.resource_costs(SimpleNamespace(w=w, num_orbitals=n), circuits, beta, angles_t)
    for name, value in calculated.items():
        if value != expected[name]:
            raise ValueError(f"resource disagreement for {name}: {value} versus {expected[name]}")
    metrics = read_json(root / "docs/evidence/step3-chemistry-metrics.json")["independent"]
    score = metrics["lambda_eff"] * calculated["toffoli"] * calculated["qubits"]
    metrics["gap_in_domain"] = True
    rejection_controls = []
    for field, value, detector in [
        ("error_1", 0.021, "error_1"),
        ("error_2", 0.021, "error_2"),
        ("Lambda", 49.0, "strict floor"),
        ("E_gap", 3.914898, "strict floor"),
        ("Lambda", float("nan"), "strict floor"),
    ]:
        mutant = metrics | {field: value}
        reason = official.rejection_reason(mutant, expected)
        if (
            reason is None
            or detector not in reason
            or not math.isinf(official.score_from_metrics(mutant, expected))
        ):
            raise ValueError(f"expected {detector} rejection for {field}")
        rejection_controls.append(
            {"field": field, "value": str(value), "expected": detector, "observed": reason}
        )
    too_wide = expected | {"angles_qubits": 129}
    reason = official.rejection_reason(metrics, too_wide)
    if (
        reason is None
        or "129" not in reason
        or not math.isinf(official.score_from_metrics(metrics, too_wide))
    ):
        raise ValueError("width control failed")
    rejection_controls.append(
        {"field": "angles_qubits", "value": "129", "expected": "width", "observed": reason}
    )
    if official.rejection_reason(metrics | {"error_1": 0.020, "error_2": 0.020}, expected) is not None:
        raise ValueError("legal residual equality rejected")
    print(
        json.dumps(
            {
                "independent_components": calculated,
                "official_components": expected,
                "score": score,
                "qrom_exhaustive_selected_blocks": [k1, k2, toffoli_k2],
                "dimensions": [r, b, c, n],
                "all_compared_components_equal": True,
                "rejection_controls": rejection_controls,
                "residual_equality_positive_control": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
