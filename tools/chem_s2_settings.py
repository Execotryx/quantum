"""Preregister S2 settings, bind the winning lane, and enforce one contingency."""

import argparse
import hashlib
import subprocess
import sys
from math import ceil, isfinite
from pathlib import Path

import numpy as np
from chem_alternating import CONTINUOUS_GATE, DECODED_GATE, REFERENCE, REFERENCE_HASH, bind
from chem_s2 import INPUTS, validate_registration
from invsqrt_direct import run_job

from qcompile.chemistry.schema import read_factorization
from qcompile.io import read_json, sha256, write_json

LIMITS = {"outer_iterations": 4, "evaluations": 1500, "restore_evaluations": 1000,
          "checkpoint_interval": 250, "wall_seconds": 7200, "penalty": 1.0}
FLOORS = {"lambda_floor": 49.05, "gap_floor": 3.916, "gap_target": 3.9161}
CONTINGENCY = {"trigger": 0.99, "multiplier": 2, "max_reruns": 1}
ATTEMPT_LEDGER = Path(__file__).resolve().parents[1] / "runs/.chem-s2-settings-history"


def settings_record(reference: Path) -> dict:
    ref = bind(reference)
    if ref["sha256"] != REFERENCE_HASH:
        raise ValueError("S2 settings require the pinned reference NPZ")
    params = read_factorization(reference, allow_extra=True)
    magnitudes = np.abs(params["H2_I"].astype(np.float64) - params["W"].sum(axis=1, dtype=np.float64))
    maximum = float(magnitudes.max())
    bound = max(1.0, ceil(4 * maximum) / 2)
    if bind(reference) != ref:
        raise ValueError("reference factorization changed while deriving S2 settings")
    return {
        "reference_offsets": {"reference": ref, "m_ref": maximum,
                              "mean_magnitude": float(magnitudes.mean()), "B0": bound},
        "limits": {**LIMITS, "offset_bound": bound},
        "floors": FLOORS, "contingency": CONTINGENCY,
    }


def checked_settings(path: Path) -> tuple[dict, dict[str, str]]:
    pin = bind(path)
    settings = read_json(path)
    if settings != settings_record(Path(settings["reference_offsets"]["reference"]["path"])) or bind(path) != pin:
        raise ValueError("S2 settings differ from the preregistered reference rule")
    return settings, pin


def bound_plan(selection_path: Path, target_path: Path, settings_path: Path) -> dict:
    selection_pin, target_pin = bind(selection_path), bind(target_path)
    selection, target = read_json(selection_path), read_json(target_path)
    settings, settings_pin = checked_settings(settings_path)
    if selection.get("status") != "go" or selection.get("s2_settings") != settings_pin:
        raise ValueError("S2 requires a selected lane with its original preregistered settings")
    inputs = selection["handoff"]
    if target["factorization_sha256"] != inputs["factorization"]["sha256"] or (
        inputs["factorization"]["sha256"] != settings["reference_offsets"]["reference"]["sha256"]
    ):
        raise ValueError("S1, the target pin, and S2 settings use different references")
    plan = {
        **{name: inputs[name] for name in INPUTS}, "target_sha256": target["target_sha256"], "brot": 12,
        "limits": settings["limits"], "floors": settings["floors"], "contingency": settings["contingency"],
        "reference_offsets": settings["reference_offsets"], "s2_settings": settings_pin,
        "handoff": selection_pin, "target_pin": target_pin,
    }
    paths, decision, registration = validate_registration(plan)
    receipt = read_json(paths["s1_checkpoint_receipt"])
    decoded = receipt["decoded_metrics"]["error_2"]
    if (registration["plan"]["lane"] != selection["selected"] or receipt["decoded_brot"] != 12
            or not 0 <= decision["best_continuous_residual"] <= CONTINUOUS_GATE
            or type(decoded) not in (int, float) or not 0 <= decoded <= DECODED_GATE):
        raise ValueError("S1 handoff missed the registered continuous or decoded gate")
    factors = read_factorization(paths["s1_checkpoint"], spec={"U": ("f", ("R", "B", "N")),
                                                              "W": ("f", ("R", "B", "C"))})
    plan["lane"] = {"id": selection["selected"], "checkpoint_receipt_sha256": inputs["s1_checkpoint_receipt"]["sha256"],
                    "vectors_sha256": hashlib.sha256(factors["U"].tobytes()).hexdigest(),
                    "weights_sha256": hashlib.sha256(factors["W"].tobytes()).hexdigest()}
    if bind(selection_path) != selection_pin or bind(target_path) != target_pin:
        raise ValueError("S1 selection or target changed during plan binding")
    return plan


