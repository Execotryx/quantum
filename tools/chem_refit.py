"""Run a registered fixed-word DFTHC pilot or build a screened ANGLE family."""

import argparse
import math
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from banked_chemistry import backend, banked_circuit
from invsqrt_direct import run_job
from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.refit import FixedWordRefit
from qcompile.chemistry.representation import batch_words
from qcompile.chemistry.schema import read_factorization
from qcompile.io import read_json, sha256, write_json


def fixed_inputs(api, params_path: Path):
    arrays = read_factorization(params_path, allow_extra=True)
    inputs = api.load_inputs(arrays)
    return replace(inputs, params={**inputs.params, "tree_edges": arrays["tree_edges"]})


def fit(plan: Path, output: Path) -> None:
    config = read_json(plan)
    params_path, words_path = (Path(config[name]["path"]) for name in ("factorization", "angle_words"))
    for name, path in (("factorization", params_path), ("angle_words", words_path)):
        if sha256(path) != config[name]["sha256"]:
            raise ValueError(f"registered {name} hash differs")
    limits = config["limits"]
    if type(limits["evaluations"]) is not int or not 1 <= limits["evaluations"] <= 128:
        raise ValueError("expected a bounded evaluation count")
    if not 0 < limits["wall_seconds"] <= 3600:
        raise ValueError("expected a wall budget within one hour")
    brot = config["brot"]
    settings, _, _, _, api = backend()
    dfthc_math = import_module("dfthcsos.scoreinfra.dfthc_math")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {"config": config, "plan_sha256": sha256(plan), "backend": settings})
    deadline = time.monotonic() + limits["wall_seconds"]
    inputs = fixed_inputs(api, params_path)
    words = np.load(words_path, allow_pickle=False)
    edges = api.load_tree_edges(inputs.params["tree_edges"], None)
    control = api.evaluate_words(inputs, words, tree_edges=edges, brot=brot)
    if not api.passes_accuracy(control):
        raise ValueError("fixed-word control failed official accuracy")
    write_json(output / "control.json", control)
    problem = FixedWordRefit(api, dfthc_math, inputs, words, brot)
    best = None
    evaluations = 0
    residual = config["maximum_residual"]
    if not 0 < residual <= min(api.ERROR_1_THRESHOLD, api.ERROR_2_THRESHOLD):
        raise ValueError("residual margin exceeds official bounds")
    if min(config["lambda_margin"], config["gap_margin"]) < 0:
        raise ValueError("floor margins must be nonnegative")

    def objective(scales) -> float:
        nonlocal best, evaluations
        if time.monotonic() >= deadline or evaluations >= limits["evaluations"]:
            raise TimeoutError("pilot budget exhausted")
        evaluations += 1
        params, candidate_words, metrics = problem.evaluate(*scales)
        overages = (
            metrics["error_1"] - residual, metrics["error_2"] - residual,
            api.LAMBDA_FLOOR + config["lambda_margin"] - metrics["Lambda"],
            api.E_GAP_FLOOR + config["gap_margin"] - metrics["E_gap"],
        )
        finite = math.isfinite(metrics["lambda_eff"])
        eligible = api.passes_accuracy(metrics) and finite and max(overages) <= 0
        score = float(metrics["lambda_eff"]) if eligible else 1e6 + sum(max(0, v) for v in overages)
        write_json(
            output / "trials" / f"{evaluations:03}.json",
            {"scales": scales.tolist(), "eligible": bool(eligible), "objective": score,
             "metrics": {k: v if math.isfinite(v) else None for k, v in metrics.items()}},
        )
        if eligible and score < control["lambda_eff"] and (best is None or score < best["objective"]):
            checkpoint = output / f"checkpoint-{evaluations:03}"
            checkpoint.mkdir()
            deterministic_npz(checkpoint / "submission.npz", params)
            read_factorization(checkpoint / "submission.npz")
            np.save(checkpoint / "words.npy", candidate_words, allow_pickle=False)
            best = {
                "objective": score, "checkpoint": checkpoint.name,
                "factorization_sha256": sha256(checkpoint / "submission.npz"),
                "words_sha256": sha256(checkpoint / "words.npy"),
            }
        return score

    bounds = config["scale_bounds"]
    if len(bounds) != 2 or any(not 0.5 <= lo < 1.0 < hi <= 1.5 for lo, hi in bounds):
        raise ValueError("weight and offset bounds must bracket the control within [0.5, 1.5]")
    try:
        result = minimize(objective, np.ones(2), method="Powell", bounds=bounds,
                          options={"maxfev": limits["evaluations"]})
        stop = str(result.message)
    except TimeoutError as error:
        stop = str(error)
    write_json(output / "decision.json", {"evaluations": evaluations, "stop": stop, "best": best})


def build(factorization: Path, words_path: Path, output: Path, brot: int, batch: int, bank: int | None) -> None:
    _, km, circuits, _, api = backend()
    params = read_factorization(factorization, allow_extra=True)
    words = np.load(words_path, allow_pickle=False)
    r, b, _ = params["U"].shape
    if words.shape != (76 + r * b, 75) or not 1 <= brot <= 52 or not 1 <= batch <= 75:
        raise ValueError("ANGLE layout disagrees with the factorization")
    _, deltas = batch_words(words, batch, brot)
    address_bits = (len(words) - 1).bit_length()
    low_bits = address_bits - 1 if bank is None else bank
    if not 1 <= low_bits < address_bits:
        raise ValueError("bank width must split the selection register")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(factorization, output / "submission.npz")
    for index, delta in enumerate(deltas):
        circuit = banked_circuit(km, circuits, delta, brot, low_bits=low_bits)
        if circuit.num_qubits > api.QUBIT_CAP:
            raise ValueError("emitted ANGLE exceeds qubit cap")
        with (output / f"angle_k_{index}.kmb").open("xb") as stream:
            circuit.to_file(stream, format="kmb")


