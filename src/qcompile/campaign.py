"""Preregistered serial full-reference measurements and frozen comparison bundles."""

import csv
import importlib.metadata
import json
import math
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .artifacts import hashes, manifest, zip_info
from .contract import load_contract
from .environment import capture
from .errors import ValidationError
from .io import canonical_json, identity, read_json, sha256, write_json
from .official import validate_backend
from .profiling import ResourceSampler, terminate_tree

BENCHMARKS = ("invsqrt", "dqi", "dfthcsos")


def validate_campaign(config: dict[str, Any]) -> None:
    runs = config.get("runs", [])
    if (
        config.get("schema_version") != 1
        or not isinstance(runs, list)
        or len(runs) != 3
        or not all(isinstance(run, dict) for run in runs)
    ):
        raise ValidationError("baseline campaign requires schema 1 and exactly three A,A,B runs")
    ids = [run.get("id") for run in runs]
    salts = [run.get("salt") for run in runs]
    if ids != ["A1", "A2", "B1"] or not all(isinstance(salt, str) and len(salt) >= 32 for salt in salts):
        raise ValidationError("campaign requires A1,A2,B1 identifiers and explicit salts of >=32 characters")
    if salts[0] != salts[1] or salts[0] == salts[2] or config.get("seed_role") != "official_local":
        raise ValidationError("baseline salts must follow A,A,B and must never be confirmation data")
    for name in ("cpu_cores", "timeout_seconds_per_run"):
        if type(config.get(name)) is not int or config[name] <= 0:
            raise ValidationError(f"positive integer required: {name}")
    for name in ("planning_wall_multiplier", "planning_memory_multiplier", "planning_disk_multiplier"):
        value = config.get(name)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 1
        ):
            raise ValidationError(f"finite headroom multiplier >=1 required: {name}")
    interval = config.get("sample_interval_seconds")
    if not isinstance(interval, (int, float)) or isinstance(interval, bool) or not 0.05 <= interval <= 10:
        raise ValidationError("sample interval must lie in [0.05,10] seconds")
    if not config.get("version") or not config.get("cache_policy"):
        raise ValidationError("version and explicit cache policy required")


def disk_bytes(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def completed_stages(directory: Path) -> list[dict[str, Any]]:
    starts: dict[str, dict[str, Any]] = {}
    ends: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("events-*.jsonl")):
        for line in path.read_text().splitlines():
            event = json.loads(line)
            target = starts if event["event"] == "start" else ends
            if event["id"] in target:
                raise ValidationError("duplicate profile stage identity")
            target[event["id"]] = event
    if not starts or starts.keys() != ends.keys() or any(e["status"] != "passed" for e in ends.values()):
        raise ValidationError("stage records are incomplete or contain failed operations")
    categories = {event["category"] for event in ends.values()}
    if not {"parsing", "hashing", "simulation"} <= categories:
        raise ValidationError("required parsing/hashing/simulation profile stages are missing")
    timing_keys = ("wall_seconds_inclusive", "self_cpu_seconds", "waited_children_cpu_seconds")
    child_totals: dict[str, dict[str, float]] = {}
    for event in ends.values():
        parent_id = event["parent_id"]
        if parent_id is not None:
            parent = ends.get(parent_id)
            if (
                parent is None
                or not parent["start_ns"] <= event["start_ns"] <= event["end_ns"] <= parent["end_ns"]
            ):
                raise ValidationError("profile stage nesting is inconsistent")
            totals = child_totals.setdefault(parent_id, dict.fromkeys(timing_keys, 0.0))
            for key in timing_keys:
                totals[key] += event[key]
    for event in ends.values():
        for key in ("wall_seconds_inclusive", "self_cpu_seconds", "waited_children_cpu_seconds"):
            event[key.replace("_inclusive", "") + "_exclusive"] = max(
                0.0, event[key] - child_totals.get(event["id"], {}).get(key, 0.0)
            )
    return sorted(ends.values(), key=lambda event: event["start_ns"])


