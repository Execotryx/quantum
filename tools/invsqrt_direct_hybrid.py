"""Build and measure a successor hybrid while preserving exact parent members."""

import argparse
import secrets
import sys
from math import isclose
from pathlib import Path

from invsqrt_direct import EXPECTED_SHOTS, ROOT, pins, require, run_job

from qcompile.artifacts import deterministic_zip, extract_archive, hashes, manifest
from qcompile.contract import load_contract
from qcompile.io import read_json, sha256, write_json
from qcompile.official import verify_candidate
from qcompile.reference.scoring import aggregate

PARENT_EVIDENCE = ROOT / "docs/evidence/invsqrt-chemistry-20261107"
PARENT_ZIP = ROOT / "runs/invsqrt-chemistry-20261107/invsqrt-chemistry.zip"
DIRECT_TOOL = ROOT / "tools/invsqrt_direct.py"
COVERAGE = {"invsqrt": EXPECTED_SHOTS, "dqi": 102_400, "dfthcsos": 254_464}


def accepted_component(screen: Path) -> tuple[dict, dict[str, str]]:
    decision_path = screen / "decision.json"
    decision = read_json(decision_path)
    winner = decision["winner"]
    require(decision["status"] == "go" and isinstance(winner, str), "missing qualifying frozen winner")
    digest = decision["winner_sha256"]
    require(
        sha256(screen / "registration.json") == decision["registration_sha256"], "screen protocol changed"
    )
    require(
        read_json(screen / "registration.json")["inputs"] == pins(), "generator or pinned runtime changed"
    )
    attempt = screen / winner / "attempt.json"
    require(sha256(attempt) == decision["attempts"][winner], "screen winner evidence changed")
    require(sha256(attempt.parent / "invsqrt.kmb") == digest, "screen winner bytes changed")
    bindings = {"decision": sha256(decision_path), "winner_sha256": digest}
    salts = set()
    for role in ("full", "confirmation"):
        receipt = screen / role / "result.json"
        record = read_json(receipt)
        registration = read_json(receipt.parent / "registration.json")
        raw = read_json(receipt.parent / "raw-verifier.json")
        require(
            record["registration_sha256"] == sha256(receipt.parent / "registration.json")
            and record["raw_sha256"] == sha256(receipt.parent / "raw-verifier.json")
            and registration["role"] == role
            and registration["artifact_sha256"] == digest
            and registration["decision_sha256"] == bindings["decision"]
            and registration["salt"] not in salts,
            f"invalid {role} receipt binding",
        )
        salts.add(registration["salt"])
        require(
            raw == record["result"]
            and raw["status"] == "PASS"
            and raw["circuit_sha256"] == digest
            and raw["verified_shots"] == EXPECTED_SHOTS
            and raw["score"] <= decision["limit"]
            and raw["worst_error_over_tolerance"] <= 0.90,
            f"{role} failed promotion",
        )
        bindings[role] = sha256(receipt)
    return read_json(attempt)["parameters"], bindings


