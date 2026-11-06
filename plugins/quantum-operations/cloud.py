"""Previewable Google Cloud operations. Credentials stay in gcloud's own store."""

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from operations import command, config, linux_path


def identifier(value: str, name: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._@:-]{0,254}", value):
        raise ValueError(f"invalid or missing {name}")
    return value


def required(settings: dict[str, Any], name: str) -> str:
    return identifier(settings.get(name, ""), name)


def remote_root(settings: dict[str, Any]) -> str:
    value = settings.get("remote_root", "")
    if not value.startswith("/") or ".." in PurePosixPath(value).parts or "\x00" in value or value == "/":
        raise ValueError("remote_root must be an absolute Linux project directory")
    return value


def base(root: Path, settings: dict[str, Any]) -> list[str]:
    configured = settings.get("gcloud")
    if configured:
        return [configured]
    installed = shutil.which("gcloud")
    if installed:
        return [installed]
    local = root / "vendor/google-cloud-sdk/bin/gcloud"
    if local.exists():
        if os.name == "nt":
            return [
                "wsl.exe",
                "-d",
                settings.get("wsl_distribution") or "Ubuntu",
                "--exec",
                linux_path(local),
            ]
        return [str(local)]
    # A preview can still show what will be executed before installation.
    return ["gcloud"]


def invoke(root: Path, arguments: list[str], execute: bool, timeout: int = 120) -> dict[str, Any]:
    settings = config(root)
    argv = [*base(root, settings), "--quiet", "--project=" + required(settings, "project"), *arguments]
    if not execute:
        return {"status": "preview", "argv": argv}
    # No credentials are accepted as tool arguments or embedded in command lines.
    # gcloud login/ADC is performed by the user in the same OS runtime.
    completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    return {
        "status": "completed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-32768:],
        "stderr": completed.stderr[-8192:],
    }


def vm(root: Path, action: str, execute: bool = False, runtime_seconds: int = 3600) -> dict[str, Any]:
    settings = config(root)
    name, zone = required(settings, "vm"), required(settings, "zone")
    if action not in ("create", "describe", "start", "stop", "delete"):
        raise ValueError("unsupported VM action")
    args = ["compute", "instances", action, name, "--zone=" + zone]
    if action == "create":
        if type(runtime_seconds) is not int or not 60 <= runtime_seconds <= 86400:
            raise ValueError("VM runtime must lie in [60,86400] seconds")
        args += [
            "--machine-type=" + required(settings, "machine_type"),
            "--image-family=ubuntu-2404-lts-amd64",
            "--image-project=ubuntu-os-cloud",
            "--boot-disk-size=30GB",
            "--no-address",
            "--metadata=enable-oslogin=TRUE",
            "--service-account=" + required(settings, "service_account"),
            "--scopes=cloud-platform",
            f"--max-run-duration={runtime_seconds}s",
            "--instance-termination-action=STOP",
        ]
    args.append("--format=json")
    return invoke(root, args, execute, timeout=180)


def ssh(root: Path, remote_command: list[str], execute: bool = False) -> dict[str, Any]:
    settings = config(root)
    return invoke(
        root,
        [
            "compute",
            "ssh",
            required(settings, "vm"),
            "--zone=" + required(settings, "zone"),
            "--tunnel-through-iap",
            "--command=" + shlex.join(remote_command),
        ],
        execute,
    )


def remote_job(root: Path, action: str, arguments: list[str], execute: bool = False) -> dict[str, Any]:
    settings = config(root)
    location = remote_root(settings)
    worker = location + "/plugins/quantum-operations/worker.py"
    return ssh(
        root, [location + "/vendor/linux-env/bin/python", worker, action, location, *arguments], execute
    )


def bootstrap_script(
    settings: dict[str, Any], source_key: str, source_sha256: str, inputs_key: str, inputs_sha256: str
) -> str:
    for digest in (source_sha256, inputs_sha256):
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("archive SHA-256 required")
    return "\n".join(
        [
            "set -eu",
            "export QUANTUM_ROOT=" + shlex.quote(remote_root(settings)),
            "export QUANTUM_SOURCE_URI=" + shlex.quote(storage_uri(settings, source_key)),
            "export QUANTUM_SOURCE_SHA256=" + shlex.quote(source_sha256),
            "export QUANTUM_INPUTS_URI=" + shlex.quote(storage_uri(settings, inputs_key)),
            "export QUANTUM_INPUTS_SHA256=" + shlex.quote(inputs_sha256),
            Path(__file__).with_name("bootstrap.sh").read_text(encoding="utf-8"),
        ]
    )


def prepare_vm(
    root: Path,
    source_key: str,
    source_sha256: str,
    inputs_key: str,
    inputs_sha256: str,
    execute: bool = False,
) -> dict[str, Any]:
    script = bootstrap_script(config(root), source_key, source_sha256, inputs_key, inputs_sha256)
    return ssh(root, ["bash", "-c", script], execute)


