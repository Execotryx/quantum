import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from qcompile.artifacts import hashes
from qcompile.errors import BlockedError, ValidationError
from qcompile.io import sha256
from qcompile.release import build_candidate, certify_release


def test_generated_artifacts_require_a_real_recipe(tmp_path, artifact_set):
    with pytest.raises(ValidationError, match="rebuild recipe"):
        build_candidate({"artifacts": artifact_set}, None, tmp_path / "build")


def test_retained_reference_is_copied_without_conversion(tmp_path, artifact_set):
    artifacts = {k: {**v, "origin": "retained_reference"} for k, v in artifact_set.items()}
    selection = {"artifacts": artifacts}
    a = build_candidate(selection, None, tmp_path / "a")
    b = build_candidate(selection, None, tmp_path / "b")
    for name in artifacts:
        assert (
            Path(a[name]).read_bytes()
            == Path(b[name]).read_bytes()
            == Path(artifacts[name]["path"]).read_bytes()
        )


def test_two_builds_really_rerun_generator_in_distinct_directories(tmp_path, artifact_set):
    # Synthetic generator proving orchestration, not an official quantum generator.
    generator = tmp_path / "generator.py"
    payload = {name: Path(item["path"]).read_bytes().decode() for name, item in artifact_set.items()}
    generator.write_text(
        "import sys,json,pathlib\n"
        f"payload=json.loads({json.dumps(json.dumps(payload))})\n"
        "root=pathlib.Path(sys.argv[1])\n"
        "for name,text in payload.items():\n"
        " p=root/name\n p.parent.mkdir(parents=True,exist_ok=True)\n p.write_text(text)\n"
        'with pathlib.Path(sys.argv[2]).open("a") as log: log.write(str(root)+"\\n")\n'
    )
    log = tmp_path / "invocations.txt"
    recipe = {
        "argv": [sys.executable, str(generator), "{output_dir}", str(log)],
        "outputs": list(artifact_set),
        "inputs": {str(generator): sha256(generator)},
    }
    selection = {"artifacts": artifact_set, "build_recipes": [recipe]}
    build_candidate(selection, None, tmp_path / "a")
    build_candidate(selection, None, tmp_path / "b")
    assert log.read_text().splitlines() == [str(tmp_path / "a"), str(tmp_path / "b")]
    generator.write_text("# changed")
    with pytest.raises(ValidationError, match="input hash mismatch"):
        build_candidate(selection, None, tmp_path / "c")


def test_release_cannot_use_incomplete_or_smoke_verification(artifact_set):
    contract = SimpleNamespace(hash="c" * 64)
    release = {"artifact_hashes": hashes(artifact_set), "contract_hash": contract.hash}
    report = {
        "kind": "official_metric_execution",
        "tier": "smoke",
        "status": "passed",
        "complete": True,
        "artifact_hashes": hashes(artifact_set),
        "contract_hash": contract.hash,
    }
    with pytest.raises(BlockedError, match="complete hash-bound full"):
        certify_release(release, report, contract, supporting_evidence={})


def test_cli_blocked_contract_exits_nonzero_and_help_is_real(project_root):
    run = subprocess.run(
        [sys.executable, "-m", "qcompile", "contract", "validate"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "blocked"
    help_run = subprocess.run(
        [sys.executable, "-m", "qcompile", "--help"], cwd=project_root, capture_output=True, text=True
    )
    assert help_run.returncode == 0
    assert "release" in help_run.stdout


def test_release_certificate_requires_actual_counters_and_cost_improvement(artifact_set):
    counts = {name: {"completed": 100, "expected": 100} for name in ("invsqrt", "dqi", "dfthcsos")}
    contract = SimpleNamespace(
        hash="c" * 64, data={"fields": {"release.coverage": {"value": dict.fromkeys(counts, 100)}}}
    )
    release = {"artifact_hashes": hashes(artifact_set), "contract_hash": contract.hash}
    actual = {"coverage_counts": counts, "costs": {"invsqrt": 5.0, "dqi": 10.0, "dfthcsos": 10.0}}
    report = {
        "kind": "official_metric_execution",
        "tier": "full",
        "status": "passed",
        "complete": True,
        "role": "official_local",
        "official_results": actual,
        "artifact_hashes": hashes(artifact_set),
        "contract_hash": contract.hash,
    }
    supporting = {
        key: {"test_only": "synthetic receipt"}
        for key in (
            "cost_breakdown",
            "numerical_margins",
            "mutation_diagnostics",
            "primitive_scope",
            "representation_stability",
            "opportunity_decision",
        )
    }
    supporting.update(coverage_counts=counts, accepted_reference_costs=dict.fromkeys(counts, 10.0))
    result = certify_release(release, report, contract, supporting_evidence=supporting)
    assert result["status"] == "locally_verified_awaiting_kaggle_acceptance"
    assert result["predicted_aggregate_score"] > 1
    report["official_results"] = {**actual, "coverage_counts": {}}
    with pytest.raises(BlockedError, match="incomplete release coverage"):
        certify_release(release, report, contract, supporting_evidence=supporting)
    report["official_results"] = {**actual, "costs": dict.fromkeys(counts, 10.0)}
    with pytest.raises(BlockedError, match="must improve"):
        certify_release(release, report, contract, supporting_evidence=supporting)


def test_release_cannot_relabel_generated_bytes_as_retained_reference(tmp_path, artifact_set):
    from qcompile.release import package_release

    environment = {"source_revision": "a" * 40, "dependency_lock_sha256": "b" * 64, "dirty": False}
    contract = SimpleNamespace(hash="c" * 64, require_ready=lambda root: None)
    candidate = {
        "state": "release_selected",
        "contract_hash": contract.hash,
        "environment": environment,
        "artifact_hashes": hashes(artifact_set),
        "artifact_sources": {
            name: {key: item[key] for key in ("origin", "provenance")} for name, item in artifact_set.items()
        },
    }
    relabeled = {name: {**item, "origin": "retained_reference"} for name, item in artifact_set.items()}
    with pytest.raises(ValidationError, match="frozen artifact provenance"):
        package_release(
            {"candidate": candidate, "artifacts": relabeled, "project_root": str(tmp_path)},
            contract,
            tmp_path / "release",
            source_environment=environment,
        )
