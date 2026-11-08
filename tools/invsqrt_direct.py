"""Generate, screen and verify direct inverse-square-root phase circuits in pinned Linux."""

import argparse
import os
import secrets
import subprocess
import sys
import time
from functools import partial
from math import isclose
from pathlib import Path
from typing import Any

import numpy as np
from invsqrt_opportunity import ROOT, THREADS, backend, counts, phase, require

from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.experiments import record_lock, validate_budget
from qcompile.invsqrt.direct import DirectFormat, build_circuit, coefficient_table, phase64
from qcompile.invsqrt.direct_screen import beta_one_targets, complete_cost, scan_phase
from qcompile.invsqrt.minimax import coefficient_table as minimax_table
from qcompile.io import read_json, sha256, write_json
from qcompile.profiling import ResourceSampler, terminate_tree

CONFIG = ROOT / "configs/invsqrt-direct-v1.json"
CONFIG_V2 = ROOT / "configs/invsqrt-direct-v2.json"
CONFIG_V3 = ROOT / "configs/invsqrt-direct-v3.json"
N_P = 10
EXPECTED_SHOTS = 200_540_928
PINS = (
    CONFIG,
    Path(__file__).resolve(),
    Path(__file__).with_name("invsqrt_opportunity.py").resolve(),
    ROOT / "src/qcompile/invsqrt/direct.py",
    ROOT / "src/qcompile/invsqrt/direct_screen.py",
    ROOT / "contracts/contract.json",
    ROOT / "uv.lock",
    ROOT / "vendor/backend.json",
    ROOT / "docs/evidence/official-baseline-20261101.json",
    ROOT / "docs/evidence/invsqrt-chemistry-20261107/archive.json",
    ROOT / "docs/evidence/invsqrt-chemistry-20261107/combined-result.json",
)


def pins(version: int = 1) -> dict[str, str]:
    paths = PINS
    if version >= 2:
        paths += (
            CONFIG_V2,
            ROOT / "src/qcompile/invsqrt/minimax.py",
            ROOT / "docs/evidence/invsqrt-direct-20261107/combined/attempt.json",
            ROOT / "docs/evidence/invsqrt-direct-20261107/combined/coefficients.json",
            ROOT / "docs/evidence/invsqrt-direct-hybrid-20261107/certificate.json",
        )
    if version == 3:
        paths += (
            CONFIG_V3,
            ROOT / "src/qcompile/invsqrt/unlookup.py",
            ROOT / "docs/evidence/next-hybrid-20261108/invsqrt/minimax-quadratic.json",
            ROOT / "docs/evidence/next-hybrid-20261108/paired-archive/comparison.json",
        )
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}


def registered(directory: Path) -> dict:
    record = read_json(directory / "registration.json")
    require(pins(record.get("version", 1)) == record["inputs"], "registered inputs changed")
    revision = capture(ROOT)
    require(
        not revision["dirty"] and revision["source_revision"] == record["environment"]["source_revision"],
        "registered source must remain clean and unchanged",
    )
    return record["protocol"]


def emit(km: Any, circuit: Any, official: Any, path: Path) -> tuple[Any, str]:
    with path.open("xb") as stream:
        circuit.to_file(stream, format="kmb")
    circuit = km.Circuit.from_file(str(path))
    digest = sha256(path)
    require(official._circuit_sha256(circuit) == digest, "noncanonical KMB")
    return circuit, digest


def fixture_inputs(max_x: int, segment_bits: int, margins: dict, policy: dict) -> list[int]:
    points = {1, max_x, margins["worst_x"], margins["minimum_margin_x"]}
    rng = np.random.default_rng(policy["seed"])
    points.update(map(int, rng.integers(1, max_x + 1, size=policy["random_inputs"])))
    for exponent in range(N_P + 1):
        scale = 4**exponent
        segments = 1 << segment_bits
        for address in range(segments, 4 * segments + 1):
            edge = (scale * address + segments - 1) // segments
            points.update(x for x in (edge - 1, edge, edge + 1) if 1 <= x <= max_x)
    return sorted(points)


