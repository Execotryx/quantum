"""Gate and measure the DQI retained-discrepancy history depth."""

import argparse
import hashlib
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

from qcompile.dqi.field import GF4096
from qcompile.dqi.history_sampling import history_statistics
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import validate_backend

ROOT = Path(__file__).resolve().parents[1]
CHUNKS, SHOTS, WORKERS = 100, 100_000, 16
PROBE_SHOTS = 256


def runtime(path: Path):
    backend = read_json(path)
    validate_backend(backend)
    sys.path[:0] = [backend["kickmix_root"], backend["verifiers_root"]]
    km, api = import_module("kickmix"), import_module("dqi.verify_submission_dqi")
    field = km.GF2Field(12)
    if field.mul(2048, 2) != 0x53:
        raise ValueError("native DQI field differs from the pinned polynomial")
    return backend, km, api, field


def probe_worker(backend: Path, output: Path) -> None:
    _, km, api, _ = runtime(backend)
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(2)]
    for i in range(3):
        builder.create_classical_register(12, f"E{i}")
    dirty = builder.alloc_qubits(1)[0]
    builder.cx(syndromes[0][0], dirty)
    builder.free(dirty)
    circuit = builder.finish_circuit()
    spec = api.ProblemSpecDQI.benchmark_instance(m=3, n=2, degree=12, num_shots=PROBE_SHOTS)
    inputs = np.zeros((PROBE_SHOTS, 2), dtype=np.int64)
    inputs[::2] = 1
    masks = np.zeros((PROBE_SHOTS, 3), dtype=np.int64)
    phases = np.zeros(PROBE_SHOTS, dtype=bool)
    try:
        result = api.verify(circuit, spec, seed=0, batch_size=PROBE_SHOTS,
                            max_workers=1, shots=(inputs, masks, phases))
        observed = (result["value_errors"], result["verified_shots"],
                    result["phase_errors"], result["verified_shots"])
    except AssertionError as error:
        match = re.fullmatch(r"Effective error rate .* \(empirical=.*?, value_errors=(\d+)/(\d+), phase_errors=(\d+)/(\d+)\)",
                             str(error))
        if match is None:
            raise
        observed = tuple(map(int, match.groups()))
    status = "per_shot_value_errors" if observed == (128, 256, 0, 256) else "unsupported"
    write_json(output, {"status": status, "counters": observed, "circuit_sha256": api._circuit_sha256(circuit)})


def probe(backend: Path, output: Path) -> None:
    runtime(backend)
    backend_hash = sha256(backend)
    output.mkdir(parents=True, exist_ok=False)
    result = output / "result.json"
    with (output / "execution.log").open("xb") as log:
        process = subprocess.run([sys.executable, __file__, "probe-worker", str(backend), str(result)],
                                 stdout=log, stderr=subprocess.STDOUT, check=False)
    observed = read_json(result) if process.returncode == 0 else {"status": "backend_aborted"}
    if sha256(backend) != backend_hash:
        raise ValueError("backend changed during the overflow probe")
    write_json(output / "probe.json", {**observed, "backend_sha256": backend_hash,
                                      "probe_source_sha256": sha256(Path(__file__)),
                                      "returncode": process.returncode})


def pins(backend: Path, probe_path: Path) -> dict:
    observation = read_json(probe_path)
    backend_hash = sha256(backend)
    if (observation.get("status") != "per_shot_value_errors" or observation.get("returncode") != 0
            or observation.get("counters") != [128, 256, 0, 256] or observation.get("backend_sha256") != backend_hash
            or observation.get("probe_source_sha256") != sha256(Path(__file__))):
        raise ValueError("history work requires a passing freed-nonzero probe on the pinned backend")
    return {"backend_sha256": backend_hash, "probe_sha256": sha256(probe_path),
            "sources": {name: sha256(ROOT / name) for name in (
                "tools/dqi_history_depth.py", "src/qcompile/dqi/bm_routed.py",
                "src/qcompile/dqi/bm_reference.py", "src/qcompile/dqi/decoder.py",
                "src/qcompile/dqi/field.py", "src/qcompile/dqi/history_sampling.py", "uv.lock",
            )}}


_SAMPLER: tuple[Any, Any, Any, Any, Any] | None = None


def initialize_worker(backend: Path, lock: Any) -> None:
    global _SAMPLER
    _, _, api, field = runtime(backend)
    spec = api.ProblemSpecDQI.benchmark_instance(num_shots=SHOTS)
    weights = api.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    _SAMPLER = spec, weights, api.FieldTables(field), GF4096(), lock


