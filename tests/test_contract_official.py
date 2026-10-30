import copy

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.assets import pin_backend
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.contract import Contract, load_contract
from qcompile.errors import BlockedError, ValidationError
from qcompile.io import read_json, sha256
from qcompile.official import validate_backend, verify_candidate
from qcompile.worker import mapped_confirmation, mapped_coverage


def test_contract_is_visibly_blocked_and_missing_fields_cannot_disappear(project_root):
    contract = load_contract(project_root / "contracts/contract.json")
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
    scope = {"__name__": "test_only_official_preflight"}
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
    np.savez(bad, **(data | {"H1_I": np.array([0.0])}))
    with pytest.raises(ValueError, match="shape"):
        scope["read_npz"](bad, SPEC)
    with pytest.raises(ValidationError, match="shape"):
        read_factorization(bad)
