"""Run preregistered paired DQI development draws using the pinned verifier."""

import argparse
import hashlib
import re
import subprocess
import sys
import time
from importlib import import_module
from pathlib import Path

import numpy as np

from invsqrt_direct import run_job
from qcompile.environment import capture
from qcompile.experiments import record_lock
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

ROOT = Path(__file__).resolve().parents[1]


def matched_pair(registration: Path, output: Path) -> None:
    registered = read_json(registration)
    settings = registered["backend"]
    validate_backend(settings)
    for role in ("kickmix", "verifiers"):
        sys.path.insert(0, settings[f"{role}_root"])
    km = import_module("kickmix")
    api = import_module("dqi.verify_submission_dqi")
    trial = read_json(output / "trial.json")
    count = {"scouting": 256, "prospective": 2560, "matched_replay": 102400}[trial["role"]]
    spec = api.ProblemSpecDQI.benchmark_instance(num_shots=count)
    seed = int.from_bytes(hashlib.sha256(trial["salt"].encode()).digest(), "big")
    rng = np.random.default_rng(seed)
    tables = api.FieldTables(km.GF2Field(spec.degree))
    weights = api.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    cases = (np.empty((count, spec.n), dtype=np.uint16),
             np.empty((count, spec.m), dtype=np.uint16), np.empty(count, dtype=bool))
    for start in range(0, count, 256):
        batch = api.sample_shots(spec, tables, rng, 256, weights)
        for target, sampled in zip(cases, batch, strict=True):
            target[start:start + 256] = sampled
    digest = hashlib.sha256()
    for array in cases:
        digest.update(memoryview(array).cast("B"))
    write_json(output / "cases.json", {"sha256": digest.hexdigest(), "shots": count, **trial})
    for side in ("control", "candidate"):
        artifact = registered["config"][side]
        path = Path(artifact["path"])
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"{side} circuit changed")
        circuit = km.Circuit.from_file(str(path))
        try:
            receipt = api.verify(circuit, spec, shots=cases, seed=seed,
                                 max_workers=registered["config"]["workers"])
        except AssertionError as error:
            detail = str(error)
            match = re.fullmatch(
                r"Effective error rate .* \(empirical=.*?, value_errors=(\d+)/(\d+), phase_errors=(\d+)/(\d+)\)",
                detail,
            )
            if match is None:
                raise
            value, value_n, phase, phase_n = map(int, match.groups())
            if value_n != count or phase_n != count or value + phase > count:
                raise ValueError("confidence rejection did not include coherent disjoint counters") from error
            write_json(output / f"{side}.json", {
                "status": "confidence_rejected", "diagnostic": detail, "circuit_sha256": artifact["sha256"],
                "verified_shots": count, "value_errors": value, "phase_errors": phase,
            })
            if side == "control" and trial["role"] != "scouting":
                raise
            continue
        if receipt["circuit_sha256"] != artifact["sha256"] or receipt["verified_shots"] != count:
            raise ValueError("pinned DQI verifier receipt does not bind the requested circuit and coverage")
        write_json(output / f"{side}.json", receipt)


def run(plan: Path, output: Path) -> None:
    config = read_json(plan)
    trials = config["trials"]
    allowed = {"scouting", "prospective", "matched_replay"}
    salts = [trial["salt"] for trial in trials]
    if (
        not 1 <= len(trials) <= 16 or any(trial["role"] not in allowed for trial in trials)
        or len(set(salts)) != len(salts) or any(not isinstance(s, str) or len(s) < 32 for s in salts)
        or type(config["workers"]) is not int or not 1 <= config["workers"] <= 4
        or not 0 < config["wall_seconds"] <= 86400
    ):
        raise ValueError("invalid bounded DQI development protocol")
    environment = capture(ROOT)
    if environment["dirty"]:
        raise ValueError("DQI development requires clean frozen source")
    settings = read_json(ROOT / "vendor/backend.json")
    validate_backend(settings)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {
        "config": config, "backend": settings, "environment": environment, "plan_sha256": sha256(plan),
    })
    # Share reservations with candidate confirmation so trial salts cannot be repurposed.
    reservations = ROOT / "runs/candidates"
    reservations.mkdir(parents=True, exist_ok=True)
    with record_lock(reservations):
        ledger_path = reservations / "development-salts.json"
        ledger = read_json(ledger_path) if ledger_path.exists() else {}
        confirmation = reservations / "confirmation-ledger.json"
        confirmed = {row["salt"] for row in read_json(confirmation)} if confirmation.exists() else set()
        if set(salts) & (set(ledger) | confirmed):
            raise ValueError("DQI development salt has already been reserved")
        ledger.update(dict.fromkeys(salts, sha256(registration)))
        write_json(ledger_path, ledger, replace=True)
    deadline = time.monotonic() + config["wall_seconds"]
    for index, trial in enumerate(trials):
        directory = output / f"trial-{index:02}"
        directory.mkdir()
        write_json(directory / "trial.json", trial)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            status = "skipped_budget"
        else:
            try:
                code = run_job([sys.executable, __file__, "worker", str(registration), str(directory)],
                               directory, remaining)
                status = "complete" if code == 0 else f"worker_exit_{code}"
            except subprocess.TimeoutExpired:
                status = "timeout"
        write_json(directory / "status.json", {"status": status})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    (run if args.action == "run" else matched_pair)(args.plan, args.output)


if __name__ == "__main__":
    main()
