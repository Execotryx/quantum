"""Profile, rank initializers, and register the compressed chemistry fit grid."""

import argparse
import hashlib
import os
import time
from pathlib import Path

import numpy as np
from banked_chemistry import backend
from chem_refit import fixed_inputs
from chem_shape_search import profile

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.factorization import (
    clustered_initialize,
    continuation_initialize,
    direct_residual,
    factor_rows,
    initialize,
    projection_score,
    shifted_target,
    svec,
)
from qcompile.io import canonical_json, read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
SHAPES = ((9, 143, 40), (9, 129, 40), (10, 129, 40), (8, 120, 40))
SEEDS = (184, 185)


def source_hashes() -> dict[str, str]:
    files = (ROOT / "tools/chem_shape_search.py", ROOT / "src/qcompile/chemistry/factorization.py",
             ROOT / "tools/chem_refit.py", ROOT / "tools/banked_chemistry.py", ROOT / "uv.lock")
    return {str(path.relative_to(ROOT)): sha256(path) for path in files}


def profiled(plan_path: Path, output: Path) -> None:
    plan = read_json(plan_path)
    if tuple(plan["shape"]) not in SHAPES:
        raise ValueError("shape is not part of the registered grid")
    source = Path(plan["factorization"])
    if sha256(source) != plan["factorization_sha256"]:
        raise ValueError("profile factorization changed")
    pins = source_hashes()
    plan_hash, wrapper_hash = sha256(plan_path), sha256(Path(__file__))
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {"plan": plan, "plan_sha256": plan_hash,
                                               "source_hashes": pins, "wrapper_sha256": wrapper_hash})
    profile(plan_path, output / "measurement")
    if (source_hashes() != pins or sha256(source) != plan["factorization_sha256"]
            or sha256(plan_path) != plan_hash or sha256(Path(__file__)) != wrapper_hash):
        raise ValueError("profile input or source changed during execution")
    write_json(output / "completion.json", {"profile_sha256": sha256(output / "measurement/profile.json"),
                                           "registration_sha256": sha256(output / "registration.json")})


def validate_profile(directory: Path, shape: tuple[int, int, int], factor_hash: str) -> tuple[Path, str, dict]:
    completion = read_json(directory / "completion.json")
    registration_path = directory / "registration.json"
    profile_path = directory / "measurement/profile.json"
    if (sha256(registration_path) != completion["registration_sha256"]
            or sha256(profile_path) != completion["profile_sha256"]):
        raise ValueError("profile receipt hash differs")
    registration = read_json(registration_path)
    report = read_json(profile_path)
    if (tuple(registration["plan"]["shape"]) != shape or tuple(report["plan"]["shape"]) != shape
            or registration["plan"] != report["plan"] or registration["plan_sha256"] != report["plan_sha256"]
            or registration["plan"]["factorization_sha256"] != factor_hash
            or report["plan"]["factorization_sha256"] != factor_hash
            or not np.isfinite(report["objective_gradient_seconds"]) or report["objective_gradient_seconds"] <= 0
            or not np.isclose(report["direct_residual"], report["pinned_tensor_residual"], rtol=1e-10, atol=1e-10)
            or report["process_peak_rss_kib"] <= 0):
        raise ValueError("profile shape, input or timing differs")
    return profile_path, completion["profile_sha256"], registration


