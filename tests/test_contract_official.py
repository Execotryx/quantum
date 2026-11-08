import copy
from typing import Any

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.assets import pin_backend
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.contract import Contract, load_contract
from qcompile.errors import BlockedError, ValidationError
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import METRIC_V10_SHA256, review_backend_pair, validate_backend, verify_candidate
from qcompile.worker import mapped_confirmation, mapped_coverage


def test_review_backend_pair_binds_receipts_and_accepts_only_path_changes(tmp_path):
    backend = {
        "metric_sha256": METRIC_V10_SHA256,
        "metric_version": 10,
        "verifiers_files": {"verify.py": "a" * 64},
        "kickmix_files": {"kickmix.so": "b" * 64},
        "project_root": "/first",
    }

    def make_receipt(name, settings):
        request = tmp_path / f"{name}.json"
        bindings = {
            "tier": "full", "contract_hash": "c" * 64,
            "seed_policy": {"role": "official_local", "salt": "d" * 64}, "environment": {},
        }
        write_json(request, {**bindings, "backend": settings, "artifacts": {"invsqrt.kmb": {"sha256": "e" * 64}}})
        return {
            **bindings, "kind": "official_metric_execution", "status": "passed", "complete": True,
            "role": "official_local",
            "backend_hash": identity(settings), "request_hash": sha256(request),
            "artifact_hashes": {"invsqrt.kmb": "e" * 64},
        }, request

    left, left_path = make_receipt("left", backend)
    right, right_path = make_receipt("right", {**backend, "project_root": "/second"})
    result = review_backend_pair(left, left_path, right, right_path)
    assert result["left_backend_hash"] != result["right_backend_hash"]
    assert result["path_changes"] == {"project_root": {"left": "/first", "right": "/second"}}
    with pytest.raises(ValidationError, match="request changed"):
        review_backend_pair(left, right_path, right, right_path)
    with pytest.raises(ValidationError, match="differs from its request"):
        review_backend_pair({**left, "artifact_hashes": {}}, left_path, right, right_path)
    changed, changed_path = make_receipt("changed", {**backend, "kickmix_files": {"kickmix.so": "f" * 64}})
    with pytest.raises(ValidationError, match="inventories differ beyond paths"):
        review_backend_pair(left, left_path, changed, changed_path)


def test_contract_is_visibly_blocked_and_missing_fields_cannot_disappear(project_root):
    # Force an unresolved fixture: the real contract may become reconciled as G0 progresses.
    data = copy.deepcopy(load_contract(project_root / "contracts/contract.json").data)
    data["fields"]["dqi.classical_binding"]["status"] = "unresolved"
    data["sources"].pop("reference", None)
    contract = Contract(data)
    blockers = contract.blockers(project_root)
    assert any("dqi.classical_binding" in b for b in blockers)
    assert any("reference" in b for b in blockers)
    with pytest.raises(BlockedError, match="G0 contract blocked"):
        contract.require_ready(project_root)
    damaged = copy.deepcopy(contract.data)
    del damaged["fields"]["dqi.modulus"]
    assert any(
        "missing required contract field: dqi.modulus" in b for b in Contract(damaged).blockers(project_root)
    )


def test_changed_official_source_cannot_remain_reconciled(tmp_path):
    source = tmp_path / "verifier.txt"
    source.write_text("original official fixture")
    data = {
        "schema_version": 1,
        "fields": {
            "dqi.modulus": {
                "value": 4179,
                "status": "reconciled",
                "release_critical": True,
                "official": {"path": source.name, "sha256": sha256(source), "location": "field.modulus"},
            }
        },
    }
    contract = Contract(data)
    assert not any("changed official provenance" in item for item in contract.blockers(tmp_path))
    source.write_text("changed official fixture")
    assert "missing or changed official provenance: dqi.modulus" in contract.blockers(tmp_path)


def test_changed_supplementary_source_blocks_reconciliation(tmp_path):
    primary, supplementary = tmp_path / "metric.txt", tmp_path / "verifier.txt"
    primary.write_text("schema imports a dimension")
    supplementary.write_text("dimension = 76")
    data = {
        "schema_version": 1,
        "fields": {
            "chemistry.npz_schema": {
                "value": 76,
                "status": "reconciled",
                "release_critical": True,
                "official": {"path": primary.name, "sha256": sha256(primary), "location": "npz_spec"},
                "supplementary_official": [
                    {"path": supplementary.name, "sha256": sha256(supplementary), "location": "ORBITALS"}
                ],
            }
        },
    }
    contract = Contract(data)
    assert not any("supplementary provenance" in item for item in contract.blockers(tmp_path))
    supplementary.write_text("dimension = 77")
    assert "missing or changed supplementary provenance: chemistry.npz_schema" in contract.blockers(tmp_path)


def test_additional_declared_source_is_also_pinned(tmp_path):
    source = tmp_path / "backend-inventory.json"
    source.write_text("original inventory")
    contract = Contract(
        {
            "schema_version": 1,
            "fields": {},
            "sources": {
                "verifiers": {"path": source.name, "sha256": sha256(source), "origin": "official fixture"}
            },
        }
    )
    assert "unpinned source: verifiers" not in contract.blockers(tmp_path)
    source.write_text("changed inventory")
    assert "unpinned source: verifiers" in contract.blockers(tmp_path)


