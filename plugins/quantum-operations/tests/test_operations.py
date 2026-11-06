import asyncio
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import cloud
import operations
import server
import staging
import worker

PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = PLUGIN.parents[1]


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src/qcompile").mkdir(parents=True)
    (tmp_path / "src/qcompile/__init__.py").touch()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.0.0'\n")
    (tmp_path / "src/qcompile/cli.py").write_text(
        "import json,subprocess,sys,time\n"
        "from pathlib import Path\n"
        "if 'experiment' in sys.argv:\n"
        " child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],start_new_session=True)\n"
        " Path('child.pid').write_text(str(child.pid))\n"
        " print('started',flush=True)\n"
        " time.sleep(120)\n"
        "elif 'baseline' in sys.argv:\n"
        " print('expected failure',file=sys.stderr); sys.exit(7)\n"
        "else: print(json.dumps({'status':'ready'}))\n"
    )
    (tmp_path / "configs").mkdir()
    settings = json.loads((PROJECT / "configs/cloud.example.json").read_text())
    settings.update(
        project="test-project",
        region="us-central1",
        zone="us-central1-a",
        vm="quantum-test",
        service_account="experiments@test-project.iam.gserviceaccount.com",
        bucket="test-quantum",
    )
    (tmp_path / "configs/cloud.example.json").write_text(json.dumps(settings))
    return tmp_path


def terminal(root: Path, job_id: str, seconds: float = 12) -> dict[str, Any]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = worker.status(root, job_id)
        if result["status"] in ("completed", "failed", "timed_out", "cancelled", "interrupted"):
            return result
        time.sleep(0.05)
    pytest.fail("job did not terminate within its bounded test timeout")


def test_command_arguments_are_argv_not_shell() -> None:
    payload = "a; $(touch NEVER) ' --root=/tmp/other"
    args = operations.command("experiment.run", {"config": payload})
    assert args[-1] == "--config=" + payload
    with pytest.raises(ValueError):
        operations.command("experiment.run", {"config": "x", "root": "/tmp/other"})
    with pytest.raises(ValueError):
        operations.command("shell.run", {})
    with pytest.raises(ValueError):
        operations.command("baseline.verify", {"artifact-dir": "x"})


def test_catalog_covers_actual_project_parser() -> None:
    # Exercise every registered CLI action against the real parser, in its locked env.
    python = PROJECT / "vendor/linux-env/bin/python"
    if sys.platform != "linux" or not python.exists():
        pytest.skip("real qcompile parser integration is checked in Ubuntu")
    samples: list[list[str]] = []
    for operation, (required, _) in operations.OPERATIONS.items():
        if operation.startswith(("checks.", "step3.")):
            continue
        samples.append(operations.command(operation, dict.fromkeys(required, "fixture"))[3:])
    script = (
        "import argparse,json; from qcompile.cli import parser; p=parser(); "
        "cases=json.loads(__import__('sys').argv[1]); [p.parse_args(a) for a in cases]; "
        "groups=next(a for a in p._actions if isinstance(a,argparse._SubParsersAction)); names=[]\n"
        "for group, sub in groups.choices.items():\n"
        " actions=[a for a in sub._actions if isinstance(a,argparse._SubParsersAction)]\n"
        " names.extend([group+'.'+n for n in actions[0].choices] if actions else [group])\n"
        "print(json.dumps(names))"
    )
    result = subprocess.run(
        [str(python), "-c", script, json.dumps(samples)],
        cwd=PROJECT,
        env={**os.environ, "PYTHONPATH": str(PROJECT / "src")},
        capture_output=True,
        text=True,
        check=True,
    )
    assert set(json.loads(result.stdout)) == {
        name for name in operations.OPERATIONS if not name.startswith(("checks.", "step3."))
    }


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process groups are required")
def test_worker_success_failure_and_log_pages(root: Path) -> None:
    job = worker.start(root, "contract.validate", {}, 10)
    result = terminal(root, job["job_id"])
    assert result["status"] == "completed" and result["exit_code"] == 0
    log = operations.bounded_read(operations.job_directory(root, job["job_id"]) / "stdout.log", limit=8)
    assert log["has_more"] and log["next_offset"] == 8
    failed = worker.start(root, "baseline.freeze", {"campaign": "fixture", "output": "fixture"}, 10)
    result = terminal(root, failed["job_id"])
    assert result["status"] == "failed" and result["exit_code"] == 7


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process groups are required")
@pytest.mark.parametrize("cancel", [True, False])
def test_cancellation_and_timeout_kill_descendants(root: Path, cancel: bool) -> None:
    job = worker.start(root, "experiment.run", {"config": "fixture"}, 30 if cancel else 1)
    deadline = time.monotonic() + 6
    while not (root / "child.pid").exists() and time.monotonic() < deadline:
        time.sleep(0.03)
    assert (root / "child.pid").exists()
    pid = int((root / "child.pid").read_text())
    if cancel:
        assert worker.cancel(root, job["job_id"])["status"] == "cancellation_requested"
    result = terminal(root, job["job_id"])
    assert result["status"] == ("cancelled" if cancel else "timed_out")
    assert worker.process_identity(pid) is None
    registration = operations.read_json(operations.job_directory(root, job["job_id"]) / "registration.json")
    assert registration["operation"] == "experiment.run"


