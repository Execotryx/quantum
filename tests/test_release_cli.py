import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from qcompile.artifacts import hashes
from qcompile.component_confirmations import dqi_counts
from qcompile.contract import load_contract
from qcompile.errors import BlockedError, ValidationError
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.release import _compare_candidate_parent, build_candidate, certify_release


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


def test_changed_backend_requires_both_bound_requests(tmp_path, project_root):
    evidence = project_root / "docs/evidence"
    parent_dir = evidence / "advance-hybrid-20261108/archive"
    successor_dir = evidence / "invsqrt-roadmap-archive-20261108"
    parent_report = read_json(parent_dir / "verification.json")
    successor = read_json(successor_dir / "verification.json")
    comparison = read_json(successor_dir / "comparison.json")
    baselines = read_json(evidence / "invsqrt-chemistry-20261107/combined-result.json")["reference"]
    certificate = tmp_path / "parent-certificate.json"
    write_json(certificate, {"verification": parent_report})
    parent = {
        "retained_benchmarks": ["dqi", "dfthcsos"],
        "backend_hash": parent_report["backend_hash"],
        "score": comparison["parent_score"],
        "costs": comparison["parent_costs"],
        "dqi_counts": dqi_counts(parent_report["official_results"]["raw_verifier_results"]["dqi"]),
        "certificate_path": str(certificate),
        "certificate_sha256": sha256(certificate),
    }
    candidate = {"config": {}, "artifacts": {"invsqrt.kmb": {"origin": "generated"}}}
    with pytest.raises(BlockedError, match="without the original verification requests"):
        _compare_candidate_parent(parent, candidate, successor, {}, baselines, comparison["successor_score"])
    requests = {
        "parent_verification_request": str(parent_dir / "request.json"),
        "verification_request": str(successor_dir / "request.json"),
    }
    review = _compare_candidate_parent(
        parent, candidate, successor, requests, baselines, comparison["successor_score"],
    )
    assert review is not None and list(review["path_changes"]) == ["project_root"]
    requests["verification_request"] = requests["parent_verification_request"]
    with pytest.raises(ValidationError, match="request changed"):
        _compare_candidate_parent(
            parent, candidate, successor, requests, baselines, comparison["successor_score"],
        )


def test_release_confirmation_backend_relocation_requires_frozen_inventory(tmp_path, project_root):
    evidence = project_root / "docs/evidence"
    archive = evidence / "invsqrt-roadmap-archive-20261108"
    verification = read_json(archive / "verification.json")
    settings = {**read_json(archive / "request.json")["backend"], "project_root": "/confirmation/source"}
    local = tmp_path / "confirmation-backend.json"
    write_json(local, settings)
    protocol: dict[str, object] = {"backend_hash": identity(settings)}
    hashes_ = verification["artifact_hashes"]
    contract = load_contract(project_root / "contracts/contract.json")
    release = {
        "artifact_hashes": hashes_,
        "contract_hash": contract.hash,
        "candidate": {
            "artifacts": {"invsqrt.kmb": {"origin": "generated"}},
            "confirmations": {"invsqrt": {"status": "passed", "protocol": protocol}},
        },
    }
    supporting: dict[str, object] = dict.fromkeys(
        ("cost_breakdown", "numerical_margins", "mutation_diagnostics", "primitive_scope",
         "representation_stability", "opportunity_decision"), {"test": "backend binding"},
    )
    supporting.update(
        coverage_counts=verification["official_results"]["coverage_counts"],
        accepted_reference_costs=read_json(evidence / "invsqrt-chemistry-20261107/combined-result.json")["reference"],
        verification_request=str(archive / "request.json"),
        benchmark_evidence={"invsqrt": {
            "component_hashes": {"invsqrt.kmb": hashes_["invsqrt.kmb"]},
            **dict.fromkeys(("opportunity", "numerical", "mutation", "primitive", "stability"), "fixture"),
        }},
    )
    with pytest.raises(BlockedError, match="lacks matching backend evidence"):
        certify_release(release, verification, contract, supporting_evidence=supporting)
    protocol["backend_inventory"] = {"path": str(local), "sha256": sha256(local)}
    certified = certify_release(release, verification, contract, supporting_evidence=supporting)
    assert list(certified["confirmation_backend_reviews"]["invsqrt"]["path_changes"]) == ["project_root"]
    write_json(local, {**settings, "project_root": "/changed"}, replace=True)
    with pytest.raises(ValidationError, match="inventory changed"):
        certify_release(release, verification, contract, supporting_evidence=supporting)


def test_legacy_hybrid_certificate_keeps_its_parent_schema(project_root):
    contract = load_contract(project_root / "contracts/contract.json")
    certificate = read_json(project_root / "docs/evidence/invsqrt-direct-hybrid-20261107/certificate.json")
    replay = certify_release(
        certificate, certificate["verification"], contract, supporting_evidence=certificate["supporting_evidence"],
    )
    assert replay == certificate


def test_cli_blocked_contract_exits_nonzero_and_help_is_real(project_root, tmp_path):
    # A fixed unresolved fixture keeps this regression valid after the real G0 contract resolves.
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "contract.json").write_text(json.dumps({"schema_version": 1, "fields": {}}))
    run = subprocess.run(
        [sys.executable, "-m", "qcompile", "--root", str(tmp_path), "contract", "validate"],
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
    supporting: dict[str, object] = {
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