def random_initial(spectrum, eigenvectors, n, shape, seed):
    r, b, c = shape
    if r * c > np.count_nonzero(spectrum > 0):
        raise ValueError("insufficient positive spectral factors")
    groups = (eigenvectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T.reshape(r, c, -1)
    vectors = np.random.default_rng(seed).normal(size=(r, b, n))
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    weights = np.empty(shape)
    for k, group in enumerate(groups):
        features = svec(vectors[k, :, :, None] * vectors[k, :, None, :])
        weights[k] = np.linalg.lstsq(features.T, group.T, rcond=1e-10)[0]
    return vectors, weights


def rank_initializers(plan_path: Path, output: Path) -> None:
    plan = read_json(plan_path)
    plan_hash, ranking_source_hash = sha256(plan_path), sha256(Path(__file__))
    source = Path(plan["factorization"]["path"])
    factor_hash = plan["factorization"]["sha256"]
    shape = tuple(plan["shape"])
    if shape not in SHAPES or sha256(source) != factor_hash:
        raise ValueError("unregistered shape or changed factorization")
    profile_path, profile_hash, profile_registration = validate_profile(Path(plan["profile_directory"]), shape, factor_hash)
    pins = source_hashes()
    if pins != profile_registration["source_hashes"]:
        raise ValueError("ranking source differs from the profile source")
    settings, _, _, _, api = backend()
    inputs = fixed_inputs(api, source)
    target = np.ascontiguousarray(shifted_target(inputs.ref["tei"], inputs.S), dtype=np.float64)
    target_hash = hashlib.sha256(memoryview(target).cast("B")).hexdigest()
    if target_hash != plan["target_sha256"]:
        raise ValueError("registered shifted target differs")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "registration.json", {
        "plan": plan, "plan_sha256": plan_hash, "profile_sha256": profile_hash,
        "profile_path": str(profile_path), "backend": settings, "source_hashes": pins,
        "ranking_source_sha256": ranking_source_hash,
        "blas_threads": {key: os.environ.get(key) for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
    })
    started = time.monotonic()
    spectrum, eigenvectors = np.linalg.eigh(target)
    r, _, c = shape
    n = inputs.num_orbitals
    spectral_rows = (eigenvectors[:, -r * c:] * np.sqrt(spectrum[-r * c:])).T
    entries = []
    for initializer, seed in (("I1", None), ("I2", SEEDS[0]), ("I2", SEEDS[1]), ("I3", None), ("I4", SEEDS[0])):
        if initializer == "I1":
            vectors, weights = initialize(spectrum, eigenvectors, n, shape)
        elif initializer == "I2":
            assert seed is not None
            vectors, weights = clustered_initialize(spectrum, eigenvectors, n, shape, seed)
        elif initializer == "I3":
            vectors, weights = continuation_initialize(inputs.params["U"], inputs.w, shape)
        else:
            assert seed is not None
            vectors, weights = random_initial(spectrum, eigenvectors, n, shape, seed)
        unit = vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)
        features = svec(unit[..., :, None] * unit[..., None, :])
        name = initializer.lower() + (f"-{seed}" if seed is not None else "") + ".npz"
        deterministic_npz(output / name, {"U": unit, "W": weights})
        entries.append({"initializer": initializer, "seed": seed, "checkpoint": name,
                        "initializer_sha256": sha256(output / name),
                        "projection_score": projection_score(spectral_rows, unit, c),
                        "initial_continuous_residual": direct_residual(target, factor_rows(features, weights))})
    if (source_hashes() != pins or sha256(source) != factor_hash or sha256(plan_path) != plan_hash
            or sha256(Path(__file__)) != ranking_source_hash):
        raise ValueError("ranking input or source changed during execution")
    entries.sort(key=lambda row: (row["projection_score"], row["initializer"], row["seed"] or -1))
    ranking_path = output / "ranking.json"
    write_json(ranking_path, {
        "shape": shape, "factorization_sha256": factor_hash, "target_sha256": target_hash,
        "profile_sha256": profile_hash, "ranking": entries, "elapsed_seconds": time.monotonic() - started,
        "scope": "initial factor-space projection diagnostic; not a tensor-residual bound or shape rejection",
    })
    write_json(output / "completion.json", {"registration_sha256": sha256(output / "registration.json"),
                                           "ranking_sha256": sha256(ranking_path)})


