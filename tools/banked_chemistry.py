"""Screen a banked ANGLE lookup and test the combined optimization archive."""

import argparse
import math
import resource
import secrets
import shutil
import sys
import time
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.artifacts import deterministic_zip, extract_archive, hashes, manifest
from qcompile.contract import load_contract
from qcompile.environment import capture
from qcompile.experiments import validate_budget
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend, verify_candidate
from qcompile.reference.scoring import aggregate

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/banked-chemistry-v1.json"
REFERENCE = ROOT / "vendor/official/sample_submission"
EVIDENCE = ROOT / "docs/evidence"
LOW_BITS = 7


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def backend():
    settings = read_json(ROOT / "vendor/backend.json")
    validate_backend(settings)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    return (
        settings,
        import_module("kickmix"),
        import_module("dfthcsos.scoreinfra.circuits"),
        import_module("dfthcsos.example_submission.angle_k_reference_circuit"),
        import_module("dfthcsos.verify"),
    )


def banked_circuit(km, api, delta, brot: int):
    rows, width = delta.shape
    address_bits = (rows - 1).bit_length()
    require(address_bits == 12 and width == 9 and brot == 12, "unexpected pinned lookup shape")
    require(bool(np.all((0 <= delta) & (delta < 2**brot))), "invalid delta word")
    builder = km.CircuitBuilder()
    selection = builder.create_quantum_register(address_bits, api.SELECTION_REGISTER)
    words = [builder.create_quantum_register(brot, api.word_register(j)) for j in range(width)]
    scratch = list(builder.alloc_qubits(LOW_BITS + 1))
    flag, helpers = scratch[0], scratch[1:4]
    bits = list(reversed(list(selection)))
    high, low = bits[:-LOW_BITS], bits[-LOW_BITS:]

    def tree(control, level: int, start: int, end: int) -> None:
        if end - start == 1:
            for register, word in zip(words, delta[start], strict=True):
                value = int(word)
                while value:
                    bit = value & -value
                    builder.cx(control, register[bit.bit_length() - 1])
                    value ^= bit
            return
        middle = (start + end) // 2
        if middle >= rows:
            tree(control, level + 1, start, middle)
            return
        address, child = low[level], scratch[level + 1]
        builder.x(address)
        builder.init_and(control, address, child)
        builder.x(address)
        tree(child, level + 1, start, middle)
        builder.cx(control, child)
        tree(child, level + 1, middle, end)
        builder.del_and(control, address, child)

    chain = list(zip([high[0], *helpers], high[1:], [*helpers, flag], strict=True))
    size = 1 << LOW_BITS
    for bank, start in enumerate(range(0, rows, size)):
        negated = [bit for k, bit in enumerate(reversed(high)) if not bank & (1 << k)]
        for bit in negated:
            builder.x(bit)
        for pair in chain:
            builder.init_and(*pair)
        for pair in reversed(chain[:-1]):
            builder.del_and(*pair)
        tree(flag, 0, start, start + size)
        for pair in chain[:-1]:
            builder.init_and(*pair)
        for pair in reversed(chain):
            builder.del_and(*pair)
        for bit in negated:
            builder.x(bit)
    return builder.finish_circuit()


