"""Supervise bounded batches of a validated chemistry fit-grid manifest."""

import argparse
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from chem_fit_grid import SHAPES
from chem_fit_grid import manifest as regenerate_manifest

from qcompile.experiments import record_lock
from qcompile.io import read_json, sha256, write_json
from qcompile.profiling import ResourceSampler, terminate_tree

ROOT = Path(__file__).resolve().parents[1]
THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
ID = re.compile(r"r(?:9-b143|9-b129|10-b129|8-b120)-c40-i[123]-(?:184|185)\Z")


def source_hashes() -> dict[str, str]:
    paths = (Path(__file__).resolve(), ROOT / "tools/chem_fit_grid.py", ROOT / "tools/chem_shape_search.py",
             ROOT / "tools/chem_refit.py", ROOT / "tools/banked_chemistry.py",
             ROOT / "src/qcompile/chemistry/factorization.py", ROOT / "src/qcompile/chemistry/refit.py",
             ROOT / "src/qcompile/chemistry/representation.py", ROOT / "src/qcompile/chemistry/schema.py",
             ROOT / "src/qcompile/profiling.py", ROOT / "src/qcompile/experiments.py",
             ROOT / "src/qcompile/io.py", ROOT / "src/qcompile/artifacts.py",
             ROOT / "vendor/backend.json", ROOT / "uv.lock")
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def validated_manifest(config: dict) -> tuple[dict, dict[str, Path]]:
    """Rebuild the 24-lane manifest and authenticate each supplied plan."""
    for name in ("manifest", "manifest_plan"):
        if sha256(Path(config[name]["path"])) != config[name]["sha256"]:
            raise ValueError(f"registered {name} hash differs")
    manifest_path = Path(config["manifest"]["path"])
    plan_path = Path(config["manifest_plan"]["path"])
    report = read_json(manifest_path)
    if report["plan_sha256"] != config["manifest_plan"]["sha256"]:
        raise ValueError("manifest does not bind the registered plan")
    with tempfile.TemporaryDirectory(prefix="chem-grid-verify-") as temporary:
        rebuilt = Path(temporary) / "manifest"
        regenerate_manifest(plan_path, rebuilt)
        if sha256(rebuilt / "manifest.json") != config["manifest"]["sha256"]:
            raise ValueError("manifest cannot be reproduced from the pinned profiles and rankings")
    lanes = report["lanes"]
    expected = {f"r{r}-b{b}-c{c}-{initial.lower()}-{seed}"
                for r, b, c in SHAPES for initial in ("I1", "I2", "I3") for seed in (184, 185)}
    if len(lanes) != 24 or {lane["id"] for lane in lanes} != expected or not all(lane["ready"] for lane in lanes):
        raise ValueError("manifest is not the complete ready 24-lane grid")
    directory = Path(config["lane_plan_directory"])
    plans = {}
    for lane in lanes:
        name = lane["id"]
        if not ID.fullmatch(name):
            raise ValueError("invalid lane identifier")
        path = directory / f"{name}.json"
        if sha256(path) != lane["plan_sha256"]:
            raise ValueError(f"registered lane plan differs: {name}")
        plans[name] = path
    selected = config["lanes"]
    if (not isinstance(selected, list) or not selected or len(selected) != len(set(selected))
            or any(name not in plans for name in selected)):
        raise ValueError("selected lanes must be distinct registered IDs")
    limits = config["limits"]
    if (type(limits["max_workers"]) is not int or not 1 <= limits["max_workers"] <= 4
            or type(limits["max_lanes_per_session"]) is not int
            or not 1 <= limits["max_lanes_per_session"] <= len(selected)
            or type(limits["worker_seconds"]) not in (int, float) or not 0 < limits["worker_seconds"] <= 86400
            or type(limits["session_seconds"]) not in (int, float) or not 0 < limits["session_seconds"] <= 86400):
        raise ValueError("invalid bounded grid execution limits")
    return report, plans


def files_in_attempt(directory: Path) -> dict[str, str]:
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("attempt contains a symbolic link")
        if path.is_file() and path != directory / "terminal.json":
            result[path.relative_to(directory).as_posix()] = sha256(path)
    return result


def check_fit(directory: Path, plan_hash: str, pins: dict[str, str]) -> dict[str, Any]:
    fit = directory / "fit"
    registration = read_json(fit / "registration.json")
    decision = read_json(fit / "decision.json")
    if (registration["plan_sha256"] != plan_hash
            or registration["runner_sha256"] != pins["tools/chem_shape_search.py"]
            or registration["factorization_module_sha256"] != pins["src/qcompile/chemistry/factorization.py"]
            or decision.get("status") not in ("go", "budget_limited", "no_go", "inconclusive")
            or type(decision.get("evaluations")) is not int or decision["evaluations"] < 1):
        raise ValueError("worker registration or terminal decision is incomplete")
    number = decision["evaluations"]
    receipt = read_json(fit / f"checkpoint-{number:05}.json")
    checkpoint = fit / f"continuous-{number:05}.npz"
    if (receipt["evaluations"] != number or receipt["continuous_sha256"] != sha256(checkpoint)
            or not math.isclose(receipt["continuous_residual"], decision["best_continuous_residual"],
                                rel_tol=1e-10, abs_tol=1e-12)):
        raise ValueError("worker terminal checkpoint does not match its decision")
    return decision


