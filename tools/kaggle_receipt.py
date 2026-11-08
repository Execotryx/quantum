"""Prepare a verified archive and reconcile its external score without uploading."""

import argparse
import csv
import hashlib
import io
import re
import shutil
import subprocess
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

from dqi_development import TRIAL_SHOTS, validate_schedule
from hybrid_preflight import preflight

from qcompile.component_confirmations import has_full_hybrid_coverage
from qcompile.io import read_json, sha256, write_json
from qcompile.official import METRIC_V10_SHA256
from qcompile.reference.scoring import aggregate, cp_upper, repetition

COMPETITION = "google-verifiable-quantum-circuit-compilation"
METRIC = "metric/google-quantum-ai-metric"
BAND = Decimal("0.00001")
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DQI = "959471d05a26373b4f14ca0cae2d8639ea25f18170d9f6532139aa51ccc04995"


def score(value) -> Decimal:
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("expected a positive finite score") from error
    if not number.is_finite() or number <= 0:
        raise ValueError("expected a positive finite score")
    return number


def submission_message(label: str, digest: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", label):
        raise ValueError("use a single label of at most 40 letters, digits, periods, underscores or hyphens")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("expected a SHA-256 archive digest")
    return f"{label} {digest[:12]}"


def read_submission(csv_text: str, message: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text.removeprefix("\ufeff")))
    if not {"fileName", "date", "description", "status", "publicScore"} <= set(reader.fieldnames or ()):
        raise ValueError("unexpected submission CSV columns")
    matching = [row for row in reader if row["description"] == message]
    if len(matching) != 1:
        raise ValueError(f"expected one submission matching the bound message, found {len(matching)}")
    row = matching[0]
    if row["status"].rsplit(".", 1)[-1].lower() not in {"complete", "completed"}:
        raise ValueError("matching submission has no terminal score")
    if row["fileName"] != "submission.zip":
        raise ValueError("matching submission has a different archive filename")
    score(row["publicScore"])
    submitted = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
    if submitted.tzinfo is None:
        submitted = submitted.replace(tzinfo=UTC)
    return {
        "submission_ref": row.get("ref") or None,
        "submission_message": row["description"],
        "submitted_at_utc": submitted.astimezone(UTC).isoformat(),
        "scored_at_utc": None,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "kaggle_public_score": row["publicScore"],
    }


def band_result(record: dict) -> dict:
    local = score(record["local_score"])
    public = score(record["kaggle_public_score"])
    kind = record["archive_class"]
    if kind == "exact":
        lower, upper = local - BAND, local + BAND
    elif kind == "failure_priced":
        low, high = map(score, record["local_score_range"])
        if low > high:
            raise ValueError("reversed score range")
        lower, upper = low - BAND, high + BAND
    else:
        raise ValueError("unsupported archive class")
    result = {
        "delta": str(public - local),
        "band": {"min": str(lower), "max": str(upper)},
        "reconciled": lower <= public <= upper,
    }
    if kind == "failure_priced" and public < lower and record.get("dqi_pricing"):
        dqi = record["dqi_pricing"]
        target = float(local / public) ** 3 * dqi["anchor_cost"] / dqi["q_squared_t"]
        shots = dqi["shots"]
        start, stop = 0, shots
        while start < stop:
            k = (start + stop) // 2
            upper_error = cp_upper(k, shots)
            if upper_error >= 1 / 16 or repetition(upper_error) >= target:
                stop = k
            else:
                start = k + 1
        result["implied_local_equivalent_failures"] = start
        result["promotion_disposition"] = "reprice_registered_draws_at_k_max_plus_2"
    return result


def require_metric(notebook: Path) -> str:
    actual = sha256(notebook)
    if actual != METRIC_V10_SHA256:
        raise ValueError(f"published metric drift: expected {METRIC_V10_SHA256}, observed {actual}")
    return actual


def run_cli(executable: str, *args: str) -> str:
    return subprocess.run([executable, *args], capture_output=True, text=True, check=True, timeout=180).stdout


