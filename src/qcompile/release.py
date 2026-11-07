"""Two genuinely independent builds; extracted bytes go to the full verifier."""

import shutil
import subprocess
from math import isclose
from pathlib import Path

from .artifacts import deterministic_zip, extract_archive, hashes, validate_manifest
from .component_confirmations import component_hashes, generated_benchmarks
from .errors import BlockedError, ValidationError
from .io import sha256, write_json
from .reference.scoring import aggregate


def build_candidate(selection, contract, output_dir):
    artifacts = selection["artifacts"]
    validate_manifest(artifacts)
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    generated = {name for name, item in artifacts.items() if item["origin"] == "generated"}
    recipes = selection.get("build_recipes", [])
    recipe_outputs = [name for recipe in recipes for name in recipe["outputs"]]
    if set(recipe_outputs) != generated or len(recipe_outputs) != len(set(recipe_outputs)):
        raise ValidationError("every generated artifact needs exactly one rebuild recipe")
    for index, recipe in enumerate(recipes):
        if not recipe.get("inputs") or not recipe.get("argv"):
            raise ValidationError("rebuild recipe needs pinned inputs and an argv command")
        for path, digest in recipe["inputs"].items():
            if sha256(Path(path)) != digest:
                raise ValidationError("release build input hash mismatch")
        argv = [arg.replace("{output_dir}", str(output)) for arg in recipe["argv"]]
        if argv == recipe["argv"]:
            raise ValidationError("generator command must receive its fresh output_dir")
        with (output.parent / (output.name + f"-build-{index}.log")).open("w") as log:
            subprocess.run(
                argv,
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=recipe.get("timeout_seconds", 3600),
            )
    for name, item in artifacts.items():
        target = output / name
        if item["origin"] in ("retained_reference", "retained_certified"):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item["path"], target)
        if not target.is_file() or target.is_symlink() or sha256(target) != item["sha256"]:
            raise ValidationError(f"rebuilt artifact differs from selected frozen bytes: {name}")
    actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    if actual != set(artifacts):
        raise ValidationError("build produced unexpected or missing files")
    return {name: output / name for name in artifacts}


def package_release(selection, contract, output_dir, *, source_environment, candidate_store=None):
    contract.require_ready(Path(selection["project_root"]))
    if source_environment.get("dirty") is not False or not source_environment.get("source_revision"):
        raise BlockedError("release needs a clean frozen source revision")
    record = selection["candidate"]
    if record["state"] != "release_selected" or record["contract_hash"] != contract.hash:
        raise BlockedError("selected candidate and current resolved contract are required")
    for key in ("source_revision", "dependency_lock_sha256"):
        if source_environment.get(key) != record["environment"].get(key):
            raise BlockedError("release source or dependency lock differs from frozen candidate")
    if record["artifact_hashes"] != hashes(selection["artifacts"]):
        raise ValidationError("release selection changed artifact bytes")
    selected_sources = {
        name: {key: item[key] for key in ("origin", "provenance")}
        for name, item in selection["artifacts"].items()
    }
    if selected_sources != record["artifact_sources"]:
        raise ValidationError("release selection changed frozen artifact provenance")
    retained = {
        name for name, item in selection["artifacts"].items() if item["origin"] == "retained_certified"
    }
    parent = None
    if retained:
        if candidate_store is None:
            raise BlockedError("certified retained chemistry must resolve through its candidate store")
        parent = candidate_store.require_chemistry_parent(record)
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    a = build_candidate(selection, contract, root / "build-a")
    b = build_candidate(selection, contract, root / "build-b")
    for name in a:
        if sha256(a[name]) != sha256(b[name]):
            raise ValidationError(f"two clean builds differ: {name}")
    deterministic_zip(root / "submission-a.zip", a)
    deterministic_zip(root / "submission.zip", b)
    if sha256(root / "submission-a.zip") != sha256(root / "submission.zip"):
        raise ValidationError("deterministic ZIP bytes differ")
    extracted = extract_archive(
        root / "submission.zip", root / "extracted", expected=record["artifact_hashes"]
    )
    release = {
        "schema_version": 1,
        "status": "built_awaiting_full_verification",
        "zip_sha256": sha256(root / "submission.zip"),
        "artifact_hashes": extracted,
        "contract_hash": contract.hash,
        "candidate_id": record["id"],
        "source_environment": source_environment,
        "candidate": record,
        "two_builds_identical": True,
        "remote_accepted": False,
    }
    if parent:
        release["parent"] = parent
    write_json(root / "release.json", release)
    return release


