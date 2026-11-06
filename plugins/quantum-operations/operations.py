"""Command catalog shared by the MCP bridge and credential-free Linux worker."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Values are required options and optional options. None means a string/path;
# tuples constrain enums. No shell or arbitrary program is accepted here.
VERIFY = {"backend": None, "seed-policy": None, "output": None, "tier": ("smoke", "full"), "timeout": ()}
OPERATIONS: dict[str, tuple[tuple[str, ...], dict[str, tuple[str, ...] | None]]] = {
    "contract.validate": ((), {"contract": None}),
    "assets.acquire-metric": ((), {"output": None}),
    "assets.pin-backend": (("metric", "verifiers", "kickmix", "output"), {}),
    "baseline.verify": (("artifact-dir", "backend", "seed-policy", "output"), VERIFY),
    "baseline.campaign": (("config", "output"), {}),
    "baseline.freeze": (("campaign", "output"), {}),
    "test": ((), {"tier": ("unit", "extended", "official")}),
    "experiment.run": (("config",), {}),
    "candidate.register": (("selection",), {}),
    "candidate.status": (("id",), {}),
    "candidate.advance": (("id", "state", "evidence"), {}),
    "candidate.verify": (("id", "backend", "seed-policy", "output"), VERIFY),
    "candidate.confirm": (("id", "protocol", "backend", "seed-policy", "output"), VERIFY),
    "release.build": (("selection", "output"), {}),
    "release.verify": (("release", "supporting-evidence", "backend", "seed-policy", "output"), VERIFY),
}
CONTROLS = (
    "phase_check",
    "dqi_check",
    "primitive_check",
    "chemistry_check",
    "chemistry_metrics",
    "chemistry_costs",
    "chemistry_stability",
    "invsqrt_rejections",
    "angle_boundaries",
    "structure_controls",
    "freeze",
)
for control in CONTROLS:
    OPERATIONS["step3." + control] = ((), {})
OPERATIONS.update({"checks.pyright": ((), {}), "checks.ruff": ((), {}), "checks.format": ((), {})})


def project_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not (root / "pyproject.toml").is_file() or not (root / "src/qcompile/cli.py").is_file():
        raise ValueError("root must name a qcompile source checkout")
    return root


def command(operation: str, options: dict[str, Any], python: str = sys.executable) -> list[str]:
    if operation not in OPERATIONS:
        raise ValueError(f"unknown operation: {operation}")
    required, optional = OPERATIONS[operation]
    unknown = options.keys() - (set(required) | optional.keys())
    if unknown or any(name not in options for name in required):
        raise ValueError(f"required options: {required}; unsupported options: {sorted(unknown)}")
    for name, value in options.items():
        if name == "timeout":
            if type(value) is not int or not 1 <= value <= 604800:
                raise ValueError("timeout must be an integer in [1,604800]")
        elif not isinstance(value, str) or not value or "\x00" in value:
            raise ValueError(f"nonempty string required: {name}")
        allowed = optional.get(name)
        if allowed and value not in allowed:
            raise ValueError(f"{name} must be one of {allowed}")
    if operation.startswith("step3."):
        return [python, "tools/step3_" + operation.split(".")[1] + ".py"]
    if operation.startswith("checks."):
        return {
            "checks.pyright": [python, "-m", "pyright", "--pythonpath", python, "src", "tests", "tools"],
            "checks.ruff": [python, "-m", "ruff", "check", "src", "tests", "tools"],
            "checks.format": [python, "-m", "ruff", "format", "--check", "src", "tests", "tools"],
        }[operation]
    args = [python, "-m", "qcompile.cli", *operation.split(".")]
    for name, value in options.items():
        # Separate argv items prevent shell substitution; equals protects leading '-'.
        args.append(f"--{name}={value}")
    return args


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return value


def config(root: Path) -> dict[str, Any]:
    path = root / "configs/cloud.local.json"
    return read_json(path if path.exists() else root / "configs/cloud.example.json")


def bounded_read(path: Path, offset: int = 0, limit: int = 16384) -> dict[str, Any]:
    if type(offset) is not int or offset < 0 or not 1 <= limit <= 65536:
        raise ValueError("offset >=0 and limit in [1,65536] required")
    with path.open("rb") as stream:
        stream.seek(offset)
        data = stream.read(limit)
        total = os.fstat(stream.fileno()).st_size
    return {
        "text": data.decode("utf-8", errors="replace"),
        "next_offset": offset + len(data),
        "bytes": total,
        "has_more": offset + len(data) < total,
    }


def job_directory(root: Path, job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("invalid job ID")
    directory = root / "runs/plugin-jobs" / job_id
    if not directory.resolve().is_relative_to((root / "runs/plugin-jobs").resolve()):
        raise ValueError("job path escapes its root")
    return directory


def run_json(argv: list[str], cwd: Path, timeout: int = 60) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"operation exited {result.returncode}: {result.stderr[-3000:]}")
    return json.loads(result.stdout)


def linux_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    # WSL's standard drive mounts; reject UNC paths rather than guessing a mount.
    if not re.fullmatch(r"[A-Za-z]:", path.drive):
        raise ValueError("Windows project/plugin must be on a local drive mounted under /mnt")
    return "/mnt/" + path.drive[0].lower() + path.as_posix()[2:]


def worker_command(root: Path, action: str, args: list[str]) -> list[str]:
    settings = config(root)
    python = settings.get("python") or "vendor/linux-env/bin/python"
    interpreter = Path(python)
    if not interpreter.is_absolute():
        interpreter = root / interpreter
    worker = Path(__file__).with_name("worker.py")
    prefix = []
    if os.name == "nt":
        prefix = ["wsl.exe", "-d", settings.get("wsl_distribution") or "Ubuntu", "--exec"]
    return [*prefix, linux_path(interpreter), linux_path(worker), action, linux_path(root), *args]
