"""Prepare the fixed compressed-chemistry stage plans from eligible receipts."""

import argparse
from pathlib import Path

from chem_alternating import bind
from chem_loader_rank import validate_registration as validate_loader
from chem_s2_settings import LIMITS as S2_LIMITS
from chem_s2_settings import bound_plan
from chem_s3 import validate_registration as validate_s3

from qcompile.io import read_json, write_json

S3_LIMITS = {"evaluations_per_step": 2000, "wall_seconds": 7200}


def prepare_s3(run: Path) -> dict:
    terminal = read_json(run / "decision.json")
    if terminal.get("status") != "eligible" or not terminal.get("selected"):
        raise ValueError("S3 requires an eligible bounded S2 run")
    decision = Path(terminal["selected"]["path"])
    if not decision.resolve().is_relative_to(run.resolve()) or bind(decision) != terminal["selected"]:
        raise ValueError("selected S2 decision changed or lies outside its run")
    run = decision.parent
    registration = run / "registration.json"
    source = read_json(registration)["plan"]
    if "handoff" not in source or any(source["limits"].get(key) != value for key, value in S2_LIMITS.items()):
        raise ValueError("S3 requires the registered alternating-fit S2 limits and handoff")
    best = read_json(decision).get("best_eligible_checkpoint")
    if not best:
        raise ValueError("S2 ended without an eligible checkpoint")
    checkpoint = (run / best["checkpoint"]).resolve()
    if not checkpoint.is_relative_to(run.resolve()):
        raise ValueError("S2 checkpoint lies outside its run")
    plan = {
        "factorization": source["factorization"], "target_sha256": source["target_sha256"],
        "s2_registration": bind(registration), "s2_decision": bind(decision),
        "s2_checkpoint_receipt": bind(checkpoint / "checkpoint.json"),
        "s2_continuous": bind(checkpoint / "continuous.npz"),
        "s2_submission": bind(checkpoint / "submission.npz"),
        "s2_words": bind(checkpoint / "words.npy"),
        "limits": S3_LIMITS.copy(),
    }
    validate_s3(plan)
    return plan


def prepare_loader(run: Path, defaults_path: Path) -> dict:
    registration = run / "registration.json"
    if read_json(registration)["plan"]["limits"] != S3_LIMITS:
        raise ValueError("loader requires the registered precision-ladder limits")
    decision = run / "decision.json"
    bits = read_json(decision).get("last_passing")
    if type(bits) is not int or bits not in (8, 9, 10, 11, 12):
        raise ValueError("S3 ended without a passing precision")
    checkpoint = run / f"precision-{bits:02}"
    defaults = read_json(defaults_path)
    plan = {
        "mode": "s3", "brot": bits, "low_bits": defaults["low_bits"], "seed": defaults["seed"],
        "shots_per_address": 2, "wall_seconds": 3600,
        "factorization": bind(checkpoint / "submission.npz"), "words": bind(checkpoint / "words.npy"),
        "s3_registration": bind(registration), "s3_decision": bind(decision),
        "s3_result": bind(checkpoint / "result.json"), "loader_defaults": bind(defaults_path),
    }
    validate_loader(plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    s2 = commands.add_parser("s2")
    s2.add_argument("selection", type=Path)
    s2.add_argument("target", type=Path)
    s2.add_argument("settings", type=Path)
    s2.add_argument("output", type=Path)
    s3 = commands.add_parser("s3")
    s3.add_argument("run", type=Path)
    s3.add_argument("output", type=Path)
    loader = commands.add_parser("loader")
    loader.add_argument("run", type=Path)
    loader.add_argument("defaults", type=Path)
    loader.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.stage == "s2":
        plan = bound_plan(args.selection, args.target, args.settings)
    elif args.stage == "s3":
        plan = prepare_s3(args.run)
    else:
        plan = prepare_loader(args.run, args.defaults)
    write_json(args.output, plan)


if __name__ == "__main__":
    main()
