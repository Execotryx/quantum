"""Explicit immutable source/input packaging and reviewable deployment path changes."""

import copy
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from typing import Any

from cloud import identifier, remote_root
from operations import read_json


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(root: Path, snapshot_id: str, additional_inputs: list[str] | None = None) -> dict[str, Any]:
    identifier(snapshot_id, "snapshot ID")
    clean = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    if clean.stdout:
        raise ValueError(
            "cloud snapshots require clean committed source; preserve and resolve local changes first"
        )
    # The Git bundle must actually contain this plugin before a remote run can start.
    subprocess.run(
        ["git", "cat-file", "-e", "HEAD:plugins/quantum-operations/worker.py"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    directory = root / "runs/cloud-snapshots" / snapshot_id
    directory.mkdir(parents=True, exist_ok=False)
    source = directory / "source.bundle"
    subprocess.run(
        ["git", "bundle", "create", str(source), "HEAD"], cwd=root, check=True, capture_output=True
    )
    inputs = directory / "inputs.tar.gz"
    # Deliberate allowlist excludes environments, downloaded tools and credentials.
    selected = [
        "vendor/official",
        "vendor/metric",
        "vendor/pages",
        "vendor/backend.json",
        "vendor/acquisition-checks.json",
        "vendor/competition_data.zip",
    ]
    for name in additional_inputs or []:
        path = (root / name).resolve()
        if (
            not path.is_relative_to(root)
            or not name.startswith(("runs/", "releases/"))
            or name.startswith(("runs/cloud-snapshots/", "runs/cloud-plans/"))
        ):
            raise ValueError("additional inputs must be explicitly selected run/release artifacts")
        selected.append(name)
    for name in selected:
        if not (root / name).exists():
            raise ValueError(f"missing pinned input: {name}")
    inventory: dict[str, str] = {}
    with tarfile.open(inputs, "w:gz") as archive:
        for name in selected:
            candidate = root / name
            files = sorted(candidate.rglob("*")) if candidate.is_dir() else [candidate]
            for path in files:
                if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo") or path.is_dir():
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError("input archive cannot contain symlinks or paths outside project")
                relative = path.relative_to(root).as_posix()
                inventory[relative] = digest(path)
                archive.add(path, arcname=relative, recursive=False)
    receipt = {
        "source": str(source),
        "source_sha256": digest(source),
        "inputs": str(inputs),
        "inputs_sha256": digest(inputs),
        "input_files": inventory,
    }
    (directory / "snapshot.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def relocation_plan(root: Path, destination: str, plan_id: str) -> dict[str, Any]:
    identifier(plan_id, "plan ID")
    location = remote_root({"remote_root": destination})
    backend_path = root / "vendor/backend.json"
    backend = read_json(backend_path)
    original = copy.deepcopy(backend)
    for key, relative in (
        ("metric_notebook", "vendor/metric/google-quantum-ai-metric.ipynb"),
        ("kickmix_root", "vendor/official/kickmix"),
        ("verifiers_root", "vendor/official/verifiers"),
    ):
        backend[key] = location.rstrip("/") + "/" + relative
    directory = root / "runs/cloud-relocation" / plan_id
    directory.mkdir(parents=True, exist_ok=False)
    proposed = directory / "backend.json"
    proposed.write_text(json.dumps(backend, indent=2) + "\n", encoding="utf-8")
    contract = read_json(root / "contracts/contract.json")
    # Keep every existing source identity except the explicitly reviewed backend inventory.
    pins = [value for value in contract["sources"].values() if value.get("path") == "vendor/backend.json"]
    if len(pins) != 1 or pins[0]["sha256"] != digest(backend_path):
        raise ValueError("current backend inventory does not match its contract source pin")
    pins[0]["sha256"] = digest(proposed)
    (directory / "contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "status": "review_required",
        "directory": str(directory),
        "old_backend_sha256": digest(backend_path),
        "new_backend_sha256": digest(proposed),
        "path_changes": {
            key: {"before": original[key], "after": backend[key]}
            for key in ("metric_notebook", "kickmix_root", "verifiers_root")
        },
        "next": "Review the path-only inventory and contract change, apply and commit them in an isolated "
        "deployment checkout, then snapshot it. Reconcile campaign assets_root separately. "
        "Run contract validation and actual native verification on the new host.",
    }
    (directory / "relocation.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