def manifest(plan_path: Path, output: Path) -> None:
    plan = read_json(plan_path)
    source = Path(plan["factorization"]["path"])
    factor_hash = plan["factorization"]["sha256"]
    if sha256(source) != factor_hash or tuple(plan["seeds"]) != SEEDS:
        raise ValueError("factorization or registered seed set differs")
    limits = plan["limits"]
    if (type(limits["evaluations"]) is not int or not 1 <= limits["evaluations"] <= 20000
            or type(limits["wall_seconds"]) not in (int, float) or not 0 < limits["wall_seconds"] <= 86400):
        raise ValueError("invalid grid budget")
    lanes = []
    shared_sources = None
    for shape in SHAPES:
        label = f"r{shape[0]}-b{shape[1]}-c{shape[2]}"
        item = plan["shapes"][label]
        profile_path, profile_hash, profile_registration = validate_profile(Path(item["profile_directory"]), shape, factor_hash)
        if shared_sources is None:
            shared_sources = profile_registration["source_hashes"]
        elif profile_registration["source_hashes"] != shared_sources:
            raise ValueError("grid profiles were generated by different sources")
        if profile_hash != item["profile_sha256"]:
            raise ValueError(f"registered profile hash differs for {label}")
        ranking_path = Path(item["ranking_path"])
        ranking_hash = item.get("ranking_sha256")
        if ranking_hash:
            if sha256(ranking_path) != ranking_hash:
                raise ValueError(f"ranking hash differs for {label}")
            completion = read_json(ranking_path.parent / "completion.json")
            rank_registration_path = ranking_path.parent / "registration.json"
            if (completion["ranking_sha256"] != ranking_hash
                    or completion["registration_sha256"] != sha256(rank_registration_path)):
                raise ValueError(f"ranking completion differs for {label}")
            rank_registration = read_json(rank_registration_path)
            if (rank_registration["profile_sha256"] != profile_hash
                    or rank_registration["source_hashes"] != profile_registration["source_hashes"]):
                raise ValueError(f"ranking source binding differs for {label}")
            rank = read_json(ranking_path)
            if (tuple(rank["shape"]) != shape or rank["profile_sha256"] != profile_hash
                    or rank["factorization_sha256"] != factor_hash or rank["target_sha256"] != plan["target_sha256"]):
                raise ValueError(f"ranking binding differs for {label}")
            found = {(entry["initializer"], entry["seed"]) for entry in rank["ranking"]}
            if (len(rank["ranking"]) != 5
                    or found != {("I1", None), ("I2", 184), ("I2", 185), ("I3", None), ("I4", 184)}):
                raise ValueError(f"initializer ranking coverage differs for {label}")
            for entry in rank["ranking"]:
                artifact = ranking_path.parent / entry["checkpoint"]
                if artifact.parent != ranking_path.parent or sha256(artifact) != entry["initializer_sha256"]:
                    raise ValueError(f"initializer artifact differs for {label}")
        for initializer in ("I1", "I2", "I3"):
            for seed in SEEDS:
                lane = f"{label}-{initializer.lower()}-{seed}"
                lane_plan = {"factorization": str(source), "factorization_sha256": factor_hash,
                             "profile": str(profile_path), "profile_sha256": profile_hash,
                             "shape": shape, "initializer": initializer, "seed": seed,
                             "max_evaluations": limits["evaluations"], "wall_seconds": limits["wall_seconds"]}
                lanes.append({"id": lane, "shape": shape, "initializer": initializer, "seed": seed,
                              "seed_semantics": "seeded initialization" if initializer == "I2" else
                                                "ignored; deterministic repeated execution",
                              "profile": str(profile_path), "profile_sha256": profile_hash,
                              "ranking_path": str(ranking_path), "ranking_sha256": ranking_hash,
                              "ready": bool(ranking_hash), "factorization": str(source),
                              "factorization_sha256": factor_hash, "max_evaluations": limits["evaluations"],
                              "wall_seconds": limits["wall_seconds"],
                              "plan_sha256": hashlib.sha256(canonical_json(lane_plan)).hexdigest()})
    if len(lanes) != 24:
        raise ValueError("grid must contain exactly 24 labeled lanes")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "manifest.json", {
        "plan": plan, "plan_sha256": sha256(plan_path), "lanes": lanes,
        "controls": [{"id": "reference-continuation", "shape": [65, 60, 60],
                      "status": "separate registration and full-size profile required"},
                     {"id": "i4-random", "seed": 184, "status": "best shape not yet selected"}],
        "scope": "registration only; blocked lanes must not be launched before rankings exist",
    })
    for lane in lanes:
        if lane["ready"]:
            write_json(output / f"{lane['id']}.json", {
                "factorization": lane["factorization"], "factorization_sha256": factor_hash,
                "profile": lane["profile"], "profile_sha256": lane["profile_sha256"],
                "shape": lane["shape"], "initializer": lane["initializer"], "seed": lane["seed"],
                "max_evaluations": lane["max_evaluations"], "wall_seconds": lane["wall_seconds"],
            })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("profile", "rank", "manifest"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    {"profile": profiled, "rank": rank_initializers, "manifest": manifest}[args.action](args.plan, args.output)


if __name__ == "__main__":
    main()
