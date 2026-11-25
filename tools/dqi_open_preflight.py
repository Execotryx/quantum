"""Replay frozen D4 captures and screen a rebuilt open DQI circuit."""

import argparse
import importlib
import sys
from pathlib import Path
from statistics import mean

import numpy as np
from dqi_compact_layout import audit_input
from dqi_compact_multi_pole import forced_sequence
from dqi_matched_batches import reconstruct, verify

from qcompile.dqi.decoder import decode, syndrome
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend


def checked_file(pin: dict) -> Path:
    path = Path(pin["path"])
    if sha256(path) != pin["sha256"]:
        raise ValueError(f"File changed since registration: {path}")
    return path


def fixtures(witnesses: Path):
    field = GF4096()
    rng = np.random.default_rng(2735)
    supports = {
        f"weight-{weight}": dict(zip(
            map(int, rng.choice(4095, weight, replace=False)),
            map(int, rng.integers(1, 4096, weight)), strict=True,
        ))
        for weight in range(36)
    }
    for row in read_json(witnesses)["cases"]:
        poles = row["local_poles"]
        label = "poles-" + "-".join(map(str, poles))
        errors = {int(position): value for position, value in row["support"].items()}
        if syndrome(errors, field) != row["syndrome"] or audit_input(errors, field)["local_poles"] != poles:
            raise ValueError(f"Archived pole witness changed: {label}")
        supports[label] = errors
    zero_slope = forced_sequence(
        field, (True, False, True),
        heads=(((0, 1), (0, 1)), ((0, 1), (1, 0)), ((0, 1), (0, 1))),
    )
    chart = audit_input(zero_slope, field, emit_folds=True)
    if chart["local_poles"] != [0, 2] or chart["folds"][1]["heads"][1] != [1, 0]:
        raise ValueError("The zero-slope witness has the wrong chart")
    supports["poles-0-2-zero-slope"] = zero_slope
    labels = list(supports)
    raw = [syndrome(errors, field) for errors in supports.values()]
    for label, words in zip(labels, raw, strict=True):
        if decode(words, field) != supports[label]:
            raise ValueError(f"Invalid sparse fixture: {label}")
    return labels, np.asarray(raw), list(supports.values())


