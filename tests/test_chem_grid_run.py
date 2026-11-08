"""Small subprocess fixtures for bounded, resumable chemistry grid execution."""

import json
import shutil
import sys
from importlib import import_module

import pytest

from qcompile.io import sha256, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    if not sys.platform.startswith("linux"):
        pytest.skip("Linux process-tree sampler required")
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_grid_run")


def mock_grid(tool, tmp_path, monkeypatch, *, count=3, mode="success"):
    names = ["r9-b143-c40-i1-184", "r9-b143-c40-i1-185", "r9-b143-c40-i2-184"][:count]
    plans = {}
    lanes = []
    for name in names:
        path = tmp_path / f"{name}.json"
        write_json(path, {"wall_seconds": 20, "name": name})
        plans[name] = path
        lanes.append({"id": name, "plan_sha256": sha256(path)})
    monkeypatch.setattr(tool, "validated_manifest", lambda _: ({"lanes": lanes}, plans))
    pins = {"tools/chem_shape_search.py": "a" * 64, "src/qcompile/chemistry/factorization.py": "b" * 64}
    monkeypatch.setattr(tool, "source_hashes", lambda: pins)
    script = tmp_path / "worker.py"
    script.write_text(
        "import hashlib,json,pathlib,sys,time\n"
        "plan=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2])\n"
        + ("time.sleep(5)\n" if mode == "slow" else "time.sleep(1.4)\n")
        + ("sys.exit(7)\n" if mode == "fail" else
           "out.mkdir(parents=True)\n"
           "sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\n"
           "dump=lambda p,x:p.write_text(json.dumps(x))\n"
           "artifact=out/'continuous-00001.npz'; artifact.write_bytes(b'checkpoint')\n"
           "dump(out/'registration.json',{'plan_sha256':sha(plan),'runner_sha256':'a'*64,'factorization_module_sha256':'b'*64})\n"
           "dump(out/'checkpoint-00001.json',{'evaluations':1,'continuous_sha256':sha(artifact),'continuous_residual':0.1})\n"
           "dump(out/'decision.json',{'status':'budget_limited','evaluations':1,'best_continuous_residual':0.1})\n"),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool, "worker_command", lambda plan, output: [sys.executable, str(script), str(plan), str(output)])
    config = {"lanes": names, "limits": {"max_workers": 2, "max_lanes_per_session": min(2, count),
                                            "worker_seconds": 10, "session_seconds": 20}}
    path = tmp_path / "config.json"
    write_json(path, config)
    return path, names


def test_bounded_sessions_resume_and_detect_mutation(tool, tmp_path, monkeypatch, capsys):
    config, names = mock_grid(tool, tmp_path, monkeypatch)
    root = tmp_path / "grid"
    first = tool.execute(config, root)
    assert len(first["results"]) == 2
    assert first["peak_workers"] == 2
    assert all(row["status"] == "complete" for row in first["results"])
    assert first["remaining_lanes"] == [names[2]]
    monkeypatch.setattr(sys, "argv", ["chem_grid_run.py", "dry-run", str(config), str(root)])
    tool.main()
    shown = capsys.readouterr().out
    assert names[2] in shown and names[0] not in shown and names[1] not in shown
    assert not (root / "lanes" / names[2]).exists()
    second = tool.execute(config, root, resume=True)
    assert len(second["previously_completed"]) == 2
    assert [row["lane"] for row in second["results"]] == [names[2]]
    assert second["remaining_lanes"] == []
    victim = root / first["results"][0]["attempt"] / "fit/continuous-00001.npz"
    victim.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="completed lane evidence changed"):
        tool.execute(config, root, resume=True)


def test_failed_attempt_isolated_and_retried(tool, tmp_path, monkeypatch):
    config, names = mock_grid(tool, tmp_path, monkeypatch, count=1, mode="fail")
    root = tmp_path / "grid"
    first = tool.execute(config, root)
    assert first["status"] == "partial_failure"
    assert first["results"][0]["status"] == "worker_failed"
    second = tool.execute(config, root, resume=True)
    assert second["results"][0]["attempt"].endswith("attempt-0002")
    assert (root / "lanes" / names[0] / "attempt-0001/terminal.json").exists()


def test_launch_failure_retains_terminal_receipt(tool, tmp_path, monkeypatch):
    config, names = mock_grid(tool, tmp_path, monkeypatch, count=1)
    monkeypatch.setattr(tool, "worker_command", lambda *_: [str(tmp_path / "missing-worker")])
    root = tmp_path / "grid"
    result = tool.execute(config, root)
    attempt = root / result["results"][0]["attempt"]
    terminal = json.loads((attempt / "terminal.json").read_text())
    assert terminal["status"] == "launch_failed"
    assert result["remaining_lanes"] == names


def test_worker_deadline_is_recorded_as_timeout(tool, tmp_path, monkeypatch):
    config, names = mock_grid(tool, tmp_path, monkeypatch, count=1, mode="slow")
    value = json.loads(config.read_text())
    value["limits"]["worker_seconds"] = 1.2
    config.unlink()
    write_json(config, value)
    result = tool.execute(config, tmp_path / "grid")
    assert result["status"] == "partial_failure"
    assert result["results"][0]["status"] == "timeout"
    assert result["remaining_lanes"] == names


def test_manifest_revalidation_and_plan_hashes(tool, tmp_path, monkeypatch):
    factor_plan = tmp_path / "manifest-plan.json"
    write_json(factor_plan, {"name": "fixture"})
    manifest_path = tmp_path / "manifest.json"
    lane_dir = tmp_path / "lanes"
    lane_dir.mkdir()
    entries = []
    for r, b, c in tool.SHAPES:
        for initial in ("i1", "i2", "i3"):
            for seed in (184, 185):
                name = f"r{r}-b{b}-c{c}-{initial}-{seed}"
                path = lane_dir / f"{name}.json"
                write_json(path, {"name": name})
                entries.append({"id": name, "ready": True, "plan_sha256": sha256(path)})
    write_json(manifest_path, {"plan_sha256": sha256(factor_plan), "lanes": entries})

    def regenerate(_plan, output):
        output.mkdir()
        shutil.copyfile(manifest_path, output / "manifest.json")

    monkeypatch.setattr(tool, "regenerate_manifest", regenerate)
    config = {"manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path)},
              "manifest_plan": {"path": str(factor_plan), "sha256": sha256(factor_plan)},
              "lane_plan_directory": str(lane_dir), "lanes": [entries[0]["id"]],
              "limits": {"max_workers": 1, "max_lanes_per_session": 1, "worker_seconds": 10,
                         "session_seconds": 20}}
    _, plans = tool.validated_manifest(config)
    assert len(plans) == 24
    (lane_dir / f"{entries[0]['id']}.json").write_text(json.dumps({"changed": True}))
    with pytest.raises(ValueError, match="lane plan differs"):
        tool.validated_manifest(config)