def xor_fixtures(km, api, circuits, deltas, seed: int):
    """Exercise nonzero XOR targets and composition on boundary addresses."""
    boundary = np.array([0, 7, 8, 127, 128, 3967, 3968, 3975], dtype=np.int64)
    addresses = np.repeat(boundary, 32)
    layout = api.register_layout(circuits)
    bits = np.arange(layout.brot, dtype=np.int64)
    selection = ((addresses[None, :] >> bits[:, None]) & 1).astype(bool)
    rng = np.random.default_rng(seed)
    target = rng.integers(0, 2**layout.brot, size=(len(addresses), layout.batch_size))
    sim = km.Simulator(batch_size=len(addresses), seed=seed)
    sim.use_same_registers_as(circuits[0])
    sim.write_across_shots(layout.selection, selection)
    for j, word in enumerate(layout.words):
        sim.write_across_shots(word, ((target[:, j][None, :] >> bits[:, None]) & 1).astype(bool))
    expected = target.copy()
    for k in [*range(len(circuits)), *reversed(range(len(circuits)))]:
        circuit = circuits[k]
        sim.do(circuit)
        api._check_state(sim, circuit, layout, selection, f"nonzero XOR fixture ANGLE_{k}")
        expected ^= deltas[k, addresses]
        actual = np.stack([(1 << bits) @ sim.read_across_shots(word) for word in layout.words], axis=1)
        require(np.array_equal(actual, expected), f"XOR fixture mismatch at ANGLE_{k}")
    require(np.array_equal(expected, target), "fixture did not restore arbitrary target")
    return {"addresses": boundary.tolist(), "shots": len(addresses), "applications": 2 * len(circuits)}


