from importlib import import_module
from types import SimpleNamespace

import pytest

from qcompile.io import read_json, sha256, write_json


def test_bank_rechecks_registered_full_draws(monkeypatch, tmp_path, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    bank = import_module("vendor_dqi_bank")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bank, "validate_backend", lambda _: None)
    api = SimpleNamespace(
        DEFAULT_LOG2_DELTA=-128,
        clopper_pearson_upper_bound=lambda fails, shots, delta: fails / shots,
        repetition_overhead=lambda rate: 1 + rate,
    )
    monkeypatch.setattr(bank, "importlib", SimpleNamespace(import_module=lambda _: api))
    source = tmp_path / "third_party/dqi-d4/SOURCE.json"
    write_json(source, {"component": "test fixture"})
    artifact = tmp_path / "dqi.kmb"
    artifact.write_bytes(b"circuit")
    digest = sha256(artifact)
    build_receipts = {}
    for name in ("a", "b"):
        path = tmp_path / name / "regeneration.json"
        write_json(path, {"status": "go", "sha256": digest, "source_sha256": sha256(source)})
        build_receipts[str(path)] = sha256(path)
    backend = tmp_path / "backend.json"
    settings = {"kickmix_root": "kickmix", "verifiers_root": "verifiers"}
    write_json(backend, settings)
    registration = tmp_path / "salts.json"
    salts = [f"{i:064x}" for i in range(8)]
    write_json(registration, {
        "backend_inventory_sha256": bank.backend_pin(settings), "salts": salts, "shots": bank.SHOTS,
        "candidates": {"d4": {"artifact": str(artifact), "sha256": digest, "build_receipts": build_receipts}},
    })
    pin = sha256(registration)
    run = tmp_path / "run"
    result = {
        "status": "PASS", "circuit_sha256": digest, "verified_shots": bank.SHOTS,
        "value_errors": 0, "phase_errors": 0, "log2_delta": -128,
        "num_qubits": 897, "toffoli_count": 430_000.0,
    }
    for i, salt in enumerate(salts, 1):
        write_json(run / f"d4/s{i}.json", {
            "candidate": "d4", "registration_sha256": pin, "salt": salt, "result": result,
        })
    price = bank.pooled_price([result] * 8, api)
    ratio = bank.REFERENCE / price["cost"]
    zero = result["num_qubits"] ** 2 * result["toffoli_count"]
    write_json(run / "decision.json", {
        "status": "go", "banked": True, "selected": "d4", "sha256": digest,
        "registration_sha256": pin, "pooled_ratio": ratio, "stage2": [{
            **price, "candidate": "d4", "qubits": 897, "mean_toffolis": 430_000.0, "zero_failure_cost": zero,
        }],
    })
    destination = tmp_path / "member.json"
    bank.bank(registration, backend, run, destination)
    assert read_json(destination)["sha256"] == digest
    last = run / "d4/s8.json"
    receipt = read_json(last)
    write_json(last, {**receipt, "salt": salts[0]}, replace=True)
    with pytest.raises(ValueError, match="invalid selected draw 8"):
        bank.bank(registration, backend, run, tmp_path / "invalid.json")
