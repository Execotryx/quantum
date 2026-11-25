"""Bind the completed routed public-DQI screen to the selected member."""

import argparse
import importlib
import sys
from pathlib import Path

from dqi_development import pooled_price, pricing_inputs
from vendor_dqi_price import REFERENCE, ROUTED_PRICE, SHOTS, backend_pin

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


def bank(registration: Path, backend: Path, run: Path, output: Path) -> None:
    plan = read_json(registration)
    decision_path = run / "decision.json"
    decision = read_json(decision_path)
    pin = sha256(registration)
    settings = read_json(backend)
    if decision["registration_sha256"] != pin or backend_pin(settings) != plan["backend_inventory_sha256"]:
        raise ValueError("bank requires the original pricing registration and verifier inventory")
    validate_backend(settings)
    if decision["status"] not in ("go", "go_recorded") or decision["banked"] is not True:
        raise ValueError("pricing decision does not bank a candidate")

    name = decision["selected"]
    candidate = plan["candidates"][name]
    artifact = Path(candidate["artifact"])
    digest = sha256(artifact)
    if digest != candidate["sha256"] or digest != decision["sha256"]:
        raise ValueError("selected circuit differs from the registered bytes")
    component = Path("third_party") / f"dqi-{name}" / "SOURCE.json"
    source_hash = sha256(component)
    for path, expected in candidate["build_receipts"].items():
        receipt_path = Path(path)
        build = read_json(receipt_path)
        if (sha256(receipt_path) != expected or build["source_sha256"] != source_hash
                or build["sha256"] != digest or build["status"] != "go"):
            raise ValueError("selected circuit does not bind both regenerated builds")

    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    rows = []
    draws = {}
    if len(plan["salts"]) != 8 or len(set(plan["salts"])) != 8 or plan["shots"] != SHOTS:
        raise ValueError("expected eight independently salted full draws")
    for index, salt in enumerate(plan["salts"], 1):
        path = run / name / f"s{index}.json"
        receipt = read_json(path)
        result = receipt["result"]
        if (receipt["registration_sha256"] != pin or receipt["candidate"] != name or receipt["salt"] != salt
                or result["status"] != "PASS" or result["circuit_sha256"] != digest):
            raise ValueError(f"invalid selected draw {index}")
        rows.append(result)
        draws[path.name] = sha256(path)

    price = pooled_price(rows, api)
    cost = price["cost"]
    if cost is None or cost >= ROUTED_PRICE:
        raise ValueError("selected candidate did not beat the routed price")
    _, bases = pricing_inputs(rows, api)
    zero_failure_cost = api.repetition_overhead(api.clopper_pearson_upper_bound(0, SHOTS, api.DEFAULT_LOG2_DELTA))
    zero_failure_cost *= max(bases)
    finalists = [row for row in decision["stage2"] if row["cost"] is not None]
    best = min(finalists, key=lambda row: (row["cost"], row["qubits"], row["mean_toffolis"], row["candidate"]))
    ratio = REFERENCE / cost
    if (best["candidate"] != name or any(best[key] != value for key, value in price.items())
            or best["zero_failure_cost"] != zero_failure_cost or decision["pooled_ratio"] != ratio
            or decision["status"] != ("go" if ratio >= 50 else "go_recorded")):
        raise ValueError("banked price differs from the final screen decision")
    write_json(output, {
        "member": "dqi-v8", "candidate": name, "status": decision["status"],
        "artifact": candidate["artifact"], "sha256": digest,
        "source_sha256": source_hash, "registration_sha256": pin,
        "decision_sha256": sha256(decision_path), "draws": draws,
        "pooled_price": cost, "pooled_ratio": ratio, "zero_failure_cost": zero_failure_cost,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("registration", "backend", "run", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    bank(args.registration, args.backend, args.run, args.output)