def run(registration: Path, backend: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    plan = read_json(registration)
    registration_hash = sha256(registration)
    if any(len(plan[key]) != 2 or len(set(plan[key])) != 2 for key in ("fixture_seeds", "panel_seeds")):
        raise ValueError("Expected two distinct simulator seeds and two distinct panel seeds")
    code = [checked_file(pin) for pin in plan["code"]]
    if Path(__file__).resolve() not in {path.resolve() for path in code}:
        raise ValueError("The registration does not pin this driver")
    settings = read_json(backend)
    validate_backend(settings)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if inventory != plan["backend_inventory_sha256"]:
        raise ValueError("Backend inventory differs from the registration")
    pins = plan["evidence"]
    for pin in plan["source"]:
        checked_file(pin)
    profile = read_json(checked_file(pins["profile"]))
    residual = read_json(checked_file(pins["residual"]))
    member = read_json(checked_file(pins["member"]))
    checked_file(pins["member_registration"])
    checked_file(pins["historical_registration"])
    control = read_json(checked_file(pins["historical_banked"]))
    artifacts = {role: checked_file(pin) for role, pin in plan["artifacts"].items()}
    builds = [checked_file(pin).resolve() for pin in plan["builds"]]
    candidate_sha = plan["artifacts"]["candidate"]["sha256"]
    if (
        set(artifacts) != {"banked", "candidate"} or len(builds) != 2 or len(set(builds)) != 2
        or {read_json(path)["sha256"] for path in builds} != {candidate_sha}
        or plan["artifacts"]["banked"]["sha256"] != member["sha256"]
        or member["registration_sha256"] != pins["member_registration"]["sha256"]
        or profile["banked_sha256"] != member["sha256"]
        or residual["circuits"]["banked"] != member["sha256"]
        or control["registration_sha256"] != pins["historical_registration"]["sha256"]
        or profile["backend_inventory_sha256"] != inventory
        or residual["backend_inventory_sha256"] != inventory
    ):
        raise ValueError("Control, build or backend identities differ")

    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    spec = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(spec.degree))
    batches_per_panel, leftover = divmod(4096, api.DEFAULT_BATCH_SIZE)
    if leftover:
        raise ValueError("Official batch size does not divide the registered panel")
    error_keys = ("phase_offsets", "value_offsets", "dirty_offsets", "mask_offsets")
    entries = {}
    for draw, receipt in profile["batch_receipts"].items():
        for name, digest in receipt["batches"].items():
            path = Path(plan["captures"]["original"]) / draw / name
            entries[path] = (digest, None)
    for row in residual["batches"]:
        name = f"batch-{row['batch_start']:06}.json"
        path = Path(plan["captures"]["residual"]) / row["draw"] / name
        entries[path] = (row["capture_sha256"], row["controls"]["banked"])
    if len(entries) != 6:
        raise ValueError("Expected four original and two residual batches")

    labels, raw, supports = fixtures(checked_file(pins["pole_witnesses"]))
    roles = {}
    for role in ("banked", "candidate"):
        print(f"{role} started", flush=True)
        circuit = km.Circuit.from_file(str(artifacts[role]))
        api.validate_registers(circuit, spec)
        archived = []
        for path, (digest, banked_expected) in entries.items():
            batch, samples, masks, expected = reconstruct(api, spec, tables, path, digest)
            result = verify(circuit, spec, api, km, samples, masks, expected, batch["sim_seed"])
            if role == "banked":
                if banked_expected is None:
                    banked_expected = {
                        f"{key}_offsets": sorted(
                            row["index"] - batch["batch_start"] for row in batch["shots"] if row[f"{key}_error"]
                        )
                        for key in ("value", "phase")
                    }
                if any(result[key] != banked_expected[key] for key in banked_expected if key in error_keys):
                    raise ValueError(f"Banked replay differs from the original observation: {path}")
            archived.append({"capture_sha256": digest, "capture": path.as_posix(), **result})
        targeted = []
        for seed in plan["fixture_seeds"]:
            for variant in ("random", "zero"):
                masks = np.random.default_rng(seed).integers(0, 4096, (len(raw), 4095))
                if variant == "zero":
                    masks.fill(0)
                expected = np.asarray([
                    sum((value & int(mask[position])).bit_count() for position, value in errors.items()) % 2
                    for errors, mask in zip(supports, masks, strict=True)
                ], dtype=bool)
                result = verify(circuit, spec, api, km, raw, masks, expected, seed)
                targeted.append({"seed": seed, "mask": variant, **result})
        panels = []
        for seed in plan["panel_seeds"]:
            rng = np.random.default_rng(seed)
            results = []
            for index in range(batches_per_panel):
                samples, masks, expected = api.sample_shots(spec, tables, rng, api.DEFAULT_BATCH_SIZE)
                results.append(verify(circuit, spec, api, km, samples, masks, expected, seed + index))
            panels.append({"seed": seed, "batches": results,
                           "mean_toffoli_like": mean(row["mean_toffoli_like"] for row in results)})
        ceiling = control["cost"] / (circuit.num_qubits**2 * control["repetition_factor"])
        roles[role] = {
            "qubits": circuit.num_qubits, "static_toffoli_like": circuit.operation_statistics().num_toffoli_like,
            "archived": archived, "targeted": targeted, "panels": panels,
            "matched_clean": not any(row[key] for row in archived + targeted for key in error_keys),
            "gate_ceiling": ceiling, "panels_clear_ceiling": max(row["mean_toffoli_like"] for row in panels) < ceiling,
        }
        print(f"{role} done: {circuit.num_qubits} qubits, panel means "
              f"{[round(row['mean_toffoli_like'], 2) for row in panels]}", flush=True)
        del circuit
    if sha256(registration) != registration_hash:
        raise ValueError("Registration changed during the preflight")
    candidate = roles["candidate"]
    write_json(output, {
        "registration_sha256": registration_hash,
        "fixture_labels": labels,
        "roles": roles,
        "native_gate_passed": candidate["matched_clean"] and candidate["panels_clear_ceiling"],
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("registration", "backend", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.registration, args.backend, args.output)


if __name__ == "__main__":
    main()
