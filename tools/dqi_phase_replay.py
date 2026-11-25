"""Replay sealed D4 verifier draws and retain disagreements and nearby controls."""

import argparse
import importlib
import inspect
import sys
from pathlib import Path

import numpy as np

from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend

INDICES = (2, 6, 7)
ANCHOR = "        stats = sim.operation_statistics()"


def capture_for(output: Path, scratch_indices: list[int] | None = None):
    def capture(start, syndromes, masks, expected, observed, value_errors, phase_errors,
                rng_seed, sim_seed, syndrome_diff, dirty):
        offsets = np.flatnonzero(value_errors | phase_errors)
        if not offsets.size:
            return
        passing = np.flatnonzero(~(value_errors | phase_errors))
        controls = {int(passing[np.argmin(np.abs(passing - offset))]) for offset in offsets} if passing.size else set()

        def row(offset: int) -> dict:
            case = {
                "index": start + int(offset),
                "syndrome": syndromes[offset].tolist(),
                "mask": masks[offset].tolist(),
                "expected_phase": bool(expected[offset]),
                "observed_phase": bool(observed[offset]),
                "value_error": bool(value_errors[offset]),
                "phase_error": bool(phase_errors[offset]),
            }
            if scratch_indices is not None:
                case["changed_syndrome_bits"] = np.flatnonzero(syndrome_diff[:, offset]).tolist()
                case["dirty_qubits"] = [scratch_indices[int(i)] for i in np.flatnonzero(dirty[:, offset])]
            return case

        write_json(output / f"batch-{start:06}.json", {
            "batch_start": start, "rng_seed": rng_seed, "sim_seed": sim_seed,
            "shots": [row(int(offset)) for offset in offsets], "controls": [row(offset) for offset in sorted(controls)],
        })

    return capture


def instrument(api) -> dict:
    source = inspect.getsource(api.verify)
    if source.count(ANCHOR) != 1:
        raise ValueError("Unexpected verifier capture point")
    capture = (
        "        capture(start, syndromes, mbuc, phases, phase_flipped, val_err, phase_err,\n"
        "                rng_seed, sim_seed, reg_diff, junk)\n"
    )
    scope = dict(vars(api))
    exec(compile(source.replace(ANCHOR, capture + ANCHOR), "<DQI verifier with capture>", "exec"), scope)
    return scope


def replay(artifact: Path, backend: Path, evidence: Path, output: Path, workers: int) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    registration_path = evidence / "salts.json"
    registration = read_json(registration_path)
    registration_sha = sha256(registration_path)
    bank = read_json(evidence / "dqi-v8.json")
    digest = sha256(artifact)
    backend_pin = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if (bank["candidate"], bank["status"], bank["registration_sha256"], bank["sha256"]) != (
        "d4", "go", registration_sha, digest
    ) or registration["candidates"]["d4"]["sha256"] != digest or (
        backend_pin != registration["backend_inventory_sha256"]
    ):
        raise ValueError("Replay requires the exact banked D4 bytes and original verifier inventory")

    draws = {}
    for index in INDICES:
        name = f"s{index}.json"
        previous = evidence / "pricing" / "d4" / name
        draws[index] = previous, bank["draws"][name]
    replay_draws(artifact, backend, settings, registration, registration_sha, digest, draws, output, workers)


def replay_campaign(
    artifact: Path, backend: Path, registration_path: Path, summary_path: Path,
    summary_sha256: str, role: str, indices: tuple[int, ...], output: Path, workers: int,
) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    if sha256(summary_path) != summary_sha256:
        raise ValueError("Campaign summary does not match its trusted hash")
    registration = read_json(registration_path)
    registration_sha = sha256(registration_path)
    summary = read_json(summary_path)
    digest = sha256(artifact)
    backend_pin = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if (
        summary["role"] != role or summary["registration_sha256"] != registration_sha
        or registration["pins"]["backend"] != backend_pin or registration["pins"][role] != digest
        or not indices or len(set(indices)) != len(indices)
        or any(not 1 <= index <= len(registration["salts"]) for index in indices)
    ):
        raise ValueError("Campaign replay identities or draw indices differ")
    draws = {
        index: (summary_path.with_name(f"s{index}.json"), summary["result_sha256"][f"s{index}.json"])
        for index in indices
    }
    replay_draws(
        artifact, backend, settings, registration, registration_sha, digest, draws, output, workers,
        role=role, summary_sha256=summary_sha256,
    )


