from pathlib import Path

import pytest

from qcompile.errors import BlockedError, ValidationError
from qcompile.experiments import CandidateStore, opportunity_decision, validate_budget

ENV = {"source_revision": "a" * 40, "dirty": False, "dependency_lock_sha256": "b" * 64}


def create(tmp_path, artifact_set):
    store = CandidateStore(tmp_path / "store")
    artifact_set = {
        name: {**item, "origin": "generated" if name == "dqi.kmb" else "retained_reference"}
        for name, item in artifact_set.items()
    }
    record = store.create(
        {"hypothesis": "unit-test-only"},
        "c" * 64,
        artifact_set,
        ENV,
        [{"kind": "exact_algorithm_intent", "assumptions": "synthetic test only"}],
    )
    return store, record


def bound(record, **extra):
    return {
        "artifact_hashes": record["artifact_hashes"],
        "contract_hash": record["contract_hash"],
        "passed": True,
        **extra,
    }


def protocol(salt="fresh-one-use-confirmation-salt-1234567890"):
    return {
        "benchmark": "dqi",
        "sample_size": 100,
        "max_failures": 0,
        "distribution": "test-only prescribed fixture",
        "confidence_procedure": "fixed threshold, registered before observation",
        "stop_rule": "one run",
        "compute_allowance": {"seconds": 30},
        "seed_policy": {"role": "confirmation", "salt": salt, "distribution": "test-only fixture"},
    }


def test_no_skipping_states_and_changed_bytes_invalidate(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    with pytest.raises(ValidationError, match="skip"):
        store.advance(record["id"], "full_local_passed", bound(record))
    store.advance(
        record["id"],
        "numerically_feasible",
        bound(record, kind="independent_numerical", report_sha256="d" * 64),
    )
    Path(artifact_set["dqi.kmb"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValidationError, match="bytes changed"):
        store.get(record["id"])


def test_report_binding_and_incomplete_evidence(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    bad = bound(record, kind="independent_numerical", report_sha256="e" * 64)
    bad["contract_hash"] = "f" * 64
    with pytest.raises(ValidationError, match="different artifacts or contract"):
        store.advance(record["id"], "numerically_feasible", bad)
    store.advance(
        record["id"],
        "numerically_feasible",
        bound(record, kind="independent_numerical", report_sha256="e" * 64),
    )
    with pytest.raises(ValidationError, match="complete official"):
        store.advance(record["id"], "circuit_smoke_passed", bound(record, kind="estimate", complete=False))


def test_full_requires_actual_frozen_source(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    store.advance(
        record["id"],
        "numerically_feasible",
        bound(record, kind="independent_numerical", report_sha256="e" * 64),
    )
    smoke = bound(
        record,
        kind="official_metric_execution",
        status="passed",
        complete=True,
        tier="smoke",
        role="official_local",
        environment=ENV,
    )
    store.advance(record["id"], "circuit_smoke_passed", smoke)
    dirty = bound(
        record,
        kind="official_metric_execution",
        status="passed",
        complete=True,
        tier="full",
        role="official_local",
        environment={**ENV, "dirty": True},
    )
    with pytest.raises(BlockedError, match="dirty source"):
        store.advance(record["id"], "full_local_passed", dirty)


def test_failed_confirmation_cannot_be_rerolled_even_with_new_config(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    p = protocol()
    store.register_confirmation(record["id"], p)
    result = store.finish_confirmation(
        record["id"],
        bound(
            record,
            role="confirmation",
            seed_policy=p["seed_policy"],
            complete=True,
            observed={"n": 100, "k": 1},
        ),
    )
    assert result["confirmation"]["status"] == "failed"
    second = store.create(
        {"hypothesis": "rename same bytes"},
        "c" * 64,
        record["artifacts"],
        ENV,
        [{"kind": "exact_algorithm_intent", "assumptions": "test"}],
    )
    with pytest.raises(ValidationError, match="failed frozen bytes"):
        store.register_confirmation(second["id"], protocol("different-independent-salt-1234567890"))


def test_confirmation_registered_before_results_and_sample_size_checked(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    p = protocol()
    report = bound(
        record, role="confirmation", seed_policy=p["seed_policy"], complete=True, observed={"n": 100, "k": 0}
    )
    with pytest.raises(ValidationError, match="registered before"):
        store.finish_confirmation(record["id"], report)
    store.register_confirmation(record["id"], p)
    with pytest.raises(ValidationError, match="incomplete"):
        store.finish_confirmation(record["id"], {**report, "observed": {"n": 99, "k": 0}})
    store.finish_confirmation(record["id"], report)
    result = store.consume_confirmation(record["id"], "used the results for a tuning decision")
    assert result["confirmation"]["status"] == "consumed_for_tuning"


def test_no_reusing_salt_for_changed_bytes(tmp_path, artifact_set):
    store, record = create(tmp_path, artifact_set)
    store.register_confirmation(record["id"], protocol())
    second = store.create(
        {"hypothesis": "other experiment"},
        "c" * 64,
        record["artifacts"],
        ENV,
        [{"kind": "exact_algorithm_intent", "assumptions": "test"}],
    )
    with pytest.raises(ValidationError, match="salt has already"):
        store.register_confirmation(second["id"], protocol())


def test_opportunity_budget_and_decision_gate():
    config = {
        "hypothesis": "cost gain",
        "parameter_ranges": [1, 2],
        "correctness_conditions": "all pass",
        "objective": "full cost",
        "stop_rule": "bounded",
        "minimum_gain": 0.01,
        "budget": {
            "max_experiments": 2,
            "max_wall_seconds": 10,
            "max_compute_seconds": 10,
            "engineer_hours": 1,
        },
    }
    validate_budget(config)
    with pytest.raises(ValidationError, match="budget"):
        validate_budget({**config, "budget": {}})
    estimate = dict(
        original_work="measured estimate", added_verification="priced", compute_delays="accounted"
    )
    assert opportunity_decision(config, [{"kind": "proxy"}], 100, estimate)["decision"] == "no_go"
    good = {"kind": "official_complete_cost", "compatible": True, "feasible": True, "cost": 90}
    assert opportunity_decision(config, [good], 100, estimate)["decision"] == "go"
    assert opportunity_decision(config, [{**good, "cost": 101}], 100, estimate)["decision"] == "no_go"
