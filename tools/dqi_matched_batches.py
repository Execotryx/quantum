"""Check original D4 batches on the banked decoder and a frozen candidate."""

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np

from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend


def reconstruct(api, spec, tables, capture: Path, digest: str):
    """Recreate a pinned shot batch and check its recorded observations."""
    if sha256(capture) != digest:
        raise ValueError(f"Captured batch changed: {capture}")
    batch = read_json(capture)
    rng = np.random.default_rng(batch["rng_seed"])
    syndromes, masks, expected = api.sample_shots(spec, tables, rng, api.DEFAULT_BATCH_SIZE)
    for case in batch["shots"] + batch["controls"]:
        offset = case["index"] - batch["batch_start"]
        if (syndromes[offset].tolist(), masks[offset].tolist(), bool(expected[offset])) != (
            case["syndrome"], case["mask"], case["expected_phase"]
        ):
            raise ValueError("Batch reconstruction differs from the captured shot")
    return batch, syndromes, masks, expected


def verify(circuit, spec, api, km, syndromes, masks, expected, seed: int) -> dict:
    syndrome, mask, scratch = api.validate_registers(circuit, spec)
    syndrome, mask = km.array(syndrome), km.array(mask)
    s0, m0 = api.to_bits(syndromes, spec.degree), api.to_bits(masks, spec.degree)
    sim = km.Simulator(batch_size=len(syndromes), counting_operations=True, seed=seed)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(syndrome, s0)
    sim.write_across_shots(mask, m0)
    sim.do(circuit)
    values = (sim.read_across_shots(syndrome) != s0).any(axis=0)
    mask_errors = (sim.read_across_shots(mask) != m0).any(axis=0)
    dirty = sim.read_across_shots(scratch).any(axis=0) if len(scratch) else np.zeros(len(syndromes), dtype=bool)
    phases = (sim.read_phase_flipped_across_shots() != expected) & ~(values | dirty)
    return {
        "phase_offsets": np.flatnonzero(phases).tolist(), "value_offsets": np.flatnonzero(values | dirty).tolist(),
        "dirty_offsets": np.flatnonzero(dirty).tolist(), "mask_offsets": np.flatnonzero(mask_errors).tolist(),
        "mean_toffoli_like": sim.operation_statistics().num_toffoli_like / len(syndromes),
    }


def replay(
    backend: Path, profile: Path, bank: Path, candidate: Path, captures: Path, output: Path,
    candidate_build: Path | None = None,
) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    profile_data = read_json(profile)
    build = read_json(candidate_build) if candidate_build is not None else None
    candidate_sha = build["circuit_sha256"] if build is not None else profile_data["circuit_sha256"]
    if build is not None and (
        build["banked_d4_sha256"] != profile_data["banked_sha256"] or build["backend_sha256"] != sha256(backend)
    ):
        raise ValueError("Candidate build is from another banked decoder or backend")
    if sha256(bank) != profile_data["banked_sha256"] or sha256(candidate) != candidate_sha:
        raise ValueError("Circuit hash differs from the diagnostic profile")
    backend_hash = sha256(backend)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if backend_hash != profile_data["backend_sha256"] and inventory != profile_data["backend_inventory_sha256"]:
        raise ValueError("Backend inventory differs from the diagnostic profile")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    spec = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(spec.degree))
    batches = []
    for draw, receipt in profile_data["batch_receipts"].items():
        for name, digest in receipt["batches"].items():
            capture = captures / draw / name
            batch, syndromes, masks, expected = reconstruct(api, spec, tables, capture, digest)
            batches.append((draw, batch, syndromes, masks, expected))
    rows = [{"draw": draw, "batch_start": b["batch_start"]} for draw, b, *_ in batches]
    for key, artifact in (("banked", bank), ("candidate", candidate)):
        circuit = km.Circuit.from_file(str(artifact))
        for row, (draw, batch, syndromes, masks, expected) in zip(rows, batches, strict=True):
            result = verify(circuit, spec, api, km, syndromes, masks, expected, batch["sim_seed"])
            if key == "banked":
                for flag in ("value", "phase"):
                    historical = [x["index"] - batch["batch_start"] for x in batch["shots"] if x[f"{flag}_error"]]
                    if result[f"{flag}_offsets"] != sorted(historical):
                        raise ValueError(f"Banked decoder did not match captured {flag} errors for {draw}")
            row[key] = result
        del circuit
    write_json(output, {
        "profile_sha256": sha256(profile), "banked_sha256": profile_data["banked_sha256"],
        "candidate_sha256": candidate_sha, "shots": len(rows) * api.DEFAULT_BATCH_SIZE,
        "build_sha256": sha256(candidate_build) if candidate_build is not None else None,
        "backend_sha256": backend_hash, "backend_inventory_sha256": inventory,
        "batches": rows,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("backend", "profile", "bank", "candidate", "captures", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--candidate-build", type=Path)
    args = parser.parse_args()
    replay(args.backend, args.profile, args.bank, args.candidate, args.captures, args.output, args.candidate_build)


if __name__ == "__main__":
    main()