def certify_release(release, verification, contract, *, supporting_evidence):
    if (
        verification.get("kind") != "official_metric_execution"
        or verification.get("tier") != "full"
        or verification.get("status") != "passed"
        or verification.get("complete") is not True
        or verification.get("artifact_hashes") != release["artifact_hashes"]
        or verification.get("contract_hash") != contract.hash
        or release["contract_hash"] != contract.hash
    ):
        raise BlockedError("extracted archive needs complete hash-bound full official verification")
    # Evidence must carry its real data, not booleans that stand in for measurements.
    for key in (
        "coverage_counts",
        "cost_breakdown",
        "numerical_margins",
        "mutation_diagnostics",
        "primitive_scope",
        "representation_stability",
        "opportunity_decision",
    ):
        if not supporting_evidence.get(key):
            raise BlockedError(f"release certificate missing {key}")
    if verification.get("role") != "official_local":
        raise BlockedError("release requires a distinct official local run role")
    official = verification.get("official_results") or {}
    actual_counts = official.get("coverage_counts") or {}
    expected_counts = contract.data["fields"]["release.coverage"]["value"]
    if not isinstance(expected_counts, dict):
        raise BlockedError("resolved expected coverage is required")
    for name in ("invsqrt", "dqi", "dfthcsos"):
        coverage = supporting_evidence["coverage_counts"].get(name, {})
        if (
            type(coverage.get("completed")) is not int
            or coverage["completed"] <= 0
            or coverage["completed"] != coverage.get("expected")
            or coverage != actual_counts.get(name)
            or coverage["expected"] != expected_counts.get(name)
        ):
            raise BlockedError(f"incomplete release coverage: {name}")
    costs = official.get("costs", {})
    baselines = supporting_evidence.get("accepted_reference_costs", {})
    score = aggregate(baselines, costs)
    if score <= 1 or not any(costs[k] < baselines[k] for k in costs):
        raise BlockedError("release must improve complete official cost and aggregate score")
    candidate = release.get("candidate") or {}
    parent = release.get("parent")
    if "confirmations" in candidate or parent:
        optimized = generated_benchmarks(candidate) | ({"dfthcsos"} if parent else set())
        supporting = supporting_evidence.get("benchmark_evidence") or {}
        if set(supporting) != optimized:
            raise BlockedError("benchmark-specific supporting evidence is incomplete")
        for benchmark in optimized:
            evidence = supporting[benchmark]
            if evidence.get("component_hashes") != component_hashes(release["artifact_hashes"], benchmark):
                raise ValidationError("supporting evidence binds a different optimized component")
            for key in ("opportunity", "numerical", "mutation", "primitive", "stability"):
                if not evidence.get(key):
                    raise BlockedError(f"missing {benchmark} {key} evidence")
            if costs[benchmark] >= baselines[benchmark]:
                raise BlockedError(f"{benchmark} cost did not improve over the reference")
        confirmations = candidate.get("confirmations") or {"invsqrt": candidate["confirmation"]}
        for benchmark, receipt in confirmations.items():
            if (
                receipt["status"] != "passed"
                or receipt["protocol"].get("backend_hash") != verification["backend_hash"]
            ):
                raise BlockedError(f"{benchmark} confirmation did not use the verified release backend")
        if parent:
            if (
                verification["backend_hash"] != parent["backend_hash"]
                or score <= parent["score"]
                or not all(
                    isclose(costs[name], parent["costs"][name], rel_tol=1e-12) for name in ("dqi", "dfthcsos")
                )
                or costs["invsqrt"] > candidate["config"]["invsqrt_cost_limit"]
                or official["raw_verifier_results"]["invsqrt"]["worst_error_over_tolerance"] > 0.90
            ):
                raise BlockedError("successor did not satisfy the measured parent comparison")
    return {
        **release,
        "predicted_aggregate_score": score,
        "status": "locally_verified_awaiting_kaggle_acceptance",
        "verification": verification,
        "supporting_evidence": supporting_evidence,
    }
