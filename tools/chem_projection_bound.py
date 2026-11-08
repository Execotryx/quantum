"""Supervise a pinned fixed-basis projection/rank diagnostic."""

import argparse
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs
from invsqrt_direct import run_job

from qcompile.chemistry.bounds import fixed_basis_rank_bound
from qcompile.chemistry.factorization import direct_residual, factor_rows, shifted_target, svec
from qcompile.chemistry.schema import read_factorization
from qcompile.io import read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("factorization", "ranking_registration", "ranking", "ranking_completion", "initializer")


def validate_registration(plan: dict) -> tuple[dict[str, Path], dict]:
    paths = {}
    for name in INPUTS:
        item = plan[name]
        path = Path(item["path"])
        if sha256(path) != item["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    registration = read_json(paths["ranking_registration"])
    ranking = read_json(paths["ranking"])
    completion = read_json(paths["ranking_completion"])
    if (completion["ranking_sha256"] != plan["ranking"]["sha256"]
            or completion["registration_sha256"] != plan["ranking_registration"]["sha256"]
            or ranking["shape"] != plan["shape"] or ranking["target_sha256"] != plan["target_sha256"]
            or ranking["factorization_sha256"] != plan["factorization"]["sha256"]
            or registration["plan"]["factorization"]["sha256"] != plan["factorization"]["sha256"]):
        raise ValueError("ranking registration, target or source does not agree")
    matches = [item for item in ranking["ranking"]
               if item["initializer"] == plan["initializer_name"] and item["seed"] == plan["seed"]]
    if (len(matches) != 1 or matches[0]["initializer_sha256"] != plan["initializer"]["sha256"]
            or matches[0]["checkpoint"] != paths["initializer"].name
            or paths["initializer"].parent.resolve() != paths["ranking"].parent.resolve()):
        raise ValueError("registered initializer is not the selected ranking artifact")
    if (type(plan["wall_seconds"]) not in (int, float) or not 0 < plan["wall_seconds"] <= 7200
            or type(plan["block"]) is not int or not 1 <= plan["block"] <= 512):
        raise ValueError("invalid diagnostic budget")
    return paths, matches[0]


def worker(plan_path: Path, output: Path, expected_hash: str) -> None:
    if sha256(plan_path) != expected_hash:
        raise ValueError("diagnostic plan hash differs")
    plan = read_json(plan_path)
    paths, initializer = validate_registration(plan)
    settings, _, _, _, api = backend()
    inputs = fixed_inputs(api, paths["factorization"])
    arrays = read_factorization(paths["initializer"], spec={
        "U": ("f", ("R", "B", inputs.num_orbitals)), "W": ("f", ("R", "B", "C")),
    })
    vectors, weights = arrays["U"], arrays["W"]
    if list(weights.shape) != plan["shape"]:
        raise ValueError("initializer shape differs")
    target = np.ascontiguousarray(shifted_target(inputs.ref["tei"], inputs.S), dtype=np.float64)
    if hashlib.sha256(memoryview(target).cast("B")).hexdigest() != plan["target_sha256"]:
        raise ValueError("shifted target hash differs")
    unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
    features = svec(unit[..., :, None] * unit[..., None, :])
    residual = direct_residual(target, factor_rows(features, weights))
    if not np.isclose(residual, initializer["initial_continuous_residual"], rtol=1e-10, atol=1e-12):
        raise ValueError("initializer residual differs from ranking receipt")
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__).resolve(), ROOT / "src/qcompile/chemistry/bounds.py",
               ROOT / "src/qcompile/chemistry/factorization.py", ROOT / "uv.lock")
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": expected_hash, "backend": settings,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        "blas_threads": {key: os.environ.get(key) for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
    })
    started = time.monotonic()
    bound = fixed_basis_rank_bound(target, vectors, rank=weights.shape[0] * weights.shape[2], block=plan["block"])
    validate_registration(plan)
    if sha256(plan_path) != expected_hash:
        raise ValueError("diagnostic plan changed")
    write_json(output / "diagnostic.json", {
        "bound": bound, "initializer_residual": residual, "elapsed_seconds": time.monotonic() - started,
        "decision": "diagnostic_only", "scope": "no finite-precision certification and no shape exclusion",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("expected_hash", nargs="?")
    args = parser.parse_args()
    if args.action == "worker":
        if args.expected_hash is None:
            parser.error("worker requires a supervisor-provided plan hash")
        worker(args.plan, args.output, args.expected_hash)
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
    write_json(args.output / "status.json", {"status": status, "scope": "execution status, not chemistry eligibility"})


if __name__ == "__main__":
    main()
