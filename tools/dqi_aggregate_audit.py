"""Audit two sealed three-task reports against the frozen archive."""

import argparse
from math import isclose
from pathlib import Path

from qcompile.artifacts import hashes
from qcompile.component_confirmations import HYBRID_COVERAGE
from qcompile.io import read_json, sha256, write_json
from qcompile.portfolio import clears_target, portfolio_target
from qcompile.reference.scoring import aggregate


def audit(registration: Path, archive: Path, structural: Path, evidence: Path, output: Path) -> None:
    record = read_json(registration)
    target = portfolio_target(record)
    archive_hash, registration_hash = sha256(archive), sha256(registration)
    shape = read_json(structural)
    coverage = shape["expected_full_coverage"]
    if (archive_hash != record["archive_sha256"] or shape["archive_sha256"] != archive_hash
            or shape["members"] != record["artifact_hashes"] or shape["metric_sha256"] != record["metric_sha256"]
            or len(set(record["salts"].values())) != 2):
        raise ValueError("Archive, structural preflight or salt identities differ")
    if target != 20:
        r, b, _ = shape["checks"]["dfthcsos"]["shape"]
        if coverage != {**HYBRID_COVERAGE, "dfthcsos": (76 + r * b) * 64}:
            raise ValueError("Structural evidence does not declare full benchmark coverage")

    expected_coverage = {
        name: {"completed": count, "expected": count}
        for name, count in coverage.items()
    }
    verified = {}
    for role, expected_role in (("metric", "official_local"), ("confirmation", "confirmation")):
        directory = evidence / role
        decision_path = directory / "decision.json"
        verification_path = directory / "verification/verification.json"
        request_path = directory / "verification/request.json"
        extracted_preflight = directory / "preflight.json"
        decision = read_json(decision_path)
        report = read_json(verification_path)
        request = read_json(request_path)
        worker = report["official_results"]
        if target != 20 and (
            hashes(request["artifacts"]) != record["artifact_hashes"]
            or request["tier"] != "full" or request["expected_coverage"] != coverage
            or request["seed_policy"] != report["seed_policy"]
        ):
            raise ValueError(f"{role} verifier request differs from the registered archive or full coverage")
        if (
            decision["registration_sha256"] != registration_hash or decision["archive_sha256"] != archive_hash
            or decision["metric_sha256"] != record["metric_sha256"] or decision["role"] != role
            or decision["verification_sha256"] != sha256(verification_path)
            or report["request_hash"] != sha256(request_path) or report["role"] != expected_role
            or report["status"] != "passed" or report["complete"] is not True or report["tier"] != "full"
            or request["backend"]["metric_sha256"] != record["metric_sha256"]
            or read_json(extracted_preflight) != shape
            or report["seed_policy"]["salt"] != record["salts"][role]
            or report["artifact_hashes"] != record["artifact_hashes"]
            or worker["completed"] is not True or worker["verification_shot_divisor"] != 1
            or worker["coverage_counts"] != expected_coverage
        ):
            raise ValueError(f"{role} is not a complete full metric result for this archive")
        score = aggregate(record["baseline_costs"], worker["costs"])
        if (decision["status"] != "go" or not clears_target(score, target, record["baseline_costs"], worker["costs"])
                or worker["costs"] != decision["costs"]
                or not isclose(score, decision["aggregate"], rel_tol=1e-12)):
            raise ValueError(f"{role} did not independently establish an aggregate above {target}")
        verified[role] = {
            "aggregate": score, "costs": worker["costs"], "coverage": worker["coverage_counts"],
            "verification_sha256": sha256(verification_path), "decision_sha256": sha256(decision_path),
        }
    certificate = {
        "status": f"verified_above_{target}",
        "archive_sha256": archive_hash,
        "archive_bytes": archive.stat().st_size,
        "registration_sha256": registration_hash,
        "metric_sha256": record["metric_sha256"],
        "members": record["artifact_hashes"],
        "verifications": verified,
    }
    if target != 20:
        certificate.update({key: record[key] for key in ("format", "minimum_score", "components")})
    write_json(output, certificate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("registration", "archive", "structural", "evidence", "output"):
        parser.add_argument(name, type=Path)
    audit(**vars(parser.parse_args()))
