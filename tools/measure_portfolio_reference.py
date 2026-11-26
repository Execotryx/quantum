"""Measure a frozen comparison archive through the full official verifier."""

import argparse
from pathlib import Path

from hybrid_preflight import preflight

from qcompile.artifacts import manifest
from qcompile.component_confirmations import candidate_coverage, has_full_hybrid_coverage
from qcompile.contract import load_contract
from qcompile.io import read_json, sha256, write_json
from qcompile.official import verify_candidate
from qcompile.reference.scoring import aggregate


def measure(registration: Path, archive: Path, backend_path: Path, output: Path) -> None:
    record = read_json(registration)
    backend = read_json(backend_path)
    expected = record["public_comparison"]
    if sha256(archive) != expected["archive_sha256"] or backend["metric_sha256"] != record["metric_sha256"]:
        raise ValueError("Comparison archive or verifier differs from the registration")
    contract = load_contract(Path("contracts/contract.json"))
    contract.require_ready(Path.cwd())
    preflight(archive, backend_path, output, check_serialization=True)
    members = manifest(output / "extracted", origin="retained_reference", provenance="Versioned public comparison")
    if {name: item["sha256"] for name, item in members.items()} != expected["member_sha256"]:
        raise ValueError("Comparison member hashes differ from the registration")
    report = verify_candidate(
        members, contract, "full",
        {"role": "official_local", "salt": record["development_salt"], "distribution": "public portfolio comparison"},
        {**backend, "project_root": str(Path.cwd())}, output / "verification", verification_profile="candidate-v1",
    )
    complete = has_full_hybrid_coverage(report, candidate_coverage(members))
    if report["status"] != "passed" or not report["complete"] or not complete:
        raise ValueError("Comparison did not complete full verification")
    costs = report["official_results"]["costs"]
    write_json(output / "comparison.json", {
        "kind": "full_reference_comparison",
        "registration_sha256": sha256(registration),
        "verification_sha256": sha256(output / "verification/verification.json"),
        "archive_sha256": expected["archive_sha256"],
        "costs": costs,
        "aggregate": aggregate(record["baseline_costs"], costs),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("registration", "archive", "backend_path", "output"):
        parser.add_argument(name, type=Path)
    measure(**vars(parser.parse_args()))
