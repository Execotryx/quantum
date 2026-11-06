"""Linux job supervisor. Stdlib only: the remote host needs no MCP installation."""

import json
import os
import signal
import subprocess
import sys
import tarfile
import time
import uuid
from pathlib import Path
from typing import Any

from operations import bounded_read, command, job_directory, project_root, read_json


def write(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def process_identity(pid: int) -> str | None:
    try:
        # comm can include whitespace and parentheses. starttime is field 22.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return None
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip() + ":" + fields[19]
    except (OSError, IndexError):
        return None


def status(root: Path, job_id: str) -> dict[str, Any]:
    directory = job_directory(root, job_id)
    if (directory / "result.json").exists():
        return {"job_id": job_id, **read_json(directory / "result.json")}
    if (directory / "process.json").exists():
        process = read_json(directory / "process.json")
        live = bool(process["identity"]) and process_identity(process["pid"]) == process["identity"]
        return {
            "job_id": job_id,
            "status": "running" if live else "interrupted",
            "process": process,
            "detail": "No terminal receipt; inspect retained logs if interrupted.",
        }
    read_json(directory / "registration.json")
    return {"job_id": job_id, "status": "starting"}


def start(root: Path, operation: str, options: dict[str, Any], timeout: int) -> dict[str, Any]:
    if sys.platform != "linux":
        raise ValueError("experiments require Linux; on Windows select the Ubuntu WSL runtime")
    if type(timeout) is not int or not 1 <= timeout <= 604800:
        raise ValueError("job timeout must lie in [1,604800] seconds")
    argv = command(operation, options)
    job_id = uuid.uuid4().hex
    directory = job_directory(root, job_id)
    directory.mkdir(parents=True, exist_ok=False)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    write(
        directory / "registration.json",
        {
            "operation": operation,
            "options": options,
            "argv": argv,
            "timeout_seconds": timeout,
            "created_at": time.time(),
            "source_revision": revision.stdout.strip(),
        },
    )
    with (directory / "launcher.log").open("ab") as log:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "supervise", str(root), job_id],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            close_fds=True,
        )
    # Write from the parent before responding. Supervisor waits for this receipt.
    write(directory / "process.json", {"pid": child.pid, "identity": process_identity(child.pid)})
    return {"job_id": job_id, "status": "starting", "directory": str(directory)}


def supervise(root: Path, job_id: str) -> None:
    directory = job_directory(root, job_id)
    registration = read_json(directory / "registration.json")
    cancelled = False

    def request_cancel(_signum: int, _frame: Any) -> None:
        nonlocal cancelled
        cancelled = True

    signal.signal(signal.SIGTERM, request_cancel)
    signal.signal(signal.SIGINT, request_cancel)
    started = time.monotonic()
    environment = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONUNBUFFERED": "1"}
    result: dict[str, Any] = {"status": "failed", "exit_code": None}
    try:
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(
                registration["argv"],
                cwd=root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            while process.poll() is None:
                timed_out = time.monotonic() - started >= registration["timeout_seconds"]
                if cancelled or timed_out:
                    terminate_tree(process.pid)
                    process.wait()
                    result = {
                        "status": "cancelled" if cancelled else "timed_out",
                        "exit_code": process.returncode,
                    }
                    break
                time.sleep(0.2)
            else:
                result = {
                    "status": "completed" if process.returncode == 0 else "failed",
                    "exit_code": process.returncode,
                }
    except Exception as error:
        result["error"] = str(error)
    result.update({"finished_at": time.time(), "elapsed_seconds": time.monotonic() - started})
    write(directory / "result.json", result)


def terminate_tree(pid: int) -> None:
    """Include verifier children that create their own sessions/process groups."""
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                parent = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
                children.setdefault(parent, []).append(int(entry.name))
            except (OSError, IndexError, ValueError):
                pass
    descendants = {pid}
    pending = [pid]
    while pending:
        for child in children.get(pending.pop(), []):
            if child not in descendants:
                descendants.add(child)
                pending.append(child)
    identities = {child: process_identity(child) for child in descendants}
    for sig in (signal.SIGTERM, signal.SIGKILL):
        # Stop the root while terminating observed descendants. /proc enumeration
        # has a sampling race; this is not a privileged cgroup boundary.
        if sig == signal.SIGTERM:
            try:
                os.kill(pid, signal.SIGSTOP)
            except ProcessLookupError:
                pass
        for child in sorted(descendants, reverse=True):
            if identities[child] and process_identity(child) == identities[child]:
                try:
                    os.kill(child, sig)
                except ProcessLookupError:
                    pass
        if sig == signal.SIGTERM:
            try:
                os.kill(pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and any(
                identity and process_identity(child) == identity for child, identity in identities.items()
            ):
                time.sleep(0.05)


def cancel(root: Path, job_id: str) -> dict[str, Any]:
    current = status(root, job_id)
    if current["status"] != "running":
        return current
    process = current["process"]
    # Recheck immediately before signalling. A stale PID must not kill a new job.
    if process_identity(process["pid"]) != process["identity"]:
        return {"job_id": job_id, "status": "interrupted"}
    os.kill(process["pid"], signal.SIGTERM)
    return {"job_id": job_id, "status": "cancellation_requested"}


def export_job(root: Path, job_id: str) -> dict[str, Any]:
    from staging import digest

    current = status(root, job_id)
    if current["status"] in ("running", "starting"):
        raise ValueError("wait for the existing job to terminate before freezing outputs")
    directory = job_directory(root, job_id)
    registration = read_json(directory / "registration.json")
    paths = [directory]
    output = registration["options"].get("output")
    if output:
        target = (root / output).resolve()
        if not target.is_relative_to(root) or not target.exists():
            raise ValueError("job output must exist inside the selected project")
        paths.append(target)
    destination = root / "runs/plugin-exports"
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / (job_id + ".tar.gz")
    if archive_path.exists():
        return {"path": str(archive_path), "sha256": digest(archive_path), "status": "retained"}
    temporary = destination / (job_id + ".partial")
    with tarfile.open(temporary, "x:gz") as archive:
        included: set[str] = set()
        for selected in paths:
            for path in sorted(selected.rglob("*")) if selected.is_dir() else [selected]:
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError("output export cannot include symlinks or outside files")
                relative = path.relative_to(root).as_posix()
                if path.is_file() and relative not in included:
                    archive.add(path, arcname=relative, recursive=False)
                    included.add(relative)
    temporary.replace(archive_path)
    return {"path": str(archive_path), "sha256": digest(archive_path), "status": "frozen"}


def main() -> None:
    action, location, *args = sys.argv[1:]
    root = project_root(location)
    if action == "start":
        result = start(root, args[0], json.loads(args[1]), int(args[2]))
    elif action == "supervise":
        supervise(root, args[0])
        return
    elif action == "status":
        result = status(root, args[0])
    elif action == "cancel":
        result = cancel(root, args[0])
    elif action == "export":
        result = export_job(root, args[0])
    elif action == "logs":
        if args[1] not in ("stdout", "stderr", "launcher"):
            raise ValueError("invalid log stream")
        path = job_directory(root, args[0]) / (args[1] + ".log")
        result = bounded_read(path, int(args[2]), int(args[3]))
    else:
        raise ValueError("unknown worker action")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