def native_smoke(km, official, circuit, spec, model, points, policy):
    batch = policy["batch"]
    xs = np.tile(np.asarray(points, dtype=np.int64), policy["repeat"])
    xs = np.pad(xs, (0, (-len(xs)) % batch), mode="edge")
    target, allowed = official.reference_values(spec, xs)
    independent = beta_one_targets(xs)
    require(
        np.array_equal(independent[0], target) and np.array_equal(independent[1], allowed),
        "independent phase targets differ",
    )
    expected = model(xs)
    io, scratch = official.validate_registers(circuit, spec)
    simulator = km.Simulator(batch_size=batch, seed=policy["seed"], counting_operations=True)
    for start in range(0, len(xs), batch):
        group = xs[start : start + batch]
        simulator.clear_for_shot()
        simulator.write_across_shots(io, official.to_bits(group.astype(np.uint64), spec.width))
        simulator.do(circuit)
        require(
            np.array_equal(official.from_bits(simulator.read_across_shots(io)), group),
            f"input restoration failed in batch {start}",
        )
        require(
            not len(scratch) or not simulator.read_across_shots(scratch).any(),
            f"scratch restoration failed in batch {start}",
        )
        for i, x in enumerate(group):
            observed = official.half_turns_to_units(simulator.read_shot_phase(i))
            require(observed == int(expected[start + i]), f"phase mismatch at x={x}, shot {start + i}")
    per_shot = counts(circuit.operation_statistics())
    executed = counts(simulator.operation_statistics())
    require(executed == tuple(n * len(xs) for n in per_shot), "executed counts differ from static counts")
    return {"fixture_inputs": len(points), "shots": len(xs), "executed_counts": executed, "counts": per_shot}


def direct_candidate(km, primitives, fmt_spec, *, liveness=None):
    settings = dict(fmt_spec)
    fit = settings.pop("fit", "taylor")
    fmt = DirectFormat(N_P, **{**settings, "fractional": tuple(settings["fractional"])})
    table = {"taylor": coefficient_table, "minimax": minimax_table}[fit](fmt)
    return build_circuit(km, primitives, fmt, table, liveness=liveness), partial(phase64, fmt, table), table


def lane(directory: Path, name: str) -> None:
    protocol = registered(directory)
    output = directory / name
    params = read_json(output / "parameters.json")
    km, primitives, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(N_P)
    control = protocol["controls"].get(name)
    liveness = {} if protocol.get("profile_liveness") else None
    if control and "widths" in control:
        prec = primitives.Precision(*control["widths"])
        model = partial(phase, primitives, prec, N_P)
        circuit = primitives.build_nr_circuit(N_P, prec=prec)
        segments = 2
    else:
        circuit, model, table = direct_candidate(km, primitives, params, liveness=liveness)
        write_json(output / "coefficients.json", table)
        segments = params["segment_bits"]
    circuit, digest = emit(km, circuit, official, output / "invsqrt.kmb")
    margins = scan_phase(model, spec.max_x, partial(official.reference_values, spec))
    points = fixture_inputs(spec.max_x, segments, margins, protocol["development"])
    native = native_smoke(km, official, circuit, spec, model, points, protocol["development"])
    score = None
    if margins["minimum_margin_phase64"] > 0:
        score = complete_cost(circuit.num_qubits, native["counts"], margins["minimum_margin_phase64"])
    if control:
        require(digest == control["sha256"], f"{name} KMB hash differs")
        require(
            score is not None and isclose(score["score"], control["cost"], rel_tol=1e-12),
            f"{name} score differs",
        )
        if "coefficients_sha256" in control:
            require(
                sha256(output / "coefficients.json") == control["coefficients_sha256"],
                f"{name} coefficient table differs",
            )
    write_json(
        output / "result.json",
        {
            "sha256": digest,
            "parameters": params,
            "margins": margins,
            "native": native,
            **({"allocated_qubits": liveness} if liveness is not None else {}),
            "cost": score,
            "phase_gate": margins["input_count"] == spec.max_x
            and not margins["nonpositive_margins"]
            and not margins["above_90_percent"],
            "coefficients_sha256": None if "widths" in (control or {}) else sha256(output / "coefficients.json"),
        },
    )


def run_job(argv: list[str], output: Path, timeout: float) -> int:
    env = {**os.environ, **dict.fromkeys(THREADS, "1")}
    with (output / "execution.log").open("xb") as log:
        with subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT) as worker:
            sampler = None
            try:
                sampler = ResourceSampler(worker.pid, output, interval=1)
                sampler.start()
                return worker.wait(timeout=timeout)
            finally:
                if worker.poll() is None:
                    terminate_tree(worker.pid)
                if sampler is not None:
                    sampler.stop()