def prepare(screen: Path, output: Path) -> None:
    params, bindings = accepted_component(screen)
    decision = read_json(screen / "decision.json")
    frozen = read_json(PARENT_EVIDENCE / "archive.json")
    parent = read_json(PARENT_EVIDENCE / "combined-result.json")
    require(frozen["sha256"] == sha256(PARENT_ZIP) == parent["archive_sha256"], "parent ZIP changed")
    output.mkdir(parents=True, exist_ok=False)
    retained = output / "parent"
    extract_archive(PARENT_ZIP, retained, expected=frozen["hashes"])
    expected = {**frozen["hashes"], "invsqrt.kmb": bindings["winner_sha256"]}
    require(
        {name for name in expected if expected[name] != frozen["hashes"][name]} == {"invsqrt.kmb"},
        "successor must change exactly the inverse-square-root member",
    )
    parameters = output / "parameters.json"
    write_json(parameters, params)
    for name in ("build-a", "build-b"):
        build = output / name
        build.mkdir()
        code = run_job([sys.executable, str(DIRECT_TOOL), "build", str(build), str(parameters)], build, 300)
        require(code == 0, f"{name} generation failed")
        generated = build / "invsqrt.kmb"
        require(sha256(generated) == expected["invsqrt.kmb"], "generated KMB differs from confirmation")
        files = {path: generated if path == "invsqrt.kmb" else retained / path for path in expected}
        require(
            all(sha256(path) == expected[member] for member, path in files.items()), "retained input changed"
        )
        deterministic_zip(output / f"{name}.zip", files)
    archive = output / "build-b.zip"
    digest = sha256(archive)
    require(digest == sha256(output / "build-a.zip"), "two independently built ZIPs differ")
    extract_archive(archive, output / "extracted", expected=expected)
    write_json(
        output / "registration.json",
        {
            "parent_archive_sha256": frozen["sha256"],
            "archive_sha256": digest,
            "artifact_hashes": expected,
            "component_receipts": bindings,
            "cost_limit": decision["limit"],
            "seed_policy": {
                "role": "official_local",
                "salt": secrets.token_hex(32),
                "distribution": "Full pinned metric on a fresh successor extraction, independent archive seed.",
            },
        },
    )


def metric(output: Path) -> None:
    frozen = read_json(output / "registration.json")
    archive = output / "build-b.zip"
    require(sha256(archive) == frozen["archive_sha256"], "successor ZIP changed")
    artifacts = manifest(
        output / "extracted", origin="generated", provenance="Exact successor ZIP extraction"
    )
    require(hashes(artifacts) == frozen["artifact_hashes"], "fresh extraction changed")
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    verification = output / "verification"
    report = verify_candidate(
        artifacts,
        contract,
        "full",
        frozen["seed_policy"],
        read_json(ROOT / "vendor/backend.json"),
        verification,
        timeout=3600,
    )
    require(report["status"] == "passed" and report["complete"], "complete successor metric failed")
    actual = report["official_results"]
    require(
        actual["coverage_counts"] == {name: {"completed": n, "expected": n} for name, n in COVERAGE.items()},
        "unexpected successor coverage",
    )
    require(sha256(archive) == frozen["archive_sha256"], "successor ZIP changed during verification")
    costs = actual["costs"]
    raw = actual["raw_verifier_results"]["invsqrt"]
    require(
        raw["circuit_sha256"] == frozen["artifact_hashes"]["invsqrt.kmb"]
        and raw["worst_error_over_tolerance"] <= 0.90
        and costs["invsqrt"] <= frozen["cost_limit"],
        "successor inverse-square-root gate failed",
    )
    parent = read_json(PARENT_EVIDENCE / "combined-result.json")
    require(
        all(isclose(costs[n], parent["costs"][n], rel_tol=1e-12) for n in ("dqi", "dfthcsos")),
        "retained benchmark costs differ",
    )
    score = aggregate(parent["reference"], costs)
    require(score > parent["relative_aggregate_score"], "successor does not improve on measured parent")
    write_json(
        output / "comparison.json",
        {
            "status": "locally_verified",
            "archive_sha256": frozen["archive_sha256"],
            "artifact_hashes": frozen["artifact_hashes"],
            "parent_archive_sha256": parent["archive_sha256"],
            "verification_sha256": sha256(verification / "verification.json"),
            "costs": costs,
            "reference": parent["reference"],
            "parent_score": parent["relative_aggregate_score"],
            "relative_aggregate_score": score,
            "coverage": COVERAGE,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "metric", "metric-worker"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--screen", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.screen is None:
            parser.error("prepare requires --screen")
        prepare(args.screen.resolve(), args.output.resolve())
    elif args.action == "metric-worker":
        metric(args.output.resolve())
    else:
        output = args.output.resolve()
        rc = run_job([sys.executable, __file__, "metric-worker", str(output)], output, 3660)
        require(rc == 0, f"successor metric failed; inspect {output / 'execution.log'}")


if __name__ == "__main__":
    main()