def validate_run(report: dict[str, Any], registration: dict[str, Any], salt: str) -> None:
    actual = report.get("official_results") or {}
    environment = report.get("environment") or {}
    if (
        set(registration["expected_coverage"]) != set(BENCHMARKS)
        or set(actual.get("raw_verifier_results", {})) != set(BENCHMARKS)
        or set(actual.get("costs", {})) != set(BENCHMARKS)
    ):
        raise ValidationError("full baseline requires all three official benchmarks")
    if not (
        report.get("complete") is True
        and report.get("status") == "passed"
        and report.get("tier") == "full"
        and actual.get("completed") is True
        and actual.get("verification_shot_divisor") == 1
    ):
        raise ValidationError("campaign requires complete full-strength actual metric execution")
    if (
        environment.get("dirty") is not False
        or environment.get("source_revision") != registration["source_revision"]
    ):
        raise ValidationError("verification did not execute the frozen clean source revision")
    if environment.get("dependency_lock_sha256") != registration["dependency_lock_sha256"]:
        raise ValidationError("verification dependency lock changed")
    if (
        report.get("artifact_hashes") != registration["artifact_hashes"]
        or report.get("backend_hash") != registration["backend_hash"]
    ):
        raise ValidationError("verification input/backend identities changed")
    if (
        report.get("contract_hash") != registration["contract_hash"]
        or report.get("seed_policy", {}).get("salt") != salt
        or report.get("role") != "official_local"
        or report.get("seed_policy", {}).get("role") != "official_local"
    ):
        raise ValidationError("verification contract or registered salt differs")
    for name, expected in registration["expected_coverage"].items():
        result = actual.get("raw_verifier_results", {}).get(name, {})
        if result.get("status") != "PASS" or result.get("verified_shots") != expected:
            raise ValidationError(f"incomplete original-reference coverage: {name}")
        cost = actual.get("costs", {}).get(name)
        if not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost <= 0:
            raise ValidationError(f"invalid actual reference cost: {name}")


