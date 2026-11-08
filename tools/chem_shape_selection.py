"""Restore offsets and rank full projected chemistry costs for passing lanes."""

from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
from banked_chemistry import backend
from chem_alternating import bind, collect_lanes
from chem_loader_rank import run_worker
from chem_refit import fixed_inputs
from chem_s2 import json_safe
from chem_s2_settings import checked_settings

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.offset_restoration import restore_offsets
from qcompile.chemistry.s2 import pinned_checkpoint
from qcompile.chemistry.schema import SPEC, read_factorization
from qcompile.io import read_json, sha256, write_json


def project_lane(pins: dict, inputs: Any, api: Any, math_api: Any,
                 settings: dict, output: Path, seed: int) -> dict:
    arrays = read_factorization(Path(pins["s1_checkpoint"]["path"]), spec={
        "U": ("f", ("R", "B", inputs.num_orbitals)), "W": ("f", ("R", "B", "C")),
    })
    vectors, weights = arrays["U"], arrays["W"]
    shape = weights.shape
    if list(shape) != read_json(Path(pins["s1_registration"]["path"]))["plan"]["shape"]:
        raise ValueError("projection checkpoint shape differs from its registration")
    offsets = np.zeros((shape[0], shape[2]))
    _, words, _ = pinned_checkpoint(api, math_api, inputs, vectors, weights, offsets, 12)
    n = inputs.num_orbitals
    edges = inputs.params["tree_edges"]
    decoded = math_api.reconstruct_u_vectors(words[n:].astype(np.float64) / (1 << 11), edges).reshape(vectors.shape)
    h1 = inputs.ref["oei"] - 0.5 * np.einsum("prrq->pq", inputs.ref["tei"])
    h1_base = h1 - inputs.ref["electrons"] * inputs.S / 2 + inputs.beta_1 * np.eye(n)
    gap_base = inputs.energy_upper - inputs.ref["ecore"] + inputs.ref["electrons"] * inputs.beta_1

    def evaluate(candidate):
        return pinned_checkpoint(api, math_api, inputs, vectors, weights, candidate, 12)[2]

    limits = settings["limits"]
    restoration = restore_offsets(decoded, weights, h1_base, gap_base, evaluate,
                                  max_evaluations=limits["restore_evaluations"], max_seconds=limits["wall_seconds"],
                                  offset_bound=limits["offset_bound"], **settings["floors"])
    write_json(output / "restoration.json", json_safe(restoration))
    record = {"status": restoration["status"], "restoration": bind(output / "restoration.json")}
    if restoration["status"] != "restored":
        return record
    lambda_proj = float(restoration["metrics"]["lambda_eff"])
    params, words, _ = pinned_checkpoint(api, math_api, inputs, vectors, weights, restoration["offsets"], 8)
    factorization = output / "projection.npz"
    word_table = output / "words.npz"
    deterministic_npz(factorization, {key: params[key] for key in SPEC})
    deterministic_npz(word_table, {"words": words, "edges": edges})
    factor_pin, words_pin = bind(factorization), bind(word_table)
    trials = []
    ranks = []
    for split in (4, 5, 6):
        plan = output / f"split-{split}.json"
        write_json(plan, {"mode": "projection", "factorization": factor_pin, "words": words_pin,
                          "brot": 8, "low_bits": split, "lambda_proj": lambda_proj,
                          "shots_per_address": 2, "seed": seed, "wall_seconds": limits["wall_seconds"]})
        work = output / f"split-{split}"
        run_worker(plan, work, sha256(plan))
        receipt = work / "ranking.json"
        ranks.extend(read_json(receipt)["ranked"])
        trials.append(bind(receipt))
    best = min(ranks, key=lambda row: (row["modeled_cost"], row["low_bits"], row["batch"]))
    return {**record, "lambda_proj": lambda_proj, "factorization": factor_pin,
            "words": words_pin, "trials": trials, "best": best}


def select_lanes(directory: Path, output: Path, settings_path: Path, seed: int) -> None:
    if seed < 0 or output.exists():
        raise ValueError("selection needs a nonnegative seed and a fresh output")
    settings, settings_pin = checked_settings(settings_path)
    lanes, eligible = collect_lanes(directory)
    projections = {}
    if eligible:
        work = output.with_name(f"{output.stem}-projections")
        work.mkdir(parents=True, exist_ok=False)
        write_json(work / "registration.json", {"seed": seed, "s2_settings": settings_pin,
                                                 "lanes": {lane: lanes[lane] for lane in eligible}})
        _, _, _, _, api = backend()
        math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
        reference = Path(settings["reference_offsets"]["reference"]["path"])
        inputs = fixed_inputs(api, reference)
        for lane in eligible:
            projections[lane] = project_lane(lanes[lane], inputs, api, math_api, settings, work / lane, seed)
    if checked_settings(settings_path)[1] != settings_pin or collect_lanes(directory) != (lanes, eligible):
        raise ValueError("settings or fitted lanes changed while projecting costs")
    survivors = [lane for lane in eligible if projections[lane]["status"] == "restored"]
    winner = min(survivors, key=lambda lane: (projections[lane]["best"]["modeled_cost"], eligible[lane], lane),
                 default=None)
    write_json(output, {"status": "go" if winner else "no_go", "selected": winner,
                        "eligible": list(eligible), "lanes": lanes, "projections": projections,
                        "s2_settings": settings_pin, "handoff": lanes[winner] if winner else None})
