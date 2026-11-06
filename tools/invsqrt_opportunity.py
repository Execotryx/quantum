"""Run a registered width screen and verify its frozen winner in Linux."""

import argparse
import math
import os
import resource
import secrets
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np

from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.experiments import validate_budget
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/invsqrt-opportunity-v1.json"
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def inputs(protocol: dict[str, Any]) -> dict[str, str]:
    paths = (
        CONFIG,
        Path(__file__).resolve(),
        ROOT / "uv.lock",
        ROOT / "contracts/contract.json",
        ROOT / "vendor/backend.json",
        ROOT / protocol["reference"]["receipt"],
        ROOT / "docs/evidence/step3-completion.json",
    )
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}


def registered(directory: Path) -> dict[str, Any]:
    record = read_json(directory / "registration.json")
    require(record["inputs"] == inputs(record["protocol"]), "registered inputs changed")
    return record["protocol"]


def backend():
    settings = read_json(ROOT / "vendor/backend.json")
    validate_backend(settings)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    return (
        import_module("kickmix"),
        import_module("invsqrt.nr_reference_circuit"),
        import_module("invsqrt.verify_submission_invsqrt"),
    )


def phase(builder, precision, n_p, xs):
    words = builder.fixed_point_model(n_p, precision, xs)
    return words.astype(np.uint64) << np.uint64(64 - precision.output_bits(n_p))


def errors(official, spec, xs, observed):
    target, tolerance = official.reference_values(spec, xs)
    used = np.abs((observed - target).view(np.int64)).view(np.uint64)
    return used, tolerance


def scan(builder, official, spec, precision, n_p):
    minimum = (1 << 64, 0)
    worst = (-1.0, 0)
    invalid = 0
    for start in range(1, spec.max_x + 1, 65536):
        xs = np.arange(start, min(start + 65536, spec.max_x + 1), dtype=np.uint64)
        used, tolerance = errors(official, spec, xs, phase(builder, precision, n_p, xs))
        margin = tolerance.astype(np.int64) - used.astype(np.int64)
        at_minimum = int(margin.argmin())
        minimum = min(minimum, (int(margin[at_minimum]), int(xs[at_minimum])))
        ratio = used / tolerance
        at_worst = int(ratio.argmax())
        worst = max(worst, (float(ratio[at_worst]), -int(xs[at_worst])))
        invalid += int(np.count_nonzero(used >= tolerance))
    return {
        "input_count": spec.max_x,
        "nonpositive_margins": invalid,
        "minimum_margin_phase64": minimum[0],
        "minimum_margin_x": minimum[1],
        "worst_tolerance_fraction": worst[0],
        "worst_x": -worst[1],
    }


def counts(stats) -> tuple[int, int, int]:
    return (
        int(stats.num_toffoli_like),
        int(stats.num_t_like),
        int(stats.num_z_pow(min_clifford_hierarchy_level=4)),
    )


def smoke(km, builder, official, circuit, spec, precision, protocol, margins):
    policy = protocol["development"]
    n_p = protocol["n_p"]
    rng = np.random.default_rng(policy["seed"])
    points = {1, spec.max_x, margins["minimum_margin_x"], margins["worst_x"]}
    points.update(int(x) for x in rng.integers(1, spec.max_x + 1, size=policy["random_inputs"]))
    for k in range(spec.width):
        for center in (2**k, 3 * 2**k):
            points.update(x for x in range(center - 1, center + 2) if 1 <= x <= spec.max_x)
    x_reg, scratch = official.validate_registers(circuit, spec)
    batch = policy["shots_per_input"]
    sim = km.Simulator(batch_size=batch, counting_operations=True, seed=policy["seed"])
    inputs_sorted = sorted(points)
    modeled = phase(builder, precision, n_p, np.array(inputs_sorted, dtype=np.uint64))
    for x, model in zip(inputs_sorted, modeled, strict=True):
        xs = np.full(batch, x, dtype=np.uint64)
        sim.clear_for_shot()
        sim.write_across_shots(x_reg, official.to_bits(xs, spec.width))
        sim.do(circuit)
        require(np.array_equal(official.from_bits(sim.read_across_shots(x_reg)), xs), f"x changed at {x}")
        require(not len(scratch) or not sim.read_across_shots(scratch).any(), f"dirty scratch at {x}")
        for i in range(batch):
            observed = official.half_turns_to_units(sim.read_shot_phase(i))
            require(observed == int(model), f"phase model mismatch at {x}, shot {i}")
    shots = len(inputs_sorted) * batch
    static = counts(circuit.operation_statistics())
    executed = counts(sim.operation_statistics())
    require(executed == tuple(n * shots for n in static), "executed and static resource counts differ")
    return {"inputs": inputs_sorted, "shots": shots, "executed_counts": executed, "counts_per_shot": static}