def execute_run(
    root: Path, slot: dict[str, str], output: Path, config: dict[str, Any], registration: dict[str, Any]
) -> dict[str, Any]:
    profile_dir, verification_dir = output / "profile", output / "verification"
    output.mkdir(parents=True, exist_ok=False)
    seed = {
        "role": "official_local",
        "salt": slot["salt"],
        "distribution": "Unmodified pinned official verifier distribution; preregistered public baseline salt, not candidate confirmation.",
    }
    write_json(output / "seed.json", seed)
    environment = os.environ.copy()
    environment.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        NUMEXPR_NUM_THREADS="1",
        QCOMPILE_PROFILE_DIR=str(profile_dir),
    )
    environment.pop("PYTHONPATH", None)
    argv = [
        "taskset",
        "-c",
        ",".join(map(str, registration["cpu_affinity"])),
        sys.executable,
        "-u",
        "-m",
        "qcompile",
        "--root",
        str(root),
        "baseline",
        "verify",
        "--artifact-dir",
        registration["artifact_directory"],
        "--backend",
        registration["backend_path"],
        "--tier",
        "full",
        "--seed-policy",
        str(output / "seed.json"),
        "--timeout",
        str(config["timeout_seconds_per_run"]),
        "--output",
        str(verification_dir),
    ]
    write_json(output / "launch.json", {"argv": argv, "source_revision": registration["source_revision"]})
    before = os.times()
    started = time.monotonic()
    with (
        (output / "launch.stdout.log").open("wb") as stdout,
        (output / "launch.stderr.log").open("wb") as stderr,
    ):
        process = subprocess.Popen(
            argv, cwd=root, env=environment, stdout=stdout, stderr=stderr, start_new_session=True
        )
        write_json(
            output / "process.json",
            {
                "pid": process.pid,
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "argv": argv,
            },
        )
        sampler = ResourceSampler(process.pid, profile_dir, config["sample_interval_seconds"])
        sampler.start()
        try:
            try:
                process.wait(timeout=config["timeout_seconds_per_run"])
            except subprocess.TimeoutExpired:
                terminate_tree(process.pid)
                process.wait()
                raise ValidationError("baseline run timed out; incomplete evidence retained") from None
        except BaseException:
            if process.poll() is None:
                terminate_tree(process.pid)
                process.wait()
            raise
        finally:
            resources = sampler.stop()
    after = os.times()
    execution = {
        "elapsed_seconds": time.monotonic() - started,
        "cpu_seconds": after.children_user
        + after.children_system
        - before.children_user
        - before.children_system,
        "exit_code": process.returncode,
        "resources": resources,
    }
    write_json(output / "execution.json", execution)
    if process.returncode != 0 or not (verification_dir / "verification.json").is_file():
        raise ValidationError("baseline run stopped without successful complete evidence; see retained logs")
    report = read_json(verification_dir / "verification.json")
    validate_run(report, registration, slot["salt"])
    if resources["missing_memory_reads"] / max(1, resources["attempted_memory_reads"]) > 0.02:
        raise ValidationError("more than 2% of attempted process memory reads are missing")
    stages = completed_stages(profile_dir)
    write_json(output / "stages.json", stages)
    with (verification_dir / "submission.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    metric_seconds = {BENCHMARKS[int(row["row_id"])]: float(row["seconds"]) for row in rows}
    if (
        len(rows) != 3
        or set(metric_seconds) != set(BENCHMARKS)
        or any(not math.isfinite(value) or value <= 0 for value in metric_seconds.values())
    ):
        raise ValidationError("actual metric per-benchmark timings are missing or invalid")
    file_hashes = {
        path.relative_to(output).as_posix(): sha256(path) for path in output.rglob("*") if path.is_file()
    }
    if any(
        file_hashes.get("verification/submission/" + name) != expected
        for name, expected in registration["artifact_hashes"].items()
    ):
        raise ValidationError("the actual copied reference inputs differ from the registered originals")
    return {
        "id": slot["id"],
        "salt": slot["salt"],
        "execution": execution,
        "verification": report,
        "stages": stages,
        "metric_seconds": metric_seconds,
        "retained_disk_bytes": disk_bytes(output),
        "directory": str(output),
        "file_hashes": file_hashes,
    }


def normalize(
    metric: Path, costs: dict[str, float], baseline: dict[str, float], seconds: dict[str, float]
) -> dict[str, Any]:
    import pandas as pd

    notebook = read_json(metric)
    source = "\n\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    scope: dict[str, Any] = {"__name__": "qcompile_baseline_normalization"}
    exec(compile(source, str(metric), "exec"), scope)
    solution = pd.DataFrame(
        [
            {"row_id": i, "benchmark": name, "baseline_cost": baseline[name]}
            for i, name in enumerate(BENCHMARKS)
        ]
    )
    submission = pd.DataFrame(
        [{"row_id": i, "cost": costs[name], "seconds": seconds[name]} for i, name in enumerate(BENCHMARKS)]
    )
    score, details = scope["score"](solution, submission, "row_id")
    return {
        "score": score,
        "details": details,
        "scope": "exact official score function; local A1 reference costs, no private-split baseline",
    }


def analyze_runs(
    config: dict[str, Any], registration: dict[str, Any], runs: list[dict[str, Any]]
) -> dict[str, Any]:
    if [run["id"] for run in runs] != ["A1", "A2", "B1"]:
        raise ValidationError("all preregistered runs are required")
    costs = [run["verification"]["official_results"]["costs"] for run in runs]
    if costs[0] != costs[1]:
        raise ValidationError("same-salt original reference costs did not reproduce exactly")
    normalized = [
        normalize(Path(registration["metric_path"]), item, costs[0], run["metric_seconds"])
        for item, run in zip(costs, runs, strict=True)
    ]
    if normalized[0]["score"] != 1.0 or normalized[1]["score"] != 1.0:
        raise ValidationError("same-reference normalization control did not equal 1.0")
    variations = {}
    for name in BENCHMARKS:
        values = [item[name] for item in costs]
        variations[name] = {
            "min": min(values),
            "max": max(values),
            "relative_range": (max(values) - min(values)) / min(values),
        }
    wall = [run["execution"]["elapsed_seconds"] for run in runs]
    cpu = [run["execution"]["cpu_seconds"] for run in runs]
    pss = [run["execution"]["resources"]["peak_pss_bytes"] for run in runs]
    working_set = [run["execution"]["resources"]["peak_pss_plus_swap_bytes"] for run in runs]
    total_cpu = [
        run["execution"]["cpu_seconds"] + run["execution"]["resources"]["profiler_cpu_seconds"]
        for run in runs
    ]
    retained = [run["retained_disk_bytes"] for run in runs]
    throughput = {}
    for run in runs:
        throughput[run["id"]] = {}
        for name in BENCHMARKS:
            simulation_seconds = sum(
                event["wall_seconds_exclusive"]
                for event in run["stages"]
                if event["category"] == "simulation" and event.get("benchmark") == name
            )
            throughput[run["id"]][name] = {
                "simulation_and_checks_seconds": simulation_seconds,
                "verified_shots_per_second": registration["expected_coverage"][name] / simulation_seconds,
            }
    return {
        "same_salt_costs_identical": True,
        "normalization": normalized,
        "cost_observed_ranges": variations,
        "wall_observed_seconds": {"min": min(wall), "max": max(wall)},
        "cpu_observed_seconds": {"min": min(cpu), "max": max(cpu)},
        "sampled_pss_observed_bytes": {"min": min(pss), "max": max(pss)},
        "throughput": throughput,
        "planning_budget": {
            "wall_seconds_per_full_run": math.ceil(max(wall) * config["planning_wall_multiplier"]),
            "cpu_seconds_per_full_run": math.ceil(max(total_cpu) * config["planning_wall_multiplier"]),
            "memory_reservation_bytes": math.ceil(max(working_set) * config["planning_memory_multiplier"]),
            "disk_bytes_per_retained_run": math.ceil(max(retained) * config["planning_disk_multiplier"]),
            "cpu_cores": config["cpu_cores"],
            "policy": "observed maxima times preregistered headroom; not official limits, measured minima, or statistical quantiles",
        },
        "scope": "three serial observations; order/cache effects are recorded, not controlled; sampled memory can miss short peaks",
    }


def run_campaign(root: Path, config: dict[str, Any], output: Path) -> dict[str, Any]:
    validate_campaign(config)
    if not sys.platform.startswith("linux"):
        raise ValidationError("baseline campaigns require Linux")
    root, output = root.resolve(), output.resolve()
    environment = capture(root)
    if environment["dirty"] is not False or not environment["source_revision"]:
        raise ValidationError("baseline campaign requires a clean committed checkout")
    if not Path(__file__).resolve().is_relative_to(root):
        raise ValidationError("campaign module was not imported from the selected clean source checkout")
    contract = load_contract(root / "contracts/contract.json")
    contract.require_ready(root)
    assets = Path(config["assets_root"]).resolve()
    backend_path = assets / "backend.json"
    backend = read_json(backend_path)
    validate_backend(backend)
    artifact_dir = (assets / "official/sample_submission").resolve()
    artifacts = manifest(
        artifact_dir,
        origin="retained_reference",
        provenance="original archive; accepted full-strength step-1 baseline",
    )
    archive = read_json(assets / "acquisition-checks.json")
    if any(
        archive["files"]["sample_submission/" + name]["sha256"] != item["sha256"]
        for name, item in artifacts.items()
    ):
        raise ValidationError("reference bytes differ from the original archive")
    affinity = sorted(os.sched_getaffinity(0))[: config["cpu_cores"]]
    if len(affinity) != config["cpu_cores"]:
        raise ValidationError("requested CPU affinity is unavailable")
    input_bytes = sum(Path(item["path"]).stat().st_size for item in artifacts.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    disk = shutil.disk_usage(output.parent)
    if disk.free < input_bytes * len(config["runs"]) * 1.25 + (512 << 20):
        raise ValidationError("insufficient free space for the preregistered retained runs")
    registration = {
        "schema_version": 1,
        "config": config,
        "config_hash": identity(config),
        "source_revision": environment["source_revision"],
        "source_tree": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD:"], text=True
        ).strip(),
        "dependency_lock_sha256": environment["dependency_lock_sha256"],
        "environment": environment,
        "contract_hash": contract.hash,
        "backend_hash": identity(backend),
        "backend_path": str(backend_path),
        "metric_path": backend["metric_notebook"],
        "artifact_directory": str(artifact_dir),
        "artifact_hashes": hashes(artifacts),
        "reference_archive_sha256": archive["archive_sha256"],
        "expected_coverage": contract.data["fields"]["release.coverage"]["value"],
        "cpu_affinity": affinity,
        "input_artifact_bytes": input_bytes,
        "disk_start": {"free_bytes": disk.free, "total_bytes": disk.total},
        "host_meminfo": Path("/proc/meminfo").read_text(),
        "host_cpuinfo_first_processor": Path("/proc/cpuinfo").read_text().split("\n\n", 1)[0],
        "source_root": str(root),
        "packages": dict(
            sorted(
                (distribution.metadata["Name"], distribution.version)
                for distribution in importlib.metadata.distributions()
            )
        ),
    }
    output.mkdir(exist_ok=False)
    write_json(output / "registration.json", registration)
    subprocess.run(
        ["git", "-C", str(root), "bundle", "create", str(output / "source.bundle"), "--all"], check=True
    )
    runs = []
    try:
        for slot in config["runs"]:
            write_json(
                output / "progress.json",
                {
                    "status": "running",
                    "campaign_pid": os.getpid(),
                    "slot": slot["id"],
                    "completed": [run["id"] for run in runs],
                },
                replace=True,
            )
            print(f"baseline campaign starting {slot['id']}", flush=True)
            result = execute_run(root, slot, output / slot["id"], config, registration)
            runs.append(result)
            print(f"baseline campaign completed {slot['id']}", flush=True)
        final_environment = capture(root)
        if (
            final_environment["dirty"] is not False
            or final_environment["source_revision"] != registration["source_revision"]
            or final_environment["dependency_lock_sha256"] != registration["dependency_lock_sha256"]
        ):
            raise ValidationError("source checkout changed during baseline execution")
        analysis = analyze_runs(config, registration, runs)
        report = {
            "status": "passed",
            "complete": True,
            "version": config["version"],
            "registration_hash": identity(registration),
            "registration": registration,
            "analysis": analysis,
            "runs": runs,
            "source_bundle_sha256": sha256(output / "source.bundle"),
        }
        write_json(output / "campaign.json", report)
        write_json(
            output / "progress.json",
            {"status": "passed", "completed": [run["id"] for run in runs]},
            replace=True,
        )
        return {"status": "passed", "campaign": str(output / "campaign.json"), "version": config["version"]}
    except BaseException as error:
        write_json(
            output / "failure.json",
            {"status": "incomplete", "error": repr(error), "completed": [run["id"] for run in runs]},
        )
        write_json(
            output / "progress.json",
            {"status": "incomplete", "completed": [run["id"] for run in runs]},
            replace=True,
        )
        raise


def safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or "\\" in name or ":" in name or ".." in path.parts or str(path) != name:
        raise ValidationError(f"unsafe baseline bundle member: {name}")


def verify_bundle(path: Path) -> dict[str, Any]:
    import hashlib

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValidationError("duplicate baseline bundle member")
        for name in names:
            safe_member(name)
        manifest_data = json.loads(archive.read("baseline-manifest.json"))
        if set(names) != set(manifest_data["members"]) | {"baseline-manifest.json"}:
            raise ValidationError("baseline bundle members differ from the frozen manifest")
        for name, expected in manifest_data["members"].items():
            digest = hashlib.sha256()
            with archive.open(name) as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
            actual = digest.hexdigest()
            if actual != expected:
                raise ValidationError(f"baseline bundle member changed: {name}")
    return manifest_data


def freeze_campaign(campaign_directory: Path, output: Path) -> dict[str, Any]:
    campaign_directory, output = campaign_directory.resolve(), output.resolve()
    if output.is_relative_to(campaign_directory):
        raise ValidationError("baseline bundle output must be outside its immutable campaign inputs")
    report = read_json(campaign_directory / "campaign.json")
    if (
        report.get("status") != "passed"
        or report.get("complete") is not True
        or len(report.get("runs", [])) != 3
    ):
        raise ValidationError("only a completed three-run full baseline can be frozen")
    registration = report["registration"]
    if identity(registration) != report["registration_hash"]:
        raise ValidationError("campaign registration changed")
    if identity(read_json(campaign_directory / "registration.json")) != report["registration_hash"]:
        raise ValidationError("original registration record changed")
    if sha256(campaign_directory / "source.bundle") != report["source_bundle_sha256"]:
        raise ValidationError("committed source bundle changed")
    for run in report["runs"]:
        directory = campaign_directory / run["id"]
        actual = {
            path.relative_to(directory).as_posix(): sha256(path)
            for path in directory.rglob("*")
            if path.is_file()
        }
        if actual != run["file_hashes"]:
            raise ValidationError(f"raw baseline run records changed before freeze: {run['id']}")
        validate_run(read_json(directory / "verification/verification.json"), registration, run["salt"])
    files = {
        "campaign/" + name: campaign_directory / name
        for name in ("campaign.json", "registration.json", "source.bundle", "progress.json")
    }
    for run in report["runs"]:
        for name in run["file_hashes"]:
            if not name.startswith("verification/submission/"):
                files[f"campaign/{run['id']}/{name}"] = campaign_directory / run["id"] / name
    root = Path(registration["source_root"])
    assets = Path(registration["config"]["assets_root"])
    original_archive = assets / "competition_data.zip"
    if sha256(original_archive) != registration["reference_archive_sha256"]:
        raise ValidationError("original competition archive changed")
    files["inputs/competition_data.zip"] = original_archive
    contract = load_contract(root / "contracts/contract.json")
    contract.require_ready(root)
    if contract.hash != registration["contract_hash"]:
        raise ValidationError("source contract changed before baseline freeze")
    vendor_paths = set()
    for record in contract.data["sources"].values():
        vendor_paths.add(record["path"])
    for field in contract.data["fields"].values():
        vendor_paths.add(field["official"]["path"])
        vendor_paths.update(item["path"] for item in field.get("supplementary_official", []))
    for name in vendor_paths:
        if (
            name.startswith("vendor/")
            and not name.startswith("vendor/official/")
            and name != "vendor/competition_data.zip"
        ):
            safe_member(name)
            files["inputs/" + name] = root / name
    for name in files:
        safe_member(name)
    frozen = {
        "kind": "baseline_reproduction_bundle",
        "version": report["version"],
        "source_revision": registration["source_revision"],
        "source_tree": registration["source_tree"],
        "contract_hash": registration["contract_hash"],
        "members": {name: sha256(path) for name, path in sorted(files.items())},
        "reference_copies": "Per-run verification/submission input copies are omitted; exact bytes occur once in inputs/competition_data.zip and their per-run hashes remain in campaign.json.",
        "relocation": "clone campaign/source.bundle; restore original competition archive and inputs/vendor aliases; uv sync --frozen --python 3.13. Absolute backend paths are recorded, not silently portable: relocation requires a new backend inventory/contract review and preserves original evidence.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    restore = output.parent / (output.stem + "-source-restore-check")
    subprocess.run(
        ["git", "clone", "--no-checkout", str(campaign_directory / "source.bundle"), str(restore)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(restore), "checkout", "--detach", registration["source_revision"]],
        check=True,
        capture_output=True,
    )
    restored_tree = subprocess.check_output(
        ["git", "-C", str(restore), "rev-parse", "HEAD:"], text=True
    ).strip()
    if restored_tree != registration["source_tree"] or subprocess.check_output(
        ["git", "-C", str(restore), "status", "--porcelain"]
    ):
        raise ValidationError("source bundle did not restore the frozen clean source tree")
    second = output.with_name(output.stem + "-independent" + output.suffix)
    for target in (output, second):
        with zipfile.ZipFile(target, "x", allowZip64=True) as archive:
            archive.writestr(zip_info("baseline-manifest.json"), canonical_json(frozen))
            for name, source in sorted(files.items()):
                with (
                    source.open("rb") as stream,
                    archive.open(zip_info(name), "w", force_zip64=True) as destination,
                ):
                    shutil.copyfileobj(stream, destination, 1 << 20)
    if sha256(output) != sha256(second):
        raise ValidationError("independent baseline bundle bytes differ")
    verify_bundle(output)
    verify_bundle(second)
    result = {
        "status": "frozen",
        "version": report["version"],
        "bundle": str(output),
        "sha256": sha256(output),
        "bytes": output.stat().st_size,
        "members": len(files) + 1,
        "independent_build_identical": True,
        "verified_all_members": True,
        "clean_source_restore_verified": True,
    }
    write_json(output.with_suffix(".receipt.json"), result)
    return result
