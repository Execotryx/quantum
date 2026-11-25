"""Run the two-stage full-coverage screen for regenerated public DQI circuits."""

import argparse
import importlib
import re
import secrets
import sys
from pathlib import Path

from dqi_development import pooled_price, pricing_inputs

from qcompile.experiments import record_lock
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend

CANDIDATES = ("d2", "d3", "d5", "d5-ozer", "d4")
SHOTS = 102_400
ROUTED_PRICE = 7_121_637_700_132.021
REFERENCE = 24_439_461_432_712.35


def backend_pin(settings: dict) -> str:
    return identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})


def register(pairs: list[list[str]], output: Path, backend: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    candidates = {}
    for name, first, second in pairs:
        if name not in CANDIDATES or name in candidates:
            raise ValueError(f"invalid or repeated DQI candidate: {name}")
        records = [Path(path).resolve() / "regeneration.json" for path in (first, second)]
        a, b = map(read_json, records)
        artifact = records[0].with_name("dqi.kmb")
        digest = sha256(artifact)
        if (records[0] == records[1] or a["status"] != "go" or b["status"] != "go"
                or a["sha256"] != b["sha256"] or a["sha256"] != digest
                or a["source_sha256"] != b["source_sha256"]
                or sha256(records[1].with_name("dqi.kmb")) != digest):
            raise ValueError(f"{name} has no matching admitted rebuilds")
        candidates[name] = {"artifact": artifact.relative_to(Path.cwd()).as_posix(), "sha256": digest,
                            "build_receipts": {path.relative_to(Path.cwd()).as_posix(): sha256(path)
                                               for path in records}}
    write_json(output, {"candidates": candidates, "backend_inventory_sha256": backend_pin(settings),
                        "driver_sha256": sha256(Path(__file__)),
                        "salts": [secrets.token_hex(32) for _ in range(8)], "shots": SHOTS})


def verify_draw(api, circuit, digest: str, salt: str, workers: int) -> dict:
    spec = api.ProblemSpecDQI.benchmark_instance(num_shots=SHOTS)
    try:
        return api.verify(circuit, spec, salt=salt, max_workers=workers)
    except AssertionError as error:
        match = re.search(r"value_errors=(\d+)/(\d+), phase_errors=(\d+)/(\d+)", str(error))
        if not match:
            raise
        values, value_shots, phases, phase_shots = map(int, match.groups())
        if value_shots != SHOTS or phase_shots != SHOTS or values + phases > SHOTS:
            raise ValueError("invalid verifier rejection counts") from error
        return {"status": "confidence_rejected", "circuit_sha256": digest,
                "verified_shots": SHOTS, "value_errors": values, "phase_errors": phases}


def evaluate(registration: Path, backend: Path, output: Path, workers: int) -> None:
    plan = read_json(registration)
    pin = sha256(registration)
    salts = plan["salts"]
    settings = read_json(backend)
    if (backend_pin(settings) != plan["backend_inventory_sha256"] or sha256(Path(__file__)) != plan["driver_sha256"]
            or plan["shots"] != SHOTS
            or len(salts) != 8 or len(set(salts)) != 8
            or any(not re.fullmatch(r"[0-9a-f]{64}", salt) for salt in salts)
            or not set(plan["candidates"]) <= set(CANDIDATES) or workers < 1):
        raise ValueError("invalid DQI pricing registration or backend")
    validate_backend(settings)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    kickmix = importlib.import_module("kickmix")
    output.mkdir(parents=True, exist_ok=True)
    with record_lock(output):
        if (output / "decision.json").exists():
            raise ValueError("DQI pricing decision already exists")

        def price(name: str, draws: int):
            candidate = plan["candidates"][name]
            artifact = Path(candidate["artifact"])
            digest = candidate["sha256"]
            if sha256(artifact) != digest or any(
                sha256(Path(path)) != receipt for path, receipt in candidate["build_receipts"].items()
            ):
                raise ValueError(f"frozen DQI build changed: {name}")
            circuit = None
            results = []
            for index, salt in enumerate(salts[:draws], 1):
                path = output / name / f"s{index}.json"
                identity = {"registration_sha256": pin, "salt": salt, "candidate": name}
                if not path.exists():
                    if circuit is None:
                        circuit = kickmix.Circuit.from_file(str(artifact))
                    result = verify_draw(api, circuit, digest, salt, workers)
                    write_json(path, {**identity, "result": result})
                receipt = read_json(path)
                result = receipt["result"]
                if (any(receipt[key] != value for key, value in identity.items())
                        or result["circuit_sha256"] != digest or result["verified_shots"] != SHOTS):
                    raise ValueError(f"DQI pricing receipt changed: {path}")
                results.append(result)
            if any(result["status"] != "PASS" for result in results):
                return {"candidate": name, "cost": None,
                        "failures_by_salt": [row["value_errors"] + row["phase_errors"] for row in results]}
            _, bases = pricing_inputs(results, api)
            zero_upper = api.clopper_pearson_upper_bound(0, SHOTS, api.DEFAULT_LOG2_DELTA)
            return {"candidate": name, **pooled_price(results, api), "qubits": results[0]["num_qubits"],
                    "mean_toffolis": max(row["toffoli_count"] for row in results),
                    "zero_failure_cost": api.repetition_overhead(zero_upper) * max(bases)}

        def order(rows):
            return sorted((row for row in rows if row["cost"] is not None),
                          key=lambda row: (row["cost"], row["qubits"], row["mean_toffolis"], row["candidate"]))

        stage1 = [price(name, 2) for name in plan["candidates"]]
        stage2 = [price(row["candidate"], 8) for row in order(stage1)[:2]]
        ranked = order(stage2)
        decision = {"status": "no_go", "registration_sha256": pin, "stage1": stage1, "stage2": stage2}
        if ranked:
            winner = ranked[0]
            ratio = REFERENCE / winner["cost"]
            banked = winner["cost"] < ROUTED_PRICE
            decision.update(status="go" if ratio >= 50 else "go_recorded", pooled_ratio=ratio,
                            banked=banked, selected=winner["candidate"],
                            sha256=plan["candidates"][winner["candidate"]]["sha256"])
        write_json(output / "decision.json", decision)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    freeze = commands.add_parser("register")
    freeze.add_argument("backend", type=Path)
    freeze.add_argument("registration", type=Path)
    freeze.add_argument("--pair", action="append", nargs=3, required=True, metavar=("ID", "BUILD_A", "BUILD_B"))
    runs = commands.add_parser("evaluate")
    runs.add_argument("backend", type=Path)
    runs.add_argument("registration", type=Path)
    runs.add_argument("output", type=Path)
    runs.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.action == "register":
        register(args.pair, args.registration, args.backend)
    else:
        evaluate(args.registration, args.backend, args.output, args.workers)


if __name__ == "__main__":
    main()
