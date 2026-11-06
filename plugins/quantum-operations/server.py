"""Codex-facing MCP bridge. Project processes use their own frozen environment."""

import json
import os
import shutil
import subprocess
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

import cloud
import staging
from operations import (
    OPERATIONS,
    bounded_read,
    command,
    config,
    project_root,
    run_json,
    worker_command,
)

mcp = FastMCP("quantum-operations")
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
CLOUD = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)


@mcp.tool(annotations=READ)
def project_catalog() -> dict[str, Any]:
    """List all CLI actions, differential controls and quality checks with required/optional options."""
    return {
        name: {"required": required, "optional": optional}
        for name, (required, optional) in OPERATIONS.items()
    }


@mcp.tool(annotations=READ)
def project_status(root: str) -> dict[str, Any]:
    """Inspect source identity, available runtime and missing cloud settings; never return credentials."""
    path = project_root(root)
    settings = config(path)
    git = subprocess.run(["git", "status", "--short"], cwd=path, capture_output=True, text=True)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True)
    executable = path / (settings.get("python") or "vendor/linux-env/bin/python")
    return {
        "root": str(path),
        "revision": revision.stdout.strip(),
        "git_status": git.stdout,
        "git_exit_code": git.returncode,
        "project_python_exists": executable.is_file(),
        "runtime": "WSL Linux" if os.name == "nt" else "Linux",
        "uv_available": shutil.which("uv") is not None,
        "gcloud_command": cloud.base(path, settings),
        "cloud_missing": [
            name
            for name in ("project", "region", "zone", "vm", "service_account", "bucket")
            if not settings.get(name)
        ],
        "credentials": "User-managed gcloud login; no token read or returned.",
        "memory_guidance": "Full native runs: measured workload reserve 11.17 GiB plus OS; start with 16 GB x86.",
    }


@mcp.tool(annotations=WRITE)
def project_run(
    root: str,
    operation: str,
    options: dict[str, Any] | None = None,
    timeout_seconds: int = 3600,
    execute: bool = False,
) -> dict[str, Any]:
    """Preview or start a durable Linux job. Use catalog options. Poll the returned ID; don't restart on timeout.

    Existing qcompile gates remain authoritative. Step-3 scripts write their existing
    evidence paths: use a separate committed checkout when retaining another campaign.
    """
    path = project_root(root)
    values = options or {}
    argv = command(operation, values)
    if not execute:
        return {
            "status": "preview",
            "operation": operation,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
            "runtime": worker_command(path, "start", []),
        }
    return run_json(
        worker_command(path, "start", [operation, json.dumps(values), str(timeout_seconds)]), path
    )


@mcp.tool(annotations=READ)
def project_job_status(root: str, job_id: str) -> dict[str, Any]:
    """Check the live supervisor identity or retained terminal receipt for an existing job."""
    path = project_root(root)
    return run_json(worker_command(path, "status", [job_id]), path)


@mcp.tool(annotations=READ)
def project_job_logs(
    root: str,
    job_id: str,
    stream: Literal["stdout", "stderr", "launcher"] = "stdout",
    offset: int = 0,
    limit: int = 16384,
) -> dict[str, Any]:
    """Read a bounded byte page from one job log. Continue at next_offset."""
    path = project_root(root)
    return run_json(worker_command(path, "logs", [job_id, stream, str(offset), str(limit)]), path)


@mcp.tool(annotations=WRITE)
def project_job_cancel(root: str, job_id: str) -> dict[str, Any]:
    """Request cancellation of an identity-verified supervisor and its experiment process group."""
    path = project_root(root)
    return run_json(worker_command(path, "cancel", [job_id]), path)


@mcp.tool(annotations=READ)
def project_evidence(root: str, relative_path: str, offset: int = 0, limit: int = 16384) -> dict[str, Any]:
    """Read a bounded evidence/log page from docs/evidence, runs or releases, excluding account config."""
    path = project_root(root)
    target = (path / relative_path).resolve()
    if not any(target.is_relative_to(path / part) for part in ("docs/evidence", "runs", "releases")):
        raise ValueError("only evidence, run and release files may be read")
    if target.suffix not in (".json", ".jsonl", ".log", ".xml", ".md", ".txt"):
        raise ValueError("unsupported evidence file type")
    return bounded_read(target, offset, limit)


@mcp.tool(annotations=CLOUD)
def cloud_vm(
    root: str,
    action: Literal["create", "describe", "start", "stop", "delete"],
    execute: bool = False,
    runtime_seconds: int = 3600,
) -> dict[str, Any]:
    """Preview/manage the configured Google VM. Creation is billed, x86, no external IP, with a runtime limit."""
    return cloud.vm(project_root(root), action, execute, runtime_seconds)


