"""Native temporary-AND controls with explicit register and phase diagnostics."""

import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.io import sha256


def main():
    root = Path(__file__).resolve().parents[1]
    native = root / "vendor/official/kickmix/kickmix.so"
    if sha256(native) != "c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e":
        raise ValueError("native backend identity changed")
    sys.path.insert(0, str(native.parent))
    km = import_module("kickmix")

    inputs = np.array([False, False, True, True])
    second = np.array([False, True, False, True])
    product = inputs & second
    builder = km.CircuitBuilder()
    qubits = builder.alloc_qubits(4)
    builder.init_and(qubits[0], qubits[1], qubits[2])
    builder.cx(qubits[2], qubits[3])
    builder.del_and(qubits[0], qubits[1], qubits[2])
    builder.cx(qubits[0], qubits[3])
    correct = builder.finish_circuit()
    text = str(correct)
    if "HMR" not in text or "CZ" not in text:
        raise ValueError("builder omitted the required measurement/correction")
    mutations = {
        "missing_phase_correction": "\n".join(line for line in text.splitlines() if "CZ" not in line),
        "dirty_scratch": text + "\nX q2",
        "changed_input": text + "\nX q0",
    }
    observed = dict.fromkeys(mutations, 0)
    for seed in range(32):
        for name, circuit in [("correct", correct)] + [
            (name, km.Circuit(body)) for name, body in mutations.items()
        ]:
            sim = km.Simulator(batch_size=4, debug_print=False, seed=seed)
            sim.write_across_shots(km.q(0), inputs)
            sim.write_across_shots(km.q(1), second)
            sim.do(circuit)
            diagnostics = {
                "changed_input": not np.array_equal(sim.read_across_shots(km.q(0)), inputs),
                "dirty_scratch": bool(sim.read_across_shots(km.q(2)).any()),
                "missing_phase_correction": any(sim.read_shot_phase(i) % 2 for i in range(4)),
            }
            if name == "correct":
                if (
                    any(diagnostics.values())
                    or not np.array_equal(sim.read_across_shots(km.q(1)), second)
                    or not np.array_equal(sim.read_across_shots(km.q(3)), product ^ inputs)
                ):
                    raise ValueError(f"correct composed primitive failed at seed {seed}")
            elif diagnostics[name]:
                observed[name] += 1
    if not all(observed.values()):
        raise ValueError("a mutation was never detected")
    print(
        json.dumps(
            {
                "native_sha256": sha256(native),
                "circuit": text,
                "seeds": list(range(32)),
                "basis_inputs_per_seed": 4,
                "correct_composition": "passed",
                "mutation_expected_and_observed": observed,
                "scope": "native basis trajectories plus conditional branch proof in the linked dated document",
            }
        )
    )


if __name__ == "__main__":
    main()
