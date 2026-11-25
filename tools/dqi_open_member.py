"""Audit a complete paired DQI campaign and bind its qualifying member."""

import argparse
import importlib
import sys
from pathlib import Path

from dqi_development import pooled_price
from dqi_open_preflight import checked_file
from vendor_dqi_price import SHOTS, backend_pin

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def audit(registration: Path, preflight: Path, report: Path, source: Path,
          backend: Path, run: Path, output: Path) -> None:
    plan, native = read_json(registration), read_json(preflight)
    digest = sha256(registration)
    pins = plan["pins"]
    settings = read_json(backend)
    validate_backend(settings)
    if (backend_pin(settings) != pins["backend"] or sha256(preflight) != pins["preflight_registration"]
            or sha256(report) != pins["preflight_report"] or not read_json(report)["native_gate_passed"]):
        raise ValueError("Campaign, backend or native qualification identities differ")
    builds = [read_json(checked_file(pin)) for pin in native["builds"]]
    if [pin["sha256"] for pin in native["builds"]] != pins["builds"]:
        raise ValueError("Campaign build identity changed")
    upstream = read_json(source)
    published = {row["sha256"] for row in upstream["published_outputs"] if row["name"] == "dqi.kmb"}
    for build in builds:
        if (build["sha256"] != pins["candidate"] or build["upstream_circuit_sha256"] not in published
                or build["source_archive_sha256"] not in {pin["sha256"] for pin in native["source"]}
                or not build["padding_exchange"]):
            raise ValueError("Candidate lacks the admitted source and padding lineage")

    decision_file = run / "decision.json"
    decision = read_json(decision_file)
    salts = plan["salts"]
    if plan["shots"] != SHOTS or len(salts) != 8 or len(set(salts)) != 8 or decision["registration_sha256"] != digest:
        raise ValueError("Campaign does not bind eight registered full draws")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    comparison = {}
    for role in ("banked", "candidate"):
        artifact = Path(plan["artifacts"][role])
        if sha256(artifact) != pins[role]:
            raise ValueError(f"{role} KMB differs from registration")
        receipts, hashes = [], {}
        for index, salt in enumerate(salts, 1):
            file = run / role / f"s{index}.json"
            record = read_json(file)
            result = record["result"]
            if (record["registration_sha256"] != digest or record["salt"] != salt or record["role"] != role
                    or result["circuit_sha256"] != pins[role] or result["status"] != "PASS"):
                raise ValueError(f"Invalid or failed draw for {role} s{index}")
            receipts.append(result)
            hashes[file.name] = sha256(file)
        price = pooled_price(receipts, api)
        if (decision[role]["result_sha256"] != hashes
                or any(decision[role][key] != value for key, value in price.items())):
            raise ValueError(f"{role} decision differs from independently recomputed receipts")
        comparison[role] = {"pooled": price, "draws": hashes}
    banked_price, candidate_price = (comparison[role]["pooled"]["cost"] for role in ("banked", "candidate"))
    if (candidate_price is None or banked_price is None or candidate_price >= banked_price
            or decision["selected"] != "candidate"):
        raise ValueError("The complete paired campaign has no qualifying replacement")
    write_json(output, {
        "member": "dqi-open-repadding",
        "status": "qualified_pending_independent_confirmation",
        "artifact": plan["artifacts"]["candidate"],
        "sha256": pins["candidate"],
        "supersedes_sha256": pins["banked"],
        "admitted_source_manifest_sha256": sha256(source),
        "build_receipts": pins["builds"],
        "registration_sha256": digest,
        "decision_sha256": sha256(decision_file),
        "native_preflight_sha256": pins["preflight_report"],
        "backend_inventory_sha256": pins["backend"],
        "comparison": comparison,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("registration", "preflight", "report", "source", "backend", "run", "output"):
        parser.add_argument(name, type=Path)
    audit(**vars(parser.parse_args()))
