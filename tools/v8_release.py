"""Prepare and verify the v8.0 hybrid release from frozen component evidence."""

import argparse
import platform
import secrets
import shutil
from math import isclose
from pathlib import Path
from typing import Any

from hybrid_preflight import preflight

from qcompile.artifacts import deterministic_zip, extract_archive, manifest
from qcompile.component_confirmations import candidate_coverage, has_full_hybrid_coverage
from qcompile.contract import load_contract
from qcompile.io import read_json, sha256, write_json
from qcompile.official import verify_candidate
from qcompile.reference.scoring import aggregate

EVIDENCE = Path("docs/evidence/review-fixes-cloud-20261108")
UPLOAD_LIMIT = Path("docs/evidence/v8/upload-limit.json")
ZLIB_PIN = Path("configs/release-zlib.json")
REGISTRATION = Path("docs/evidence/v8/v8.0/registration.json")


def require(condition: bool, diagnostic: str) -> None:
    if not condition:
        raise ValueError(diagnostic)


def prepare(parent: Path, decoder: Path, output: Path) -> None:
    parent_record = read_json(EVIDENCE / "v6-paired/registration.json")
    comparison = read_json(EVIDENCE / "v6-paired/comparison.json")
    parent_report = EVIDENCE / "v6-paired/verification/verification.json"
    verification = read_json(parent_report)
    require(sha256(parent) == parent_record["archive_sha256"] == comparison["archive_sha256"]
            and sha256(parent_report) == comparison["verification_sha256"]
            and verification["status"] == "passed" and verification["complete"]
            and verification["artifact_hashes"] == parent_record["artifact_hashes"], "invalid parent release")
    dqi = EVIDENCE / "dqi-strength"
    complete = read_json(dqi / "complete.json")
    registration = read_json(dqi / "registration.json")
    digest = sha256(decoder)
    require(sha256(dqi / "registration.json") == complete["registration_sha256"]
            and digest == registration["circuit_sha256"], "invalid routed DQI registration")
    dqi_results = {}
    for role, receipt_hash in complete["receipts"].items():
        path = dqi / role / "result.json"
        receipt = read_json(path)
        result = receipt["result"]
        require(sha256(path) == receipt_hash and receipt["registration_sha256"] == complete["registration_sha256"]
                and receipt["salt"] == registration["salts"][role] and result["circuit_sha256"] == digest
                and result["status"] == "PASS" and result["verified_shots"] == 102400
                and not (result["value_errors"] or result["phase_errors"]), f"invalid DQI result: {role}")
        dqi_results[role] = result["score"]
    require(len(dqi_results) == 7 and dqi_results["full"] == dqi_results["confirmation"],
            "incomplete or inconsistent DQI certification")

    parent_members = parent_record["artifact_hashes"]
    limit_record = read_json(UPLOAD_LIMIT)
    limit = limit_record["limit"]
    require((type(limit) is int and limit > 0) or limit == "unknown", "invalid upload size observation")
    require(not REGISTRATION.exists(), "v8.0 already has a frozen registration")
    output.mkdir(parents=True, exist_ok=False)
    extracted = output / "parent"
    extract_archive(parent, extracted, expected=parent_members)
    files = {name: extracted / name for name in parent_members}
    legacy = output / "v6-stored-check.zip"
    deterministic_zip(legacy, files, compression="stored")
    require(sha256(legacy) == parent_record["archive_sha256"], "stored mode changed the v6 archive bytes")
    stored_regression_hash = sha256(legacy)
    legacy.unlink()
    files["dqi.kmb"] = decoder
    members = {**parent_members, "dqi.kmb": digest}
    pin = read_json(ZLIB_PIN)
    require(pin["python_build"] == platform.python_version() and pin["python_distribution"]
            and tuple(pin["python_build_details"]) == platform.python_build(), "packer differs from the pinned Python build")
    runtime = pin["zlib_runtime"]
    builds = {"stored": output / "stored.zip", "deflate9": output / "deflate9.zip"}
    deterministic_zip(builds["stored"], files)
    deterministic_zip(builds["deflate9"], files, compression="deflate9", zlib_runtime=runtime)
    sizes = {mode: path.stat().st_size for mode, path in builds.items()}
    mode = "stored" if type(limit) is int and sizes["stored"] <= limit else "deflate9"
    if type(limit) is int and sizes[mode] > limit:
        write_json(output / "no-go.json", {"sizes": sizes, "limit": limit, "status": "no_go"})
        return

    first = builds[mode]
    second = output / "rebuild" / "submission.zip"
    second.parent.mkdir()
    if mode == "deflate9":
        deterministic_zip(second, files, compression="deflate9", zlib_runtime=runtime)
    else:
        deterministic_zip(second, files)
    archive_hash = sha256(second)
    require(sha256(first) == archive_hash, "independent builds differ")
    extraction_hashes = {}
    for other, path in builds.items():
        extracted_mode = output / f"extracted-{other}"
        extraction_hashes[other] = extract_archive(path, extracted_mode, expected=members)
        shutil.rmtree(extracted_mode)
    require(extraction_hashes["stored"] == extraction_hashes["deflate9"], "container changed extracted member hashes")
    baseline = read_json(Path("docs/evidence/invsqrt-trimmed-paired-20261108/registration.json"))["baseline_costs"]
    full_costs = {**comparison["successor_costs"], "dqi": dqi_results["full"]}
    conservative_cost = read_json(dqi / "pricing.json")["cost"]
    require(0 < conservative_cost <= registration["price_limit"], "routed DQI did not clear pricing")
    conservative_costs = {**full_costs, "dqi": conservative_cost}
    write_json(REGISTRATION, {
        "release": "v8.0", "archive_sha256": archive_hash, "artifact_hashes": members,
        "parent_archive_sha256": sha256(parent), "selection": dict.fromkeys(full_costs, "fallback"),
        "vendored_provenance": {}, "compression": mode, "sizes": sizes,
        "upload_limit": limit_record, "upload_limit_sha256": sha256(UPLOAD_LIMIT),
        "stored_regression_sha256": stored_regression_hash,
        "zlib_pin": pin, "zlib_pin_sha256": sha256(ZLIB_PIN),
        "metric_salt": secrets.token_hex(32), "confirmation_salt": secrets.token_hex(32),
        "baseline_costs": baseline, "full_costs": full_costs,
        "score_full": aggregate(baseline, full_costs), "score_conservative": aggregate(baseline, conservative_costs),
        "parent_verification_sha256": sha256(parent_report), "dqi_certificate_sha256": sha256(dqi / "complete.json"),
        "dqi_pricing_sha256": sha256(dqi / "pricing.json"),
        "driver_sha256": sha256(Path(__file__)),
    })