def storage_uri(settings: dict[str, Any], key: str) -> str:
    bucket = required(settings, "bucket")
    prefix = settings.get("prefix") or "quantum"
    combined = PurePosixPath(prefix) / key
    if (
        not key
        or key.startswith("/")
        or ".." in combined.parts
        or re.search(r"[\x00-\x20*?\[\]#\\]", str(combined))
    ):
        raise ValueError("object key must be a literal relative path without traversal or wildcards")
    return f"gs://{bucket}/{combined}"


def transfer(root: Path, direction: str, local: str, key: str, execute: bool = False) -> dict[str, Any]:
    path = (root / local).resolve()
    if not path.is_relative_to(root) or not local.startswith(("runs/", "releases/", "vendor/")):
        raise ValueError("transfers must name a file under project runs/, releases/ or vendor/")
    if direction not in ("upload", "download"):
        raise ValueError("direction must be upload or download")
    if direction == "download" and path.exists():
        raise ValueError("download destination already exists")
    if direction == "upload" and not path.is_file():
        raise ValueError("upload source must be a file")
    settings = config(root)
    uri = storage_uri(settings, key)
    arguments = [linux_path(path) if base(root, settings)[0] == "wsl.exe" else str(path), uri]
    if direction == "download":
        arguments.reverse()
        if execute:
            path.parent.mkdir(parents=True, exist_ok=True)
    return invoke(root, ["storage", "cp", "--no-clobber", *arguments], execute, timeout=600)


def batch(
    root: Path, action: str, job_id: str, config_path: str = "", execute: bool = False
) -> dict[str, Any]:
    settings = config(root)
    identifier(job_id, "job ID")
    if action not in ("submit", "describe", "delete", "logs"):
        raise ValueError("unsupported Batch action")
    args = ["batch", "jobs", action, job_id, "--location=" + required(settings, "region")]
    if action == "submit":
        path = (root / config_path).resolve()
        if not path.is_relative_to(root / "runs") or not path.is_file():
            raise ValueError("Batch configuration must be a prepared file under runs/")
        contents = json.loads(path.read_text(encoding="utf-8"))
        if (
            not contents.get("taskGroups")
            or contents.get("logsPolicy", {}).get("destination") != "CLOUD_LOGGING"
        ):
            raise ValueError("Batch configuration requires taskGroups and CLOUD_LOGGING")
        value = linux_path(path) if base(root, settings)[0] == "wsl.exe" else str(path)
        args += ["--config=" + value]
    if action == "logs":
        # Batch logs are queried through Cloud Logging using the job resource UID.
        # job_id here is the UID obtained from describe, not the display job name.
        args = [
            "logging",
            "read",
            f'resource.type="batch_task" AND labels.job_uid="{job_id}"',
            "--limit=100",
            "--format=json",
        ]
    else:
        args.append("--format=json")
    return invoke(root, args, execute)


def prepare_batch(
    root: Path,
    job_id: str,
    operation: str,
    options: dict[str, Any],
    source_key: str,
    source_sha256: str,
    inputs_key: str,
    inputs_sha256: str,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Prepare an inspectable one-task job from immutable source and input archives."""
    settings = config(root)
    identifier(job_id, "job ID")
    if not 60 <= timeout_seconds <= 86400:
        raise ValueError("Batch timeout must lie in [60,86400]")
    location = remote_root(settings)
    argv = command(operation, options, location + "/vendor/linux-env/bin/python")
    script = "\n".join(
        [
            bootstrap_script(settings, source_key, source_sha256, inputs_key, inputs_sha256),
            # Upload receipts even when the delegated operation fails.
            "cd " + shlex.quote(location),
            "set +e",
            shlex.join(argv) + " > /tmp/quantum-stdout.log 2> /tmp/quantum-stderr.log",
            "code=$?",
            "set -e",
            "printf '%s\\n' \"$code\" > /tmp/quantum-exit-code.txt",
            "tar -czf /tmp/quantum-results.tar.gz --ignore-failed-read runs releases docs/evidence "
            "/tmp/quantum-stdout.log /tmp/quantum-stderr.log /tmp/quantum-exit-code.txt",
            "gcloud storage cp --no-clobber /tmp/quantum-results.tar.gz "
            + shlex.quote(storage_uri(settings, job_id + "/results.tar.gz")),
            'exit "$code"',
        ]
    )
    payload = {
        "taskGroups": [
            {
                "taskCount": 1,
                "parallelism": 1,
                "taskSpec": {
                    "runnables": [{"script": {"text": script}}],
                    "computeResource": {"cpuMilli": 2000, "memoryMib": 14336},
                    "maxRunDuration": str(timeout_seconds) + "s",
                },
            }
        ],
        "allocationPolicy": {
            "instances": [
                {
                    "policy": {
                        "machineType": required(settings, "machine_type"),
                        "provisioningModel": "STANDARD",
                    }
                }
            ],
            "serviceAccount": {"email": required(settings, "service_account")},
        },
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
    }
    directory = root / "runs/cloud-plans" / job_id
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "batch.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "prepared",
        "config_path": str(path),
        "script": script,
        "note": "Bootstrap verifies archive hashes; contract readiness is still enforced by qcompile.",
    }
