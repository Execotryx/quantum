"""Compare three frozen D4 circuits on the full-grid repair's error batches."""

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
from dqi_extraction_oracle import paired_reference
from dqi_matched_batches import verify

from qcompile.dqi.decoder import decode
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend


def compare(backend: Path, controls: Path, captures: Path, artifacts: dict[str, Path], output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    pins = read_json(controls)
    request = read_json(captures / "request.json")
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    circuit_hashes = {role: sha256(path) for role, path in artifacts.items()}
    registration = "docs/evidence/d4-extraction-repair-20261115/full-cloud-registration.json"
    if (
        circuit_hashes != pins["circuits"] or inventory != pins["backend_inventory_sha256"]
        or request["role"] != "candidate" or request["circuit_sha256"] != circuit_hashes["full_grid"]
        or request["registration_sha256"] != pins["evidence_sha256"][registration]
        or request["draw_indices"] != pins["replay_draws"]
    ):
        raise ValueError("Residual replay does not match the frozen controls")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    spec = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(spec.degree))
    batches = []
    field = GF4096()
    for index in request["draw_indices"]:
        draw = captures / f"s{index}"
        receipt = read_json(draw / "result.json")
        old = f"docs/evidence/d4-extraction-repair-20261115/full-cloud/campaign/candidate/s{index}.json"
        if not receipt["matches_historical_result"] or receipt["historical_receipt_sha256"] != pins["evidence_sha256"][old]:
            raise ValueError(f"Unmatched residual replay receipt: s{index}")
        for name, digest in receipt["failure_batches"].items():
            path = draw / name
            if sha256(path) != digest:
                raise ValueError(f"Residual replay batch changed: {path}")
            batch = read_json(path)
            rng = np.random.default_rng(batch["rng_seed"])
            samples, masks, phases = api.sample_shots(spec, tables, rng, api.DEFAULT_BATCH_SIZE)
            diagnostics = []
            for case in batch["shots"] + batch["controls"]:
                offset = case["index"] - batch["batch_start"]
                if (samples[offset].tolist(), masks[offset].tolist(), bool(phases[offset])) != (
                    case["syndrome"], case["mask"], case["expected_phase"],
                ):
                    raise ValueError(f"Residual shot reconstruction differs: {case['index']}")
                algebra = paired_reference(case["syndrome"], field)
                diagnostics.append({
                    "index": case["index"], "value_error": case["value_error"],
                    "dirty_qubits": case["dirty_qubits"], "changed_syndrome_bits": case["changed_syndrome_bits"],
                    "weight": len(decode(case["syndrome"], field)), "scalar_chart": algebra,
                })
            row = {
                "draw": f"s{index}", "batch_start": batch["batch_start"], "capture_sha256": digest,
                "diagnostics": diagnostics, "controls": {},
            }
            batches.append((row, batch, samples, masks, phases))

    for role, artifact in artifacts.items():
        circuit = km.Circuit.from_file(str(artifact))
        for row, batch, samples, masks, phases in batches:
            result = verify(circuit, spec, api, km, samples, masks, phases, batch["sim_seed"])
            if role == "full_grid":
                for flag in ("value", "phase"):
                    expected = sorted(case["index"] - batch["batch_start"] for case in batch["shots"] if case[f"{flag}_error"])
                    if result[f"{flag}_offsets"] != expected:
                        raise ValueError(f"Full-grid matched replay changed {flag} offsets")
            row["controls"][role] = result
        del circuit
    write_json(output, {
        "controls_sha256": sha256(controls), "replay_request_sha256": sha256(captures / "request.json"),
        "backend_inventory_sha256": inventory, "circuits": circuit_hashes,
        "batches": [row for row, *_ in batches],
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("backend", "controls", "captures", "banked", "homogeneous", "full_grid", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    artifacts = {"banked": args.banked, "homogeneous": args.homogeneous, "full_grid": args.full_grid}
    compare(args.backend, args.controls, args.captures, artifacts, args.output)


if __name__ == "__main__":
    main()
