"""Prepare and measure the paired trimmed inverse-square-root archive."""
import argparse
import shutil
import sys
from math import isclose
from pathlib import Path

from invsqrt_direct import backend, emit, require, run_job

from qcompile.artifacts import deterministic_zip, extract_archive, manifest
from qcompile.component_confirmations import candidate_coverage, dqi_counts, has_full_hybrid_coverage
from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.invsqrt.trimmed import TrimmedFormat, build_circuit
from qcompile.io import read_json, sha256, write_json
from qcompile.official import review_backend_pair, verify_candidate
from qcompile.reference.scoring import aggregate

PAYLOAD = Path(__file__).resolve().parent
WORKSPACE = PAYLOAD.parent
INV = "invsqrt.kmb"


def prepare(source: Path, parent_archive: Path) -> None:
    campaign = WORKSPACE.parent
    parent_dir = source / "docs/evidence/invsqrt-roadmap-archive-20261108"
    screen = read_json(campaign / "screen-registration.json")
    decision = read_json(campaign / "screen-decision.json")
    require(decision["status"] == "go"
            and decision["registration_sha256"] == sha256(campaign / "screen-registration.json"),
            "screen decision is not bound to registration")
    environment = capture(source)
    require(not environment["dirty"] and all(
        sha256(source / name) == digest for name, digest in screen["inputs"].items()
        if name != "vendor/backend.json"
    ), "archive source differs from frozen component recipe")
    parent = read_json(parent_dir / "registration.json")
    parent_report = read_json(parent_dir / "verification.json")
    costs = parent_report["official_results"]["costs"]
    require(parent["artifact_hashes"] == parent_report["artifact_hashes"]
            and parent["seed_policy"] == parent_report["seed_policy"]
            and parent["archive_sha256"] == sha256(parent_archive)
            and parent_report["complete"] and parent_report["status"] == "passed"
            and costs["invsqrt"] == screen["control_cost"], "paired control does not match v4")
    digest = decision["winner_sha256"]
    salts = {parent["seed_policy"]["salt"]}
    receipts = {}
    for role in ("full", "confirmation"):
        stage = campaign / role
        receipt = read_json(stage / "result.json")
        registration = read_json(stage / "registration.json")
        raw = read_json(stage / "raw-verifier.json")
        require(registration["role"] == role and registration["artifact_sha256"] == digest
                and registration["salt"] not in salts and raw["circuit_sha256"] == digest
                and registration["decision_sha256"] == sha256(campaign / "screen-decision.json")
                and receipt["registration_sha256"] == sha256(stage / "registration.json")
                and receipt["raw_sha256"] == sha256(stage / "raw-verifier.json")
                and receipt["result"] == raw and raw["status"] == "PASS"
                and raw["verified_shots"] == screen["expected_shots"] and raw["score"] <= decision["limit"]
                and raw["worst_error_over_tolerance"] <= screen["worst_tolerance_limit"],
                f"invalid {role} component evidence")
        salts.add(registration["salt"])
        receipts[role] = sha256(stage / "result.json")
        shutil.copyfile(stage / "result.json", PAYLOAD / f"{role}-result.json")
    retained = WORKSPACE / "parent"
    extract_archive(parent_archive, retained, expected=parent["artifact_hashes"])
    members = {**parent["artifact_hashes"], INV: digest}
    builds = {}
    for lane, name in (("development", "build-a.zip"), ("development-rebuild", "build-b.zip")):
        frozen = campaign / lane / INV
        require(sha256(frozen) == digest, "component bytes differ")
        path = WORKSPACE / name
        deterministic_zip(path, {member: frozen if member == INV else retained / member for member in members})
        builds[name] = sha256(path)
    require(len(set(builds.values())) == 1, "independent archive builds differ")
    for name in ("request.json", "verification.json", "registration.json"):
        shutil.copyfile(parent_dir / name, PAYLOAD / f"parent-{name}")
    write_json(PAYLOAD / "registration.json", {
        "artifact_hashes": members, "archive_sha256": builds["build-a.zip"],
        "parent_archive_sha256": parent["archive_sha256"], "parent_artifact_hashes": parent["artifact_hashes"],
        "seed_policy": parent["seed_policy"], "cost_limit": decision["limit"],
        "component_receipts": receipts, "driver_sha256": sha256(Path(__file__)),
        "source_revision": environment["source_revision"],
        "component_source_revision": screen["environment"]["source_revision"],
        "dependency_lock_sha256": screen["environment"]["dependency_lock_sha256"],
        "parent_verification_sha256": sha256(PAYLOAD / "parent-verification.json"),
        "baseline_costs": read_json(source / "docs/evidence/invsqrt-chemistry-20261107/combined-result.json")["reference"],
    })


