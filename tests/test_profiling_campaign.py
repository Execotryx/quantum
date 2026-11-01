import copy
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from typing import Any

import pytest

from qcompile.campaign import (
    completed_stages,
    run_campaign,
    safe_member,
    validate_campaign,
    validate_run,
    verify_bundle,
)
from qcompile.errors import ValidationError
from qcompile.profiling import ResourceSampler, StageRecorder, terminate_tree


def test_observation_preserves_return_and_exception_identity(tmp_path):
    profile = StageRecorder(tmp_path)
    result, error = object(), ValueError("actual source error")

    def actual(value):
        if value is error:
            raise error
        return value

    observed = profile.wrap(actual, "delegate", "scoring")
    assert observed(result) is result
    with pytest.raises(ValueError) as caught:
        observed(error)
    assert caught.value is error
    profile.stream.close()
    assert json.loads((tmp_path / f"current-{profile.pid}.json").read_text())["stage"] is None
    events = [
        json.loads(line) for line in (tmp_path / f"events-{profile.pid}.jsonl").read_text().splitlines()
    ]
    assert [e["status"] for e in events if e["event"] == "end"] == ["passed", "ValueError"]


def test_nested_stages_have_nonduplicated_exclusive_times(tmp_path):
    profile = StageRecorder(tmp_path)
    with profile.stage("reader", "parsing"):
        with profile.stage("digest", "hashing"):
            hashlib.sha256(b"x" * (1 << 20)).digest()
        with profile.stage("cpu_control", "simulation"):
            assert sum(i * i for i in range(500000)) > 0
    profile.stream.close()
    events = completed_stages(tmp_path)
    root = next(event for event in events if event["name"] == "reader")
    children = [event for event in events if event["parent_id"] == root["id"]]
    assert root["wall_seconds_inclusive"] >= sum(event["wall_seconds_inclusive"] for event in children)
    assert sum(event["wall_seconds_exclusive"] for event in events) == pytest.approx(
        root["wall_seconds_inclusive"]
    )
    assert next(event for event in events if event["name"] == "cpu_control")["self_cpu_seconds"] > 0


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="actual Linux procfs control")
def test_sampler_observes_allocated_grandchild_memory(tmp_path):
    child_code = "import time; data=bytearray(b'x'*(24<<20)); print('ready',flush=True); time.sleep(20)"
    parent_code = (
        "import subprocess,sys,time; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}],stdout=subprocess.PIPE,text=True); "
        "child.stdout.readline(); print(child.pid,flush=True); time.sleep(20)"
    )
    process = subprocess.Popen([sys.executable, "-u", "-c", parent_code], stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None
        assert int(process.stdout.readline()) > 0
        sampler = ResourceSampler(process.pid, tmp_path, 0.05)
        sampler.start()
        time.sleep(0.25)
        summary = sampler.stop()
        assert summary["peak_process_count"] >= 2
        assert summary["peak_pss_bytes"] >= 24 << 20
        assert summary["peak_summed_rss_bytes"] >= summary["peak_pss_bytes"]
        assert summary["peak_pss_plus_swap_bytes"] >= summary["peak_pss_bytes"]
        assert summary["samples"] > 0
    finally:
        terminate_tree(process.pid)
        process.wait(timeout=5)


def test_preregistration_rejects_confirmation_and_non_aab_salts(project_root):
    config = json.loads((project_root / "configs/baseline-campaign-v1.json").read_text())
    validate_campaign(config)
    with pytest.raises(ValidationError, match="confirmation"):
        validate_campaign(config | {"seed_role": "confirmation"})
    altered = copy.deepcopy(config)
    altered["runs"][2]["salt"] = altered["runs"][0]["salt"]
    with pytest.raises(ValidationError, match="A,A,B"):
        validate_campaign(altered)
    with pytest.raises(ValidationError, match="three"):
        validate_campaign(config | {"runs": None})


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux campaign requirement")
def test_dirty_committed_checkout_cannot_start_campaign(tmp_path, project_root):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source = tmp_path / "source.txt"
    source.write_text("original")
    subprocess.run(["git", "-C", str(tmp_path), "add", "source.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "test fixture",
        ],
        check=True,
    )
    source.write_text("local edit")
    config = json.loads((project_root / "configs/baseline-campaign-v1.json").read_text())
    with pytest.raises(ValidationError, match="clean committed"):
        run_campaign(tmp_path, config, tmp_path / "output")
    assert source.read_text() == "local edit"
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "damage", ["dirty", "coverage", "lock", "salt", "artifact", "divisor", "role", "benchmark"]
)
def test_incomplete_or_stale_official_results_cannot_pass_campaign(damage):
    registration: dict[str, Any] = {
        "source_revision": "source",
        "dependency_lock_sha256": "lock",
        "artifact_hashes": {"circuit": "bytes"},
        "backend_hash": "backend",
        "contract_hash": "contract",
        "expected_coverage": dict.fromkeys(("invsqrt", "dqi", "dfthcsos"), 100),
    }
    report: dict[str, Any] = {
        "status": "passed",
        "complete": True,
        "tier": "full",
        "environment": {"dirty": False, "source_revision": "source", "dependency_lock_sha256": "lock"},
        "artifact_hashes": {"circuit": "bytes"},
        "backend_hash": "backend",
        "contract_hash": "contract",
        "seed_policy": {"salt": "salt", "role": "official_local"},
        "role": "official_local",
        "official_results": {
            "completed": True,
            "verification_shot_divisor": 1,
            "raw_verifier_results": {
                name: {"status": "PASS", "verified_shots": 100} for name in ("invsqrt", "dqi", "dfthcsos")
            },
            "costs": dict.fromkeys(("invsqrt", "dqi", "dfthcsos"), 1.0),
        },
    }
    validate_run(report, registration, "salt")
    if damage == "dirty":
        report["environment"]["dirty"] = True
    elif damage == "coverage":
        report["official_results"]["raw_verifier_results"]["invsqrt"]["verified_shots"] = 99
    elif damage == "lock":
        report["environment"]["dependency_lock_sha256"] = "other"
    elif damage == "salt":
        report["seed_policy"]["salt"] = "other"
    elif damage == "artifact":
        report["artifact_hashes"] = {}
    elif damage == "role":
        report["role"] = "confirmation"
    elif damage == "benchmark":
        report["official_results"]["raw_verifier_results"].pop("dqi")
    else:
        report["official_results"]["verification_shot_divisor"] = 1024
    with pytest.raises(ValidationError):
        validate_run(report, registration, "salt")


def test_bundle_mutation_is_rejected(tmp_path):
    original = b"actual diagnostic fixture"
    expected = hashlib.sha256(original).hexdigest()
    for name, payload in (("good", original), ("changed", b"changed diagnostic")):
        path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(path, "x") as archive:
            archive.writestr("baseline-manifest.json", json.dumps({"members": {"data.txt": expected}}))
            archive.writestr("data.txt", payload)
    assert verify_bundle(tmp_path / "good.zip")["members"]["data.txt"] == expected
    with pytest.raises(ValidationError, match="member changed"):
        verify_bundle(tmp_path / "changed.zip")


@pytest.mark.parametrize("name", ["../data", "/data", "C:/data", "a\\data", "a/./data"])
def test_bundle_paths_are_relative_and_portable(name):
    with pytest.raises(ValidationError, match="unsafe"):
        safe_member(name)