def screen(directory: Path, version: int = 1) -> None:
    protocol = read_json(CONFIG)
    for config in (CONFIG_V2, CONFIG_V3)[: version - 1]:
        updates = read_json(config)
        protocol = {**protocol, **updates, "controls": {**protocol["controls"], **updates["controls"]}}
    validate_budget(protocol)
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    environment = capture(ROOT)
    require(not environment["dirty"], "screen requires clean committed source")
    memory = next(
        int(line.split()[1])
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    budget = protocol["budget"]
    require(memory >= budget["minimum_available_memory_kib"], "insufficient screening memory")
    directory.mkdir(parents=True, exist_ok=False)
    write_json(
        directory / "registration.json",
        {
            "protocol": protocol,
            "version": version,
            "inputs": pins(version),
            "contract_hash": contract.hash,
            "environment": environment,
            "registered_unix": time.time(),
            "available_memory_kib": memory,
            "screen_lanes": 1,
        },
    )
    started = time.monotonic()
    cpu_start = os.times()
    attempts: dict[str, dict] = {}

    def usage() -> tuple[float, float]:
        cpu = os.times()
        return (
            time.monotonic() - started,
            cpu.children_user + cpu.children_system - cpu_start.children_user - cpu_start.children_system,
        )

    def in_budget() -> bool:
        elapsed, cpu = usage()
        return (
            elapsed < budget["max_wall_seconds"]
            and cpu < budget["max_compute_seconds"]
            and len(attempts) <= budget["max_experiments"]
        )

    def attempt(name: str, params: dict) -> dict:
        out = directory / name
        out.mkdir()
        write_json(out / "parameters.json", params)
        print(f"Screening {name}", flush=True)
        if not in_budget() or len(attempts) >= budget["max_experiments"]:
            evidence = {"status": "skipped", "reason": "budget exhausted"}
        else:
            try:
                elapsed, cpu = usage()
                timeout = min(budget["max_wall_seconds"] - elapsed, budget["max_compute_seconds"] - cpu)
                rc = run_job([sys.executable, __file__, "lane", str(directory), name], out, timeout)
                require(rc == 0, f"worker exit {rc}; see execution.log")
                evidence = {"status": "completed", **read_json(out / "result.json")}
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                evidence = {"status": "failed", "reason": str(error)}
        write_json(out / "attempt.json", evidence)
        attempts[name] = evidence
        return evidence

    def passed(row: dict) -> bool:
        return row.get("status") == "completed" and row["phase_gate"] and row["cost"] is not None

    def ranking(name: str):
        row = attempts[name]
        return row["cost"]["score"], -row["margins"]["minimum_margin_phase64"], name

    controls_pass = all(
        attempt(name, control.get("parameters", {}))["status"] == "completed"
        for name, control in protocol["controls"].items()
    )
    if controls_pass:
        if version < 3:
            attempt("direct-control", protocol["direct_control"])
        for name, params in protocol["piecewise"].items():
            attempt(name, params)
        feasible = [n for n, row in attempts.items() if n not in protocol["controls"] and passed(row)]
        if feasible:
            parent = min(feasible, key=ranking)
            params = attempts[parent]["parameters"]
            if version == 1:
                fused = attempt("fused", {**params, "fused": True})
                reuse = attempt("reuse", {**params, "reuse_lookup": True})
                if all(passed(row) and row["cost"]["score"] < ranking(parent)[0] for row in (fused, reuse)):
                    attempt("combined", {**params, "fused": True, "reuse_lookup": True})
            elif version == 2:
                for name, changes in protocol["ablations"].items():
                    settings = {**params, **changes}
                    if settings != params:
                        attempt(name, settings)
            elif version == 3:
                comparison = protocol["comparison"]
                improved = {name for name in feasible if ranking(name)[0] < ranking(comparison)[0]}
                precision = improved.intersection(protocol["precision_lanes"])
                if precision and "phase-repair" in improved:
                    settings = {**attempts[min(precision, key=ranking)]["parameters"], "measurement_unlookup": True}
                    combined = attempt("precision-with-phase-repair", settings)
                    if passed(combined) and "binary-normalization" in improved:
                        attempt("combined-v3", {**settings, "binary_normalization": True})
    limit = protocol["controls"][protocol.get("comparison", "incumbent")]["cost"] * (1 - protocol["minimum_gain"])
    eligible = [
        n
        for n, row in attempts.items()
        if n not in protocol["controls"] and passed(row) and row["cost"]["score"] <= limit
    ]
    winner = min(eligible, key=ranking) if controls_pass and in_budget() and eligible else None
    elapsed, cpu = usage()
    write_json(
        directory / "decision.json",
        {
            "status": "go" if winner else "no_go",
            "winner": winner,
            "winner_sha256": attempts[winner]["sha256"] if winner else None,
            "limit": limit,
            "wall_seconds": elapsed,
            "cpu_seconds": cpu,
            "controls_pass": controls_pass,
            "in_budget": in_budget(),
            "registration_sha256": sha256(directory / "registration.json"),
            "attempts": {name: sha256(directory / name / "attempt.json") for name in attempts},
        },
    )


def verify_worker(directory: Path, role: str) -> None:
    protocol = registered(directory)
    output = directory / role
    record = read_json(output / "registration.json")
    path = directory / record["winner"] / "invsqrt.kmb"
    digest = sha256(path)
    require(digest == record["artifact_sha256"], "frozen circuit changed before verification")
    km, _, official = backend()
    spec = official.ProblemSpecInvSqrt.for_n_p(N_P)
    result = official.verify(
        km.Circuit.from_file(str(path)),
        spec,
        salt=record["salt"],
        max_workers=protocol["promotion"]["workers"],
    )
    write_json(output / "raw-verifier.json", result)
    require(
        result["status"] == "PASS"
        and result["verified_shots"] == EXPECTED_SHOTS
        and result["circuit_sha256"] == digest == sha256(path)
        and result["worst_error_over_tolerance"] <= 0.90
        and result["score"] <= record["cost_limit"],
        "verification failed coverage, identity or measured promotion gates",
    )
    write_json(
        output / "result.json",
        {
            "result": result,
            "registration_sha256": sha256(output / "registration.json"),
            "raw_sha256": sha256(output / "raw-verifier.json"),
        },
    )


def verify(directory: Path, role: str) -> None:
    protocol = registered(directory)
    decision = read_json(directory / "decision.json")
    winner = decision["winner"]
    require(decision["status"] == "go" and isinstance(winner, str), "screen did not qualify")
    require(
        decision["registration_sha256"] == sha256(directory / "registration.json"),
        "screen registration changed",
    )
    for name, expected in decision["attempts"].items():
        require(sha256(directory / name / "attempt.json") == expected, "screen evidence changed")
    digest = sha256(directory / winner / "invsqrt.kmb")
    require(digest == decision["winner_sha256"], "frozen winner changed")
    if role == "confirmation":
        full = read_json(directory / "full" / "result.json")
        require(
            full["result"]["circuit_sha256"] == digest
            and full["result"]["verified_shots"] == EXPECTED_SHOTS
            and full["registration_sha256"] == sha256(directory / "full" / "registration.json")
            and full["raw_sha256"] == sha256(directory / "full" / "raw-verifier.json"),
            "missing bound full pass",
        )
    else:
        km, primitives, official = backend()
        params = read_json(directory / winner / "attempt.json")["parameters"]
        circuit, _, _ = direct_candidate(km, primitives, params)
        require(official._circuit_sha256(circuit) == digest, "independent direct build differs")
    output = directory / role
    history = directory.parent / ".invsqrt-direct-history"
    history.mkdir(exist_ok=True)
    with record_lock(history):
        reservation = history / f"{digest}-{role}.json"
        require(not reservation.exists(), f"unchanged bytes already registered for {role}")
        output.mkdir(exist_ok=False)
        record = {
            "role": role,
            "winner": winner,
            "artifact_sha256": digest,
            "salt": secrets.token_hex(32),
            "expected_shots": EXPECTED_SHOTS,
            "cost_limit": decision["limit"],
            "decision_sha256": sha256(directory / "decision.json"),
            "registered_unix": time.time(),
        }
        write_json(reservation, record)
        write_json(output / "registration.json", record)
    rc = run_job(
        [sys.executable, __file__, "verify-worker", str(directory), role],
        output,
        protocol["promotion"]["timeout_seconds"],
    )
    require(rc == 0, f"{role} failed; inspect {output / 'execution.log'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("screen", "lane", "full", "confirmation", "verify-worker", "build")
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("name", nargs="?")
    parser.add_argument("--protocol", choices=(1, 2, 3), type=int, default=1)
    args = parser.parse_args()
    if args.action == "build":
        if args.name is None:
            parser.error("build needs a pinned JSON parameter file")
        km, primitives, official = backend()
        circuit, _, _ = direct_candidate(km, primitives, read_json(Path(args.name)))
        emit(km, circuit, official, args.directory / "invsqrt.kmb")
    elif args.action == "screen":
        screen(args.directory, args.protocol)
    elif args.action == "lane":
        lane(args.directory, args.name)
    elif args.action == "verify-worker":
        verify_worker(args.directory, args.name)
    else:
        verify(args.directory, args.action)


if __name__ == "__main__":
    main()