def test_resolved_discrepancy_requires_unchanged_evidence(tmp_path):
    source = tmp_path / "actual-result.json"
    source.write_text("actual completed result")
    contract = Contract(
        {
            "schema_version": 1,
            "fields": {},
            "discrepancies": [
                {
                    "id": "baseline-validity",
                    "status": "resolved",
                    "release_critical": True,
                    "resolution": "measured reference acceptance",
                    "official": {"path": source.name, "sha256": sha256(source), "location": "status"},
                }
            ],
        }
    )
    issue = "unverified discrepancy resolution: baseline-validity"
    assert issue not in contract.blockers(tmp_path)
    source.write_text("changed result")
    assert issue in contract.blockers(tmp_path)


def test_backend_inventory_rejects_changes_and_ignores_only_bytecode(tmp_path, monkeypatch):
    metric = tmp_path / "metric.ipynb"
    metric.write_text("{}")
    for role in ("verifiers", "kickmix"):
        root = tmp_path / role
        root.mkdir()
        (root / "source.py").write_text("# TEST ONLY")
    monkeypatch.setattr("qcompile.assets.METRIC_V10_SHA256", sha256(metric))
    monkeypatch.setattr("qcompile.official.METRIC_V10_SHA256", sha256(metric))
    config = pin_backend(metric, tmp_path / "verifiers", tmp_path / "kickmix", tmp_path / "backend.json")
    validate_backend(config)
    cache = tmp_path / "verifiers/__pycache__"
    cache.mkdir()
    (cache / "source.pyc").write_bytes(b"ignored cache")
    validate_backend(config)
    (tmp_path / "verifiers/source.py").write_text("# changed")
    with pytest.raises(BlockedError, match="inventory mismatch"):
        validate_backend(config)


def test_official_verification_missing_backend_cannot_pass(tmp_path, artifact_set, project_root):
    contract = load_contract(project_root / "contracts/contract.json")
    backend = {
        "metric_notebook": str(tmp_path / "absent.ipynb"),
        "metric_sha256": read_json(project_root / "contracts/sources.lock.json")["sources"]["metric"][
            "sha256"
        ],
    }
    seed = {"role": "official_local", "salt": "0" * 32, "distribution": "test-only"}
    with pytest.raises(BlockedError, match="unavailable"):
        verify_candidate(artifact_set, contract, "full", seed, backend, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_actual_counter_mapping_never_invents_coverage():
    results = {"dqi": {"sample": {"n": 102400, "k": 3}}}
    assert mapped_confirmation(results, {"benchmark": "dqi", "n": "sample.n", "k": "sample.k"}) == {
        "n": 102400,
        "k": 3,
    }
    assert mapped_coverage(results, {"dqi": {"completed": "sample.n"}}) == {"dqi": {"completed": 102400}}
    assert mapped_confirmation(results, None) is None
    with pytest.raises(KeyError):
        mapped_confirmation(results, {"benchmark": "dqi", "n": "missing", "k": "sample.k"})
    with pytest.raises(ValueError, match="actual integer"):
        mapped_coverage({"dqi": {"n": True}}, {"dqi": {"completed": "n"}})


def test_confirmation_sums_disjoint_official_failure_counters():
    results = {"dqi": {"verified_shots": 102400, "value_errors": 2, "phase_errors": 3}}
    mapping = {"benchmark": "dqi", "n": "verified_shots", "k": ["value_errors", "phase_errors"]}
    assert mapped_confirmation(results, mapping) == {"n": 102400, "k": 5}
    with pytest.raises(ValueError, match="nonempty and distinct"):
        mapped_confirmation(results, mapping | {"k": ["phase_errors", "phase_errors"]})
    with pytest.raises(ValueError, match="exceed completed"):
        mapped_confirmation(results, mapping | {"n": "value_errors"})


@pytest.mark.official
def test_acquired_metric_real_npz_preflight_differential(tmp_path, project_root):
    """Real v10 notebook preflight only. This is NOT a circuit/baseline run."""
    lock = read_json(project_root / "contracts/sources.lock.json")["sources"]["metric"]
    path = project_root / lock["path"]
    if not path.exists():
        pytest.skip("acquire the pinned official notebook to run this preflight differential")
    assert sha256(path) == lock["sha256"]
    notebook = read_json(path)
    source = "\n\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    scope: dict[str, Any] = {"__name__": "test_only_official_preflight"}
    exec(compile(source, str(path), "exec"), scope)
    data = {
        "U": np.ones((1, 1, 76)),
        "W": np.ones((1, 1, 1)),
        "H2_I": np.ones((1, 1)),
        "H1_I": np.array(0.0),
        "Hsym_lower": np.zeros(2926),
        "tree_edges": np.zeros((75, 2), dtype=np.int64),
    }
    good = tmp_path / "good.npz"
    deterministic_npz(good, data)
    ours = read_factorization(good)
    actual = scope["read_npz"](good, SPEC)
    for key in data:
        np.testing.assert_array_equal(ours[key], actual[key])
    bad = tmp_path / "bad.npz"
    np.savez(
        bad,
        U=data["U"],
        W=data["W"],
        H2_I=data["H2_I"],
        H1_I=np.array([0.0]),
        Hsym_lower=data["Hsym_lower"],
        tree_edges=data["tree_edges"],
    )
    with pytest.raises(ValueError, match="shape"):
        scope["read_npz"](bad, SPEC)
    with pytest.raises(ValidationError, match="shape"):
        read_factorization(bad)
