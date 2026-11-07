"""Rebuild, verify and certify the pinned hybrid and its direct-phasing successor."""

import argparse
import secrets
import sys
from math import isclose
from pathlib import Path

from hybrid_parent_audit import EVIDENCE, HISTORICAL_CHEMISTRY, HISTORICAL_INVSQRT, audit
from invsqrt_direct import ROOT, require, run_job
from invsqrt_direct_hybrid import accepted_component

from qcompile.artifacts import deterministic_zip, extract_archive
from qcompile.component_confirmations import component_hashes, fail_fast_observed, has_full_hybrid_coverage
from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.experiments import CandidateStore
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import verify_candidate
from qcompile.release import build_candidate, certify_release

BACKEND = ROOT / "vendor/backend.json"
PARENT_MANIFEST = EVIDENCE / "archive.json"
PARENT_RESULT = EVIDENCE / "combined-result.json"
PARENT_RECIPE = ROOT / "tools/hybrid_parent_recipes.py"
CANDIDATES = ROOT / "runs/candidates"


def bundle_artifacts(directory: Path, member_hashes: dict, *, successor: bool) -> dict:
    return {
        name: {
            "path": str((directory / name).resolve()),
            "sha256": digest,
            "origin": "retained_reference"
            if name in ("dqi.kmb", "dfthcsos/submission.npz")
            else "retained_certified"
            if successor and name.startswith("dfthcsos/")
            else "generated",
            "provenance": "Hash-bound member of the verified hybrid archive",
        }
        for name, digest in member_hashes.items()
    }


def prepare_parent(output: Path) -> None:
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    environment = capture(ROOT)
    require(not environment["dirty"], "parent build requires clean committed source")
    pinned = read_json(PARENT_MANIFEST)
    original = HISTORICAL_CHEMISTRY / "invsqrt-chemistry.zip"
    require(sha256(original) == pinned["sha256"], "original hybrid ZIP changed")
    output.mkdir(parents=True, exist_ok=False)
    extract_archive(original, output / "inputs", expected=pinned["hashes"])
    artifacts = bundle_artifacts(output / "inputs", pinned["hashes"], successor=False)
    lock = ROOT / "uv.lock"
    words = ROOT / "runs/step3-chemistry/recovered-words.npz"
    recipes = []
    for benchmark, names, inputs in (
        (
            "invsqrt",
            ["invsqrt.kmb"],
            [ROOT / "configs/invsqrt-opportunity-v1.json", ROOT / "tools/invsqrt_opportunity.py"],
        ),
        (
            "dfthcsos",
            [name for name in artifacts if name.startswith("dfthcsos/angle_k_")],
            [words, ROOT / "tools/banked_chemistry.py"],
        ),
    ):
        recipes.append(
            {
                "argv": [sys.executable, str(PARENT_RECIPE), benchmark, "{output_dir}"],
                "outputs": names,
                "inputs": {
                    str(path): sha256(path)
                    for path in (PARENT_RECIPE, BACKEND, PARENT_MANIFEST, lock, *inputs)
                },
            }
        )
    for name in ("build-a", "build-b"):
        files = build_candidate({"artifacts": artifacts, "build_recipes": recipes}, contract, output / name)
        archive = output / f"{name}.zip"
        deterministic_zip(archive, files)
        require(sha256(archive) == pinned["sha256"], "parent ZIP differs from the verified archive")
    extract_archive(output / "build-b.zip", output / "extracted", expected=pinned["hashes"])
    review = audit(require, output / "extracted")
    write_json(output / "historical-confirmations.json", review)
    write_json(
        output / "registration.json",
        {
            "archive_sha256": pinned["sha256"],
            "artifact_hashes": pinned["hashes"],
            "recipe_identity": identity(recipes),
            "source_environment": environment,
            "historical_confirmations_sha256": sha256(output / "historical-confirmations.json"),
            "seed_policy": {
                "role": "official_local",
                "salt": secrets.token_hex(32),
                "distribution": "Pinned full metric on the exact rebuilt parent extraction",
            },
        },
    )


