"""Rank and independently rebuild banked ANGLE families for pinned chemistry inputs."""

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs
from chem_s2 import json_safe
from invsqrt_direct import run_job

from qcompile.chemistry.loaders import family, max_batch, rank_complete_cost, verify_nonzero_xor
from qcompile.chemistry.precision import passes_margins
from qcompile.io import read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]


def validate_registration(plan: dict) -> dict[str, Path]:
    mode = plan["mode"]
    if mode not in ("reference_control", "s3"):
        raise ValueError("expected an explicit reference_control or s3 input")
    names = ["factorization", "words"]
    if mode == "s3":
        names += ["s3_registration", "s3_decision", "s3_result"]
    paths = {}
    for name in names:
        item = plan[name]
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    if mode == "reference_control":
        pinned = read_json(ROOT / "docs/evidence/step3-chemistry-words.json")
        if (plan["factorization"]["sha256"] != pinned["factorization_sha256"]
                or plan["words"]["sha256"] != pinned["words_sha256"] or plan["brot"] != pinned["brot"]):
            raise ValueError("reference control must use the pinned factorization, words and precision")
    else:
        registration = read_json(paths["s3_registration"])
        decision = read_json(paths["s3_decision"])
        result = read_json(paths["s3_result"])
        bits = decision.get("last_passing")
        if (decision.get("status") not in ("ladder_passed", "step_failed", "budget_limited", "inconclusive")
                or type(bits) is not int or bits != plan["brot"] or result.get("eligible") is not True
                or not passes_margins(result.get("metrics", {}))
                or paths["s3_registration"].parent.resolve() != paths["s3_decision"].parent.resolve()
                or paths["s3_result"].parent.resolve() != (paths["s3_decision"].parent / f"precision-{bits:02}").resolve()
                or result["hashes"]["submission.npz"] != plan["factorization"]["sha256"]
                or result["hashes"]["words.npy"] != plan["words"]["sha256"]
                or not any(step["brot"] == bits and step["eligible"] is True
                           and step["result"]["checkpoint"] == f"precision-{bits:02}" for step in decision["steps"])):
            raise ValueError("loader input is not the terminal S3 passing handoff")
        if not registration.get("plan_sha256"):
            raise ValueError("S3 registration lacks its plan identity")
    if (type(plan["brot"]) is not int or not 1 <= plan["brot"] <= 52
            or type(plan["low_bits"]) is not int or plan["low_bits"] < 1
            or type(plan["shots_per_address"]) is not int or not 1 <= plan["shots_per_address"] <= 64
            or type(plan["seed"]) is not int or plan["seed"] < 0
            or type(plan["wall_seconds"]) not in (int, float) or not 0 < plan["wall_seconds"] <= 86400):
        raise ValueError("invalid registered loader budget or precision")
    return paths


