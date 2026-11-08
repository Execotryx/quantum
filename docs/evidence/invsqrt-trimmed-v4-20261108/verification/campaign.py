import secrets
import subprocess
import sys
from math import isclose
from pathlib import Path

from invsqrt_direct import EXPECTED_SHOTS, backend, pins, require, run_job

from qcompile.environment import capture
from qcompile.io import read_json, sha256, write_json

out = Path(__file__).resolve().parent
root = Path.cwd()
environment = capture(root)
require(not environment["dirty"], "campaign source must be clean")
driver = Path(__file__).resolve()
screen_path = out / "screen-registration.json"
if len(sys.argv) == 1:
    files = (
        "src/qcompile/invsqrt/trimmed.py", "tools/invsqrt_trimmed.py",
        "tools/invsqrt_trimmed_price.py", "tools/invsqrt_trimmed_trace.py",
        "docs/evidence/invsqrt-trimmed-v4-20261108/price.json",
        "docs/evidence/invsqrt-trimmed-v4-20261108/control-trace.json",
    )
    record = {
        "environment": environment, "driver_sha256": sha256(driver),
        "inputs": {**pins(4), **{name: sha256(Path(name)) for name in files}},
        "control_sha256": "c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9",
        "control_cost": 509471.48180735623, "minimum_gain": 0.05,
        "candidate_sha256": "f4c8503d87c9e7cedb8a79a796e0b195623c2e88467691ca1b08af1a70fb200d",
        "expected_shots": EXPECTED_SHOTS, "worst_tolerance_limit": 0.90,
        "native_workers": 10, "worker_seconds": 1200,
        "order": ["control-trace", "development", "development-rebuild", "full", "confirmation"],
    }
    write_json(screen_path, record)
    subprocess.run([sys.executable, "tools/invsqrt_trimmed_trace.py", out / "control-trace.json"], check=True)
    require(sha256(out / "control-trace.json") == record["inputs"][files[-1]], "v4 control trace changed")
    result_digests = {}
    for lane in ("development", "development-rebuild"):
        subprocess.run([sys.executable, "tools/invsqrt_trimmed.py", out / lane], check=True)
        evidence = out / lane / "result.json"
        result = read_json(evidence)
        require(result["sha256"] == record["candidate_sha256"] == sha256(evidence.with_name("invsqrt.kmb"))
                and result["gain_fraction"] >= record["minimum_gain"]
                and result["intermediate_bounds_checked"] == 3133452
                and result["margins"]["worst_tolerance_fraction"] <= record["worst_tolerance_limit"],
                f"{lane} did not pass")
        result_digests[lane] = sha256(evidence)
    require(len(set(result_digests.values())) == 1, "independent development results differ")
    write_json(out / "screen-decision.json", {
        "status": "go", "registration_sha256": sha256(screen_path), "lanes": result_digests,
        "winner_sha256": record["candidate_sha256"], "cost": result["cost"]["score"],
        "limit": record["control_cost"] * (1 - record["minimum_gain"]),
    })
    print("Registered candidate passed both development builds.", flush=True)
    salts = {read_json(Path(name))["salt"] for name in (
        "docs/evidence/invsqrt-roadmap-confirmation-20261108/full-registration.json",
        "docs/evidence/invsqrt-roadmap-confirmation-20261108/confirmation-registration.json")}
    for role in ("full", "confirmation"):
        salt = secrets.token_hex(32)
        require(salt not in salts, "verification salt is not fresh")
        salts.add(salt)
        stage = out / role
        stage.mkdir()
        write_json(stage / "registration.json", {
            "role": role, "artifact_sha256": record["candidate_sha256"], "salt": salt,
            "decision_sha256": sha256(out / "screen-decision.json"), "expected_shots": record["expected_shots"],
            "source_revision": environment["source_revision"],
            "preceding_full_sha256": sha256(out / "full/result.json") if role == "confirmation" else None,
        })
        require(run_job([sys.executable, str(driver), role], stage, record["worker_seconds"]) == 0,
                f"{role} failed. Inspect {stage / 'execution.log'}")
        print(role, read_json(stage / "result.json")["result"]["score"], flush=True)
else:
    record = read_json(screen_path)
    decision = read_json(out / "screen-decision.json")
    require(environment["source_revision"] == record["environment"]["source_revision"]
            and sha256(driver) == record["driver_sha256"]
            and all(sha256(Path(path)) == digest for path, digest in record["inputs"].items()),
            "registered source, driver or inputs changed")
    role = sys.argv[1]
    require(role in ("full", "confirmation"), "invalid run role")
    stage = out / role
    registration = read_json(stage / "registration.json")
    candidate = out / "development/invsqrt.kmb"
    require(registration["decision_sha256"] == sha256(out / "screen-decision.json")
            and registration["role"] == role and decision["status"] == "go"
            and registration["artifact_sha256"] == decision["winner_sha256"] == sha256(candidate),
            "frozen decision or KMB changed")
    if role == "confirmation":
        require(registration["preceding_full_sha256"] == sha256(out / "full/result.json")
                and registration["salt"] != read_json(out / "full/registration.json")["salt"],
                "confirmation lacks a distinct salt and preceding full pass")
    km, _, verifier = backend()
    observed = verifier.verify(km.Circuit.from_file(str(candidate)), verifier.ProblemSpecInvSqrt.for_n_p(10),
                               salt=registration["salt"], max_workers=record["native_workers"])
    write_json(stage / "raw-verifier.json", observed)
    require(observed["status"] == "PASS" and observed["verified_shots"] == record["expected_shots"]
            and observed["circuit_sha256"] == registration["artifact_sha256"] == sha256(candidate)
            and observed["worst_error_over_tolerance"] <= record["worst_tolerance_limit"]
            and observed["score"] <= decision["limit"]
            and isclose(observed["score"], decision["cost"], rel_tol=1e-12), f"{role} acceptance gate failed")
    write_json(stage / "result.json", {
        "result": observed, "registration_sha256": sha256(stage / "registration.json"),
        "raw_sha256": sha256(stage / "raw-verifier.json"),
    })
