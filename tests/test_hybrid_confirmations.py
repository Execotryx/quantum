import shutil

import pytest

from qcompile.component_confirmations import (
    CANDIDATE_PROFILE,
    FAIL_FAST,
    HYBRID_COVERAGE,
    component_hashes,
    review_invsqrt_confirmation,
)
from qcompile.errors import BlockedError, ValidationError
from qcompile.experiments import CandidateStore
from qcompile.io import read_json, sha256, write_json

CONTRACT = "a" * 64
BACKEND = "b" * 64


def test_reviewed_standalone_confirmation_binds_original_v5_receipts(tmp_path, project_root):
    original = project_root / "docs/evidence/invsqrt-trimmed-v4-20261108/verification"
    screen = read_json(original / "screen-registration.json")
    candidate = screen["candidate_sha256"]
    backend = screen["inputs"]["vendor/backend.json"]
    reviewed = review_invsqrt_confirmation(original, candidate, backend)
    assert reviewed["confirmation"]["raw"]["verified_shots"] == FAIL_FAST["invsqrt"]
    assert reviewed["full"]["registration"]["salt"] != reviewed["confirmation"]["registration"]["salt"]
    copy = shutil.copytree(original, tmp_path / "verification")
    registration = copy / "confirmation-registration.json"
    data = read_json(registration)
    data["preceding_full_sha256"] = "0" * 64
    write_json(registration, data, replace=True)
    with pytest.raises(ValidationError, match="standalone confirmation receipt"):
        review_invsqrt_confirmation(copy, candidate, backend)


def candidate(store, artifacts, config=None):
    return store.create(
        config or {},
        CONTRACT,
        artifacts,
        {"source_revision": "c" * 40, "dependency_lock_sha256": "d" * 64, "dirty": False},
        [{"kind": "sampled_circuit_acceptance", "assumptions": "synthetic fixture"}],
    )


def protocol(benchmark, salt):
    return {
        "benchmark": benchmark,
        "sample_size": FAIL_FAST[benchmark],
        "max_failures": 0,
        "backend_hash": BACKEND,
        "verifier_artifact_sha256": "f" * 64,
        "distribution": "fixture",
        "confidence_procedure": "fail fast",
        "stop_rule": "one attempt",
        "compute_allowance": 1,
        "seed_policy": {"role": "confirmation", "salt": salt * 32},
    }


def test_candidate_v1_standalone_scope_requires_explicit_review(tmp_path, artifact_set, monkeypatch):
    monkeypatch.setattr("qcompile.experiments.candidate_coverage", lambda _: HYBRID_COVERAGE.copy())
    store = CandidateStore(tmp_path / "store")
    record = candidate(store, artifact_set, {"verification_profile": CANDIDATE_PROFILE})
    policy = {**protocol("invsqrt", "i"), "standalone_invsqrt": {"fixture": True}}
    receipt = {**result(record, policy), "tier": "full"}
    original_raw = receipt["raw_benchmark"]
    monkeypatch.setattr(CandidateStore, "_standalone_invsqrt", staticmethod(lambda *_: original_raw))
    store.register_confirmation(record["id"], policy)
    with pytest.raises(ValidationError, match="bound standalone"):
        store.finish_confirmation(record["id"], receipt, benchmark="invsqrt")
    receipt["kind"] = "reviewed_standalone_invsqrt"
    record = store.finish_confirmation(record["id"], receipt, benchmark="invsqrt")
    assert store.require_confirmation(record, "invsqrt")["status"] == "passed"
    record["confirmations"]["invsqrt"]["evidence"]["raw_benchmark"] = {}
    with pytest.raises(BlockedError, match="stored benchmark result"):
        store.require_confirmation(record, "invsqrt")


def result(record, policy):
    benchmark = policy["benchmark"]
    n = policy["sample_size"]
    return {
        "role": "confirmation",
        "complete": True,
        "benchmark": benchmark,
        "backend_hash": BACKEND,
        "seed_policy": policy["seed_policy"],
        "contract_hash": CONTRACT,
        "artifact_hashes": record["artifact_hashes"],
        "component_hashes": component_hashes(record["artifact_hashes"], benchmark),
        "raw_benchmark": {
            "status": "PASS",
            "verified_shots": n,
            "circuit_sha256": record["artifact_hashes"]["invsqrt.kmb"],
            "submission_sha256": policy["verifier_artifact_sha256"],
        },
        "observed": {"n": n, "k": 0},
    }


