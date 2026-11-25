"""Register and evaluate a qualified open DQI successor against banked D4."""

import argparse
import re
import secrets
from pathlib import Path

import dqi_repair_campaign as paired
from dqi_open_preflight import checked_file

from qcompile.experiments import record_lock
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import validate_backend


def register(preflight: Path, report: Path, backend: Path, ledger: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    settings = read_json(backend)
    validate_backend(settings)
    plan, observed = read_json(preflight), read_json(report)
    selected = observed["roles"]["candidate"]
    evidence = plan["evidence"]
    banked = checked_file(plan["artifacts"]["banked"])
    candidate = checked_file(plan["artifacts"]["candidate"])
    builds = [checked_file(pin) for pin in plan["builds"]]
    build_records = [read_json(path) for path in builds]
    nested_artifacts = [checked_file(record["artifact"]) for record in build_records]
    candidate_sha = plan["artifacts"]["candidate"]["sha256"]
    historical_sources = [checked_file(evidence[key]) for key in ("member_registration", "historical_registration")]
    if (
        len(builds) != 2 or len({path.resolve() for path in nested_artifacts}) != 2
        or any(record["artifact"]["sha256"] != candidate_sha for record in build_records)
        or candidate not in nested_artifacts
        or plan["backend_inventory_sha256"] != paired.backend_pin(settings)
        or observed["registration_sha256"] != sha256(preflight)
        or not observed["native_gate_passed"]
        or not selected["matched_clean"] or not selected["panels_clear_ceiling"]
        or len(selected["archived"]) != 6 or len(selected["targeted"]) != 4 or len(selected["panels"]) != 2
        or any(row[key] for row in selected["archived"] + selected["targeted"]
               for key in ("phase_offsets", "value_offsets", "dirty_offsets", "mask_offsets"))
    ):
        raise ValueError("Two exact builds and a complete passing native preflight are required")
    prior = {salt for path in historical_sources for salt in read_json(path)["salts"]}
    ledger.mkdir(parents=True, exist_ok=True)
    with record_lock(ledger):
        development = ledger / "development-salts.json"
        confirmation = ledger / "confirmation-ledger.json"
        reserved = read_json(development) if development.exists() else {}
        confirmed = {row["salt"] for row in read_json(confirmation)} if confirmation.exists() else set()
        salts = []
        while len(salts) < 8:
            salt = secrets.token_hex(32)
            if salt not in reserved and salt not in confirmed and salt not in prior and salt not in salts:
                salts.append(salt)
        registration = {
            "pins": {
                "driver": sha256(Path(paired.__file__)),
                "open_driver": sha256(Path(__file__)),
                "backend": paired.backend_pin(settings),
                "banked": plan["artifacts"]["banked"]["sha256"],
                "candidate": candidate_sha,
                "builds": list(map(sha256, builds)),
                "preflight_registration": sha256(preflight),
                "preflight_report": sha256(report),
            },
            "artifacts": {"banked": banked.as_posix(), "candidate": candidate.as_posix()},
            "salts": salts,
            "shots": paired.SHOTS,
        }
        reserved.update(dict.fromkeys(salts, identity(registration)))
        write_json(development, reserved, replace=True)
        write_json(output, registration)


def evaluate(registration: Path, backend: Path, output: Path, workers: int) -> None:
    plan = read_json(registration)
    if plan["pins"]["open_driver"] != sha256(Path(__file__)) or any(
        re.fullmatch(r"[0-9a-f]{64}", salt) is None for salt in plan["salts"]
    ):
        raise ValueError("Open campaign identity or salt syntax changed")
    artifacts = plan["artifacts"]
    common = registration, backend, Path(artifacts["banked"]), Path(artifacts["candidate"]), output, workers
    for role in paired.ROLES:
        paired.evaluate(*common, role, draw_limit=2)
    initial = [read_json(output / role / f"s{index}.json") for role in paired.ROLES for index in (1, 2)]
    if any(row["result"]["status"] != "PASS" for row in initial):
        decision = {"selected": "banked", "reason": "initial_verifier_rejection"}
    else:
        for role in paired.ROLES:
            paired.evaluate(*common, role)
        banked, candidate = (read_json(output / role / "summary.json") for role in paired.ROLES)
        improved = banked["passes"] == candidate["passes"] == 8 and candidate["cost"] < banked["cost"]
        decision = {
            "selected": "candidate" if improved else "banked",
            "reason": "strict_pooled_improvement" if improved else "pooled_qualification_failed",
            "banked": banked,
            "candidate": candidate,
        }
    decision["registration_sha256"] = sha256(registration)
    path = output / "decision.json"
    if not path.exists():
        write_json(path, decision)
    elif read_json(path) != decision:
        raise ValueError("Sealed comparison decision changed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    registration = commands.add_parser("register")
    for name in ("preflight", "report", "backend", "ledger", "output"):
        registration.add_argument(name, type=Path)
    campaign = commands.add_parser("evaluate")
    for name in ("registration", "backend", "output"):
        campaign.add_argument(name, type=Path)
    campaign.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.action == "register":
        register(args.preflight, args.report, args.backend, args.ledger, args.output)
    else:
        evaluate(args.registration, args.backend, args.output, args.workers)


if __name__ == "__main__":
    main()