def test_stale_process_never_signalled(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = "a" * 32
    directory = operations.job_directory(root, job_id)
    directory.mkdir(parents=True)
    worker.write(directory / "process.json", {"pid": os.getpid(), "identity": "old-boot:old-start"})
    monkeypatch.setattr(worker.os, "kill", lambda *args: pytest.fail("stale process was signalled"))
    assert worker.cancel(root, job_id)["status"] == "interrupted"


def test_evidence_cannot_read_credentials_or_traverse(root: Path) -> None:
    with pytest.raises(ValueError):
        server.project_evidence(str(root), "configs/cloud.example.json")
    with pytest.raises(ValueError):
        server.project_evidence(str(root), "runs/../../credentials.json")
    with pytest.raises(ValueError):
        operations.job_directory(root, "../credentials")


def test_cloud_previews_and_quoting(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cloud.subprocess, "run", lambda *a, **k: pytest.fail("preview executed a command"))
    result = cloud.vm(root, "create")
    assert result["status"] == "preview"
    assert "--machine-type=e2-highmem-2" in result["argv"] and "--no-address" in result["argv"]
    run = cloud.remote_job(root, "start", ["experiment.run", '{"config":"a; touch NO"}', "3600"])
    parsed = shlex.split(run["argv"][-1].removeprefix("--command="))
    assert parsed[-2] == '{"config":"a; touch NO"}'
    with pytest.raises(ValueError):
        cloud.storage_uri(cloud.config(root), "../other-object")
    with pytest.raises(ValueError):
        cloud.remote_root({"remote_root": "/"})


def test_cloud_execute_propagates_failure(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fail(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 3, "", "not authenticated")

    monkeypatch.setattr(cloud.subprocess, "run", fail)
    result = cloud.vm(root, "describe", execute=True)
    assert result["status"] == "failed" and result["exit_code"] == 3
    assert "--project=test-project" in seen[0]


def test_batch_config_delegates_and_preserves_failure(root: Path) -> None:
    result = cloud.prepare_batch(
        root, "batch-one", "contract.validate", {}, "source.bundle", "a" * 64, "inputs.tar.gz", "b" * 64
    )
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["taskGroups"][0]["taskSpec"]["computeResource"]["memoryMib"] == 14336
    assert 'exit "$code"' in result["script"]
    assert "--frozen" in result["script"] and "sha256sum -c" in result["script"]
    preview = cloud.batch(root, "submit", "batch-one", result["config_path"])
    assert any(arg.startswith("--config=") for arg in preview["argv"])
    with pytest.raises(ValueError):
        cloud.prepare_batch(root, "bad", "contract.validate", {}, "source", "", "inputs", "")


@pytest.mark.skipif(sys.platform != "linux", reason="bootstrap is a Linux shell workflow")
def test_bootstrap_rejects_modified_transfer(root: Path, tmp_path: Path) -> None:
    # Exercise the real shell/hash boundary using a local stand-in for storage.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gcloud = fake_bin / "gcloud"
    gcloud.write_text('#!/bin/sh\ncp "$3" "$4"\n')
    gcloud.chmod(0o755)
    source = tmp_path / "source.bundle"
    inputs = tmp_path / "inputs.tar.gz"
    source.write_bytes(b"modified transfer")
    inputs.write_bytes(b"irrelevant inputs")
    destination = tmp_path / "fresh-project"
    env = {
        **os.environ,
        "PATH": str(fake_bin) + ":" + os.environ["PATH"],
        "QUANTUM_ROOT": str(destination),
        "QUANTUM_SOURCE_URI": str(source),
        "QUANTUM_SOURCE_SHA256": "a" * 64,
        "QUANTUM_INPUTS_URI": str(inputs),
        "QUANTUM_INPUTS_SHA256": "b" * 64,
    }
    result = subprocess.run(["bash", str(PLUGIN / "bootstrap.sh")], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and not destination.exists()
    assert "FAILED" in result.stdout


def test_relocation_leaves_current_pins_unchanged(root: Path) -> None:
    (root / "vendor").mkdir()
    backend = {
        "metric_notebook": "/old/vendor/metric/x.ipynb",
        "kickmix_root": "/old/kickmix",
        "verifiers_root": "/old/verifiers",
        "kickmix_files": {"kickmix.so": "pinned"},
    }
    old_bytes = json.dumps(backend).encode()
    (root / "vendor/backend.json").write_bytes(old_bytes)
    (root / "contracts").mkdir()
    contract = {
        "sources": {
            "verifiers": {"path": "vendor/backend.json", "sha256": hashlib.sha256(old_bytes).hexdigest()}
        }
    }
    (root / "contracts/contract.json").write_text(json.dumps(contract))
    plan = staging.relocation_plan(root, "/var/tmp/quantum", "test-plan")
    assert plan["status"] == "review_required"
    assert (root / "vendor/backend.json").read_bytes() == old_bytes
    proposed = json.loads((Path(plan["directory"]) / "backend.json").read_text())
    assert proposed["kickmix_files"] == backend["kickmix_files"]


def test_snapshot_rejects_dirty_source(root: Path) -> None:
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    with pytest.raises(ValueError, match="clean committed"):
        staging.snapshot(root, "dirty")


def test_clean_snapshot_roundtrip_and_allowlist(root: Path) -> None:
    import tarfile

    (root / "plugins/quantum-operations").mkdir(parents=True)
    (root / "plugins/quantum-operations/worker.py").write_text("# committed worker\n")
    (root / ".gitignore").write_text("vendor/\nruns/\nreleases/\nconfigs/cloud.local.json\n")
    for name in ("vendor/official", "vendor/metric", "vendor/pages"):
        (root / name).mkdir(parents=True)
        (root / name / "input.txt").write_text("pinned input")
    for name in ("vendor/backend.json", "vendor/acquisition-checks.json", "vendor/competition_data.zip"):
        (root / name).write_bytes(b"pinned bytes")
    (root / "configs/cloud.local.json").write_text('{"secret":"DO-NOT-PACK"}')
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-m",
            "fixture",
        ],
        cwd=root,
        capture_output=True,
        check=True,
    )
    receipt = staging.snapshot(root, "roundtrip")
    assert staging.digest(Path(receipt["source"])) == receipt["source_sha256"]
    with tarfile.open(receipt["inputs"]) as archive:
        names = archive.getnames()
        assert "vendor/competition_data.zip" in names
        assert not any("cloud.local" in name or ".venv" in name for name in names)
    restored = root / "runs/restored"
    subprocess.run(["git", "clone", receipt["source"], str(restored)], capture_output=True, check=True)
    assert (restored / "plugins/quantum-operations/worker.py").exists()


@pytest.mark.skipif(sys.platform != "linux", reason="experiment export requires a Linux job")
def test_export_retains_terminal_receipts(root: Path) -> None:
    import tarfile

    job = worker.start(root, "contract.validate", {}, 10)
    assert terminal(root, job["job_id"])["status"] == "completed"
    receipt = worker.export_job(root, job["job_id"])
    with tarfile.open(receipt["path"]) as archive:
        assert any(name.endswith("result.json") for name in archive.getnames())
    assert worker.export_job(root, job["job_id"])["sha256"] == receipt["sha256"]


def test_stdio_mcp_startup_catalog_and_preview() -> None:
    async def exercise() -> None:
        params = StdioServerParameters(
            command=sys.executable, args=[str(PLUGIN / "server.py")], cwd=str(PLUGIN)
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"project_run", "project_job_cancel", "cloud_batch", "cloud_vm_prepare"} <= names
                catalog = await session.call_tool("project_catalog", {})
                assert not catalog.isError
                preview = await session.call_tool(
                    "project_run", {"root": str(PROJECT), "operation": "contract.validate"}
                )
                assert not preview.isError
                invalid = await session.call_tool("project_run", {"root": str(PROJECT), "operation": "shell"})
                assert invalid.isError

    asyncio.run(exercise())


@pytest.mark.skipif(sys.platform != "linux", reason="durable experiments use Linux")
def test_mcp_disconnect_preserves_live_job(root: Path) -> None:
    settings = operations.config(root)
    settings["python"] = sys.executable
    (root / "configs/cloud.local.json").write_text(json.dumps(settings))

    async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        params = StdioServerParameters(
            command=sys.executable, args=[str(PLUGIN / "server.py")], cwd=str(PLUGIN)
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                assert not result.isError
                assert result.structuredContent is not None
                return result.structuredContent

    async def exercise() -> None:
        job = await call(
            "project_run",
            {
                "root": str(root),
                "operation": "experiment.run",
                "options": {"config": "fixture"},
                "execute": True,
            },
        )
        try:
            status = await call("project_job_status", {"root": str(root), "job_id": job["job_id"]})
            assert status["status"] == "running"
        finally:
            await call("project_job_cancel", {"root": str(root), "job_id": job["job_id"]})
        assert terminal(root, job["job_id"])["status"] == "cancelled"

    asyncio.run(exercise())