def mixed(artifact_set):
    return {
        name: {
            **item,
            "origin": "retained_reference" if name in ("dqi.kmb", "dfthcsos/submission.npz") else "generated",
        }
        for name, item in artifact_set.items()
    }


def test_hybrid_requires_matching_component_scopes(tmp_path, artifact_set):
    store = CandidateStore(tmp_path / "store")
    record = candidate(store, mixed(artifact_set))
    inv = protocol("invsqrt", "i")
    chemistry = protocol("dfthcsos", "c")
    store.register_confirmation(record["id"], inv)
    store.register_confirmation(record["id"], chemistry)
    with pytest.raises(ValidationError, match="mismatch"):
        store.finish_confirmation(record["id"], result(record, chemistry), benchmark="invsqrt")
    record = store.finish_confirmation(record["id"], result(record, inv), benchmark="invsqrt")
    assert record["confirmation"]["status"] == "partial"
    with pytest.raises(BlockedError, match="unused"):
        store.require_confirmation(record, "dfthcsos")
    bad = result(record, chemistry)
    bad["raw_benchmark"]["verified_shots"] -= 1
    with pytest.raises(ValidationError, match="fail-fast"):
        store.finish_confirmation(record["id"], bad, benchmark="dfthcsos")
    record = store.finish_confirmation(record["id"], result(record, chemistry), benchmark="dfthcsos")
    assert store.require_confirmation(record, "dfthcsos")["component_hashes"]["dfthcsos/submission.npz"]
    record["confirmations"]["dfthcsos"]["protocol"]["backend_hash"] = "x" * 64
    with pytest.raises(BlockedError, match="one-use ledger"):
        store.require_confirmation(record, "dfthcsos")


def test_changed_other_component_cannot_reserve_chemistry_again(tmp_path, artifact_set):
    store = CandidateStore(tmp_path / "store")
    artifacts = mixed(artifact_set)
    parent = candidate(store, artifacts)
    store.register_confirmation(parent["id"], protocol("dfthcsos", "c"))
    alternate = tmp_path / "different-invsqrt.kmb"
    alternate.write_bytes(b"changed inverse-square-root circuit")
    changed = {
        **artifacts,
        "invsqrt.kmb": {**artifacts["invsqrt.kmb"], "path": str(alternate), "sha256": sha256(alternate)},
    }
    successor = candidate(store, changed)
    with pytest.raises(ValidationError, match="unchanged frozen bytes"):
        store.register_confirmation(successor["id"], protocol("dfthcsos", "s"))
    retained = {
        **changed,
        "dfthcsos/angle_k_0.kmb": {**changed["dfthcsos/angle_k_0.kmb"], "origin": "retained_certified"},
    }
    child = candidate(store, retained, {"retained_chemistry": {"candidate_id": parent["id"]}})
    with pytest.raises(BlockedError, match="trusted parent"):
        store.require_chemistry_parent(child)


def test_hybrid_full_receipt_can_satisfy_smoke_at_exact_coverage(tmp_path, artifact_set):
    store = CandidateStore(tmp_path / "store")
    record = candidate(store, mixed(artifact_set), {"hybrid_archive_sha256": "f" * 64})
    bound = {"artifact_hashes": record["artifact_hashes"], "contract_hash": CONTRACT, "passed": True}
    store.advance(
        record["id"],
        "numerically_feasible",
        {
            **bound,
            "kind": "independent_numerical",
            "report_sha256": "e" * 64,
        },
    )
    report = {
        **bound,
        "kind": "official_metric_execution",
        "status": "passed",
        "tier": "full",
        "complete": True,
        "role": "official_local",
        "environment": record["environment"],
    }
    with pytest.raises(ValidationError, match="complete official"):
        store.advance(record["id"], "circuit_smoke_passed", report)
    report["official_results"] = {
        "coverage_counts": {name: {"completed": n, "expected": n} for name, n in HYBRID_COVERAGE.items()}
    }
    assert store.advance(record["id"], "circuit_smoke_passed", report)["state"] == "circuit_smoke_passed"
    assert store.advance(record["id"], "full_local_passed", report)["state"] == "full_local_passed"