@mcp.tool(annotations=CLOUD)
def cloud_vm_prepare(
    root: str, source_key: str, source_sha256: str, inputs_key: str, inputs_sha256: str, execute: bool = False
) -> dict[str, Any]:
    """Bootstrap a fresh VM directory from hash-verified uploaded archives and the frozen dependency lock."""
    return cloud.prepare_vm(project_root(root), source_key, source_sha256, inputs_key, inputs_sha256, execute)


@mcp.tool(annotations=WRITE)
def cloud_snapshot(root: str, snapshot_id: str, additional_inputs: list[str] | None = None) -> dict[str, Any]:
    """Package a clean committed source Git bundle and selected pinned inputs, retaining hashes. No upload."""
    return staging.snapshot(project_root(root), snapshot_id, additional_inputs)


@mcp.tool(annotations=WRITE)
def cloud_relocation_plan(root: str, destination: str, plan_id: str) -> dict[str, Any]:
    """Prepare backend/contract path changes for review. Does not modify pins or close any gate."""
    return staging.relocation_plan(project_root(root), destination, plan_id)


@mcp.tool(annotations=CLOUD)
def cloud_project_run(
    root: str,
    operation: str,
    options: dict[str, Any] | None = None,
    timeout_seconds: int = 3600,
    execute: bool = False,
) -> dict[str, Any]:
    """Start the same durable project worker on the prepared Google VM through SSH/IAP."""
    values = options or {}
    command(operation, values)
    return cloud.remote_job(
        project_root(root), "start", [operation, json.dumps(values), str(timeout_seconds)], execute
    )


@mcp.tool(annotations=CLOUD)
def cloud_project_job(
    root: str,
    action: Literal["status", "logs", "cancel"],
    job_id: str,
    stream: Literal["stdout", "stderr", "launcher"] = "stdout",
    offset: int = 0,
    limit: int = 16384,
    execute: bool = False,
) -> dict[str, Any]:
    """Poll, page logs or cancel an existing Google VM worker job. Uses the same durable job ID."""
    args = [job_id]
    if action == "logs":
        args += [stream, str(offset), str(limit)]
    return cloud.remote_job(project_root(root), action, args, execute)


@mcp.tool(annotations=CLOUD)
def cloud_storage(
    root: str,
    direction: Literal["upload", "download"],
    local_path: str,
    object_key: str,
    execute: bool = False,
) -> dict[str, Any]:
    """Transfer one selected project artifact through the configured bucket, without overwriting objects."""
    return cloud.transfer(project_root(root), direction, local_path, object_key, execute)


@mcp.tool(annotations=CLOUD)
def cloud_project_collect(root: str, job_id: str, object_key: str, execute: bool = False) -> dict[str, Any]:
    """Freeze a terminal VM job's receipts/outputs and upload its archive to the selected object key."""
    path = project_root(root)
    settings = config(path)
    from operations import job_directory

    job_directory(path, job_id)
    location = cloud.remote_root(settings)
    export = [
        location + "/vendor/linux-env/bin/python",
        location + "/plugins/quantum-operations/worker.py",
        "export",
        location,
        job_id,
    ]
    upload = [
        "gcloud",
        "storage",
        "cp",
        "--no-clobber",
        location + "/runs/plugin-exports/" + job_id + ".tar.gz",
        cloud.storage_uri(settings, object_key),
    ]
    import shlex

    return cloud.ssh(path, ["bash", "-c", shlex.join(export) + " && " + shlex.join(upload)], execute)


@mcp.tool(annotations=WRITE)
def cloud_batch_prepare(
    root: str,
    job_id: str,
    operation: str,
    options: dict[str, Any],
    source_key: str,
    source_sha256: str,
    inputs_key: str,
    inputs_sha256: str,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Write an inspectable one-task Batch script/config using hash-pinned source and input archives."""
    return cloud.prepare_batch(
        project_root(root),
        job_id,
        operation,
        options,
        source_key,
        source_sha256,
        inputs_key,
        inputs_sha256,
        timeout_seconds,
    )


@mcp.tool(annotations=CLOUD)
def cloud_batch(
    root: str,
    action: Literal["submit", "describe", "delete", "logs"],
    job_id: str,
    config_path: str = "",
    execute: bool = False,
) -> dict[str, Any]:
    """Submit/monitor/delete a Batch job or read its Cloud Logging records (logs requires job UID)."""
    return cloud.batch(project_root(root), action, job_id, config_path, execute)


if __name__ == "__main__":
    mcp.run(transport="stdio")