def screen(out: Path, words_path: Path, invsqrt_path: Path) -> None:
    protocol = read_json(CONFIG)
    validate_budget(protocol)
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    settings, km, api, builder, official = backend()
    pinned = read_json(EVIDENCE / "step3-chemistry-words.json")
    original = REFERENCE / "dfthcsos/submission.npz"
    baseline = read_json(EVIDENCE / "step3-chemistry-costs.json")
    require(sha256(words_path) == pinned["words_sha256"], "reference words hash differs")
    require(sha256(original) == pinned["factorization_sha256"], "factorization hash differs")
    require(sha256(invsqrt_path) == protocol["invsqrt_sha256"], "inverse-square-root hash differs")
    out.mkdir(parents=True, exist_ok=False)
    inputs = {
        str(path): sha256(path)
        for path in (
            CONFIG,
            Path(__file__).resolve(),
            ROOT / "uv.lock",
            ROOT / "vendor/backend.json",
            EVIDENCE / "step3-chemistry-costs.json",
            EVIDENCE / "step3-chemistry-words.json",
            EVIDENCE / "step3-chemistry-metrics.json",
            words_path,
            invsqrt_path,
            original,
        )
    }
    write_json(
        out / "registration.json",
        {
            "protocol": protocol,
            "inputs": inputs,
            "environment": capture(ROOT),
            "contract_hash": contract.hash,
            "registered_unix": time.time(),
        },
    )
    start = time.monotonic()
    cpu_start = time.process_time()
    with np.load(words_path, allow_pickle=False) as recovered:
        words, edges = recovered["words"], recovered["edges"]
    brot = pinned["brot"]
    params = official.load_inputs(original)

    def measure(directory: Path):
        started = time.monotonic()
        result = official.evaluate_circuits(
            params,
            directory,
            edges,
            shots_per_address=protocol["development_shots_per_address"],
            seed=protocol["development_seed"],
        )
        exact = np.array_equal(words, result.pop("angle_words"))
        require(exact, "serialized family returned different angle words")
        reason = official.rejection_reason(result["metrics"], result["resources"])
        require(reason is None, str(reason))
        require(
            result["verified_shots"] == len(words) * protocol["development_shots_per_address"],
            "incomplete development coverage",
        )
        return {**result, "words_exact": bool(exact), "evaluation_seconds": time.monotonic() - started}

    control = out / "reference-j8"
    control.mkdir()
    builder.write_kmx_family(builder.build_angle_k_family(words, brot, 8), control, format="kmb")
    reference_result = measure(control)
    write_json(out / "reference-j8.json", reference_result)
    require(
        math.isclose(reference_result["score"], baseline["score"], rel_tol=1e-12),
        "J8 rebuild cost differs from baseline",
    )
    print("J8 control passed", flush=True)

    deltas = builder.batch_deltas(words, 9)
    naive = builder.build_angle_k_circuit(deltas[0], brot)
    require(naive.num_qubits == 131, "unexpected naive J9 width control")
    write_json(
        out / "naive-j9.json", {"width": naive.num_qubits, "expected": "above 128", "status": "rejected"}
    )
    del naive
    submission = out / "submission"
    chemistry = submission / "dfthcsos"
    chemistry.mkdir(parents=True)
    build_start = time.monotonic()
    family = [banked_circuit(km, api, delta, brot) for delta in deltas]
    require(len(family) == 9 and all(c.num_qubits <= 128 for c in family), "family exceeds the width cap")
    files = builder.write_kmx_family(family, chemistry, format="kmb")
    build_seconds = time.monotonic() - build_start
    del family
    rebuilt = out / "banked-rebuild"
    rebuilt.mkdir()
    repeated = builder.write_kmx_family(
        [banked_circuit(km, api, delta, brot) for delta in deltas], rebuilt, format="kmb"
    )
    require(
        [sha256(path) for path in files] == [sha256(path) for path in repeated],
        "independent synthesis changed circuit bytes",
    )
    fixture = xor_fixtures(km, api, api.load_circuits(chemistry), deltas, protocol["development_seed"])
    measured = measure(chemistry)
    gain = 1 - measured["score"] / baseline["score"]
    elapsed = time.monotonic() - start
    cpu = time.process_time() - cpu_start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    budget = protocol["budget"]
    passed = (
        gain >= protocol["minimum_gain"]
        and 3 <= budget["max_experiments"]
        and elapsed <= budget["max_wall_seconds"]
        and cpu <= budget["max_compute_seconds"]
        and rss <= budget["max_rss_kib"]
    )
    write_json(
        out / "screen.json",
        {
            "status": "go" if passed else "no_go",
            "chemistry": measured,
            "gain": gain,
            "build_seconds": build_seconds,
            "wall_seconds": elapsed,
            "cpu_seconds": cpu,
            "peak_rss_kib": rss,
            "xor_fixtures": fixture,
            "rebuild_identical": True,
            "registration_sha256": sha256(out / "registration.json"),
            "chemistry_hashes": {path.name: sha256(path) for path in files},
        },
    )
    require(passed, "banked J9 did not meet the registered gain or budget")
    print(f"Banked J9 qualified with measured complete cost {measured['score']:.6f}", flush=True)

    acquisition = read_json(ROOT / "vendor/acquisition-checks.json")
    dqi = REFERENCE / "dqi.kmb"
    require(sha256(dqi) == acquisition["files"]["sample_submission/dqi.kmb"]["sha256"], "DQI hash differs")
    shutil.copyfile(original, chemistry / "submission.npz")
    shutil.copyfile(dqi, submission / "dqi.kmb")
    shutil.copyfile(invsqrt_path, submission / "invsqrt.kmb")
    items = manifest(submission, origin="generated", provenance="screened banked chemistry and frozen lead")
    for name in ("dqi.kmb", "dfthcsos/submission.npz"):
        items[name].update(origin="retained_reference", provenance="unchanged pinned reference bytes")
    archive = out / "invsqrt-chemistry.zip"
    deterministic_zip(archive, {name: item["path"] for name, item in items.items()})
    write_json(out / "archive.json", {"sha256": sha256(archive), "hashes": hashes(items), "artifacts": items})


