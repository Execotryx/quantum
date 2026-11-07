"""Benchmark boundaries and fail-fast evidence rules for hybrid confirmation."""

from pathlib import Path
from typing import Any

from qcompile.chemistry.schema import read_factorization
from qcompile.errors import ValidationError
from qcompile.io import read_json

BENCHMARKS = ("invsqrt", "dqi", "dfthcsos")
FAIL_FAST = {"invsqrt": 200_540_928, "dfthcsos": 254_464}
HYBRID_COVERAGE = {**FAIL_FAST, "dqi": 102_400}
CANDIDATE_PROFILE = "candidate-v1"


def candidate_coverage(artifacts: dict[str, Any]) -> dict[str, int]:
    """Derive the full shot counts from metric v10 and the validated factor shapes."""
    arrays = read_factorization(Path(artifacts["dfthcsos/submission.npz"]["path"]), allow_extra=True)
    r, b, _ = arrays["W"].shape
    return {**HYBRID_COVERAGE, "dfthcsos": (76 + r * b) * 64}


def registered_coverage(record: dict[str, Any]) -> dict[str, int] | None:
    config = record.get("config", {})
    if config.get("verification_profile") == CANDIDATE_PROFILE:
        return config["expected_coverage"]
    return None


def member_benchmark(name: str) -> str:
    return name.split("/", 1)[0] if "/" in name else name.split(".", 1)[0]


def component_hashes(artifacts: dict[str, str], benchmark: str) -> dict[str, str]:
    if benchmark not in BENCHMARKS:
        raise ValidationError("unknown confirmation benchmark")
    subset = {name: digest for name, digest in artifacts.items() if member_benchmark(name) == benchmark}
    if not subset:
        raise ValidationError("empty benchmark component")
    return subset


def generated_benchmarks(record: dict[str, Any]) -> set[str]:
    return {
        member_benchmark(name) for name, item in record["artifacts"].items() if item["origin"] == "generated"
    }


def component_binding(record: dict[str, Any], benchmark: str) -> dict[str, Any]:
    return {
        "benchmark": benchmark,
        "contract_hash": record["contract_hash"],
        "component_hashes": component_hashes(record["artifact_hashes"], benchmark),
    }


def fail_fast_observed(
    benchmark: str, raw: dict[str, Any], coverage: dict[str, int] | None = None
) -> dict[str, int]:
    """These pinned verifiers raise on a bad trajectory and return only after all shots."""
    expected = (coverage or FAIL_FAST).get(benchmark) if benchmark in FAIL_FAST else None
    completed = raw.get("verified_shots")
    if expected is None or raw.get("status") != "PASS" or type(completed) is not int or completed != expected:
        raise ValidationError("confirmation requires an actual complete fail-fast verifier pass")
    return {"n": completed, "k": 0}


def dqi_observed(raw: dict[str, Any], expected: int) -> dict[str, int]:
    n, value, phase = (raw.get(key) for key in ("verified_shots", "value_errors", "phase_errors"))
    if (
        raw.get("status") != "PASS" or type(n) is not int or n != expected
        or type(value) is not int or type(phase) is not int
        or min(value, phase) < 0 or value + phase > n
    ):
        raise ValidationError("confirmation requires complete DQI counters")
    return {"n": n, "k": value + phase}


def dqi_counts(raw: dict[str, Any]) -> dict[str, Any]:
    return {name: raw.get(name) for name in ("circuit_sha256", "verified_shots", "value_errors", "phase_errors")}


def has_full_hybrid_coverage(
    report: dict[str, Any], coverage: dict[str, int] | None = None
) -> bool:
    results = report.get("official_results") or {}
    expected = coverage or HYBRID_COVERAGE
    if results.get("coverage_counts") != {name: {"completed": n, "expected": n} for name, n in expected.items()}:
        return False
    if coverage is not None:
        raw = results.get("raw_verifier_results") or {}
        return all(
            raw.get(name, {}).get("status") == "PASS"
            and type(raw.get(name, {}).get("verified_shots")) is int
            and raw[name]["verified_shots"] == n
            for name, n in expected.items()
        )
    return True


def scopes_for_legacy_row(store, row: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """Use the prior candidate's protocol rather than assuming a legacy row's scope."""
    if "benchmark" in row:
        return row["benchmark"], row["component_hashes"]
    if not store._path(row["candidate"]).is_file():
        raise ValidationError("legacy confirmation row has no candidate to establish its scope")
    # Paths can have been relocated. Scope depends on the existing record's
    # digests and protocol rather than reading that candidate's source files.
    previous = read_json(store._path(row["candidate"]))
    confirmation = previous["confirmation"]
    if confirmation.get("protocol_id") != row["protocol_id"]:
        raise ValidationError("legacy confirmation reservation and candidate disagree")
    benchmark = confirmation["protocol"]["benchmark"]
    return benchmark, component_hashes(row["artifact_hashes"], benchmark)
