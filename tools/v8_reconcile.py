"""Record the single external observation for the registered v8.0 archive."""

import argparse
from math import isclose
from pathlib import Path

from kaggle_receipt import cp_upper, read_submission, repetition, submission_message

from qcompile.component_confirmations import HYBRID_COVERAGE, has_full_hybrid_coverage
from qcompile.io import read_json, sha256, write_json
from qcompile.official import METRIC_V10_SHA256, review_verification_request
from qcompile.reference.scoring import aggregate

ROOT = Path("docs/evidence/v8/v8.0")
DQI = Path("docs/evidence/review-fixes-cloud-20261108/dqi-strength/full/result.json")


def release_evidence(archive: Path) -> tuple[dict, str, dict[str, str]]:
    registration_path = ROOT / "registration.json"
    registration = read_json(registration_path)
    digest = sha256(archive)
    if digest != registration["archive_sha256"] or archive.name != "submission.zip":
        raise ValueError("external observation requires the exact named archive")
    registration_hash = sha256(registration_path)
    if registration["metric_salt"] == registration["confirmation_salt"]:
        raise ValueError("release requires a distinct confirmation salt")
    lower, upper = registration["score_conservative"] * 0.99, registration["score_full"] * 1.01
    decisions = {}
    for role in ("metric", "confirmation"):
        directory = ROOT / role
        decision_path = directory / "decision.json"
        decision = read_json(decision_path)
        verification_path = directory / "verification/verification.json"
        verification = read_json(verification_path)
        preflight = read_json(directory / "preflight.json")
        r, b, _ = preflight["checks"]["dfthcsos"]["shape"]
        coverage = {**HYBRID_COVERAGE, "dfthcsos": (76 + r * b) * 64}
        backend = review_verification_request(verification, verification_path.with_name("request.json"))
        costs = verification["official_results"]["costs"]
        score = aggregate(registration["baseline_costs"], costs)
        if (decision["status"] != "go" or decision["registration_sha256"] != registration_hash
                or decision["verification_sha256"] != sha256(verification_path)
                or verification["seed_policy"]["salt"] != registration[f"{role}_salt"]
                or verification["role"] != ("official_local" if role == "metric" else "confirmation")
                or verification["tier"] != "full"
                or verification["artifact_hashes"] != registration["artifact_hashes"]
                or preflight["archive_sha256"] != digest or preflight["members"] != registration["artifact_hashes"]
                or backend["metric_sha256"] != METRIC_V10_SHA256
                or preflight["metric_sha256"] != METRIC_V10_SHA256
                or not has_full_hybrid_coverage(verification, coverage)
                or not lower <= score <= upper or not isclose(decision["aggregate"], score, rel_tol=1e-12)
                or any(not isclose(costs[name], registration["full_costs"][name], rel_tol=1e-9)
                       for name in ("invsqrt", "dfthcsos"))):
            raise ValueError(f"{role} evidence does not bind the registered archive")
        decisions[role] = sha256(decision_path)
    return registration, registration_hash, decisions


def reconcile(listing: Path, archive: Path, output: Path) -> None:
    registration, registration_hash, decisions = release_evidence(archive)
    digest = registration["archive_sha256"]
    observation = read_submission(listing.read_text(encoding="utf-8-sig"), submission_message("v8.0", digest))
    public = float(observation["kaggle_public_score"])
    lower, upper = registration["score_conservative"] * 0.99, registration["score_full"] * 1.01
    record = {
        **observation, "archive_sha256": digest, "registration_sha256": registration_hash,
        "decisions": decisions, "listing_sha256": sha256(listing),
        "band": {"min": lower, "max": upper}, "reconciled": lower <= public <= upper,
    }
    if public < lower:
        circuit = read_json(DQI)["result"]
        if circuit["circuit_sha256"] != registration["artifact_hashes"]["dqi.kmb"]:
            raise ValueError("routed DQI anchor differs from the registered archive")
        base = circuit["num_qubits"] ** 2 * circuit["toffoli_count"]
        costs = registration["full_costs"]
        baselines = registration["baseline_costs"]
        implied_cost = (baselines["dqi"] * (baselines["invsqrt"] / costs["invsqrt"])
                        * (baselines["dfthcsos"] / costs["dfthcsos"]) / public**3)
        shots = circuit["verified_shots"]
        low, high = 0, shots
        while low < high:
            guess = (low + high) // 2
            bound = cp_upper(guess, shots)
            if bound >= 1 / 16 or repetition(bound) * base >= implied_cost:
                high = guess
            else:
                low = guess + 1
        record["estimated_public_ratios"] = {
            "dqi": baselines["dqi"] / implied_cost,
            "invsqrt": baselines["invsqrt"] / costs["invsqrt"],
            "dfthcsos": baselines["dfthcsos"] / costs["dfthcsos"],
        }
        record["implied_local_equivalent_dqi_failures"] = low
    write_json(output, record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("listing", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    reconcile(args.listing, args.archive, args.output)