def load_words(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    loaded = np.load(path, allow_pickle=False)
    if isinstance(loaded, np.ndarray):
        return loaded, None
    with loaded as archive:
        if set(archive.files) != {"words", "edges"} or len(archive.files) != 2:
            raise ValueError("reference word archive must contain exactly words and tree edges")
        return np.array(archive["words"]), np.array(archive["edges"])


def run_worker(plan_path: Path, output: Path, expected_plan_hash: str) -> None:
    if sha256(plan_path) != expected_plan_hash:
        raise ValueError("registered loader plan hash differs")
    plan = read_json(plan_path)
    paths = validate_registration(plan)
    settings, km, circuits_api, _, verifier = backend()
    inputs = fixed_inputs(verifier, paths["factorization"])
    words, edges = load_words(paths["words"])
    if edges is not None and not np.array_equal(edges, inputs.params["tree_edges"]):
        raise ValueError("registered word tree disagrees with factorization")
    r, b, _ = inputs.w.shape
    rows = inputs.num_orbitals + r * b
    brot, bank = plan["brot"], plan["low_bits"]
    if words.shape != (rows, inputs.num_orbitals - 1):
        raise ValueError("registered word table disagrees with factorization shape")
    metrics = verifier.evaluate_words(inputs, words, tree_edges=inputs.params["tree_edges"], brot=brot)
    if not verifier.passes_accuracy(metrics) or not passes_margins(metrics):
        raise ValueError("loader input does not pass exact decoded project margins")
    expected_metrics = (read_json(ROOT / "docs/evidence/step3-chemistry-metrics.json")["official"]
                        if plan["mode"] == "reference_control" else read_json(paths["s3_result"])["metrics"])
    for key in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff"):
        if not math.isclose(metrics[key], expected_metrics[key], rel_tol=2e-9, abs_tol=2e-9):
            raise ValueError(f"exact decoded metric {key} differs from the pinned input receipt")
    cap = min(inputs.num_orbitals - 1, max_batch(rows, brot, bank))
    if cap < 3:
        raise ValueError("no registered batch from 3 fits the ANGLE cap")
    output.mkdir(parents=True, exist_ok=False)
    source_files = (Path(__file__).resolve(), ROOT / "src/qcompile/chemistry/loaders.py",
                    ROOT / "src/qcompile/chemistry/representation.py", ROOT / "uv.lock")
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": expected_plan_hash, "backend": settings,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in source_files},
        "metrics": json_safe(metrics), "expected_full_coverage": rows * 64,
        "scope": "reference control" if plan["mode"] == "reference_control" else "S3 handoff",
    })
    ranked = []
    for batch in range(3, cap + 1):
        candidate = family(km, circuits_api, words, brot, batch, bank)
        recovered, _, toffoli = circuits_api.recover_words_from_circuits(
            candidate, num_vectors=rows, num_angles=inputs.num_orbitals - 1,
            shots_per_address=plan["shots_per_address"], seed=plan["seed"]
        )
        if not np.array_equal(recovered, words):
            raise ValueError(f"native verifier disagrees with the registered table at J={batch}")
        ranking = rank_complete_cost(verifier, inputs, [(batch, candidate, toffoli)], brot, metrics["lambda_eff"])[0]
        write_json(output / "trials" / f"batch-{batch:02}.json", {
            **ranking, "verified_shots": rows * plan["shots_per_address"],
            "scope": "development trial; no complete metric or confirmation",
        })
        ranked.append(ranking)
    ranked.sort(key=lambda entry: (entry["modeled_cost"], entry["batch"]))
    best = ranked[0]["batch"]
    shutil.copyfile(paths["factorization"], output / "submission.npz")
    hashes = []
    nonzero_receipts = []
    for build_index in (1, 2):
        directory = output / f"build-{build_index}"
        directory.mkdir()
        built = family(km, circuits_api, words, brot, best, bank)
        nonzero = verify_nonzero_xor(km, circuits_api, built, words, brot, best, plan["seed"] + build_index)
        nonzero_receipts.append(nonzero)
        for index, circuit in enumerate(built):
            with (directory / f"angle_k_{index}.kmb").open("xb") as stream:
                circuit.to_file(stream, format="kmb")
        hashes.append({path.name: sha256(path) for path in sorted(directory.iterdir())})
    if hashes[0] != hashes[1]:
        raise ValueError("independent loader builds differ")
    validate_registration(plan)
    if sha256(plan_path) != expected_plan_hash:
        raise ValueError("loader plan changed during execution")
    write_json(output / "ranking.json", {
        "ranked": ranked, "selected_batch": best, "factorization_sha256": sha256(output / "submission.npz"),
        "independent_build_hashes": hashes,
        "nonzero_fixtures": nonzero_receipts, "verified_shots_per_candidate": rows * plan["shots_per_address"],
        "expected_full_coverage": rows * 64, "scope": "development only; no complete metric or confirmation",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("expected_plan_hash", nargs="?")
    args = parser.parse_args()
    if args.action == "worker":
        if args.expected_plan_hash is None:
            parser.error("worker requires a supervisor-provided plan hash")
        run_worker(args.plan, args.output, args.expected_plan_hash)
        return
    plan = read_json(args.plan)
    validate_registration(plan)
    args.output.mkdir(parents=True, exist_ok=False)
    plan_hash = sha256(args.plan)
    write_json(args.output / "registration.json", {"plan": plan, "plan_sha256": plan_hash})
    try:
        code = run_job([sys.executable, __file__, "worker", str(args.plan), str(args.output / "worker"), plan_hash],
                       args.output, plan["wall_seconds"])
        status = "complete" if code == 0 else f"worker_exit_{code}"
    except subprocess.TimeoutExpired:
        status = "timeout"
    write_json(args.output / "status.json", {"status": status, "scope": "execution status, not chemistry acceptance"})


if __name__ == "__main__":
    main()
