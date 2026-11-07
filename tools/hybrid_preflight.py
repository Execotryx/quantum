"""Check an archive through pinned metric readers and register validators, without simulation."""

import argparse
from importlib import import_module
from pathlib import Path

from qcompile.artifacts import extract_archive
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.component_confirmations import HYBRID_COVERAGE
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend
from qcompile.worker import load_metric


def preflight(archive: Path, backend_path: Path, output: Path) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    output.mkdir(parents=True, exist_ok=False)
    root = output / "extracted"
    archive_hash = sha256(archive)
    members = extract_archive(archive, root)
    if sha256(archive) != archive_hash:
        raise ValueError("archive changed during preflight extraction")
    metric = load_metric(backend)
    invsqrt = import_module("invsqrt.verify_submission_invsqrt")
    dqi = import_module("dqi.verify_submission_dqi")
    chemistry = import_module("dfthcsos.verify")
    circuits = import_module("dfthcsos.scoreinfra.circuits")
    read_circuit = metric["read_circuit"]

    def circuit_summary(name, register_cap, validate, spec):
        circuit = read_circuit(root / name, register_cap)
        validate(circuit, spec)
        if name == "dqi.kmb" and "Z_POW" in circuit.operation_statistics():
            raise ValueError("DQI does not permit Z_POW")
        return {"qubits": circuit.num_qubits, "bits": circuit.num_bits, "registers": circuit.num_registers}

    dqi_spec = dqi.ProblemSpecDQI.benchmark_instance()
    summaries = {
        "invsqrt": circuit_summary(
            "invsqrt.kmb", 1, invsqrt.validate_registers, invsqrt.ProblemSpecInvSqrt.for_n_p(10),
        ),
        "dqi": circuit_summary("dqi.kmb", dqi_spec.n + dqi_spec.m, dqi.validate_registers, dqi_spec),
    }
    npz = root / "dfthcsos/submission.npz"
    arrays = metric["read_npz"](npz, SPEC)
    r, b, c = arrays["W"].shape
    del arrays
    # Check complete required payloads without loading optional trainer arrays.
    read_factorization(npz, allow_extra=True)
    angle_count = len(members) - 3
    angles = [read_circuit(root / f"dfthcsos/angle_k_{index}.kmb", chemistry.QUBIT_CAP)
              for index in range(angle_count)]
    layout = circuits.register_layout(angles)
    circuits._reject_rotations(angles)
    if max(circuit.num_qubits for circuit in angles) > chemistry.QUBIT_CAP:
        raise ValueError("ANGLE family exceeds physical qubit cap")
    if (
        angle_count != (75 + layout.batch_size - 1) // layout.batch_size
        or len(layout.selection) != (75 + r * b).bit_length()
    ):
        raise ValueError("ANGLE layout does not cover the factorization")
    summaries["dfthcsos"] = {
        "shape": [r, b, c], "angle_count": angle_count, "brot": layout.brot,
        "batch_size": layout.batch_size, "max_angle_qubits": max(circuit.num_qubits for circuit in angles),
    }
    write_json(output / "preflight.json", {
        "archive_sha256": archive_hash, "members": members, "metric_sha256": backend["metric_sha256"],
        "checks": summaries, "expected_full_coverage": {**HYBRID_COVERAGE, "dfthcsos": (76 + r * b) * 64},
        "kind": "structural_preflight",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    preflight(args.archive, args.backend, args.output)