def lane(directory: Path, name: str, cpu: int) -> None:
    os.sched_setaffinity(0, {cpu})
    started = time.time()
    protocol = registered(directory)
    km, builder, official = backend()
    n_p = protocol["n_p"]
    spec = official.ProblemSpecInvSqrt.for_n_p(n_p)
    precision = builder.Precision(*protocol["widths"][name])
    circuit = builder.build_nr_circuit(n_p, prec=precision)
    path = directory / name / "invsqrt.kmb"
    with path.open("xb") as stream:
        circuit.to_file(stream, format="kmb")
    circuit = km.Circuit.from_file(str(path))
    digest = sha256(path)
    require(official._circuit_sha256(circuit) == digest, "KMB round trip changed bytes")
    margins = scan(builder, official, spec, precision, n_p)
    require(margins["nonpositive_margins"] == 0, "full-domain model has nonpositive margins")
    sampled = smoke(km, builder, official, circuit, spec, precision, protocol, margins)
    toffoli, t_base, rotations = sampled["counts_per_shot"]
    epsilon = math.pi * margins["minimum_margin_phase64"] / 2**64 / rotations
    cost = circuit.num_qubits * (
        toffoli + (t_base + rotations * official.rotation_t_count(epsilon)) / official.T_PER_TOFFOLI
    )
    reference = protocol["reference"]
    gain = 1 - cost / reference["score"]
    if name == "reference":
        require(digest == reference["sha256"], "reference KMB hash mismatch")
        require(math.isclose(cost, reference["score"], rel_tol=1e-12), "reference complete cost mismatch")
    usage = resource.getrusage(resource.RUSAGE_SELF)
    write_json(
        path.parent / "result.json",
        {
            "status": "passed",
            "widths": protocol["widths"][name],
            "sha256": digest,
            "qubits": circuit.num_qubits,
            "reaction_depth": circuit.reaction_depth(),
            "operations": len(circuit),
            "margins": margins,
            "native_development": sampled,
            "rotation_epsilon_radians": epsilon,
            "complete_modeled_cost": cost,
            "gain": gain,
            "eligible": gain >= protocol["minimum_gain"]
            and margins["worst_tolerance_fraction"] <= protocol["maximum_tolerance_fraction"],
            "started_unix": started,
            "finished_unix": time.time(),
            "cpu_seconds": usage.ru_utime + usage.ru_stime,
            "peak_rss_kib": usage.ru_maxrss,
            "affinity_cpu": cpu,
        },
    )