def replay_draws(
    artifact: Path, backend: Path, settings: dict, registration: dict,
    registration_sha: str, digest: str, draws: dict[int, tuple[Path, str]], output: Path, workers: int,
    *, role: str | None = None, summary_sha256: str | None = None,
) -> None:
    previous_results = {}
    for index, (previous, receipt_hash) in draws.items():
        if sha256(previous) != receipt_hash:
            raise ValueError(f"Historical draw no longer matches its sealed receipt: {previous.name}")
        expected = read_json(previous)
        if (
            (expected["registration_sha256"], expected["salt"]) != (registration_sha, registration["salts"][index - 1])
            or expected["result"]["circuit_sha256"] != digest
            or expected["result"]["verified_shots"] != registration["shots"]
            or (role is not None and expected["role"] != role)
        ):
            raise ValueError(f"Historical draw identity changed: {previous.name}")
        previous_results[index] = expected

    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    spec = api.ProblemSpecDQI.benchmark_instance(num_shots=registration["shots"])
    circuit = km.Circuit.from_file(str(artifact))
    if api.__file__ is None:
        raise ValueError("Expected a pinned verifier source file")
    verifier_path = Path(api.__file__)
    scope = instrument(api)
    scratch_indices = None
    if role is not None:
        _, _, scratch = api.validate_registers(circuit, spec)
        scratch_set = set(scratch)
        scratch_indices = [index for index in range(circuit.num_qubits) if km.q(index) in scratch_set]
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "request.json", {
        "circuit_sha256": digest, "registration_sha256": registration_sha,
        "verifier_sha256": sha256(verifier_path), "backend_sha256": sha256(backend),
        "driver_sha256": sha256(Path(__file__)), "draw_indices": list(draws), "workers": workers,
        **({"role": role, "summary_sha256": summary_sha256} if role is not None else {}),
    })
    for index, expected in previous_results.items():
        salt = expected["salt"]
        draw = output / f"s{index}"
        draw.mkdir()
        scope["capture"] = capture_for(draw, scratch_indices)
        print(f"s{index} started", flush=True)
        result = scope["verify"](circuit, spec, salt=salt, max_workers=workers)
        batches = sorted(draw.glob("batch-*.json"))
        failures = [shot for batch in batches for shot in read_json(batch)["shots"]]
        recorded = (sum(shot["value_error"] for shot in failures), sum(shot["phase_error"] for shot in failures))
        matched = result == expected["result"]
        write_json(draw / "result.json", {
            "salt": salt, "result": result, "historical_receipt_sha256": draws[index][1],
            "matches_historical_result": matched,
            "failure_batches": {batch.name: sha256(batch) for batch in batches},
        })
        if not matched or recorded != (result["value_errors"], result["phase_errors"]):
            raise ValueError(f"D4 replay failed to reproduce the original receipt or capture counts: s{index}")
        print(f"s{index} matched; value errors={recorded[0]}, phase errors={recorded[1]}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("backend", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--summary-sha256")
    parser.add_argument("--role", choices=("banked", "candidate"))
    parser.add_argument("--draws", type=int, nargs="+")
    args = parser.parse_args()
    if args.registration is not None:
        if args.summary_sha256 is None or args.role is None or args.draws is None:
            parser.error("Campaign replay requires --summary-sha256, --role and --draws")
        replay_campaign(
            args.artifact, args.backend, args.registration, args.evidence, args.summary_sha256,
            args.role, tuple(args.draws), args.output, args.workers,
        )
    else:
        if args.summary_sha256 is not None or args.role is not None or args.draws is not None:
            parser.error("Campaign options require --registration")
        replay(args.artifact, args.backend, args.evidence, args.output, args.workers)


if __name__ == "__main__":
    main()
