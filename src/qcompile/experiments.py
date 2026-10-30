"""File-based candidate state machine and one-use frozen confirmation ledger."""

import csv
from contextlib import contextmanager
from pathlib import Path

from .artifacts import hashes, validate_manifest
from .errors import BlockedError, ValidationError
from .io import identity, nonnegative_int, positive_int, read_json, sha256, write_json

STATES = [
    "draft",
    "numerically_feasible",
    "circuit_smoke_passed",
    "full_local_passed",
    "release_selected",
    "remote_accepted",
]
CLAIMS = {"exact_algorithm_intent", "algebraically_proved_primitive", "sampled_circuit_acceptance"}


@contextmanager
def record_lock(root):
    lock = Path(root) / ".record-lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise BlockedError(
            f"record store busy; inspect any interrupted writer before removing {lock}"
        ) from error
    try:
        yield
    finally:
        lock.rmdir()


def validate_budget(config):
    for key in ("hypothesis", "parameter_ranges", "correctness_conditions", "objective", "stop_rule"):
        if not config.get(key):
            raise ValidationError(f"experiment registration missing {key}")
    for key in ("max_experiments", "max_wall_seconds", "max_compute_seconds", "engineer_hours"):
        value = config.get("budget", {}).get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 < value < float("inf"):
            raise ValidationError(f"missing finite positive numeric budget: {key}")
    positive_int(config["budget"]["max_experiments"], "max_experiments")
    gain = config.get("minimum_gain")
    if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not 0 <= gain < 1:
        raise ValidationError("minimum_gain must be registered as a fraction in [0,1)")


def opportunity_decision(registration, observations, baseline, estimate):
    validate_budget(registration)
    if not observations or len(observations) > registration["budget"]["max_experiments"]:
        raise ValidationError("prototype count absent or exceeds registered budget")
    for observation in observations:
        if (
            observation.get("kind") != "official_complete_cost"
            or observation.get("compatible") is not True
            or observation.get("feasible") is not True
        ):
            return {"decision": "no_go", "reason": "compatibility/feasibility/full cost not established"}
    if not estimate or not all(
        estimate.get(k) for k in ("original_work", "added_verification", "compute_delays")
    ):
        raise ValidationError("selected-path effort re-estimate is required")
    cost = min(item["cost"] for item in observations)
    if not 0 < baseline < float("inf") or not 0 < cost < float("inf"):
        raise ValidationError("invalid opportunity cost")
    gain = 1 - cost / baseline
    return {
        "decision": "go" if gain >= registration["minimum_gain"] and cost < baseline else "no_go",
        "gain": gain,
        "selected_path_estimate": estimate,
    }


class CandidateStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, candidate_id):
        if len(candidate_id) != 64 or any(c not in "0123456789abcdef" for c in candidate_id):
            raise ValidationError("invalid candidate id")
        return self.root / candidate_id / "candidate.json"

    def create(self, config, contract_hash, artifacts, environment, claims):
        validate_manifest(artifacts)
        if not claims or any(c.get("kind") not in CLAIMS or not c.get("assumptions") for c in claims):
            raise ValidationError("scoped correctness claims and assumptions are required")
        for claim in claims:
            if claim["kind"] == "algebraically_proved_primitive" and not claim.get("proof_reference"):
                raise ValidationError("a proved claim requires a proof reference")
        frozen = {
            "config": config,
            "contract_hash": contract_hash,
            "artifact_hashes": hashes(artifacts),
            "artifact_sources": {
                name: {key: item[key] for key in ("origin", "provenance")} for name, item in artifacts.items()
            },
        }
        candidate_id = identity(frozen)
        record = {
            "id": candidate_id,
            **frozen,
            "artifacts": artifacts,
            "environment": environment,
            "claims": claims,
            "state": "draft",
            "confirmation": {"status": "not_run"},
            "history": [],
        }
        write_json(self._path(candidate_id), record)
        self._index()
        return record

    def get(self, candidate_id):
        record = read_json(self._path(candidate_id))
        validate_manifest(record["artifacts"])
        frozen = {
            key: record[key] for key in ("config", "contract_hash", "artifact_hashes", "artifact_sources")
        }
        actual_sources = {
            name: {key: item[key] for key in ("origin", "provenance")}
            for name, item in record["artifacts"].items()
        }
        if (
            identity(frozen) != record["id"]
            or hashes(record["artifacts"]) != record["artifact_hashes"]
            or actual_sources != record["artifact_sources"]
        ):
            raise ValidationError("candidate identity changed")
        return record

    def _save(self, record):
        write_json(self._path(record["id"]), record, replace=True)
        self._index()

    def _index(self):
        # A convenience index; immutable records/history remain authoritative.
        rows = [read_json(path) for path in sorted(self.root.glob("*/candidate.json"))]
        with (self.root / "candidates.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", "state", "contract_hash", "confirmation"])
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {key: row[key] for key in ("id", "state", "contract_hash")}
                    | {"confirmation": row["confirmation"]["status"]}
                )

    @staticmethod
    def _bound(record, evidence):
        if (
            evidence.get("artifact_hashes") != record["artifact_hashes"]
            or evidence.get("contract_hash") != record["contract_hash"]
        ):
            raise ValidationError("evidence is bound to different artifacts or contract")

    def advance(self, candidate_id, target, evidence):
        with record_lock(self.root):
            record = self.get(candidate_id)
            if target == "rejected":
                if not evidence.get("reason"):
                    raise ValidationError("rejection reason required")
            else:
                current = record["state"]
                if (
                    current not in STATES
                    or target not in STATES
                    or STATES.index(target) != STATES.index(current) + 1
                ):
                    raise ValidationError("candidate cannot skip or reverse required states")
                self._bound(record, evidence)
                passed = (
                    evidence.get("status") == "passed"
                    if evidence.get("kind") == "official_metric_execution"
                    else evidence.get("passed") is True
                )
                if not passed:
                    raise ValidationError("passing evidence required")
                if target == "numerically_feasible":
                    if evidence.get("kind") != "independent_numerical" or not evidence.get("report_sha256"):
                        raise ValidationError("hash-bound independent numerical report required")
                elif target in ("circuit_smoke_passed", "full_local_passed"):
                    tier = "smoke" if target == "circuit_smoke_passed" else "full"
                    if (
                        evidence.get("kind") != "official_metric_execution"
                        or evidence.get("tier") != tier
                        or evidence.get("complete") is not True
                        or evidence.get("role") != "official_local"
                    ):
                        raise ValidationError("complete official local verification evidence required")
                    source = record["environment"]
                    for key in ("source_revision", "dependency_lock_sha256"):
                        if evidence.get("environment", {}).get(key) != source.get(key):
                            raise ValidationError("verification used a different source or dependency lock")
                    if (
                        target == "full_local_passed"
                        and evidence.get("environment", {}).get("dirty") is not False
                    ):
                        raise BlockedError("full evidence was produced by a dirty source tree")
                    if target == "full_local_passed" and (
                        source.get("dirty") is not False
                        or not source.get("source_revision")
                        or not source.get("dependency_lock_sha256")
                    ):
                        raise BlockedError(
                            "full release evidence requires a clean frozen source and dependency lock"
                        )
                elif target == "release_selected":
                    generated = any(a["origin"] == "generated" for a in record["artifacts"].values())
                    if generated and record["confirmation"]["status"] != "passed":
                        raise BlockedError("independent unused frozen-artifact confirmation required")
                    for key in ("g0", "g1", "opportunity", "mutations", "stability", "improvement"):
                        receipt = evidence.get(key)
                        if (
                            not isinstance(receipt, dict)
                            or not receipt.get("path")
                            or not receipt.get("sha256")
                        ):
                            raise BlockedError(f"release prerequisite receipt absent: {key}")
                        path = Path(receipt["path"])
                        if not path.is_file() or sha256(path) != receipt["sha256"]:
                            raise ValidationError(f"release receipt missing or changed: {key}")
                        data = read_json(path)
                        if (
                            data.get("passed") is not True
                            or data.get("contract_hash") != record["contract_hash"]
                        ):
                            raise BlockedError(f"release prerequisite did not pass current contract: {key}")
                        if (
                            key in ("mutations", "stability", "improvement")
                            and data.get("artifact_hashes") != record["artifact_hashes"]
                        ):
                            raise ValidationError(f"release receipt has different artifacts: {key}")
                elif target == "remote_accepted":
                    if (
                        not evidence.get("submission_id")
                        or not evidence.get("zip_sha256")
                        or not 1 < evidence.get("score", 0) < float("inf")
                        or not evidence.get("remote_evidence")
                    ):
                        raise ValidationError("remote acceptance evidence and improved score required")
            record["history"].append({"from": record["state"], "to": target, "evidence": evidence})
            record["state"] = target
            self._save(record)
            return record

    def register_confirmation(self, candidate_id, protocol):
        with record_lock(self.root):
            record = self.get(candidate_id)
            if record["confirmation"]["status"] != "not_run":
                raise ValidationError("confirmation already registered; no retry on unchanged bytes")
            generated_benchmarks = {
                ("dfthcsos" if name.startswith("dfthcsos/") else name.split(".")[0])
                for name, item in record["artifacts"].items()
                if item["origin"] == "generated"
            }
            if generated_benchmarks != {protocol.get("benchmark")}:
                raise BlockedError(
                    "first-release confirmation supports one optimized benchmark per candidate; benchmark must match all generated files"
                )
            positive_int(protocol.get("sample_size"), "confirmation sample_size")
            nonnegative_int(protocol.get("max_failures"), "max_failures")
            if protocol["max_failures"] >= protocol["sample_size"]:
                raise ValidationError("confirmation rule must reject some possible outcomes")
            for key in (
                "distribution",
                "confidence_procedure",
                "stop_rule",
                "compute_allowance",
                "seed_policy",
            ):
                if not protocol.get(key):
                    raise ValidationError(f"confirmation protocol missing {key}")
            seed = protocol["seed_policy"]
            if seed.get("role") != "confirmation" or len(seed.get("salt", "")) < 32:
                raise ValidationError("confirmation needs a distinct registered seed policy")
            history_salts = [h["evidence"].get("seed_policy", {}).get("salt") for h in record["history"]]
            if seed["salt"] in history_salts:
                raise ValidationError("development salt cannot be reused for confirmation")
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = read_json(ledger_path) if ledger_path.exists() else []
            # Salt identifies the challenge material, even if renamed with a new distribution label.
            if any(item["salt"] == seed["salt"] for item in ledger):
                raise ValidationError("confirmation salt has already been used or reserved")
            if any(
                item["artifact_hashes"] == record["artifact_hashes"] and item["status"] == "failed"
                for item in ledger
            ):
                raise ValidationError("failed frozen bytes cannot be repeatedly confirmed")
            if any(item["artifact_hashes"] == record["artifact_hashes"] for item in ledger):
                raise ValidationError(
                    "unchanged frozen bytes already have confirmation history; revise the artifact rather than rerun"
                )
            protocol_id = identity(protocol)
            ledger.append(
                {
                    "candidate": candidate_id,
                    "salt": seed["salt"],
                    "protocol_id": protocol_id,
                    "artifact_hashes": record["artifact_hashes"],
                    "status": "registered",
                }
            )
            write_json(ledger_path, ledger, replace=True)
            record["confirmation"] = {
                "status": "registered",
                "protocol": protocol,
                "protocol_id": protocol_id,
                "artifact_hashes": record["artifact_hashes"],
            }
            self._save(record)
            return record

    def finish_confirmation(self, candidate_id, evidence, *, consumed=False):
        with record_lock(self.root):
            record = self.get(candidate_id)
            confirmation = record["confirmation"]
            if confirmation["status"] != "registered":
                raise ValidationError("confirmation must be registered before observing results")
            self._bound(record, evidence)
            protocol = confirmation["protocol"]
            if (
                evidence.get("seed_policy") != protocol["seed_policy"]
                or evidence.get("role") != "confirmation"
            ):
                raise ValidationError("confirmation protocol/seed mismatch")
            observed = evidence.get("observed", {})
            n, k = observed.get("n"), observed.get("k")
            positive_int(n, "observed n")
            nonnegative_int(k, "observed k")
            if k > n or n != protocol["sample_size"]:
                raise ValidationError("incomplete or inconsistent confirmation sample")
            passed = evidence.get("complete") is True and k <= protocol["max_failures"]
            status = ("consumed_for_tuning" if consumed else "passed") if passed else "failed"
            confirmation.update(status=status, evidence=evidence)
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = read_json(ledger_path)
            for entry in ledger:
                if entry["protocol_id"] == confirmation["protocol_id"] and entry["candidate"] == candidate_id:
                    entry["status"] = status
            write_json(ledger_path, ledger, replace=True)
            self._save(record)
            return record

    def consume_confirmation(self, candidate_id, reason):
        with record_lock(self.root):
            record = self.get(candidate_id)
            if record["confirmation"]["status"] != "passed" or not reason:
                raise ValidationError("only passed confirmation can be consumed, with a reason")
            if record["state"] in ("release_selected", "remote_accepted"):
                raise ValidationError("selected/released confirmation cannot be repurposed")
            record["confirmation"]["status"] = "consumed_for_tuning"
            record["confirmation"]["reason"] = reason
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = read_json(ledger_path)
            for item in ledger:
                if item["candidate"] == candidate_id:
                    item["status"] = "consumed_for_tuning"
            write_json(ledger_path, ledger, replace=True)

            self._save(record)
            return record