def screen(directory: Path) -> None:
    protocol = read_json(CONFIG)
    validate_budget(protocol)
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    cpus = sorted(os.sched_getaffinity(0))
    require(len(cpus) >= 2, "two available CPUs are required")
    available = next(
        int(line.split()[1])
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    require(available >= protocol["budget"]["minimum_available_memory_kib"], "insufficient available RAM")
    directory.mkdir(parents=True, exist_ok=False)
    write_json(
        directory / "registration.json",
        {
            "protocol": protocol,
            "inputs": inputs(protocol),
            "environment": capture(ROOT),
            "registered_unix": time.time(),
            "contract_hash": contract.hash,
            "available_memory_kib": available,
        },
    )
    start = time.monotonic()
    budget = protocol["budget"]
    deadline = start + budget["max_wall_seconds"]
    env = {**os.environ, **dict.fromkeys(THREADS, "1")}

    def attempt(name: str, cpu: int):
        output = directory / name
        output.mkdir()
        print(f"Starting {name} on CPU {cpu}", flush=True)
        try:
            with (output / "execution.log").open("wb") as log:
                subprocess.run(
                    [sys.executable, __file__, "lane", str(directory), name, str(cpu)],
                    env=env,
                    check=True,
                    timeout=max(0.001, deadline - time.monotonic()),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            return read_json(output / "result.json")
        except (subprocess.SubprocessError, OSError, ValueError) as error:
            failure = {"status": "failed", "error": str(error), "eligible": False}
            write_json(output / "failure.json", failure)
            return failure

    reference = attempt("reference", cpus[0])
    attempts = {"reference": reference}
    if reference["status"] == "passed":
        with ThreadPoolExecutor(max_workers=2) as pool:
            lead = pool.submit(attempt, "lead", cpus[0])
            fallback = pool.submit(attempt, "fallback", cpus[1])
            attempts.update(lead=lead.result(), fallback=fallback.result())
    elapsed = time.monotonic() - start
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_seconds = usage.ru_utime + usage.ru_stime
    eligible = sorted(
        (r["complete_modeled_cost"], -r["margins"]["minimum_margin_phase64"], name)
        for name, r in attempts.items()
        if r["eligible"]
    )
    within_budget = (
        len(attempts) <= budget["max_experiments"]
        and elapsed <= budget["max_wall_seconds"]
        and cpu_seconds <= budget["max_compute_seconds"]
    )
    winner = eligible[0][2] if within_budget and eligible else None
    decision = {
        "status": "go" if winner else "no_go",
        "winner": winner,
        "winner_sha256": attempts[winner]["sha256"] if winner else None,
        "registration_sha256": sha256(directory / "registration.json"),
        "wall_seconds": elapsed,
        "cpu_seconds": cpu_seconds,
        "within_budget": within_budget,
        "attempts": {
            name: {"status": r["status"], "eligible": r["eligible"]} for name, r in attempts.items()
        },
        "scope": "Bounded development evidence. Full verification and confirmation are separate.",
    }
    write_json(directory / "decision.json", decision)
    print(decision, flush=True)


def verify(directory: Path, role: str) -> None:
    protocol = registered(directory)
    decision = read_json(directory / "decision.json")
    require(decision["status"] == "go", "screen did not qualify")
    require(
        decision["registration_sha256"] == sha256(directory / "registration.json"), "registration changed"
    )
    path = directory / decision["winner"] / "invsqrt.kmb"
    digest = decision["winner_sha256"]
    require(sha256(path) == digest, "frozen KMB hash changed")
    if role == "confirmation":
        full = read_json(directory / "full" / "result.json")
        require(full["result"]["circuit_sha256"] == digest, "full verification hash differs")
        require(full["result"]["status"] == "PASS", "full verification did not pass")
    output = directory / role
    output.mkdir(exist_ok=False)
    km, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(protocol["n_p"])
    salt = secrets.token_hex(32)
    if role == "confirmation":
        require(salt != read_json(directory / "full" / "registration.json")["salt"], "salt was reused")
    registration = {
        "role": role,
        "salt": salt,
        "artifact_sha256": digest,
        "input_count": spec.max_x,
        "shots_per_input": spec.shots_per_x,
        "expected_shots": spec.num_shots,
        "distribution": "Official exhaustive inputs with separate pseudorandom measurement streams",
        "decision_sha256": sha256(directory / "decision.json"),
        "environment": capture(ROOT),
        "registered_unix": time.time(),
    }
    write_json(output / "registration.json", registration)
    start = time.monotonic()
    print(f"{role}: verifying {digest} across {spec.num_shots:,} trajectories", flush=True)
    try:
        result = official.verify(
            km.Circuit.from_file(str(path)), spec, salt=salt, max_workers=protocol["promotion"]["workers"]
        )
        require(
            result["status"] == "PASS"
            and result["verified_shots"] == spec.num_shots
            and result["circuit_sha256"] == digest
            and sha256(path) == digest
            and result["score"] < protocol["reference"]["score"],
            "verification failed coverage, identity or measured improvement",
        )
    except Exception as error:
        write_json(
            output / "failure.json", {"error": repr(error), "elapsed_seconds": time.monotonic() - start}
        )
        raise
    write_json(
        output / "result.json",
        {
            "result": result,
            "elapsed_seconds": time.monotonic() - start,
            "registration_sha256": sha256(output / "registration.json"),
        },
    )
    print(result, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("screen", "lane", "full", "confirmation"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("name", nargs="?", choices=("reference", "lead", "fallback"))
    parser.add_argument("cpu", nargs="?", type=int)
    args = parser.parse_args()
    directory = args.directory.resolve()
    require(directory.is_relative_to(ROOT / "runs"), "use a new output directory under runs/")
    if args.action == "screen":
        screen(directory)
    elif args.action == "lane":
        lane(directory, args.name, args.cpu)
    else:
        verify(directory, args.action)


if __name__ == "__main__":
    main()