def rank(plan: Path, output: Path) -> None:
    settings, _, _, _, api = backend()
    proposals = read_json(plan)["layouts"]
    results = rank_layouts(api, proposals)
    write_json(output, {
        "plan_sha256": sha256(plan), "backend": settings, "layouts": results,
        "scope": "structural ranking with zero ANGLE Toffolis and no numerical score factor",
    })


def rank_layouts(api, proposals):
    if not 1 <= len(proposals) <= 64:
        raise ValueError("layout shortlist must contain between 1 and 64 entries")
    results = []
    for proposal in proposals:
        r, b, c, brot, batch = (proposal[name] for name in ("r", "b", "c", "brot", "batch"))
        if any(type(n) is not int or n < 1 for n in (r, b, c, brot, batch)) or brot > 52 or batch > 75:
            raise ValueError("invalid layout dimensions")
        rows = 76 + r * b
        address = (rows - 1).bit_length()
        low = proposal.get("bank", address - 1)
        if type(low) is not int or not 1 <= low < address:
            raise ValueError("invalid shortlist bank width")
        high = address - low
        scratch = max(low + int(high > 1), high - 1)
        angle_qubits = address + brot * batch + scratch
        prep = api.heuristic_costs(76, r, b, c, brot)
        full_qubits = prep["persistent_qubits"] + batch * brot + max(prep["temporary_qubits"], scratch)
        results.append({
            **proposal, "angle_qubits": angle_qubits, "within_cap": angle_qubits <= api.QUBIT_CAP,
            "angle_count": (75 + batch - 1) // batch, "expected_shots": 64 * rows,
            "two_body_factors": r * c, "lookup_rows": rows, "address_bits": address,
            "heuristic": prep, "projected_qubits": full_qubits,
            "preparation_rotation_tq": prep["toffoli"] * full_qubits,
        })
    results.sort(key=lambda row: (not row["within_cap"], row["preparation_rotation_tq"]))
    return results


def quantize(factorization: Path, words_path: Path, output: Path, source_bits: int, brot: int) -> None:
    if not 1 <= brot <= source_bits <= 52:
        raise ValueError("target precision must be between one bit and the source precision")
    settings, _, _, _, api = backend()
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    inputs = fixed_inputs(api, factorization)
    words = np.load(words_path, allow_pickle=False)
    if words.dtype.kind not in "iu" or np.any(words < 0) or np.any(words >= (1 << source_bits)):
        raise ValueError("source angle words outside the declared precision")
    reduced = np.rint(words.astype(np.float64) / (1 << (source_bits - brot))).astype(np.int64) % (1 << brot)
    params, regenerated, metrics = FixedWordRefit(api, math_api, inputs, reduced, brot).evaluate(1.0, 1.0)
    output.mkdir(parents=True, exist_ok=False)
    eligible = api.passes_accuracy(metrics)
    write_json(output / "quantization.json", {
        "factorization_sha256": sha256(factorization), "source_words_sha256": sha256(words_path),
        "source_bits": source_bits, "brot": brot, "eligible": bool(eligible), "backend": settings,
        "metrics": {key: value if math.isfinite(value) else None for key, value in metrics.items()},
    })
    if eligible:
        deterministic_npz(output / "submission.npz", params)
        np.save(output / "words.npy", regenerated, allow_pickle=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    pilot = commands.add_parser("fit")
    pilot.add_argument("plan", type=Path)
    pilot.add_argument("output", type=Path)
    worker = commands.add_parser("fit-worker")
    worker.add_argument("plan", type=Path)
    worker.add_argument("output", type=Path)
    shortlist = commands.add_parser("rank")
    shortlist.add_argument("plan", type=Path)
    shortlist.add_argument("output", type=Path)
    precision = commands.add_parser("quantize")
    precision.add_argument("factorization", type=Path)
    precision.add_argument("words", type=Path)
    precision.add_argument("output", type=Path)
    precision.add_argument("--source-bits", type=int, required=True)
    precision.add_argument("--brot", type=int, required=True)
    synthesis = commands.add_parser("build")
    synthesis.add_argument("factorization", type=Path)
    synthesis.add_argument("words", type=Path)
    synthesis.add_argument("output", type=Path)
    synthesis.add_argument("--brot", type=int, required=True)
    synthesis.add_argument("--batch", type=int, required=True)
    synthesis.add_argument("--bank", type=int)
    args = parser.parse_args()
    if args.action == "fit-worker":
        fit(args.plan, args.output)
    elif args.action == "fit":
        timeout = read_json(args.plan)["limits"]["wall_seconds"]
        if not 0 < timeout <= 3600:
            raise ValueError("expected a wall budget within one hour")
        args.output.mkdir(parents=True, exist_ok=False)
        try:
            code = run_job([sys.executable, __file__, "fit-worker", str(args.plan), str(args.output / "fit")],
                           args.output, timeout)
            status = "complete" if code == 0 else f"worker_exit_{code}"
        except subprocess.TimeoutExpired:
            status = "timeout"
        write_json(args.output / "status.json", {"status": status})
    elif args.action == "rank":
        rank(args.plan, args.output)
    elif args.action == "quantize":
        quantize(args.factorization, args.words, args.output, args.source_bits, args.brot)
    else:
        build(args.factorization, args.words, args.output, args.brot, args.batch, args.bank)


if __name__ == "__main__":
    main()