def measure(archive: Path, backend_path: Path, output: Path, role: str) -> None:
    record = read_json(REGISTRATION)
    require(sha256(Path(__file__)) == record["driver_sha256"], "release driver differs from registration")
    require(sha256(archive) == record["archive_sha256"], "release archive bytes differ from registration")
    meminfo = Path("/proc/meminfo").read_text()
    available = next(int(line.split()[1]) for line in meminfo.splitlines() if line.startswith("MemAvailable:"))
    require(available * 1024 >= 8_000_000_000, "preflight requires at least 8 GB available RAM")
    preflight(archive, backend_path, output)
    artifacts = manifest(output / "extracted", origin="generated", provenance="Fresh extraction of registered v8.0")
    require({name: item["sha256"] for name, item in artifacts.items()} == record["artifact_hashes"],
            "preflight members differ from registration")
    backend = {**read_json(backend_path), "project_root": str(Path.cwd())}
    contract = load_contract(Path("contracts/contract.json"))
    contract.require_ready(Path.cwd())
    seed = {"role": "confirmation" if role == "confirmation" else "official_local",
            "salt": record[f"{role}_salt"], "distribution": "v8.0 complete pinned metric on fresh extraction"}
    report = verify_candidate(artifacts, contract, "full", seed, backend, output / "verification",
                              verification_profile="candidate-v1")
    decision: dict[str, Any] = {
        "status": "no_go",
        "verification_sha256": sha256(output / "verification/verification.json"),
    }
    if report["status"] == "passed" and report["complete"] and has_full_hybrid_coverage(report, candidate_coverage(artifacts)):
        costs = report["official_results"]["costs"]
        score = aggregate(record["baseline_costs"], costs)
        decision.update(costs=costs, aggregate=score,
                        ratios={name: record["baseline_costs"][name] / cost for name, cost in costs.items()})
        if (record["score_conservative"] * 0.99 <= score <= record["score_full"] * 1.01
                and all(isclose(costs[name], record["full_costs"][name], rel_tol=1e-9)
                        for name in ("invsqrt", "dfthcsos"))):
            decision["status"] = "go"
    write_json(output / "decision.json", {**decision, "registration_sha256": sha256(REGISTRATION)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("parent", type=Path)
    build.add_argument("decoder", type=Path)
    build.add_argument("output", type=Path)
    verify = commands.add_parser("measure")
    verify.add_argument("archive", type=Path)
    verify.add_argument("backend", type=Path)
    verify.add_argument("output", type=Path)
    verify.add_argument("role", choices=("metric", "confirmation"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.parent, args.decoder, args.output)
    else:
        measure(args.archive, args.backend, args.output, args.role)


if __name__ == "__main__":
    main()
