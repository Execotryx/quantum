from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace

import pytest

from qcompile.component_confirmations import BENCHMARKS, HYBRID_COVERAGE, component_hashes
from qcompile.io import sha256, write_json
from qcompile.portfolio import ABOVE_34, ABOVE_36, bind_lineage, portfolio_target


def test_portfolio_binds_two_builds_and_each_component(tmp_path):
    members = {
        "invsqrt.kmb": "1" * 64,
        "dqi.kmb": "2" * 64,
        "dfthcsos/submission.npz": "3" * 64,
        **{f"dfthcsos/angle_k_{k}.kmb": "4" * 64 for k in range(19)},
    }
    declaration = {}
    for name in BENCHMARKS:
        source = tmp_path / f"{name}-source.json"
        write_json(source, {"component": name})
        receipts = []
        for build in range(2):
            receipt = tmp_path / f"{name}-build-{build}.json"
            write_json(receipt, {
                "build": build,
                "source_sha256": sha256(source),
                "members": component_hashes(members, name),
            })
            receipts.append(receipt.name)
        declaration[name] = {"source": source.name, "builds": receipts}
    lineage = tmp_path / "lineage.json"
    write_json(lineage, declaration)
    record = {"artifact_hashes": members, **bind_lineage(lineage, members)}
    assert record["format"] == ABOVE_34
    assert portfolio_target(record) == 34
    assert len(record["components"]["dfthcsos"]["members"]) == 20

    successor = {"artifact_hashes": members, **bind_lineage(lineage, members, minimum_score=36)}
    assert successor["format"] == ABOVE_36
    assert portfolio_target(successor) == 36

    for key, value in (("minimum_score", 20), ("minimum_score", 36),
                       ("format", "portfolio-v999"), ("components", {})):
        altered = {**record, key: value}
        with pytest.raises(ValueError):
            portfolio_target(altered)

    altered = deepcopy(record)
    altered["artifact_hashes"]["dfthcsos/angle_k_18.kmb"] = "0" * 64
    with pytest.raises(ValueError, match="lineage"):
        portfolio_target(altered)

    declaration["dqi"]["builds"][1] = declaration["dqi"]["builds"][0]
    write_json(lineage, declaration, replace=True)
    with pytest.raises(ValueError, match="build receipt"):
        bind_lineage(lineage, members)


def test_portfolio_legacy_registration_promotes_above_twenty():
    assert portfolio_target({"archive_sha256": "a" * 64}) == 20


def test_portfolio_preflight_reports_native_serialization_failure(project_root, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    angle_summary = import_module("hybrid_preflight").angle_summary
    for index in range(15):
        (tmp_path / f"angle_k_{index}.kmb").write_bytes(b"0" * (index + 1))
    layout = SimpleNamespace(batch_size=5, selection=range(11), brot=7)
    circuits = SimpleNamespace(register_layout=lambda _: layout, _reject_rotations=lambda _: None)
    chemistry = SimpleNamespace(QUBIT_CAP=128)
    calls = []

    def read_circuit(path, _cap):
        def serialize(_stream, **_kwargs):
            calls.append(path.name)
            raise ValueError("Failed to write to file.")

        return SimpleNamespace(num_qubits=128, to_file=serialize)

    with pytest.raises(ValueError, match="native ANGLE serialization"):
        angle_summary(tmp_path, 15, 9, 127, read_circuit, chemistry, circuits, check_serialization=True)
    assert calls == ["angle_k_14.kmb"]


@pytest.mark.parametrize("minimum_score,version", [(34, ABOVE_34), (36, ABOVE_36)])
@pytest.mark.parametrize("margin", [0, 1])
def test_certificate_requires_both_role_scores_strictly_above_target(
    project_root, tmp_path, monkeypatch, minimum_score, version, margin
):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    audit = import_module("dqi_aggregate_audit").audit
    archive = tmp_path / "test.zip"
    archive.write_bytes(b"synthetic archive for the report audit only")
    members = {"invsqrt.kmb": "1" * 64, "dqi.kmb": "2" * 64,
               "dfthcsos/submission.npz": "3" * 64, "dfthcsos/angle_k_0.kmb": "4" * 64}
    coverage = {**HYBRID_COVERAGE, "dfthcsos": (76 + 9 * 127) * 64}
    preflight = tmp_path / "preflight.json"
    shape = {"archive_sha256": sha256(archive), "members": members, "metric_sha256": "m",
             "checks": {"dfthcsos": {"shape": [9, 127, 46]}},
             "expected_full_coverage": coverage}
    write_json(preflight, shape)
    registration = tmp_path / "registration.json"
    salts = {"metric": "metric", "confirmation": "confirmation"}
    write_json(registration, {
        "format": version, "minimum_score": minimum_score,
        "archive_sha256": shape["archive_sha256"], "metric_sha256": "m",
        "artifact_hashes": members, "salts": salts,
        "baseline_costs": dict.fromkeys(BENCHMARKS, minimum_score),
        "components": {
            name: {"source_sha256": "a" * 64, "build_receipt_sha256": ["b" * 64, "c" * 64],
                   "members": component_hashes(members, name)}
            for name in BENCHMARKS
        },
    })
    for role, verification_role, score in (("metric", "official_local", minimum_score + 1),
                                           ("confirmation", "confirmation", minimum_score + margin)):
        root = tmp_path / role
        request = root / "verification/request.json"
        report = root / "verification/verification.json"
        costs = dict.fromkeys(BENCHMARKS, minimum_score / score)
        write_json(root / "preflight.json", shape)
        seed_policy = {"salt": salts[role]}
        write_json(request, {"backend": {"metric_sha256": "m"}, "seed_policy": seed_policy,
                             "tier": "full", "expected_coverage": coverage,
                             "artifacts": {name: {"sha256": digest} for name, digest in members.items()}})
        write_json(report, {
            "request_hash": sha256(request), "role": verification_role, "status": "passed",
            "complete": True, "tier": "full", "artifact_hashes": members,
            "seed_policy": seed_policy,
            "official_results": {
                "completed": True, "verification_shot_divisor": 1,
                "coverage_counts": {name: {"completed": count, "expected": count}
                                    for name, count in coverage.items()},
                "costs": costs,
            },
        })
        write_json(root / "decision.json", {
            "registration_sha256": sha256(registration), "archive_sha256": sha256(archive),
            "metric_sha256": "m", "role": role, "verification_sha256": sha256(report),
            "status": "go", "aggregate": score, "costs": costs,
        })
    certificate = tmp_path / "certificate.json"
    if margin == 0:
        with pytest.raises(ValueError, match=f"confirmation.*above {minimum_score}"):
            audit(registration, archive, preflight, tmp_path, certificate)
        assert not certificate.exists()
    else:
        audit(registration, archive, preflight, tmp_path, certificate)
        assert f"verified_above_{minimum_score}" in certificate.read_text()