def completed_attempts(root: Path, plans: dict[str, Path], pins: dict[str, str]) -> dict[str, str]:
    completed = {}
    lanes = root / "lanes"
    if not lanes.exists():
        return completed
    for lane in lanes.iterdir():
        if lane.is_symlink() or not lane.is_dir() or lane.name not in plans:
            raise ValueError("unexpected lane path in result store")
        for attempt in sorted(lane.iterdir()):
            if attempt.is_symlink() or not attempt.is_dir() or not re.fullmatch(r"attempt-[0-9]{4}", attempt.name):
                raise ValueError("unexpected attempt path in result store")
            terminal_path = attempt / "terminal.json"
            if not terminal_path.exists():
                continue
            terminal = read_json(terminal_path)
            if terminal.get("status") != "complete":
                continue
            if (terminal["plan_sha256"] != sha256(plans[lane.name])
                    or terminal["source_hashes"] != pins or terminal["hashes"] != files_in_attempt(attempt)):
                raise ValueError(f"completed lane evidence changed: {lane.name}")
            check_fit(attempt, terminal["plan_sha256"], pins)
            if lane.name in completed:
                raise ValueError(f"multiple completed attempts for {lane.name}")
            completed[lane.name] = attempt.relative_to(root).as_posix()
    return completed


def worker_command(plan: Path, output: Path) -> list[str]:
    return [sys.executable, str(ROOT / "tools/chem_shape_search.py"), "fit", str(plan), str(output)]


def execute(config_path: Path, root: Path, *, resume: bool = False) -> dict[str, Any]:
    config = read_json(config_path)
    report, plans = validated_manifest(config)
    config_hash, pins = sha256(config_path), source_hashes()
    plan_hashes = {lane["id"]: lane["plan_sha256"] for lane in report["lanes"]}
    if resume:
        registration = read_json(root / "registration.json")
        if registration["config_sha256"] != config_hash or registration["source_hashes"] != pins:
            raise ValueError("resume configuration or sources changed")
    else:
        root.mkdir(parents=True, exist_ok=False)
        write_json(root / "registration.json", {"config": config, "config_sha256": config_hash,
                                                  "source_hashes": pins, "scope": "bounded grid supervisor"})
    with record_lock(root):
        return execute_session(config_path, root, config, plans, plan_hashes, config_hash, pins)


