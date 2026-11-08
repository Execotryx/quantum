"""External ranking-supervisor execution status and source-plan pinning."""

from importlib import import_module

import pytest

from qcompile.io import read_json, write_json


@pytest.fixture
def tool(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("chem_grid_supervise")


def test_worker_failure_is_not_scientific_result(tool, tmp_path, monkeypatch):
    plan = tmp_path / "plan.json"
    write_json(plan, {"shape": [9, 143, 40]})
    monkeypatch.setattr(tool, "run_job", lambda *_: 23)
    output = tmp_path / "output"
    tool.run(plan, output, 60)
    assert read_json(output / "status.json")["status"] == "worker_exit_23"
    assert not (output / "ranking/ranking.json").exists()


def test_changed_plan_never_receives_success_status(tool, tmp_path, monkeypatch):
    plan = tmp_path / "plan.json"
    write_json(plan, {"shape": [9, 143, 40]})

    def mutate(*_):
        plan.unlink()
        write_json(plan, {"shape": [8, 120, 40]})
        return 0

    monkeypatch.setattr(tool, "run_job", mutate)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="plan changed"):
        tool.run(plan, output, 60)
    assert not (output / "status.json").exists()