def run(plan_path: Path, output: Path, expected_hash: str) -> None:
    if sha256(plan_path) != expected_hash:
        raise ValueError("S2 plan differs from its registered hash")
    plan = read_json(plan_path)
    if plan != bound_plan(Path(plan["handoff"]["path"]), Path(plan["target_pin"]["path"]),
                          Path(plan["s2_settings"]["path"])):
        raise ValueError("S2 plan differs from the registered primary plan")
    if output.exists():
        raise ValueError("S2 needs a fresh output directory")
    write_json(ATTEMPT_LEDGER / f"{expected_hash}.json", {"plan": bind(plan_path), "output": str(output.resolve())})
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {"plan": bind(plan_path), "contingency": CONTINGENCY})
    attempts = []
    for number in (1, 2):
        attempt = output / f"attempt-{number}"
        attempt.mkdir()
        if number == 2:
            plan = {**plan, "limits": {**plan["limits"], "offset_bound": 2 * plan["limits"]["offset_bound"]},
                    "primary_plan_sha256": expected_hash, "primary_decision": attempts[0]["decision"]}
            plan_path = attempt / "plan.json"
            write_json(plan_path, plan)
        plan_hash = expected_hash if number == 1 else sha256(plan_path)
        worker = attempt / "worker"
        try:
            code = run_job([sys.executable, str(Path(__file__).with_name("chem_s2.py")), "worker",
                            str(plan_path), str(worker), plan_hash], attempt, plan["limits"]["wall_seconds"])
            status = "complete" if code == 0 else f"worker_exit_{code}"
        except subprocess.TimeoutExpired:
            status = "timeout"
        record: dict[str, str | bool | float | dict[str, str]] = {"status": status, "plan_sha256": plan_hash}
        attempts.append(record)
        if status != "complete":
            break
        decision_path = worker / "decision.json"
        decision = read_json(decision_path)
        restored = decision["restoration"]
        magnitude = float(np.max(np.abs(np.asarray(restored["offsets"], dtype=np.float64))))
        if not isfinite(magnitude):
            raise ValueError("S2 restoration returned nonfinite offsets")
        active = restored["status"] == "restored" and magnitude >= CONTINGENCY["trigger"] * plan["limits"]["offset_bound"]
        record.update(decision=bind(decision_path), max_restored_offset=magnitude, active_bound=active)
        if not active:
            status = "eligible" if decision.get("best_eligible_checkpoint") else decision["status"]
            break
        status = "budget_limited"
    write_json(output / "decision.json", {"status": status, "attempts": attempts,
                                          "selected": attempts[-1].get("decision") if status == "eligible" else None})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    register = commands.add_parser("register")
    register.add_argument("output", type=Path)
    register.add_argument("--reference", type=Path, default=REFERENCE)
    write = commands.add_parser("write")
    for name in ("selection", "target", "settings", "output"):
        write.add_argument(name, type=Path)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("plan", type=Path)
    run_parser.add_argument("output", type=Path)
    run_parser.add_argument("expected_plan_hash")
    args = parser.parse_args()
    if args.action == "register":
        write_json(args.output, settings_record(args.reference))
    elif args.action == "write":
        write_json(args.output, bound_plan(args.selection, args.target, args.settings))
    else:
        run(args.plan, args.output, args.expected_plan_hash)


if __name__ == "__main__":
    main()