def sample_chunk(index: int, seed: int) -> dict:
    if _SAMPLER is None:
        raise ValueError("depth worker must use the registered sampler")
    spec, weights, tables, field, lock = _SAMPLER
    api = import_module("dqi.verify_submission_dqi")
    started = time.monotonic()
    # The pinned sampler allocates a full mask table. Keep just one such
    # allocation live while the independent recurrence workers run in parallel.
    with lock:
        syndromes, masks, phases = api.sample_shots(spec, tables, np.random.default_rng(seed), SHOTS, weights)
        del masks, phases
    digest = hashlib.sha256(memoryview(syndromes).cast("B")).hexdigest()
    return {"chunk": index, "seed": seed, "sample_sha256": digest,
            **history_statistics(syndromes, field), "wall_seconds": time.monotonic() - started}


def read_chunk(path: Path, registration_hash: str, index: int, seed: int) -> dict:
    record = read_json(path)
    content_hash = record.pop("content_sha256", None)
    if (content_hash != identity(record) or record.get("registration_sha256") != registration_hash
            or record.get("chunk") != index or record.get("seed") != seed):
        raise ValueError(f"history chunk identity differs: {path.name}")
    return record


def run(backend: Path, probe_path: Path, output: Path, base_seed: int, *, resume: bool = False) -> None:
    import fcntl

    if base_seed < 0:
        raise ValueError("history depth requires a nonnegative registered seed")
    runtime(backend)
    registration = {"pins": pins(backend, probe_path), "base_seed": base_seed, "chunks": CHUNKS,
                    "shots_per_chunk": SHOTS, "workers": WORKERS,
                    "max_exceedances": 10, "max_degree": 35}
    registration_path = output / "registration.json"
    if not resume:
        output.mkdir(parents=True, exist_ok=False)
        write_json(registration_path, registration)
    if read_json(registration_path) != registration:
        raise ValueError("registered history inputs changed")
    with (output / ".campaign.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "decision.json").exists():
            raise ValueError("history campaign already has a terminal decision")
        run_registered(backend, probe_path, output, registration, sha256(registration_path))


def run_registered(backend: Path, probe_path: Path, output: Path, registration: dict,
                   registration_hash: str) -> None:
    started = time.monotonic()
    base_seed = registration["base_seed"]
    paths = [output / f"chunk-{i:03}.json" for i in range(CHUNKS)]
    records = {path: read_chunk(path, registration_hash, i, base_seed + i)
               for i, path in enumerate(paths) if path.is_file()}
    remaining = [i for i, path in enumerate(paths) if path not in records]
    if remaining and all(record["status"] == "complete" for record in records.values()):
        context = mp.get_context("spawn")
        workers = min(WORKERS, len(remaining), getattr(os, "process_cpu_count", os.cpu_count)() or 1)
        print(f"Sampling {len(remaining)} remaining chunks with {workers} workers", flush=True)
        with ProcessPoolExecutor(max_workers=workers, mp_context=context, initializer=initialize_worker,
                                 initargs=(backend.resolve(), context.BoundedSemaphore(1))) as pool:
            futures = [pool.submit(sample_chunk, i, base_seed + i) for i in remaining]
            for future in as_completed(futures):
                result = {**future.result(), "registration_sha256": registration_hash}
                path = paths[result["chunk"]]
                write_json(path, {**result, "content_sha256": identity(result)}, replace=True)
                records[path] = result
                if result["status"] != "complete":
                    for pending in futures:
                        pending.cancel()
                    break
    if pins(backend, probe_path) != registration["pins"]:
        raise ValueError("preregistered depth inputs changed during sampling")
    decision = {"registration_sha256": registration_hash,
                "chunk_sha256": {path.name: sha256(path) for path in records},
                "final_window_wall_seconds": time.monotonic() - started,
                "summed_chunk_wall_seconds": sum(record.get("wall_seconds", 0) for record in records.values())}
    violation = next((path.name for path, record in records.items() if record["status"] != "complete"), None)
    if violation:
        decision.update(status="degree_violation", violation=violation)
    else:
        totals = list(map(sum, zip(*(record["histogram"] for record in records.values()), strict=True)))
        maximum = list(map(max, zip(*(record["max_degree_by_round"] for record in records.values()), strict=True)))
        shifted = max(record["max_active_shifted_degree"] for record in records.values())
        if sum(totals) != CHUNKS * SHOTS:
            raise ValueError("registered history sampling is incomplete")
        exceedances = [sum(totals[h + 1:]) for h in (1, 2, 3)]
        depth = next((h for h, count in enumerate(exceedances, 1) if count <= 10), 3)
        decision.update(status="complete", depth=depth, histogram=totals, exceedances=exceedances,
                        max_degree_by_round=maximum, max_active_shifted_degree=shifted)
    write_json(output / "decision.json", decision)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("probe", "probe-worker", "run"):
        command = commands.add_parser(name)
        command.add_argument("backend", type=Path)
        command.add_argument("output", type=Path)
        if name == "run":
            command.add_argument("probe", type=Path)
            command.add_argument("--seed", type=int, required=True)
            command.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.action == "run":
        run(args.backend, args.probe, args.output, args.seed, resume=args.resume)
    elif args.action == "probe":
        probe(args.backend, args.output)
    else:
        probe_worker(args.backend, args.output)


if __name__ == "__main__":
    main()