def matched_score_range(directory: Path, certificate: dict) -> dict:
    registration_path = directory / "registration.json"
    registered = read_json(registration_path)["config"]
    validate_schedule(registered)
    if registered.get("dqi_kind") != "failure_priced":
        raise ValueError("score range requires a registered failure-priced DQI campaign")
    verification = certificate["verification"]
    costs = verification["official_results"]["costs"]
    raw = verification["official_results"]["raw_verifier_results"]["dqi"]
    candidate = certificate["artifact_hashes"]["dqi.kmb"]
    if candidate != raw["circuit_sha256"] or candidate != registered["candidate"]["sha256"]:
        raise ValueError("multi-salt campaign is for a different DQI artifact")
    baselines = certificate["supporting_evidence"]["accepted_reference_costs"]
    scores = []
    receipts = []
    failures = []
    for index, trial in enumerate(registered["trials"]):
        if trial["role"] != "full_development":
            continue
        lane = directory / f"trial-{index:02}"
        receipt_path = lane / "candidate.json"
        receipt = read_json(receipt_path)
        cases = read_json(lane / "cases.json")
        if (
            read_json(lane / "status.json")["status"] != "complete"
            or read_json(lane / "trial.json") != trial or cases["salt"] != trial["salt"]
            or receipt["status"] != "PASS" or receipt["circuit_sha256"] != candidate
            or receipt["verified_shots"] != TRIAL_SHOTS["full_development"]
            or cases["shots"] != receipt["verified_shots"]
        ):
            raise ValueError(f"incomplete or unbound full DQI development receipt for lane {index}")
        scores.append(aggregate(baselines, {**costs, "dqi": receipt["score"]}))
        receipts.append(sha256(receipt_path))
        counts = receipt["value_errors"], receipt["phase_errors"]
        if any(type(value) is not int or value < 0 for value in counts) or sum(counts) > receipt["verified_shots"]:
            raise ValueError(f"invalid disjoint DQI failure counts for lane {index}")
        failures.append(sum(counts))
    pricing_path = directory / "pricing.json"
    pricing = read_json(pricing_path)
    if (
        pricing["status"] != "priced" or pricing["failures_by_salt"] != failures
        or pricing["k_max"] != max(failures) or pricing["priced_failures"] != max(failures) + 2
    ):
        raise ValueError("missing conservative full-development DQI price")
    return {
        "local_score_range": [str(min(scores)), str(max(scores))],
        "dqi_pricing": {
            "shots": raw["verified_shots"], "q_squared_t": raw["num_qubits"] ** 2 * raw["toffoli_count"],
            "anchor_cost": costs["dqi"], "registration_sha256": sha256(registration_path),
            "pricing_sha256": sha256(pricing_path), "receipt_sha256": receipts,
        },
    }


def prepare(
    release: Path,
    label: str,
    output: Path,
    backend: Path,
    ledger: Path,
    executable: str,
    *,
    exact_dqi: bool = False,
    dqi_campaign: Path | None = None,
) -> None:
    records = {path.name: read_json(path) for path in ledger.glob("*.json")}
    superseded = {row["supersedes"] for row in records.values() if row.get("supersedes")}
    if any(row.get("archive_class") == "exact" and row.get("reconciled") is False
           for name, row in records.items() if name not in superseded):
        raise ValueError("an exact external score remains outside its reconciliation band")
    certificate_path = release.resolve() / "certificate.json"
    certificate_digest = sha256(certificate_path)
    certificate = read_json(certificate_path)
    verification = certificate["verification"]
    archive = certificate_path.with_name("submission.zip")
    digest = sha256(archive)
    if (
        certificate["status"] != "locally_verified_awaiting_kaggle_acceptance"
        or not certificate["two_builds_identical"]
        or certificate["zip_sha256"] != digest or verification["status"] != "passed"
        or verification["tier"] != "full" or verification["complete"] is not True
    ):
        raise ValueError("archive does not bind a complete local release certificate")
    local = score(certificate["predicted_aggregate_score"])
    raw_dqi = verification["official_results"]["raw_verifier_results"]["dqi"]
    reference_dqi = raw_dqi["circuit_sha256"] == REFERENCE_DQI
    if exact_dqi and not reference_dqi and (
        certificate.get("candidate", {}).get("config", {}).get("dqi_kind") != "exact"
        or raw_dqi["value_errors"] != 0 or raw_dqi["phase_errors"] != 0
    ):
        raise ValueError("optimized DQI needs a registered exact classification and a zero-error archive pass")
    if dqi_campaign is not None and (exact_dqi or reference_dqi):
        raise ValueError("choose either an exact classification or a failure-priced range")
    if not (exact_dqi or reference_dqi or dqi_campaign is not None):
        raise ValueError("optimized DQI requires an explicit exact classification or a registered multi-salt campaign")
    pricing = matched_score_range(dqi_campaign, certificate) if dqi_campaign is not None else {}
    message = submission_message(label, digest)
    version = run_cli(executable, "--version").strip()
    if not version:
        raise ValueError("could not identify the Kaggle CLI version")
    with TemporaryDirectory(prefix="qcompile-preflight-") as temp:
        scratch = Path(temp)
        run_cli(executable, "kernels", "pull", METRIC, "-p", str(scratch), "-m")
        metric_hash = require_metric(scratch / "google-quantum-ai-metric.ipynb")
        check_dir = scratch / "preflight"
        preflight(archive, backend, check_dir)
        check = read_json(check_dir / "preflight.json")
        if (
            check["archive_sha256"] != digest or check["metric_sha256"] != metric_hash
            or check["members"] != certificate["artifact_hashes"]
            or check["members"] != verification["artifact_hashes"]
            or not has_full_hybrid_coverage(verification, check["expected_full_coverage"])
            or sha256(certificate_path) != certificate_digest
        ):
            raise ValueError("release or metric evidence changed before preparation")
        output.mkdir(parents=True, exist_ok=False)
        prepared = output / "submission.zip"
        shutil.copyfile(archive, prepared)
        if sha256(prepared) != digest:
            prepared.unlink()
            raise ValueError("copied submission bytes differ from the local certificate")
        shutil.copyfile(check_dir / "preflight.json", output / "preflight.json")
        write_json(output / "prepared.json", {
            "submission_message": message, "zip_sha256": digest, "zip_bytes": prepared.stat().st_size,
            "binding": "direct", "kaggle_cli_version": version, "local_score": str(local),
            "local_certificate": {"path": str(certificate_path), "sha256": certificate_digest},
            "metric_sha256": metric_hash, "archive_class": "exact" if dqi_campaign is None else "failure_priced",
            **pricing,
            "preflight_sha256": sha256(output / "preflight.json"),
        })
    print(message)


