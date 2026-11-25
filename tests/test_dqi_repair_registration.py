from importlib import import_module
from pathlib import Path

import pytest

from qcompile.io import read_json, sha256, write_json


def test_repair_registration_binds_original_batch_offsets(project_root, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    campaign = import_module("dqi_repair_campaign")
    monkeypatch.setattr(campaign, "validate_backend", lambda _settings: None)
    backend = tmp_path / "backend.json"
    settings = {"fixture": "portable registration only"}
    write_json(backend, settings)
    banked = tmp_path / "banked.kmb"
    banked.write_bytes(b"banked fixture")
    bank_sha = sha256(banked)
    bank_record = tmp_path / "member.json"
    write_json(bank_record, {"sha256": bank_sha, "source_sha256": "source fixture"})
    history = tmp_path / "salts.json"
    write_json(history, {"salts": [f"{index:064x}" for index in range(8)]})
    next_salt = iter(f"{index:064x}" for index in range(16))
    monkeypatch.setattr(campaign.secrets, "token_hex", lambda _count: next(next_salt))
    builds = [tmp_path / name for name in ("a", "b")]
    for directory in builds:
        directory.mkdir()
        artifact = directory / "dqi.kmb"
        artifact.write_bytes(b"candidate fixture")
        write_json(directory / "build.json", {
            "circuit_sha256": sha256(artifact), "banked_d4_sha256": bank_sha,
            "source_sha256": "source fixture", "backend_sha256": sha256(backend), "scan_count": 4095,
        })

    profile = tmp_path / "profile.json"
    write_json(profile, {
        "circuit_sha256": bank_sha, "homogeneous_ablation": [],
        "batch_receipts": {"s2": {"batches": {f"batch-{start:06}.json": "fixture" for start in range(0, 1024, 256)}}},
        "profiles": [
            {"draw": "s2", "index": start + 7, "phase_error": True, "value_error": False}
            for start in range(0, 1024, 256)
        ],
    })
    matched = tmp_path / "matched.json"
    replay = {
        "banked_sha256": bank_sha, "candidate_sha256": sha256(builds[0] / "dqi.kmb"), "shots": 1024,
        "build_sha256": sha256(builds[0] / "build.json"), "profile_sha256": sha256(profile),
        "backend_inventory_sha256": campaign.backend_pin(settings),
        "batches": [
            {"draw": "s2", "batch_start": start, "banked": {"phase_offsets": [7], "value_offsets": []},
             "candidate": {key: [] for key in ("phase_offsets", "value_offsets", "mask_offsets", "dirty_offsets")}}
            for start in range(0, 1024, 256)
        ],
    }
    replay["batches"][0]["banked"]["phase_offsets"] = [8]
    write_json(matched, replay)
    output = tmp_path / "registration.json"
    with pytest.raises(ValueError, match="fixed batch regression"):
        campaign.register(backend, bank_record, banked, builds, matched, profile, output)
    assert not output.exists()
    replay["batches"][0]["banked"]["phase_offsets"] = [7]
    write_json(matched, replay, replace=True)
    campaign.register(backend, bank_record, banked, builds, matched, profile, output)
    result = read_json(output)
    assert result["salts"] == [f"{index:064x}" for index in range(8, 16)]
    assert result["pins"]["control_profile"] == sha256(profile)


def test_open_registration_requires_two_exact_builds_and_clean_fixtures(project_root, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    campaign = import_module("dqi_open_campaign")
    monkeypatch.setattr(campaign, "validate_backend", lambda _settings: None)

    def pin(path):
        return {"path": path.as_posix(), "sha256": sha256(path)}

    backend = tmp_path / "backend.json"
    write_json(backend, {})
    banked = tmp_path / "banked.kmb"
    banked.write_bytes(b"banked")
    builds = []
    for name in ("a", "b"):
        path = tmp_path / f"{name}.kmb"
        path.write_bytes(b"candidate")
        receipt = tmp_path / f"{name}.json"
        write_json(receipt, {"artifact": pin(path)})
        builds.append(pin(receipt))
    prior = tmp_path / "history.json"
    write_json(prior, {"salts": [f"{index:064x}" for index in range(8)]})
    preflight = tmp_path / "preflight.json"
    write_json(preflight, {
        "builds": builds,
        "artifacts": {"banked": pin(banked), "candidate": pin(tmp_path / "a.kmb")},
        "backend_inventory_sha256": campaign.paired.backend_pin({}),
        "evidence": {"member_registration": pin(prior), "historical_registration": pin(prior)},
    })
    errors = ("phase_offsets", "value_offsets", "dirty_offsets", "mask_offsets")
    clean = dict.fromkeys(errors, [])
    candidate = {
        "matched_clean": True, "panels_clear_ceiling": True,
        "archived": [clean] * 6, "targeted": [clean] * 4, "panels": [{}, {}],
    }
    report = {
        "registration_sha256": sha256(preflight), "native_gate_passed": True,
        "roles": {"candidate": candidate},
    }
    evidence = tmp_path / "native.json"
    campaign_path, ledger = tmp_path / "campaign.json", tmp_path / "ledger"
    candidate["targeted"][0] = {**clean, "dirty_offsets": [7]}
    write_json(evidence, report)
    with pytest.raises(ValueError, match="passing native preflight"):
        campaign.register(preflight, evidence, backend, ledger, campaign_path)
    assert not campaign_path.exists()
    candidate["targeted"][0] = clean
    archived = candidate["archived"].pop()
    write_json(evidence, report, replace=True)
    with pytest.raises(ValueError, match="passing native preflight"):
        campaign.register(preflight, evidence, backend, ledger, campaign_path)
    candidate["archived"].append(archived)
    write_json(evidence, report, replace=True)
    second = tmp_path / "b.kmb"
    second.write_bytes(b"changed candidate")
    with pytest.raises(ValueError, match="changed since registration"):
        campaign.register(preflight, evidence, backend, ledger, campaign_path)
    second.write_bytes(b"candidate")
    candidates = iter(f"{index:064x}" for index in range(16))
    monkeypatch.setattr(campaign.secrets, "token_hex", lambda _count: next(candidates))
    campaign.register(preflight, evidence, backend, ledger, campaign_path)
    salts = [f"{index:064x}" for index in range(8, 16)]
    assert read_json(campaign_path)["salts"] == salts
    assert read_json(ledger / "development-salts.json") == dict.fromkeys(salts, sha256(campaign_path))


def test_paired_evaluation_rejects_a_stale_draw_before_resuming(project_root, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    paired = import_module("dqi_repair_campaign")
    import_module("dqi_development")
    import_module("vendor_dqi_price")
    monkeypatch.setattr(paired, "validate_backend", lambda _settings: None)
    monkeypatch.setattr(paired.importlib, "import_module", lambda _name: object())
    settings = {"kickmix_root": "", "verifiers_root": ""}
    backend = tmp_path / "backend.json"
    write_json(backend, settings)
    banked, candidate = tmp_path / "banked.kmb", tmp_path / "candidate.kmb"
    banked.write_bytes(b"banked")
    candidate.write_bytes(b"candidate")
    registration = tmp_path / "registration.json"
    salts = [f"{index:064x}" for index in range(8)]
    driver = paired.__file__
    assert driver is not None
    write_json(registration, {
        "pins": {"driver": sha256(Path(driver)), "backend": paired.backend_pin(settings),
                 "banked": sha256(banked), "candidate": sha256(candidate)},
        "salts": salts,
        "shots": paired.SHOTS,
    })
    output = tmp_path / "campaign"
    write_json(output / "banked/s1.json", {
        "registration_sha256": sha256(registration), "salt": salts[1], "role": "banked",
        "result": {"circuit_sha256": sha256(banked), "verified_shots": paired.SHOTS},
    })
    with pytest.raises(ValueError, match="Unexpected verifier result identity"):
        paired.evaluate(registration, backend, banked, candidate, output, 1, "banked", draw_limit=2)
    assert not (output / "banked/s2.json").exists()