def measure_parent(output: Path) -> None:
    registration = read_json(output / "registration.json")
    require(
        registration["archive_sha256"] == sha256(output / "build-b.zip"),
        "parent archive changed after registration",
    )
    settings = read_json(BACKEND)
    contract = load_contract(ROOT / "contracts/contract.json")
    artifacts = bundle_artifacts(output / "extracted", registration["artifact_hashes"], successor=False)
    policy = registration["seed_policy"]
    result = verify_candidate(
        artifacts, contract, "full", policy, settings, output / "verification", timeout=3600
    )
    require(
        result["complete"] and result["status"] == "passed" and has_full_hybrid_coverage(result),
        "parent full verification did not complete",
    )
    previous = read_json(PARENT_RESULT)
    for benchmark, cost in result["official_results"]["costs"].items():
        require(
            isclose(cost, previous["costs"][benchmark], rel_tol=1e-12), f"parent {benchmark} cost changed"
        )


def import_confirmation(store, candidate, benchmark, reviewed, backend_hash: str) -> None:
    raw = reviewed["raw"]
    observed = fail_fast_observed(benchmark, raw)
    registration = reviewed["registration"]
    seed = {
        "role": "confirmation",
        "salt": registration["salt"],
        "distribution": "Pinned verifier distribution, independently registered on frozen bytes",
    }
    policy = {
        "benchmark": benchmark,
        "sample_size": observed["n"],
        "max_failures": 0,
        "backend_hash": backend_hash,
        "seed_policy": seed,
        "distribution": seed["distribution"],
        "confidence_procedure": "Full pinned coverage and fail-fast acceptance",
        "stop_rule": "One frozen registered confirmation",
        "compute_allowance": {"seconds": 3600},
        "historical_receipt_sha256": identity(reviewed),
        "verifier_artifact_sha256": raw.get("submission_sha256", raw.get("circuit_sha256")),
    }
    existing = store.confirmation_for(candidate["id"], benchmark)
    if existing["status"] == "not_run":
        store.register_confirmation(candidate["id"], policy)
    else:
        require(existing.get("protocol") == policy, "registered confirmation differs from reviewed receipt")
        if existing["status"] == "passed":
            store.require_confirmation(store.get(candidate["id"]), benchmark)
            return
        require(existing["status"] == "registered", "cannot reuse a failed or consumed confirmation")
    store.finish_confirmation(
        candidate["id"],
        {
            "artifact_hashes": candidate["artifact_hashes"],
            "contract_hash": candidate["contract_hash"],
            "complete": True,
            "benchmark": benchmark,
            "role": "confirmation",
            "seed_policy": seed,
            "backend_hash": backend_hash,
            "component_hashes": component_hashes(candidate["artifact_hashes"], benchmark),
            "raw_benchmark": raw,
            "observed": observed,
            "reviewed": reviewed,
        },
        benchmark=benchmark,
    )


def evidence_for(record: dict, supporting: dict, key: str) -> dict:
    return {
        "passed": True,
        "contract_hash": record["contract_hash"],
        "artifact_hashes": record["artifact_hashes"],
        "evidence": supporting[key],
    }


def evidence_files(output: Path, record: dict, supporting: dict) -> dict:
    refs = {}
    for name in ("g0", "g1", "opportunity", "mutations", "stability", "improvement"):
        path = output / "evidence" / f"{name}.json"
        write_or_match(path, evidence_for(record, supporting, name))
        refs[name] = {"path": str(path), "sha256": sha256(path)}
    return refs


def write_or_match(path: Path, payload: dict) -> None:
    if path.exists():
        require(read_json(path) == payload, f"immutable evidence differs: {path}")
    else:
        write_json(path, payload)


def advance_or_match(store, candidate_id: str, state: str, evidence: dict) -> dict:
    record = store.get(candidate_id)
    completed = [entry for entry in record["history"] if entry["to"] == state]
    if completed:
        require(
            len(completed) == 1 and completed[0]["evidence"] == evidence, f"recorded {state} evidence differs"
        )
        return record
    return store.advance(candidate_id, state, evidence)


