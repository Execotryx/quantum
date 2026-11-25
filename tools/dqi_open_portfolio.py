"""Freeze and verify the three-task archive for the above-20 target."""

import argparse
import platform
import secrets
from pathlib import Path

from hybrid_preflight import preflight
from vendor_dqi_price import backend_pin

from qcompile.artifacts import deterministic_zip, extract_archive, manifest
from qcompile.component_confirmations import candidate_coverage, has_full_hybrid_coverage
from qcompile.contract import load_contract
from qcompile.experiments import record_lock
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import validate_backend, verify_candidate
from qcompile.reference.scoring import aggregate

CONTRACT = Path("contracts/contract.json")
PACKER = Path("configs/release-zlib.json")
BASELINE = Path("docs/evidence/v8/v8.0/metric/verification/verification.json")
BASE_REGISTRATION = Path("docs/evidence/v8/v8.0/registration.json")
ROLES = ("metric", "confirmation")
MEMBERS = ("invsqrt.kmb", "dfthcsos/submission.npz", *(f"dfthcsos/angle_k_{i}.kmb" for i in range(15)))


def prepare(member: Path, publisher: Path, roots: tuple[Path, Path], backend: Path,
            ledger: Path, output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    dqi = read_json(member)
    candidate = Path(dqi["artifact"])
    if (dqi["status"] != "qualified_pending_independent_confirmation"
            or sha256(candidate) != dqi["sha256"]
            or dqi["backend_inventory_sha256"] != backend_pin(settings)):
        raise ValueError("DQI archive member is not campaign-qualified on this backend")
    published = {name: digest for digest, name in
                 (line.split(maxsplit=1) for line in publisher.read_text().splitlines())}
    expected = {name: published[name.replace("/", "__")] for name in MEMBERS}
    if roots[0].resolve() == roots[1].resolve():
        raise ValueError("Independent precursor build directories are required")
    builds = [{name: root / name for name in MEMBERS} for root in roots]
    for files in builds:
        if {name: sha256(path) for name, path in files.items()} != expected:
            raise ValueError("A regenerated companion member differs from the publisher")
    packer = read_json(PACKER)
    if (packer["python_build"] != platform.python_version()
            or tuple(packer["python_build_details"]) != platform.python_build()):
        raise ValueError("Archive packer differs from the pinned Linux Python build")
    output.mkdir(parents=True, exist_ok=False)
    expected["dqi.kmb"] = dqi["sha256"]
    archives = [output / "submission.zip", output / "rebuild/submission.zip"]
    archives[1].parent.mkdir()
    for files, archive in zip(builds, archives, strict=True):
        deterministic_zip(archive, {**files, "dqi.kmb": candidate}, compression="deflate9",
                          zlib_runtime=packer["zlib_runtime"])
    digest = sha256(archives[0])
    if sha256(archives[1]) != digest:
        raise ValueError("Independent archives differ")
    extract_archive(archives[0], output / "prepare-extraction", expected=expected)
    baseline = read_json(BASE_REGISTRATION)
    contract = load_contract(CONTRACT)
    contract.require_ready(Path.cwd())
    ledger.mkdir(parents=True, exist_ok=True)
    with record_lock(ledger):
        development = ledger / "development-salts.json"
        confirmation = ledger / "confirmation-ledger.json"
        reserved = read_json(development) if development.exists() else {}
        confirmed = {row["salt"] for row in read_json(confirmation)} if confirmation.exists() else set()
        old = {baseline["metric_salt"], baseline["confirmation_salt"]}
        salts = {}
        for role in ROLES:
            while True:
                salt = secrets.token_hex(32)
                if salt not in old and salt not in confirmed and salt not in reserved and salt not in salts.values():
                    salts[role] = salt
                    break
        record = {
            "archive_sha256": digest,
            "artifact_hashes": expected,
            "backend_inventory_sha256": backend_pin(settings),
            "metric_sha256": settings["metric_sha256"],
            "contract_sha256": sha256(CONTRACT),
            "driver_sha256": sha256(Path(__file__)),
            "dqi_member_sha256": sha256(member),
            "publisher_manifest_sha256": sha256(publisher),
            "packer_sha256": sha256(PACKER),
            "baseline_registration_sha256": sha256(BASE_REGISTRATION),
            "baseline_metric_report_sha256": sha256(BASELINE),
            "baseline_costs": baseline["baseline_costs"],
            "salts": salts,
        }
        reserved.update(dict.fromkeys(salts.values(), identity(record)))
        write_json(development, reserved, replace=True)
        write_json(output / "registration.json", record)


def measure(registration: Path, archive: Path, backend: Path, output: Path, role: str) -> None:
    record = read_json(registration)
    settings = read_json(backend)
    validate_backend(settings)
    if (sha256(Path(__file__)) != record["driver_sha256"] or sha256(archive) != record["archive_sha256"]
            or sha256(CONTRACT) != record["contract_sha256"] or backend_pin(settings) != record["backend_inventory_sha256"]
            or settings["metric_sha256"] != record["metric_sha256"]
            or sha256(BASE_REGISTRATION) != record["baseline_registration_sha256"]
            or sha256(BASELINE) != record["baseline_metric_report_sha256"]
            or read_json(BASE_REGISTRATION)["baseline_costs"] != record["baseline_costs"]
            or len(set(record["salts"].values())) != len(ROLES)):
        raise ValueError("Archive, backend or verification registration differs")
    contract = load_contract(CONTRACT)
    contract.require_ready(Path.cwd())
    preflight(archive, backend, output)
    artifacts = manifest(output / "extracted", origin="generated",
                         provenance="Fresh extraction of above-20 portfolio registration")
    if {name: item["sha256"] for name, item in artifacts.items()} != record["artifact_hashes"]:
        raise ValueError("Extracted member differs from registration")
    seed = {"role": "confirmation" if role == "confirmation" else "official_local",
            "salt": record["salts"][role], "distribution": "complete pinned aggregate above-20 metric"}
    report = verify_candidate(
        artifacts, contract, "full", seed, {**settings, "project_root": str(Path.cwd())},
        output / "verification", verification_profile="candidate-v1",
    )
    complete = (report["status"] == "passed" and report["complete"]
                and has_full_hybrid_coverage(report, candidate_coverage(artifacts)))
    costs = report["official_results"]["costs"] if complete else None
    score = aggregate(record["baseline_costs"], costs) if costs else None
    write_json(output / "decision.json", {
        "status": "go" if score is not None and score > 20 else "no_go",
        "registration_sha256": sha256(registration), "archive_sha256": record["archive_sha256"],
        "metric_sha256": record["metric_sha256"], "role": role, "aggregate": score,
        "costs": costs, "verification_sha256": sha256(output / "verification/verification.json"),
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    build = commands.add_parser("prepare")
    for name in ("member", "publisher", "first", "second", "backend", "ledger", "output"):
        build.add_argument(name, type=Path)
    verify = commands.add_parser("measure")
    for name in ("registration", "archive", "backend", "output"):
        verify.add_argument(name, type=Path)
    verify.add_argument("role", choices=ROLES)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.member, args.publisher, (args.first, args.second), args.backend, args.ledger, args.output)
    else:
        measure(args.registration, args.archive, args.backend, args.output, args.role)


if __name__ == "__main__":
    main()
