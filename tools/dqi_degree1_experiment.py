"""Matched reduced-shape reference and radius-one decoder development run."""

import argparse
import hashlib
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
from dqi_degree1 import build

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def run(backend_path: Path, output: Path, *, seed: int) -> None:
    backend = read_json(backend_path)
    validate_backend(backend)
    official = Path(backend["verifiers_root"]) / "dqi"
    sys.path[:0] = [backend["kickmix_root"], str(official)]
    km = import_module("kickmix")
    reference = import_module("dqi_reference_circuit")
    verifier = import_module("verify_submission_dqi")
    shots = 2560
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "scope": "reduced-shape development only", "m": 63, "n": 2, "degree": 12,
        "shots": shots, "seed": seed, "batch_size": 256, "workers": 1,
        "backend": backend, "verifier_sha256": sha256(official / "verify_submission_dqi.py"),
        "reference_source_sha256": sha256(official / "dqi_reference_circuit.py"),
        "candidate_source_sha256": sha256(Path(__file__).resolve().parents[1] / "src/qcompile/dqi/degree1.py"),
    })
    build(backend_path, output / "candidate", m=63)
    candidate_path = output / "candidate/degree1.kmb"
    reference_path = output / "reference.kmb"
    ref = reference.build_reference_circuit(63, 2, 12)
    ref.to_file(str(reference_path), format="kmb")
    del ref
    write_json(output / "freeze.json", {
        "candidate_sha256": sha256(candidate_path), "reference_sha256": sha256(reference_path),
        "registration_sha256": sha256(output / "registration.json"),
    })
    spec = verifier.ProblemSpecDQI.benchmark_instance(m=63, n=2, degree=12, num_shots=shots)
    weights = verifier.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    tables = verifier.FieldTables(km.GF2Field(spec.degree))
    rng = np.random.default_rng(seed)
    cases = (np.empty((shots, 2), dtype=np.uint16), np.empty((shots, 63), dtype=np.uint16),
             np.empty(shots, dtype=bool))
    for start in range(0, shots, 256):
        batch = verifier.sample_shots(spec, tables, rng, 256, weights)
        for target, sample in zip(cases, batch, strict=True):
            target[start:start + 256] = sample
    digest = hashlib.sha256()
    for array in cases:
        digest.update(memoryview(array).cast("B"))
    write_json(output / "cases.json", {"sha256": digest.hexdigest(), "shots": shots})
    for name, path in (("reference", reference_path), ("candidate", candidate_path)):
        circuit = km.Circuit.from_file(str(path))
        result = verifier.verify(circuit, spec, shots=cases, seed=seed, batch_size=256, max_workers=1)
        if result["circuit_sha256"] != sha256(path):
            raise ValueError("verifier circuit hash differs from frozen artifact")
        write_json(output / f"{name}.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    run(args.backend, args.output, seed=args.seed)
