"""Narrow subprocess adapter to the acquired, hash-pinned metric notebook v10.

We call its real generate_standard_submission entry point. No guessed gate
counts, simulated acceptance, replacement verifier, or implicit remote upload.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .artifacts import hashes, validate_manifest
from .component_confirmations import CANDIDATE_PROFILE, candidate_coverage, has_full_hybrid_coverage
from .environment import capture
from .errors import BlockedError, ValidationError
from .io import identity, read_json, sha256, write_json
from .profiling import recorder

METRIC_V10_SHA256 = "df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73"
BACKEND_PATHS = ("metric_notebook", "verifiers_root", "kickmix_root", "project_root")


def review_verification_request(report: dict, path: Path) -> dict:
    """Recover an inventory from the exact request bound to a completed receipt."""
    if sha256(path) != report.get("request_hash"):
        raise ValidationError("verification request changed")
    request = read_json(path)
    backend = request["backend"]
    if (
        report.get("kind") != "official_metric_execution"
        or report.get("status") != "passed"
        or report.get("complete") is not True
        or report.get("backend_hash") != identity(backend)
        or report.get("role") != request["seed_policy"]["role"]
        or any(report.get(key) != request[key] for key in ("tier", "environment", "seed_policy", "contract_hash"))
        or report.get("artifact_hashes") != {name: item["sha256"] for name, item in request["artifacts"].items()}
    ):
        raise ValidationError("verification receipt differs from its request")
    return backend


def review_backend_pair(left_report: dict, left_request: Path, right_report: dict, right_request: Path) -> dict:
    """Compare inventories while preserving their individual receipt identities."""
    left = review_verification_request(left_report, left_request)
    right = review_verification_request(right_report, right_request)
    left_pins = {key: value for key, value in left.items() if key not in BACKEND_PATHS}
    right_pins = {key: value for key, value in right.items() if key not in BACKEND_PATHS}
    if left_pins != right_pins:
        raise ValidationError("verification inventories differ beyond paths")
    if (
        left_pins.get("metric_sha256") != METRIC_V10_SHA256
        or left_pins.get("metric_version") != 10
        or not left_pins.get("verifiers_files")
        or not left_pins.get("kickmix_files")
    ):
        raise ValidationError("verification inventories lack reviewed backend pins")
    return {
        "left_backend_hash": left_report["backend_hash"],
        "right_backend_hash": right_report["backend_hash"],
        "left_request_sha256": left_report["request_hash"],
        "right_request_sha256": right_report["request_hash"],
        "inventory_sha256": identity(left_pins),
        "path_changes": {
            key: {"left": left.get(key), "right": right.get(key)}
            for key in BACKEND_PATHS
            if left.get(key) != right.get(key)
        },
    }


def tree_manifest(root):
    root = Path(root)
    if not root.is_dir():
        raise BlockedError(f"official source directory unavailable: {root}")
    files = {}
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValidationError(f"linked backend source: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = sha256(path)
    if not files:
        raise BlockedError(f"official source directory is empty: {root}")
    return files


def validate_backend(config):
    metric = Path(config["metric_notebook"])
    if config.get("metric_sha256") != METRIC_V10_SHA256:
        raise BlockedError("metric is not the reviewed official v10 notebook hash")
    if not metric.is_file() or sha256(metric) != config.get("metric_sha256"):
        raise BlockedError("official metric notebook unavailable or hash mismatch")
    for role in ("verifiers", "kickmix"):
        observed = tree_manifest(config[role + "_root"])
        if observed != config.get(role + "_files"):
            raise BlockedError(f"{role} source inventory mismatch; reacquire or reconcile explicitly")
    if config.get("metric_version") != 10:
        raise BlockedError("adapter reviewed only for official metric notebook v10")


def verify_candidate(
    artifacts, contract, tier, seed_policy, backend, output_dir, *,
    timeout=86400, verification_profile=None,
):
    if tier not in ("smoke", "full") or seed_policy.get("role") not in (
        "development",
        "confirmation",
        "official_local",
    ):
        raise ValidationError("explicit verification tier and run role required")
    salt = seed_policy.get("salt")
    if not isinstance(salt, str) or len(salt) < 32 or not seed_policy.get("distribution"):
        raise ValidationError(
            "local seed policy requires a salt of >=32 characters and distribution description"
        )
    with recorder().stage("adapter_input_integrity", "hashing", benchmark="all"):
        validate_manifest(artifacts)
        validate_backend(backend)
        if verification_profile not in (None, CANDIDATE_PROFILE):
            raise ValidationError("unknown verification profile")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    environment = capture(Path(backend.get("project_root", Path(__file__).resolve().parents[2])))
    request = {
        "environment": environment,
        "artifacts": artifacts,
        "contract_hash": contract.hash,
        "tier": tier,
        "seed_policy": seed_policy,
        "backend": backend,
    }
    if verification_profile == CANDIDATE_PROFILE and tier == "full":
        request["expected_coverage"] = candidate_coverage(artifacts)
    write_json(output_dir / "request.json", request)
    started = time.monotonic()
    status, diagnostic = "incomplete", None
    with (output_dir / "stdout.log").open("w") as stdout, (output_dir / "stderr.log").open("w") as stderr:
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "qcompile.worker", str(output_dir / "request.json")],
                cwd=output_dir,
                stdout=stdout,
                stderr=stderr,
                start_new_session=os.name == "posix",
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                raise
            status = "passed" if process.returncode == 0 else "failed"
            diagnostic = f"worker exit code {process.returncode}"
        except subprocess.TimeoutExpired:
            diagnostic = "official verification timed out; incomplete evidence retained"
    worker_path = output_dir / "worker-result.json"
    worker = read_json(worker_path) if worker_path.is_file() else None
    # Recheck identities after execution to catch byte/source mutation during a run.
    with recorder().stage("adapter_final_integrity", "hashing", benchmark="all"):
        validate_manifest(artifacts)
        validate_backend(backend)
    complete = status == "passed" and worker is not None and worker.get("completed") is True
    if complete and "expected_coverage" in request and not has_full_hybrid_coverage(
        {"official_results": worker}, request["expected_coverage"]
    ):
        complete, status = False, "failed"
        diagnostic = "official worker returned incomplete or inconsistent candidate coverage"
    report = {
        "schema_version": 1,
        "kind": "official_metric_execution",
        "status": status,
        "complete": complete,
        "tier": tier,
        "role": seed_policy["role"],
        "artifact_hashes": hashes(artifacts),
        "contract_hash": contract.hash,
        "environment": environment,
        "backend_hash": identity(backend),
        "seed_policy": seed_policy,
        "request_hash": sha256(output_dir / "request.json"),
        "elapsed_seconds": time.monotonic() - started,
        "logs": {p.name: sha256(p) for p in (output_dir / "stdout.log", output_dir / "stderr.log")},
        "diagnostic": diagnostic,
        "official_results": worker,
        "coverage": "unmodified official verifier completed" if complete else "incomplete",
        "remote_accepted": False,
    }
    write_json(output_dir / "verification.json", report)
    return report