def archive(source: Path, parent_archive: Path) -> None:
    registration = read_json(PAYLOAD / "registration.json")
    environment = capture(source)
    require(not environment["dirty"] and environment["source_revision"] == registration["source_revision"]
            and environment["dependency_lock_sha256"] == registration["dependency_lock_sha256"]
            and sha256(Path(__file__)) == registration["driver_sha256"]
            and sha256(parent_archive) == registration["parent_archive_sha256"], "archive source or control changed")
    parent = WORKSPACE / "parent"
    extract_archive(parent_archive, parent, expected=registration["parent_artifact_hashes"])
    table = read_json(source / "docs/evidence/invsqrt-lattice-20261108/28-20-14.json")
    fmt = TrimmedFormat(10, 7, tuple(table["fractional"]), True, True, True, True)
    km, primitives, official = backend()
    rebuilt = build_circuit(km, primitives, fmt, tuple(tuple(row) for row in table["coefficients"]))
    _, digest = emit(km, rebuilt, official, WORKSPACE / INV)
    members = registration["artifact_hashes"]
    require(digest == members[INV], "independently rebuilt KMB differs")
    archive_path = WORKSPACE / "hybrid.zip"
    deterministic_zip(archive_path, {name: WORKSPACE / INV if name == INV else parent / name for name in members})
    require(sha256(archive_path) == registration["archive_sha256"], "cloud build differs from both local archives")
    fresh = WORKSPACE / "extracted"
    extract_archive(archive_path, fresh, expected=members)
    artifacts = manifest(fresh, origin="generated", provenance="Fresh extraction of the frozen trimmed-width archive")
    settings = {**read_json(source / "vendor/backend.json"), "project_root": str(source)}
    contract = load_contract(source / "contracts/contract.json")
    receipts = WORKSPACE / "receipts"
    verify = receipts / "verification"
    write_json(receipts / "prepare.json", {"archive_sha256": sha256(archive_path), "source_environment": environment,
               "registration_sha256": sha256(PAYLOAD / "registration.json"), "rebuilt_invsqrt_sha256": digest})
    report = verify_candidate(artifacts, contract, "full", registration["seed_policy"], settings, verify,
                              verification_profile="candidate-v1", timeout=2300)
    require(report["status"] == "passed" and report["complete"]
            and has_full_hybrid_coverage(report, candidate_coverage(artifacts)), "full archive verification failed")
    prior_path = PAYLOAD / "parent-verification.json"
    require(sha256(prior_path) == registration["parent_verification_sha256"], "parent verification changed")
    prior = read_json(prior_path)
    relocation = review_backend_pair(prior, PAYLOAD / "parent-request.json", report, verify / "request.json")
    write_json(receipts / "backend-pair.json", relocation)
    require(report["seed_policy"] == prior["seed_policy"] and report["contract_hash"] == prior["contract_hash"],
            "matched archive seed or contract differs")
    before, after = prior["official_results"], report["official_results"]
    for benchmark in ("dqi", "dfthcsos"):
        require(isclose(before["costs"][benchmark], after["costs"][benchmark], rel_tol=1e-12),
                f"retained {benchmark} cost differs")
    require(dqi_counts(before["raw_verifier_results"]["dqi"]) == dqi_counts(after["raw_verifier_results"]["dqi"]),
            "matched DQI outcomes differ")
    confirmation_path = PAYLOAD / "confirmation-result.json"
    require(sha256(confirmation_path) == registration["component_receipts"]["confirmation"], "confirmation changed")
    confirm = read_json(confirmation_path)["result"]
    inv = after["raw_verifier_results"]["invsqrt"]
    require(inv["circuit_sha256"] == digest and isclose(inv["score"], confirm["score"], rel_tol=1e-12)
            and inv["score"] <= registration["cost_limit"], "invsqrt archive cost missed the registered gate")
    base = registration["baseline_costs"]
    write_json(receipts / "comparison.json", {
        "archive_sha256": registration["archive_sha256"], "parent_archive_sha256": registration["parent_archive_sha256"],
        "verification_sha256": sha256(verify / "verification.json"),
        "parent_costs": before["costs"], "successor_costs": after["costs"],
        "parent_score": aggregate(base, before["costs"]), "successor_score": aggregate(base, after["costs"]),
        "coverage_counts": after["coverage_counts"], "matched_retained_costs": True,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "archive", "measure"))
    parser.add_argument("source", type=Path)
    parser.add_argument("parent", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.source.resolve(), args.parent.resolve())
    elif args.action == "archive":
        archive(args.source.resolve(), args.parent.resolve())
    else:
        output = WORKSPACE / "receipts"
        output.mkdir()
        sys.exit(run_job([sys.executable, str(Path(__file__).resolve()), "archive",
                          str(args.source), str(args.parent)], output, 2420))


if __name__ == "__main__":
    main()
