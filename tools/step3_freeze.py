"""Audit required step-3 evidence and freeze a reproducible local archive."""

import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from qcompile.artifacts import zip_info
from qcompile.campaign import verify_bundle
from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.io import canonical_json, read_json, sha256, write_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/evidence"
    records = {path.stem.removeprefix("step3-"): read_json(path) for path in evidence.glob("step3-*.json")}
    phase = records["invsqrt-phase"]
    require(phase["inputs_compared"] == 3133452 and phase["rotation_price_cases"] == 131, "phase coverage")
    margin = phase["margin_control"]
    require(
        margin["full_domain"]
        and margin["nonpositive_margin_count"] == 0
        and sum(margin["margin_histogram_eighths_of_tolerance"]) == 3133452,
        "margin coverage",
    )
    dqi = records["dqi-decoding"]
    require(
        dqi["field_powers"] == 4095 and dqi["weights"] == list(range(36)) and sum(dqi["phase_counts"]) == 72,
        "DQI fixture coverage",
    )
    for row in records["dqi-statistics"]["bounds"]:
        require(
            math.isclose(row["independent"], row["official"], rel_tol=1e-10), "DQI confidence discrepancy"
        )
    for row in records["dqi-statistics"]["penalties"]:
        require(math.isclose(row["independent"], row["official"], rel_tol=1e-7), "DQI repetition discrepancy")
    words = records["chemistry-words"]
    require(
        words["vectors"] * words["shots_per_address"] == 254464
        and words["angles_per_vector"] == 75
        and words["max_vector_discrepancy"] <= 2e-14,
        "word coverage",
    )
    words_path = root / "runs/step3-chemistry/recovered-words.npz"
    require(sha256(words_path) == words["words_sha256"], "word archive changed")
    metrics = records["chemistry-metrics"]
    for name, value in metrics["independent"].items():
        require(
            math.isclose(value, metrics["official"][name], rel_tol=2e-9, abs_tol=2e-9),
            "chemistry discrepancy",
        )
    costs = records["chemistry-costs"]
    require(
        all(
            value == costs["official_components"][name]
            for name, value in costs["independent_components"].items()
        ),
        "resource discrepancy",
    )
    stability = records["chemistry-stability"]
    require(len(stability["full_reference_controls"]) == 2, "missing representation controls")
    for control in stability["full_reference_controls"]:
        require(
            max(control["metric_absolute_differences"].values()) <= control["absolute_tolerance"],
            "unstable representation",
        )
    require(max(stability["near_degenerate_reconstruction_errors"]) <= 5e-15, "degenerate matching")
    require(len(records["angle-boundaries"]["boundary_controls"]) == 6, "missing angle boundaries")
    primitive = records["native-primitive"]
    require(
        primitive["correct_composition"] == "passed"
        and len(primitive["seeds"]) == 32
        and all(primitive["mutation_expected_and_observed"].values()),
        "primitive controls",
    )
    for control in records["invsqrt-rejections"]["records"][1:] + records["structure-controls"]["controls"]:
        require(control["expected"] in control["observed"], "incorrect rejection diagnostic")
    require(len(records["chemistry-rejections"]["controls"]) == 6, "chemistry rejection coverage")
    suites = ET.parse(root / "runs/step3-tests.xml").getroot().findall("testsuite")
    require(sum(int(suite.attrib["tests"]) for suite in suites) == 291, "test coverage changed")
    require(
        all(int(suite.attrib[key]) == 0 for suite in suites for key in ("failures", "errors", "skipped")),
        "test failures",
    )
    contract = load_contract(root / "contracts/contract.json")
    contract.require_ready(root)
    verify_bundle(root / "releases/baseline-v1/baseline-v1.zip")
    require(
        not subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "HEAD",
                "--",
                "src",
                "tools",
                "tests",
                "contracts",
                "uv.lock",
                "pyproject.toml",
            ]
        ),
        "execution source is uncommitted",
    )
    output = root / "releases/step3-validation-v1"
    output.mkdir(exist_ok=False)
    source = output / "source.bundle"
    subprocess.run(["git", "-C", str(root), "bundle", "create", str(source), "HEAD"], check=True)
    restored = output / "restored-source"
    subprocess.run(["git", "clone", str(source), str(restored)], check=True, capture_output=True)
    expected_tree = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD:"], text=True)
    restored_tree = subprocess.check_output(["git", "-C", str(restored), "rev-parse", "HEAD:"], text=True)
    require(
        expected_tree == restored_tree
        and not subprocess.check_output(["git", "-C", str(restored), "status", "--porcelain"]),
        "source bundle restore failed",
    )
    files = {"evidence/" + path.name: path for path in evidence.glob("step3-*.json")}
    files.update(
        {
            "source.bundle": source,
            "raw/tests.xml": root / "runs/step3-tests.xml",
            "raw/recovered-words.npz": words_path,
            "inputs/competition_data.zip": root / "vendor/competition_data.zip",
            "primitive-proof.md": root / "docs/step3-and-cleanup-02-11-2026-03-20-00.md",
        }
    )
    paths = {record["path"] for record in contract.data["sources"].values()}
    for field in contract.data["fields"].values():
        paths.add(field["official"]["path"])
        paths.update(item["path"] for item in field.get("supplementary_official", []))
    for name in paths:
        if (
            name.startswith("vendor/")
            and not name.startswith("vendor/official/")
            and name != "vendor/competition_data.zip"
        ):
            files["inputs/" + name] = root / name
    audit = {
        "kind": "step3_independent_validation",
        "version": "step3-validation-v1",
        "gates": {"G0": "passed", "G1": "passed"},
        "environment": capture(root),
        "contract_hash": contract.hash,
        "test_count": 291,
        "evidence_scope": "Pinned reference inputs, independent mathematics, native primitive branch assumptions and representative defect controls",
        "limitations": [
            "DQI decoder comparisons use 72 stratified fixtures, supported by exhaustive unary field tests.",
            "Primitive coherent correctness uses the stated algebraic branch proof and native instruction/trajectory controls.",
            "Planning and opportunity experiments require their own registration.",
        ],
    }
    audit_path = output / "audit.json"
    write_json(audit_path, audit)
    files["audit.json"] = audit_path
    manifest = {"members": {name: sha256(path) for name, path in sorted(files.items())}}
    targets = [output / "validation.zip", output / "validation-independent.zip"]
    for target in targets:
        with zipfile.ZipFile(target, "x") as archive:
            archive.writestr(zip_info("baseline-manifest.json"), canonical_json(manifest))
            for name, path in sorted(files.items()):
                with (
                    path.open("rb") as original,
                    archive.open(zip_info(name), "w", force_zip64=True) as destination,
                ):
                    shutil.copyfileobj(original, destination, 1 << 20)
        verify_bundle(target)
    require(sha256(targets[0]) == sha256(targets[1]), "independent bundle builds differ")
    receipt = {
        "status": "frozen",
        "sha256": sha256(targets[0]),
        "members": len(files) + 1,
        "gates": audit["gates"],
        "bundle": str(targets[0]),
        "all_members_verified": True,
    }
    write_json(root / "docs/evidence/step3-completion.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
