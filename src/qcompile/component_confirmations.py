"""Benchmark boundaries and fail-fast evidence rules for hybrid confirmation."""

from typing import Any

from qcompile.errors import ValidationError
from qcompile.io import read_json

BENCHMARKS = ("invsqrt", "dqi", "dfthcsos")
FAIL_FAST = {"invsqrt": 200_540_928, "dfthcsos": 254_464}
HYBRID_COVERAGE = {**FAIL_FAST, "dqi": 102_400}


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


def fail_fast_observed(benchmark: str, raw: dict[str, Any]) -> dict[str, int]:
    """These pinned verifiers raise on a bad trajectory and return only after all shots."""
    expected = FAIL_FAST.get(benchmark)
    completed = raw.get("verified_shots")
    if expected is None or raw.get("status") != "PASS" or type(completed) is not int or completed != expected:
        raise ValidationError("confirmation requires an actual complete fail-fast verifier pass")
    return {"n": completed, "k": 0}


def has_full_hybrid_coverage(report: dict[str, Any]) -> bool:
    counts = (report.get("official_results") or {}).get("coverage_counts")
    return counts == {name: {"completed": n, "expected": n} for name, n in HYBRID_COVERAGE.items()}


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