def supporting_evidence(output: Path, hashes: dict, result: dict, screen: Path | None) -> dict:
    baseline = read_json(PARENT_RESULT)["reference"]
    assert all(value > 0 for value in baseline.values())
    step3 = read_json(ROOT / "docs/evidence/step3-completion.json")
    require(
        step3["gates"] == {"G0": "passed", "G1": "passed"} and step3["all_members_verified"],
        "independent prerequisite gates are incomplete",
    )
    bundle = Path(step3["bundle"])
    require(sha256(bundle) == step3["sha256"], "independent validation bundle changed")
    chemistry = read_json(EVIDENCE / "screen.json")
    require(
        chemistry["status"] == "go"
        and chemistry["chemistry"]["words_exact"]
        and chemistry["rebuild_identical"]
        and chemistry["chemistry"]["resources"]["angles_within_cap"],
        "chemistry supporting screen failed",
    )
    inv_directory = screen if screen is not None else HISTORICAL_INVSQRT
    inv_decision = read_json(inv_directory / "decision.json")
    inv_lane = inv_directory / inv_decision["winner"]
    inv = read_json(inv_lane / "result.json")
    require(
        inv_decision["winner_sha256"] == hashes["invsqrt.kmb"] and inv["margins"]["nonpositive_margins"] == 0,
        "inverse-square-root supporting screen differs",
    )
    evdir = ROOT / "docs/evidence"
    benchmarks = {}
    for name, screen_data, numerical, primitive in (
        ("invsqrt", inv_decision, inv["margins"], inv["native"] if screen else inv["native_development"]),
        ("dfthcsos", chemistry, chemistry["chemistry"]["metrics"], chemistry["xor_fixtures"]),
    ):
        mutation = read_json(
            evdir / f"step3-{'invsqrt' if name == 'invsqrt' else 'chemistry'}-rejections.json"
        )
        benchmarks[name] = {
            "component_hashes": component_hashes(hashes, name),
            "opportunity": screen_data,
            "numerical": numerical,
            "primitive": primitive,
            "mutation": mutation,
            "stability": {"two_archive_builds": sha256(output / "build-a.zip")},
        }
    costs = result["official_results"]["costs"]
    require(all(costs[n] < baseline[n] for n in benchmarks), "optimized benchmark did not improve")
    return {
        "g0": step3,
        "g1": step3,
        "opportunity": {n: b["opportunity"] for n, b in benchmarks.items()},
        "mutations": {n: b["mutation"] for n, b in benchmarks.items()},
        "stability": {n: b["stability"] for n, b in benchmarks.items()},
        "improvement": {n: baseline[n] - costs[n] for n in benchmarks},
        "coverage_counts": result["official_results"]["coverage_counts"],
        "cost_breakdown": costs,
        "numerical_margins": {n: b["numerical"] for n, b in benchmarks.items()},
        "mutation_diagnostics": {n: b["mutation"] for n, b in benchmarks.items()},
        "primitive_scope": {n: b["primitive"] for n, b in benchmarks.items()},
        "representation_stability": {n: b["stability"] for n, b in benchmarks.items()},
        "opportunity_decision": {n: b["opportunity"] for n, b in benchmarks.items()},
        "accepted_reference_costs": baseline,
        "benchmark_evidence": benchmarks,
    }