def verify(out: Path) -> None:
    registration = read_json(out / "registration.json")
    protocol = registration["protocol"]
    for path, expected in registration["inputs"].items():
        require(sha256(Path(path)) == expected, f"registered input changed: {path}")
    contract = load_contract(ROOT / "contracts/contract.json")
    contract.require_ready(ROOT)
    require(contract.hash == registration["contract_hash"], "contract changed")
    screen_record = read_json(out / "screen.json")
    require(screen_record["status"] == "go", "chemistry screen did not pass")
    require(screen_record["registration_sha256"] == sha256(out / "registration.json"), "registration changed")
    archive = out / "invsqrt-chemistry.zip"
    frozen = read_json(out / "archive.json")
    require(sha256(archive) == frozen["sha256"], "frozen archive changed")
    require(frozen["hashes"]["invsqrt.kmb"] == protocol["invsqrt_sha256"], "invsqrt bytes changed")
    for name, expected in screen_record["chemistry_hashes"].items():
        require(frozen["hashes"][f"dfthcsos/{name}"] == expected, f"screened bytes changed: {name}")
    extracted = out / "extracted"
    extract_archive(archive, extracted, expected=frozen["hashes"])
    artifacts = {name: {**item, "path": str(extracted / name)} for name, item in frozen["artifacts"].items()}
    print("Running the pinned full metric on the extracted combined archive", flush=True)
    settings = read_json(ROOT / "vendor/backend.json")
    policy = read_json(ROOT / "configs/local-seed.json")
    report = verify_candidate(
        artifacts,
        contract,
        "full",
        policy,
        settings,
        out / "combined-verification",
        timeout=protocol["full_timeout_seconds"],
    )
    require(report["complete"] and report["status"] == "passed", "combined full metric failed")
    costs = report["official_results"]["costs"]
    reference = {
        "invsqrt": 2076774.233715282,
        "dqi": 24439461432712.35,
        "dfthcsos": 3355599588.3155375,
    }
    require(
        costs["invsqrt"] < reference["invsqrt"] and costs["dqi"] == reference["dqi"],
        "unexpected invsqrt or retained DQI result",
    )
    require(
        1 - costs["dfthcsos"] / reference["dfthcsos"] >= protocol["minimum_gain"],
        "full chemistry result did not improve enough",
    )
    require(
        math.isclose(costs["dfthcsos"], screen_record["chemistry"]["score"], rel_tol=1e-12),
        "full chemistry cost differs from the screen",
    )
    write_json(
        out / "combined-result.json",
        {
            "status": "passed",
            "costs": costs,
            "reference": reference,
            "relative_aggregate_score": aggregate(reference, costs),
            "archive_sha256": frozen["sha256"],
            "metric_receipt_sha256": sha256(out / "combined-verification/verification.json"),
        },
    )
    _, _, _, _, official = backend()
    confirm = out / "chemistry-confirmation"
    confirm.mkdir(exist_ok=False)
    salt = secrets.token_hex(32)
    write_json(
        confirm / "registration.json",
        {
            "salt": salt,
            "expected_shots": 3976 * 64,
            "registered_unix": time.time(),
            "archive_sha256": frozen["sha256"],
            "chemistry_hashes": screen_record["chemistry_hashes"],
            "factorization_sha256": frozen["hashes"]["dfthcsos/submission.npz"],
        },
    )
    print("Running fresh chemistry confirmation on the same extracted bytes", flush=True)
    result = official.verify(extracted / "dfthcsos", salt=salt)
    require(
        result["status"] == "PASS" and result["verified_shots"] == 3976 * 64,
        "chemistry confirmation did not complete",
    )
    require(math.isclose(result["score"], costs["dfthcsos"], rel_tol=1e-12), "confirmation cost differs")
    for name, expected in frozen["hashes"].items():
        require(sha256(extracted / name) == expected, f"artifact changed: {name}")
    require(sha256(archive) == frozen["sha256"], "archive changed during verification")
    write_json(confirm / "result.json", result)
    print("Combined full metric and chemistry confirmation passed", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("screen", "verify"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--words", type=Path, default=ROOT / "runs/step3-chemistry/recovered-words.npz")
    parser.add_argument(
        "--invsqrt", type=Path, default=ROOT / "runs/invsqrt-opportunity-20261107/lead/invsqrt.kmb"
    )
    args = parser.parse_args()
    out = args.output.resolve()
    require(out.is_relative_to(ROOT / "runs"), "output must be under runs/")
    if args.action == "screen":
        screen(out, args.words.resolve(), args.invsqrt.resolve())
    else:
        verify(out)


if __name__ == "__main__":
    main()
