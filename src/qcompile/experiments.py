"""File-based candidate state machine and one-use frozen confirmation ledger."""

import csv
from collections.abc import Sequence
from contextlib import contextmanager
from math import isfinite
from pathlib import Path
from typing import Literal

from .artifacts import hashes, validate_manifest
from .component_confirmations import (
    BENCHMARKS,
    CANDIDATE_PROFILE,
    FAIL_FAST,
    candidate_coverage,
    component_binding,
    component_hashes,
    dqi_counts,
    dqi_observed,
    fail_fast_observed,
    generated_benchmarks,
    has_full_hybrid_coverage,
    registered_coverage,
    scopes_for_legacy_row,
)
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
ScreenOutcome = Literal["go", "no_go", "budget_limited", "inconclusive"]


def screen_outcome(
    objectives: Sequence[float],
    threshold: float,
    *,
    cap_reached: bool = False,
    optimizer_converged: bool = True,
    excluded_by_bound: bool = False,
) -> ScreenOutcome:
    """Classify a nonnegative minimization trace against its registered gate."""
    if not isfinite(threshold) or threshold <= 0 or any(not isfinite(v) or v < 0 for v in objectives):
        raise ValidationError("screen objectives must be finite and nonnegative with a positive threshold")
    best = min(objectives, default=float("inf"))
    if best <= threshold:
        if excluded_by_bound:
            raise ValidationError("screen observations contradict the exclusion bound")
        return "go"
    if excluded_by_bound:
        return "no_go"
    if len(objectives) >= 4:
        window = max(2, (len(objectives) + 3) // 4)
        before = min(objectives[:len(objectives) - window + 1])
        relative_gain = (before - best) / before
        if relative_gain < 0.001 and best > 2 * threshold:
            return "no_go"
        if cap_reached and relative_gain >= 0.01:
            return "budget_limited"
    if cap_reached and not optimizer_converged:
        return "budget_limited"
    return "inconclusive"


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

    def create(self, config, contract_hash, artifacts, environment, claims, *, resume=False):
        validate_manifest(artifacts)
        profile = config.get("verification_profile")
        if profile not in (None, CANDIDATE_PROFILE):
            raise ValidationError("unknown verification profile")
        if profile == CANDIDATE_PROFILE:
            config = {**config, "expected_coverage": candidate_coverage(artifacts)}
        elif any(item["origin"] == "retained_parent" for item in artifacts.values()):
            raise ValidationError("retained parent artifacts require the candidate verification profile")
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
        required = generated_benchmarks(record)
        if len(required) > 1:
            record["confirmations"] = {benchmark: {"status": "not_run"} for benchmark in sorted(required)}
        try:
            write_json(self._path(candidate_id), record)
        except FileExistsError:
            if not resume:
                raise
            existing = self.get(candidate_id)
            if existing["environment"] != environment or existing["claims"] != claims:
                raise ValidationError("existing candidate differs from the registered environment or claims")
            return existing
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
            identity(frozen) != record["id"] or record["id"] != candidate_id
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
                    coverage = registered_coverage(record)
                    hybrid = coverage is not None or bool(record["config"].get("hybrid_archive_sha256"))
                    full_hybrid = (
                        hybrid and evidence.get("tier") == "full"
                        and has_full_hybrid_coverage(evidence, coverage)
                    )
                    if (
                        evidence.get("kind") != "official_metric_execution"
                        or (evidence.get("tier") != tier and not full_hybrid)
                        or (hybrid and tier == "full" and not full_hybrid)
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
                    for benchmark in generated_benchmarks(record):
                        self.require_confirmation(record, benchmark)
                    self.require_release_parent(record)
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

    @staticmethod
    def _slot(record, benchmark=None):
        required = generated_benchmarks(record)
        if benchmark is None and len(required) == 1:
            benchmark = next(iter(required))
        if benchmark not in required:
            raise BlockedError("confirmation benchmark must name an optimized component")
        if "confirmations" in record:
            return benchmark, record["confirmations"][benchmark]
        if len(required) != 1:
            raise BlockedError("benchmark-keyed records are required for multiple optimized components")
        return benchmark, record["confirmation"]

    @staticmethod
    def _set_slot(record, benchmark, confirmation):
        if "confirmations" not in record:
            record["confirmation"] = confirmation
            return
        record["confirmations"][benchmark] = confirmation
        statuses = {slot["status"] for slot in record["confirmations"].values()}
        status = next(iter(statuses)) if len(statuses) == 1 else "partial"
        record["confirmation"] = {"status": status}

    def _ledger(self):
        path = self.root / "confirmation-ledger.json"
        return read_json(path) if path.exists() else []

    def confirmation_for(self, candidate_id, benchmark):
        return self._slot(self.get(candidate_id), benchmark)[1]

    def require_release_parent(self, record):
        if registered_coverage(record) is None:
            return self.require_chemistry_parent(record)
        binding = record["config"].get("release_parent") or {}
        parent_id = binding.get("candidate_id")
        changed = generated_benchmarks(record)
        if not isinstance(parent_id, str) or parent_id == record["id"] or not changed:
            raise BlockedError("candidate release requires changed components and a distinct certified parent")
        parent = self.get(parent_id)
        anchor_path = self._path(parent_id).with_name("local-certificate.json")
        if not anchor_path.is_file():
            raise BlockedError("trusted parent certificate is unavailable")
        anchor = read_json(anchor_path)
        certificate_path = Path(anchor["certificate_path"])
        if not certificate_path.is_file() or sha256(certificate_path) != anchor["certificate_sha256"]:
            raise ValidationError("parent certificate changed")
        certificate = read_json(certificate_path)
        verification = certificate["verification"]
        if (
            parent["state"] not in ("release_selected", "remote_accepted")
            or anchor["candidate_id"] != parent_id
            or any(anchor.get(key) != binding.get(key) for key in ("zip_sha256", "certificate_sha256", "backend_hash"))
            or parent["contract_hash"] != record["contract_hash"] or anchor["contract_hash"] != record["contract_hash"]
            or anchor["dependency_lock_sha256"] != record["environment"]["dependency_lock_sha256"]
            or certificate["artifact_hashes"] != parent["artifact_hashes"]
            or verification.get("artifact_hashes") != parent["artifact_hashes"]
            or verification.get("complete") is not True
            or verification.get("backend_hash") != anchor["backend_hash"]
        ):
            raise BlockedError("candidate parent does not match the trusted full certificate")
        retained = set(BENCHMARKS) - changed
        for benchmark in BENCHMARKS:
            current = component_hashes(record["artifact_hashes"], benchmark)
            previous = component_hashes(parent["artifact_hashes"], benchmark)
            if (current == previous) != (benchmark in retained):
                raise BlockedError("declared changed scope disagrees with complete component bytes")
        for name, item in record["artifacts"].items():
            if item["origin"] != "generated" and parent["artifact_hashes"].get(name) != item["sha256"]:
                raise BlockedError("retained member differs from its certified parent")
        for benchmark in retained & generated_benchmarks(parent):
            self.require_confirmation(parent, benchmark)
        if retained and certificate.get("parent"):
            if self.require_release_parent(parent) != certificate["parent"]:
                raise BlockedError("inherited component lineage no longer matches its certificate")
        return {
            **anchor,
            "artifact_hashes": parent["artifact_hashes"],
            "retained_benchmarks": sorted(retained),
            "dqi_counts": dqi_counts(verification["official_results"]["raw_verifier_results"]["dqi"]),
        }

    def require_chemistry_parent(self, record):
        retained = {
            name for name, item in record["artifacts"].items() if item["origin"] == "retained_certified"
        }
        if not retained:
            return None
        binding = record["config"].get("retained_chemistry") or {}
        parent_id = binding.get("candidate_id")
        if not isinstance(parent_id, str) or parent_id == record["id"]:
            raise BlockedError("retained chemistry requires a distinct certified parent")
        parent = self.get(parent_id)
        anchor_path = self._path(parent_id).with_name("local-certificate.json")
        if not anchor_path.is_file():
            raise BlockedError("trusted parent certificate is unavailable")
        anchor = read_json(anchor_path)
        certificate_path = Path(anchor["certificate_path"])
        if not certificate_path.is_file() or sha256(certificate_path) != anchor["certificate_sha256"]:
            raise ValidationError("parent certificate changed")
        chemistry = component_hashes(record["artifact_hashes"], "dfthcsos")
        receipt = self.require_confirmation(parent, "dfthcsos")
        if (
            generated_benchmarks(record) != {"invsqrt"}
            or retained != {name for name in chemistry if name != "dfthcsos/submission.npz"}
            or parent["state"] not in ("release_selected", "remote_accepted")
            or anchor["candidate_id"] != parent_id
            or any(
                anchor.get(key) != binding.get(key)
                for key in ("zip_sha256", "certificate_sha256", "backend_hash")
            )
            or parent["contract_hash"] != record["contract_hash"]
            or anchor["contract_hash"] != record["contract_hash"]
            or anchor["backend_hash"] != receipt["protocol"]["backend_hash"]
            or anchor["dependency_lock_sha256"] != record["environment"]["dependency_lock_sha256"]
            or chemistry != component_hashes(parent["artifact_hashes"], "dfthcsos")
            or record["artifact_hashes"]["dqi.kmb"] != parent["artifact_hashes"]["dqi.kmb"]
        ):
            raise BlockedError("retained chemistry identity differs from its certified parent")
        return {**anchor, "chemistry_protocol_id": receipt["protocol_id"]}

    def record_local_certificate(self, candidate_id, path):
        with record_lock(self.root):
            record = self.get(candidate_id)
            path = Path(path).resolve()
            certificate = read_json(path)
            verification = certificate.get("verification") or {}
            if (
                record["state"] != "release_selected"
                or certificate.get("candidate_id") != candidate_id
                or certificate.get("artifact_hashes") != record["artifact_hashes"]
                or certificate.get("contract_hash") != record["contract_hash"]
                or certificate.get("status") != "locally_verified_awaiting_kaggle_acceptance"
                or verification.get("status") != "passed"
                or verification.get("complete") is not True
            ):
                raise BlockedError("complete local certificate does not match selected candidate")
            for benchmark in generated_benchmarks(record):
                self.require_confirmation(record, benchmark)
            anchor = {
                "candidate_id": candidate_id,
                "zip_sha256": certificate["zip_sha256"],
                "certificate_sha256": sha256(path),
                "certificate_path": str(path),
                "contract_hash": record["contract_hash"],
                "backend_hash": verification["backend_hash"],
                "dependency_lock_sha256": record["environment"]["dependency_lock_sha256"],
                "score": certificate["predicted_aggregate_score"],
                "costs": verification["official_results"]["costs"],
            }
            anchor_path = self._path(candidate_id).with_name("local-certificate.json")
            if anchor_path.exists():
                if read_json(anchor_path) != anchor:
                    raise ValidationError("different local certificate already recorded")
            else:
                write_json(anchor_path, anchor)
            return anchor

    def require_confirmation(self, record, benchmark):
        _, confirmation = self._slot(record, benchmark)
        if confirmation["status"] != "passed":
            raise BlockedError("independent unused frozen-artifact confirmation required")
        matches = [
            item
            for item in self._ledger()
            if item["candidate"] == record["id"] and item["protocol_id"] == confirmation["protocol_id"]
        ]
        binding = component_binding(record, benchmark)
        if (
            len(matches) != 1
            or matches[0]["status"] != "passed"
            or matches[0]["salt"] != confirmation["protocol"]["seed_policy"]["salt"]
            or scopes_for_legacy_row(self, matches[0]) != (benchmark, binding["component_hashes"])
            or (
                "component_hashes" in confirmation
                and any(confirmation.get(key) != value for key, value in binding.items())
            )
        ):
            raise BlockedError("benchmark confirmation does not match the one-use ledger")
        return confirmation

    def register_confirmation(self, candidate_id, protocol):
        with record_lock(self.root):
            record = self.get(candidate_id)
            benchmark, confirmation = self._slot(record, protocol.get("benchmark"))
            if protocol.get("benchmark") != benchmark:
                raise BlockedError("confirmation protocol must identify its benchmark")
            if confirmation["status"] != "not_run":
                raise ValidationError("confirmation already registered; no retry on unchanged bytes")
            positive_int(protocol.get("sample_size"), "confirmation sample_size")
            nonnegative_int(protocol.get("max_failures"), "max_failures")
            coverage = registered_coverage(record)
            if benchmark in FAIL_FAST and (
                protocol["sample_size"] != (coverage or FAIL_FAST)[benchmark]
                or protocol["max_failures"] != 0
                or not protocol.get("backend_hash")
                or (benchmark == "dfthcsos" and not protocol.get("verifier_artifact_sha256"))
            ):
                raise ValidationError("fail-fast confirmation needs full coverage and a pinned backend")
            if coverage is not None and (
                protocol["sample_size"] != coverage[benchmark] or not protocol.get("backend_hash")
            ):
                raise ValidationError("candidate confirmation needs full coverage and a pinned backend")
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
            binding = component_binding(record, benchmark)
            development = self.root / "development-salts.json"
            if development.is_file():
                reserved = read_json(development).get(seed["salt"])
                if reserved is not None and not (
                    isinstance(reserved, dict) and reserved.get("role") == "confirmation"
                    and benchmark == "dqi" and reserved.get("component_hashes") == binding["component_hashes"]
                ):
                    raise ValidationError("salt is registered for development or reserved for another component")
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = self._ledger()
            # Salt identifies the challenge material, even if renamed with a new distribution label.
            if any(item["salt"] == seed["salt"] for item in ledger):
                raise ValidationError("confirmation salt has already been used or reserved")
            for item in ledger:
                if scopes_for_legacy_row(self, item) == (benchmark, binding["component_hashes"]):
                    if item["status"] == "failed":
                        raise ValidationError("failed frozen bytes cannot be repeatedly confirmed")
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
                    **binding,
                    "status": "registered",
                }
            )
            write_json(ledger_path, ledger, replace=True)
            self._set_slot(
                record,
                benchmark,
                {
                    "status": "registered",
                    "protocol": protocol,
                    "protocol_id": protocol_id,
                    "artifact_hashes": record["artifact_hashes"],
                    **binding,
                },
            )
            self._save(record)
            return record

    def finish_confirmation(self, candidate_id, evidence, *, consumed=False, benchmark=None):
        with record_lock(self.root):
            record = self.get(candidate_id)
            benchmark, confirmation = self._slot(record, benchmark)
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
            coverage = registered_coverage(record)
            raw = evidence.get("raw_benchmark", {})
            if benchmark in FAIL_FAST and (
                evidence.get("benchmark") != benchmark
                or evidence.get("backend_hash") != protocol["backend_hash"]
                or evidence.get("component_hashes") != confirmation["component_hashes"]
                or observed != fail_fast_observed(benchmark, raw, coverage)
                or (
                    benchmark == "invsqrt"
                    and evidence["raw_benchmark"].get("circuit_sha256")
                    != confirmation["component_hashes"]["invsqrt.kmb"]
                )
                or (
                    benchmark == "dfthcsos"
                    and evidence["raw_benchmark"].get("submission_sha256")
                    != protocol["verifier_artifact_sha256"]
                )
            ):
                raise ValidationError("confirmation receipt differs from its registered benchmark or runtime")
            if coverage is not None and benchmark == "dqi" and (
                evidence.get("benchmark") != benchmark
                or evidence.get("backend_hash") != protocol["backend_hash"]
                or evidence.get("component_hashes") != confirmation["component_hashes"]
                or raw.get("circuit_sha256") != confirmation["component_hashes"]["dqi.kmb"]
                or observed != dqi_observed(raw, coverage["dqi"])
            ):
                raise ValidationError("DQI confirmation receipt differs from its registered benchmark or runtime")
            if coverage is not None and (
                evidence.get("tier") != "full"
                or raw != (evidence.get("official_results") or {}).get("raw_verifier_results", {}).get(benchmark)
                or not has_full_hybrid_coverage(evidence, coverage)
            ):
                raise ValidationError("candidate confirmation requires the bound full metric receipt")
            n, k = observed.get("n"), observed.get("k")
            positive_int(n, "observed n")
            nonnegative_int(k, "observed k")
            if k > n or n != protocol["sample_size"]:
                raise ValidationError("incomplete or inconsistent confirmation sample")
            passed = evidence.get("complete") is True and k <= protocol["max_failures"]
            status = ("consumed_for_tuning" if consumed else "passed") if passed else "failed"
            confirmation.update(status=status, evidence=evidence)
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = self._ledger()
            matches = [
                item
                for item in ledger
                if item["protocol_id"] == confirmation["protocol_id"] and item["candidate"] == candidate_id
            ]
            if len(matches) != 1 or matches[0]["status"] != "registered":
                raise ValidationError("confirmation reservation is missing or already terminal")
            matches[0]["status"] = status
            write_json(ledger_path, ledger, replace=True)
            self._set_slot(record, benchmark, confirmation)
            self._save(record)
            return record

    def consume_confirmation(self, candidate_id, reason, *, benchmark=None):
        with record_lock(self.root):
            record = self.get(candidate_id)
            benchmark, _ = self._slot(record, benchmark)
            if not reason:
                raise ValidationError("confirmation consumption requires a reason")
            if record["state"] in ("release_selected", "remote_accepted"):
                raise ValidationError("selected/released confirmation cannot be repurposed")
            confirmation = self.require_confirmation(record, benchmark)
            confirmation.update(status="consumed_for_tuning", reason=reason)
            ledger_path = self.root / "confirmation-ledger.json"
            ledger = read_json(ledger_path)
            for item in ledger:
                if item["candidate"] == candidate_id and item["protocol_id"] == confirmation["protocol_id"]:
                    item["status"] = "consumed_for_tuning"
            write_json(ledger_path, ledger, replace=True)

            self._set_slot(record, benchmark, confirmation)
            self._save(record)
            return record