def bound_preparation(directory: Path) -> dict:
    record = read_json(directory / "prepared.json")
    archive = directory / "submission.zip"
    certificate = record["local_certificate"]
    if (
        archive.stat().st_size != record["zip_bytes"] or sha256(archive) != record["zip_sha256"]
        or sha256(Path(certificate["path"])) != certificate["sha256"]
        or sha256(directory / "preflight.json") != record["preflight_sha256"]
    ):
        raise ValueError("prepared archive, local certificate or preflight changed")
    return record


def record_submission(directory: Path, executable: str) -> None:
    prepared = bound_preparation(directory)
    version = run_cli(executable, "--version").strip()
    if not version:
        raise ValueError("could not identify the Kaggle CLI version")
    listing = run_cli(executable, "competitions", "submissions", COMPETITION, "--csv", "--quiet")
    write_json(directory / "observed.json", {
        "prepared_sha256": sha256(directory / "prepared.json"),
        "receipt_kaggle_cli_version": version,
        "listing_sha256": hashlib.sha256(listing.encode()).hexdigest(),
        **read_submission(listing, prepared["submission_message"]),
    })


def reconcile(directory: Path, ledger: Path, supersedes: str | None = None) -> Path:
    prepared = bound_preparation(directory)
    observed = read_json(directory / "observed.json")
    if (observed["prepared_sha256"] != sha256(directory / "prepared.json")
        or observed["submission_message"] != prepared["submission_message"]):
        raise ValueError("external observation binds a different preparation")
    record = {**prepared, **observed}
    submission_date = datetime.fromisoformat(record["submitted_at_utc"]).date()
    stem = f"{submission_date}-{record['zip_sha256'][:12]}"
    if supersedes is not None:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9a-f]{12}(?:-[0-9a-f]{12})?\.json", supersedes):
            raise ValueError("invalid superseded ledger filename")
        old = read_json(ledger / supersedes)
        if old["zip_sha256"] != record["zip_sha256"] or old["submission_ref"] != record["submission_ref"]:
            raise ValueError("correction must identify the same upload")
        stem += "-" + sha256(directory / "observed.json")[:12]
        record["supersedes"] = supersedes
    destination = ledger / f"{stem}.json"
    write_json(destination, {**record, **band_result(record)})
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("release", type=Path)
    setup.add_argument("--label", required=True)
    setup.add_argument("--output", type=Path, required=True)
    setup.add_argument("--backend", type=Path, default=ROOT / "vendor/backend.json")
    setup.add_argument("--exact-dqi", action="store_true")
    setup.add_argument("--dqi-campaign", type=Path)
    observe = commands.add_parser("record")
    compare = commands.add_parser("reconcile")
    for action in (observe, compare):
        action.add_argument("directory", type=Path)
    for action in (setup, observe):
        action.add_argument("--kaggle", default="kaggle")
    for action in (setup, compare):
        action.add_argument("--ledger", type=Path, default=ROOT / "docs/evidence/kaggle")
    compare.add_argument("--supersedes")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.release, args.label, args.output, args.backend, args.ledger, args.kaggle,
                exact_dqi=args.exact_dqi, dqi_campaign=args.dqi_campaign)
    elif args.action == "record":
        record_submission(args.directory, args.kaggle)
    else:
        print(reconcile(args.directory, args.ledger, args.supersedes))


if __name__ == "__main__":
    main()
