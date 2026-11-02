"""Known defects through the actual inverse-square-root verify entry point."""

import json
import sys
from dataclasses import replace
from importlib import import_module
from pathlib import Path

from qcompile.io import read_json
from qcompile.official import validate_backend


def main():
    root = Path(__file__).resolve().parents[1]
    backend = read_json(root / "vendor/backend.json")
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    km = import_module("kickmix")
    official = import_module("invsqrt.verify_submission_invsqrt")
    spec = replace(official.ProblemSpecInvSqrt.for_n_p(2), max_x=1, shots_per_x=64)
    records = []
    for name, mutation, expected in [
        ("valid_x1", None, None),
        ("phase", "z", "phase error"),
        ("input", "x", "x was not restored"),
        ("scratch", "scratch", "did not return to"),
    ]:
        builder = km.CircuitBuilder()
        x = builder.create_quantum_register(spec.width, name="x")
        scratch = builder.alloc_qubits(1)[0]
        builder.init_and(False, False, scratch)
        if mutation == "z":
            builder.z(x[0])
        elif mutation == "x":
            builder.x(x[0])
        elif mutation == "scratch":
            builder.x(scratch)
        circuit = builder.finish_circuit()
        try:
            result = official.verify(circuit, spec, seed=3103, batch_size=64, max_workers=1)
        except (AssertionError, ValueError) as error:
            if expected is None or expected not in str(error):
                raise
            records.append({"fixture": name, "expected": expected, "observed": str(error)})
        else:
            if expected is not None or result["verified_shots"] != 64:
                raise ValueError("mutation accepted or positive control incomplete")
            records.append({"fixture": name, "observed": result["status"], "verified_shots": 64})
    print(
        json.dumps(
            {
                "scope": "x=1 bounded diagnostic problem with the actual verifier",
                "seed": 3103,
                "records": records,
            }
        )
    )


if __name__ == "__main__":
    main()