def execute_session(config_path: Path, root: Path, config: dict, plans: dict[str, Path],
                    plan_hashes: dict[str, str], config_hash: str, pins: dict[str, str]) -> dict[str, Any]:
    completed = completed_attempts(root, plans, pins)
    limits = config["limits"]
    pending = [name for name in config["lanes"] if name not in completed][:limits["max_lanes_per_session"]]
    sessions = root / "sessions"
    sessions.mkdir(exist_ok=True)
    serial = len(list(sessions.glob("session-*.json"))) + 1
    session_path = sessions / f"session-{serial:04}.json"
    deadline = time.monotonic() + limits["session_seconds"]
    active: dict[str, dict[str, Any]] = {}
    results = []
    interrupted = False
    next_audit = 0.0
    peak_workers = 0

    def interrupt(_signal, _frame):
        raise KeyboardInterrupt

    previous_handler = signal.signal(signal.SIGTERM, interrupt)
    try:
        while pending or active:
            if time.monotonic() >= next_audit:
                if sha256(config_path) != config_hash or source_hashes() != pins:
                    raise ValueError("grid configuration or source changed during execution")
                next_audit = time.monotonic() + 5
            while pending and len(active) < limits["max_workers"] and time.monotonic() < deadline:
                name = pending.pop(0)
                lane_root = root / "lanes" / name
                lane_root.mkdir(parents=True, exist_ok=True)
                existing = sorted(lane_root.glob("attempt-*"))
                number = max((int(path.name.removeprefix("attempt-")) for path in existing), default=0) + 1
                attempt = lane_root / f"attempt-{number:04}"
                attempt.mkdir()
                plan_hash = sha256(plans[name])
                if plan_hash != plan_hashes[name]:
                    raise ValueError(f"registered lane plan changed: {name}")
                timeout = min(float(limits["worker_seconds"]), float(read_json(plans[name])["wall_seconds"]),
                              max(0.0, deadline - time.monotonic()))
                write_json(attempt / "attempt.json", {"lane": name, "plan_sha256": plan_hash,
                                                       "timeout_seconds": timeout, "source_hashes": pins,
                                                       "blas_threads": 1, "started_unix": time.time()})
                log = (attempt / "execution.log").open("xb")
                env = {**os.environ, **dict.fromkeys(THREADS, "1")}
                worker_started = time.monotonic()
                try:
                    process = subprocess.Popen(worker_command(plans[name], attempt / "fit"), stdout=log,
                                               stderr=subprocess.STDOUT, env=env)
                except OSError as error:
                    log.close()
                    write_json(attempt / "terminal.json", {
                        "lane": name, "status": "launch_failed", "error": str(error),
                        "plan_sha256": plan_hash, "source_hashes": pins, "hashes": files_in_attempt(attempt),
                    })
                    results.append({"lane": name, "attempt": attempt.relative_to(root).as_posix(),
                                    "status": "launch_failed"})
                    continue
                try:
                    sampler = ResourceSampler(process.pid, attempt, interval=1)
                    sampler.start()
                except BaseException:
                    terminate_tree(process.pid)
                    process.wait()
                    log.close()
                    raise
                active[name] = {"process": process, "sampler": sampler, "log": log, "attempt": attempt,
                                "deadline": worker_started + timeout, "started": worker_started,
                                "plan_sha256": plan_hash}
                peak_workers = max(peak_workers, len(active))
            for name, item in list(active.items()):
                process = item["process"]
                expired = time.monotonic() >= item["deadline"]
                if process.poll() is None and not expired:
                    continue
                if process.poll() is None:
                    terminate_tree(process.pid)
                code = process.wait()
                item["sampler"].stop()
                item["log"].close()
                status = "timeout" if expired else "complete" if code == 0 else "worker_failed"
                decision = None
                if status == "complete":
                    try:
                        if sha256(config_path) != config_hash or source_hashes() != pins:
                            raise ValueError("grid configuration or source changed")
                        validated_manifest(config)
                        decision = check_fit(item["attempt"], item["plan_sha256"], pins)
                    except (OSError, KeyError, TypeError, ValueError) as error:
                        status = "invalid_receipt"
                        decision = {"error": str(error)}
                terminal = {"lane": name, "status": status, "exit_code": code, "decision": decision,
                            "plan_sha256": item["plan_sha256"], "source_hashes": pins,
                            "elapsed_seconds": time.monotonic() - item["started"],
                            "hashes": files_in_attempt(item["attempt"]),
                            "scope": "execution receipt; scientific result remains in fit/decision.json"}
                write_json(item["attempt"] / "terminal.json", terminal)
                results.append({"lane": name, "attempt": item["attempt"].relative_to(root).as_posix(), "status": status})
                del active[name]
            if time.monotonic() >= deadline and not active:
                break
            if active:
                time.sleep(0.2)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        for name, item in active.items():
            process = item["process"]
            if process.poll() is None:
                terminate_tree(process.pid)
            code = process.wait()
            item["sampler"].stop()
            item["log"].close()
            write_json(item["attempt"] / "terminal.json", {
                "lane": name, "status": "interrupted", "exit_code": code,
                "plan_sha256": item["plan_sha256"], "source_hashes": pins,
                "elapsed_seconds": time.monotonic() - item["started"],
                "hashes": files_in_attempt(item["attempt"]), "scope": "interrupted execution; no scientific claim",
            })
            results.append({"lane": name, "attempt": item["attempt"].relative_to(root).as_posix(),
                            "status": "interrupted"})
        signal.signal(signal.SIGTERM, previous_handler)
    status = ("interrupted" if interrupted else "budget_limited" if pending else
              "partial_failure" if any(row["status"] != "complete" for row in results) else "complete")
    newly_completed = {row["lane"] for row in results if row["status"] == "complete"}
    remaining = [name for name in config["lanes"] if name not in completed and name not in newly_completed]
    summary = {"status": status, "results": results, "peak_workers": peak_workers,
               "previously_completed": completed, "not_launched": pending, "remaining_lanes": remaining,
               "scope": "session execution status; no aggregate chemistry acceptance"}
    write_json(session_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("dry-run", "run", "resume"))
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    config = read_json(args.config)
    if args.action == "dry-run":
        _, plans = validated_manifest(config)
        completed = {}
        if args.output is not None:
            registration = read_json(args.output / "registration.json")
            pins = source_hashes()
            if registration["config_sha256"] != sha256(args.config) or registration["source_hashes"] != pins:
                raise ValueError("dry-run resume configuration or sources changed")
            completed = completed_attempts(args.output, plans, pins)
        pending = [name for name in config["lanes"] if name not in completed]
        for name in pending[:config["limits"]["max_lanes_per_session"]]:
            print(f"{name} {plans[name]}")
        return
    if args.output is None:
        parser.error("run and resume require a result directory")
    summary = execute(args.config, args.output, resume=args.action == "resume")
    if summary["status"] != "complete" or any(row["status"] != "complete" for row in summary["results"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
