"""Register and run the two-decoder full-strength D4 repair campaign."""

import argparse
import importlib
import secrets
import sys
from pathlib import Path

from qcompile.experiments import record_lock
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend

ROLES = ("banked", "candidate")
SHOTS = 102_400


def backend_pin(settings: dict) -> str:
    return identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})


def register(
    backend: Path, bank_record: Path, banked: Path, builds: list[Path],
    matched: Path, control_profile: Path, output: Path,
) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    receipts = [directory / "build.json" for directory in builds]
    artifacts = [directory / "dqi.kmb" for directory in builds]
    records = list(map(read_json, receipts))
    if len({directory.resolve() for directory in builds}) != 2 or records[0] != records[1]:
        raise ValueError("Expected matching build records from independent directories")
    candidate = records[0]
    member = read_json(bank_record)
    if (
        sha256(banked) != member["sha256"]
        or candidate["banked_d4_sha256"] != member["sha256"]
        or candidate["source_sha256"] != member["source_sha256"]
        or candidate["backend_sha256"] != sha256(backend)
        or candidate["scan_count"] != 4095
        or candidate["circuit_sha256"] == member["sha256"]
        or any(sha256(path) != candidate["circuit_sha256"] for path in artifacts)
    ):
        raise ValueError("Repair build or original decoder identity differs")
    replay = read_json(matched)
    profile = read_json(control_profile)
    if profile["circuit_sha256"] != member["sha256"] or profile["homogeneous_ablation"]:
        raise ValueError("Matched batches require the unmodified native banked profile")
    expected = {}
    for draw, receipt in profile["batch_receipts"].items():
        for name in receipt["batches"]:
            start = int(Path(name).stem.removeprefix("batch-"))
            selected = [row for row in profile["profiles"] if row["draw"] == draw and start <= row["index"] < start + 256]
            expected[draw, start] = {
                f"{flag}_offsets": sorted(row["index"] - start for row in selected if row[f"{flag}_error"])
                for flag in ("phase", "value")
            }
    observed = {
        (row["draw"], row["batch_start"]): {key: row["banked"][key] for key in ("phase_offsets", "value_offsets")}
        for row in replay["batches"]
    }
    if (
        replay["banked_sha256"] != member["sha256"]
        or replay["candidate_sha256"] != candidate["circuit_sha256"]
        or replay["build_sha256"] != sha256(receipts[0])
        or replay["profile_sha256"] != sha256(control_profile)
        or replay["backend_inventory_sha256"] != backend_pin(settings)
        or observed != expected
        or replay["shots"] != 1024
        or len(replay["batches"]) != 4
        or sum(len(row["banked"]["phase_offsets"]) for row in replay["batches"]) != 4
        or any(row["candidate"][key] for row in replay["batches"]
               for key in ("phase_offsets", "value_offsets", "mask_offsets", "dirty_offsets"))
    ):
        raise ValueError("The fixed batch regression did not clear all four failures")
    pins = {
        "driver": sha256(Path(__file__)), "backend": backend_pin(settings),
        "bank_record": sha256(bank_record), "banked": member["sha256"],
        "candidate": candidate["circuit_sha256"], "matched": sha256(matched),
        "control_profile": sha256(control_profile),
        "builds": list(map(sha256, receipts)),
    }
    historical = set(read_json(bank_record.with_name("salts.json"))["salts"])
    salts = []
    while len(salts) < 8:
        salt = secrets.token_hex(32)
        if salt not in historical and salt not in salts:
            salts.append(salt)
    write_json(output, {"pins": pins, "shots": SHOTS, "salts": salts})


def evaluate(
    registration: Path, backend: Path, banked: Path, candidate: Path, output: Path, workers: int, role: str,
    *, draw_limit: int = 8,
) -> None:
    from dqi_development import pooled_price
    from vendor_dqi_price import REFERENCE, verify_draw

    settings = read_json(backend)
    validate_backend(settings)
    plan = read_json(registration)
    pin = sha256(registration)
    pins = plan["pins"]
    salts = plan["salts"]
    if (
        pins["driver"] != sha256(Path(__file__))
        or pins["backend"] != backend_pin(settings)
        or pins["banked"] != sha256(banked)
        or pins["candidate"] != sha256(candidate)
        or plan["shots"] != SHOTS
        or len(salts) != 8
        or len(set(salts)) != 8
        or workers < 1
        or draw_limit not in (2, 8)
    ):
        raise ValueError("Full-strength campaign identities do not match")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    file = {"banked": banked, "candidate": candidate}[role]
    output.mkdir(parents=True, exist_ok=True)
    with record_lock(output):
        receipts = []
        circuit = None
        for index, salt in enumerate(salts[:draw_limit], 1):
            path = output / role / f"s{index}.json"
            identifier = {"registration_sha256": pin, "salt": salt, "role": role}
            if not path.exists():
                if circuit is None:
                    circuit = km.Circuit.from_file(str(file))
                print(f"{role} s{index} started", flush=True)
                result = verify_draw(api, circuit, pins[role], salt, workers)
                write_json(path, {**identifier, "result": result})
            receipt = read_json(path)
            result = receipt["result"]
            if (
                any(receipt[key] != value for key, value in identifier.items())
                or result["circuit_sha256"] != pins[role]
                or result["verified_shots"] != SHOTS
            ):
                raise ValueError(f"Unexpected verifier result identity for {role} s{index}")
            print(f"{role} s{index}: {result['status']} value={result['value_errors']} phase={result['phase_errors']}",
                  flush=True)
            receipts.append(result)
        if draw_limit != 8:
            return
        outcome = {
            "registration_sha256": pin, "role": role,
            "passes": sum(result["status"] == "PASS" for result in receipts),
            "coverage": len(receipts) * SHOTS,
            "value_errors": sum(result["value_errors"] for result in receipts),
            "phase_errors": sum(result["phase_errors"] for result in receipts),
            "result_sha256": {f"s{i}.json": sha256(output / role / f"s{i}.json") for i in range(1, 9)},
        }
        if outcome["passes"] == len(receipts):
            price = pooled_price(receipts, api)
            outcome.update(price, official_reference_ratio=REFERENCE / price["cost"],
                           qubits=receipts[0]["num_qubits"],
                           static_toffoli_like=receipts[0]["max_toffoli_count"],
                           average_mean_toffoli_like=sum(row["toffoli_count"] for row in receipts) / len(receipts))
        prior = output / role / "summary.json"
        if prior.exists():
            if read_json(prior) != outcome:
                raise ValueError("Existing campaign summary differs from the sealed receipts")
        else:
            write_json(prior, outcome)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for op, paths in (
        ("register", ("backend", "bank_record", "banked", "matched", "control_profile", "output")),
        ("evaluate", ("registration", "backend", "banked", "candidate", "output")),
    ):
        command = commands.add_parser(op)
        for name in paths:
            command.add_argument(name, type=Path)
        if op == "register":
            command.add_argument("--builds", type=Path, nargs=2, required=True)
        else:
            command.add_argument("--role", choices=ROLES, required=True)
            command.add_argument("--workers", type=int, default=2)
    a = parser.parse_args()
    if a.operation == "register":
        register(a.backend, a.bank_record, a.banked, a.builds, a.matched, a.control_profile, a.output)
    else:
        evaluate(a.registration, a.backend, a.banked, a.candidate, a.output, a.workers, a.role)


if __name__ == "__main__":
    main()
