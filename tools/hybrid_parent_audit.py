"""Audit historical confirmation against the unchanged parent hybrid bytes."""

from math import isclose
from pathlib import Path

import banked_chemistry

from qcompile.io import read_json, sha256
from qcompile.official import validate_backend

ROOT = banked_chemistry.ROOT
EVIDENCE = ROOT / "docs/evidence/invsqrt-chemistry-20261107"
HISTORICAL_CHEMISTRY = ROOT / "runs/invsqrt-chemistry-20261107"
HISTORICAL_INVSQRT = ROOT / "runs/invsqrt-opportunity-20261107"
BACKEND = ROOT / "vendor/backend.json"


def audit(require, extracted: Path) -> dict:
    """Audit the legacy development history before any ledger import."""
    manifest = read_json(EVIDENCE / "archive.json")
    combined = read_json(EVIDENCE / "combined-result.json")
    verifier = read_json(EVIDENCE / "verification.json")
    expected = manifest["hashes"]
    require(
        manifest["sha256"]
        == combined["archive_sha256"]
        == sha256(HISTORICAL_CHEMISTRY / "invsqrt-chemistry.zip"),
        "historical parent ZIP hash differs",
    )
    require(
        verifier["artifact_hashes"] == expected
        and verifier["complete"]
        and verifier["status"] == "passed"
        and combined["metric_receipt_sha256"] == sha256(EVIDENCE / "verification.json"),
        "historical complete metric receipt differs",
    )
    require(
        all(sha256(extracted / name) == digest for name, digest in expected.items()),
        "extracted parent member changed",
    )
    validate_backend(read_json(BACKEND))
    for registration in (
        EVIDENCE / "registration.json",
        HISTORICAL_INVSQRT / "registration.json",
    ):
        for name, digest in read_json(registration)["inputs"].items():
            path = Path(name)
            resolved = path if path.is_absolute() else ROOT / path
            require(
                resolved.is_file() and sha256(resolved) == digest,
                f"historic source input differs: {resolved}",
            )

    records = {}
    salts = {verifier["seed_policy"]["salt"]}
    earlier = 0.0
    for role in ("full", "confirmation"):
        source = HISTORICAL_INVSQRT / role
        registration = read_json(source / "registration.json")
        receipt = read_json(source / "result.json")
        raw = receipt["result"]
        require(
            receipt["registration_sha256"] == sha256(source / "registration.json")
            and registration["role"] == role
            and registration["decision_sha256"] == sha256(HISTORICAL_INVSQRT / "decision.json")
            and registration["artifact_sha256"] == raw["circuit_sha256"] == expected["invsqrt.kmb"]
            and registration["registered_unix"] > earlier
            and registration["salt"] not in salts
            and raw["status"] == "PASS"
            and raw["verified_shots"] == registration["expected_shots"] == 200_540_928
            and isclose(raw["score"], combined["costs"]["invsqrt"], rel_tol=1e-12),
            f"historical inverse-square-root {role} receipt differs",
        )
        earlier = registration["registered_unix"] + receipt["elapsed_seconds"]
        salts.add(registration["salt"])
        if role == "confirmation":
            records["invsqrt"] = {"registration": registration, "raw": raw}

    source = HISTORICAL_CHEMISTRY / "chemistry-confirmation"
    require(
        sha256(source / "registration.json") == sha256(EVIDENCE / "chemistry-confirmation-registration.json")
        and sha256(source / "result.json") == sha256(EVIDENCE / "chemistry-confirmation-result.json"),
        "chemistry confirmation differs from its tracked copy",
    )
    registration = read_json(source / "registration.json")
    raw = read_json(source / "result.json")
    _, _, api, _, official = banked_chemistry.backend()
    chemistry = extracted / "dfthcsos"
    digest = api.submission_sha256(
        api.load_circuits(chemistry), chemistry / "submission.npz", official.load_tree_edges(None, chemistry)
    )
    require(
        registration["archive_sha256"] == manifest["sha256"]
        and registration["factorization_sha256"] == expected["dfthcsos/submission.npz"]
        and registration["chemistry_hashes"]
        == {
            Path(name).name: member_hash
            for name, member_hash in expected.items()
            if name.startswith("dfthcsos/angle_")
        }
        and registration["registered_unix"] > earlier
        and registration["salt"] not in salts
        and raw["status"] == "PASS"
        and raw["verified_shots"] == registration["expected_shots"] == 254_464
        and raw["submission_sha256"] == digest
        and isclose(raw["score"], combined["costs"]["dfthcsos"], rel_tol=1e-12),
        "historical chemistry confirmation receipt differs",
    )
    records["dfthcsos"] = {"registration": registration, "raw": raw}
    return records