def certify(output: Path, *, screen: Path | None, parent_id: str | None) -> None:
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    registration = read_json(output / "registration.json")
    expected = registration["artifact_hashes"]
    archive = output / "build-b.zip"
    digest = registration["archive_sha256"]
    require(digest == sha256(archive) == sha256(output / "build-a.zip"), "independent ZIPs differ")
    report = read_json(output / "verification/verification.json")
    require(has_full_hybrid_coverage(report), "hybrid certificate requires exact full-strength coverage")
    require(report["seed_policy"] == registration["seed_policy"], "metric used an unregistered seed")
    environment = report["environment"]
    if screen is None:
        expected_environment = registration["source_environment"]
        require(
            expected_environment["source_revision"] == environment["source_revision"],
            "parent was built and measured on different revisions",
        )
    backend_hash = identity(read_json(BACKEND))
    require(report["backend_hash"] == backend_hash, "verification backend changed")
    store = CandidateStore(CANDIDATES)
    config = {"hybrid_archive_sha256": digest}
    if screen is not None:
        if parent_id is None:
            raise ValueError("successor needs its trusted parent candidate ID")
        accepted_component(screen)
        source = screen / "confirmation"
        scopes = {
            "invsqrt": {
                "registration": read_json(source / "registration.json"),
                "raw": read_json(source / "raw-verifier.json"),
            }
        }
        parent_record = store.get(parent_id)
        parent_anchor = read_json(store.root / parent_id / "local-certificate.json")
        original = read_json(PARENT_MANIFEST)
        require(
            parent_anchor["zip_sha256"] == original["sha256"]
            and parent_record["artifact_hashes"] == original["hashes"],
            "trusted parent differs from the pinned hybrid",
        )
        config["retained_chemistry"] = {
            key: parent_anchor[key]
            for key in ("candidate_id", "zip_sha256", "certificate_sha256", "backend_hash")
        }
        config["invsqrt_cost_limit"] = registration["cost_limit"]
    else:
        reviewed = output / "historical-confirmations.json"
        require(
            sha256(reviewed) == registration["historical_confirmations_sha256"], "reviewed evidence changed"
        )
        scopes = read_json(reviewed)
    supporting = supporting_evidence(output, expected, report, screen)
    artifacts = bundle_artifacts(output / "extracted", expected, successor=screen is not None)
    record = store.create(
        config,
        contract.hash,
        artifacts,
        environment,
        [
            {
                "kind": "sampled_circuit_acceptance",
                "assumptions": "Pinned verifier on the exact local archive extraction",
            },
        ],
        resume=True,
    )
    advance_or_match(
        store,
        record["id"],
        "numerically_feasible",
        {
            "artifact_hashes": expected,
            "contract_hash": contract.hash,
            "passed": True,
            "kind": "independent_numerical",
            "report_sha256": identity(supporting["numerical_margins"]),
        },
    )
    advance_or_match(store, record["id"], "circuit_smoke_passed", report)
    advance_or_match(store, record["id"], "full_local_passed", report)
    for benchmark, reviewed in scopes.items():
        import_confirmation(store, record, benchmark, reviewed, backend_hash)
    record = advance_or_match(
        store,
        record["id"],
        "release_selected",
        {
            "artifact_hashes": expected,
            "contract_hash": contract.hash,
            "passed": True,
            **evidence_files(output, record, supporting),
        },
    )
    release = {
        "archive_sha256": digest,
        "zip_sha256": digest,
        "artifact_hashes": expected,
        "contract_hash": contract.hash,
        "candidate": record,
        "candidate_id": record["id"],
        "source_environment": environment,
        "two_builds_identical": True,
        "remote_accepted": False,
    }
    if screen is not None:
        release["parent"] = store.require_chemistry_parent(record)
    certificate = certify_release(release, report, contract, supporting_evidence=supporting)
    write_or_match(output / "certificate.json", certificate)
    store.record_local_certificate(record["id"], output / "certificate.json")
    print(record["id"], certificate["predicted_aggregate_score"], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare-parent", "measure-parent", "parent-worker", "certify"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--screen", type=Path)
    parser.add_argument("--parent-id")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.action == "prepare-parent":
        prepare_parent(output)
    elif args.action == "parent-worker":
        measure_parent(output)
    elif args.action == "measure-parent":
        code = run_job([sys.executable, __file__, "parent-worker", str(output)], output, 3900)
        require(code == 0, f"parent metric failed; inspect {output / 'execution.log'}")
    else:
        certify(output, screen=args.screen, parent_id=args.parent_id)


if __name__ == "__main__":
    main()
