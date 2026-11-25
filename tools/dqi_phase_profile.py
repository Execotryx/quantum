"""Inspect extraction and converter boundaries in banked D4 or its ablation."""

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path

import numpy as np

from qcompile.dqi.decoder import _divide, _trim
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored.dqi_d4 import homogeneous_groups


def degree_profile(words: list[int], field: GF4096) -> dict:
    def sqrt(value: int) -> int:
        return field.exp[2048 * field.log[value] % field.order] if value else 0

    odd = [sqrt(word) for word in words[1::2]]
    even = [sqrt(word) for word in words[::2]]
    # The monic-root routine removes the leading even term before solving
    # the short chart. This is the same reduction used by the emitter.
    reduced = [term ^ field.mul(even[-1], coefficient) for term, coefficient in zip(even[:-1], odd, strict=True)]
    left, right = _trim([*odd, 1]), _trim(reduced)
    degrees = [len(left) - 1]
    while right != [0]:
        degrees.append(len(right) - 1)
        _, remainder = _divide(left, right, field)
        left, right = right, remainder
    gaps = [a - b for a, b in zip(degrees, degrees[1:])]
    return {"degrees": degrees, "drops": gaps, "largest_drop": max(gaps, default=None), "gcd_degree": degrees[-1]}


def load_decoder(source: Path, km):
    entry = source / "exp/r-main/stream/decode.py"
    spec = importlib.util.spec_from_file_location("diagnostic_decoder", entry)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load the D4 decoder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.modules["circ"] = km
    spec.loader.exec_module(module)
    return module


def build(source: Path, output: Path, km, expected_sha: str, groups: tuple[int, ...]):
    module = load_decoder(source, km)

    scope = module.decode.__globals__
    convert = scope["convert_safe"]
    synthesize = scope["synthesize"]
    boundaries = {}

    def observe(builder, a, b, *args, **kwargs):
        if "convert" not in boundaries:
            boundaries["convert"] = (builder.finish_circuit(), a, b)
        return convert(builder, a, b, *args, **kwargs)

    def observe_extraction(builder, words, pole):
        boundaries["extraction"] = (builder.finish_circuit(), tuple(tuple(word) for word in words), pole)
        return synthesize(builder, words, pole)

    scope["convert_safe"] = observe
    scope["synthesize"] = observe_extraction
    builder = km.CircuitBuilder()
    syndrome_wires = [builder.alloc_qubits(12) for _ in range(70)]
    mask_wires = [builder.alloc_bits(12) for _ in range(4095)]
    try:
        with homogeneous_groups(module, groups):
            module.decode(builder, syndrome_wires, mask_wires)
    finally:
        scope["convert_safe"] = convert
        scope["synthesize"] = synthesize
    # Reproduce the exact upstream metadata and ordering. No diagnostic
    # gates are inserted in either the original circuit or this rebuild.
    metadata = []
    for kind, label, count, first in (("q", "S", 70, 0), ("b", "E", 4095, 70)):
        for index in range(count):
            register = first + index
            metadata.append(f'REGISTER r{register} "{label}{index}"')
            metadata.extend(f"APPEND_TO_REGISTER {kind}{12 * index + bit} r{register}" for bit in range(12))
    rebuilt = km.Circuit("\n".join(metadata)) + builder.finish_circuit()
    path = output / "decoder.kmb"
    if path.exists():
        raise FileExistsError(path)
    try:
        rebuilt.to_file(str(path), format="kmb")
        digest = sha256(path)
    finally:
        if not groups:
            path.unlink(missing_ok=True)
    if (digest == expected_sha) != (not groups):
        raise ValueError("Diagnostic or ablation build has an unexpected identity")
    stats = rebuilt.operation_statistics()
    build_record = {"sha256": digest, "qubits": rebuilt.num_qubits, "static_toffoli_like": stats.num_toffoli_like}
    return boundaries, syndrome_wires, mask_wires, build_record


def profile(
    component: Path, backend: Path, replay: Path, bank_path: Path, output: Path, groups: tuple[int, ...] = (),
) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    bank = read_json(bank_path)
    registration = bank_path.with_name("salts.json")
    backend_pin = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    request = read_json(replay / "request.json")
    if sha256(component / "SOURCE.json") != bank["source_sha256"] or (
        request["circuit_sha256"] != bank["sha256"]
        or request["registration_sha256"] != sha256(registration)
        or bank["registration_sha256"] != sha256(registration)
        or read_json(registration)["backend_inventory_sha256"] != backend_pin
    ):
        raise ValueError("Profile inputs differ from the banked D4 identity")
    for record in read_json(component / "SOURCE.json")["files"]:
        if sha256(component / record["path"]) != record["sha256"]:
            raise ValueError(f"Vendored source hash mismatch: {record['path']}")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    if api.__file__ is None or sha256(Path(api.__file__)) != request["verifier_sha256"]:
        raise ValueError("DQI verifier differs from the original replay")
    km = importlib.import_module("kickmix")
    s = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(s.degree))
    batch_size = api.DEFAULT_BATCH_SIZE
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    boundaries, syndrome_wires, mask_wires, build_record = build(
        component / "src", output.parent, km, bank["sha256"], groups,
    )
    extraction, extracted, pole = boundaries["extraction"]
    prefix, a, b = boundaries["convert"]

    def native_array(words):
        return km.array([wire for word in words for wire in word])

    def read_words(sim, wires):
        bits = sim.read_across_shots(wires).T.reshape(batch_size, -1, 12)
        return (bits * (1 << np.arange(12))).sum(axis=2)

    field = GF4096()
    rows = []
    receipts = {}
    for draw in sorted(replay.glob("s*")):
        result_path = draw / "result.json"
        record = read_json(result_path)
        if (not record["matches_historical_result"]
                or record["historical_receipt_sha256"] != bank["draws"][f"{draw.name}.json"]):
            raise ValueError("Cannot profile a replay with different counts")
        receipts[draw.name] = {"result": sha256(result_path), "batches": record["failure_batches"]}
        for name, digest in record["failure_batches"].items():
            batch_file = draw / name
            if sha256(batch_file) != digest:
                raise ValueError(f"Captured batch changed: {batch_file}")
            batch = read_json(batch_file)
            rng = np.random.default_rng(batch["rng_seed"])
            syndromes, masks, phases = api.sample_shots(s, tables, rng, batch_size)
            def simulate(circuit):
                sim = km.Simulator(batch_size=batch_size, seed=batch["sim_seed"])
                sim.use_same_registers_as(circuit)
                sim.write_across_shots(native_array(syndrome_wires), api.to_bits(syndromes, s.degree))
                sim.write_across_shots(native_array(mask_wires), api.to_bits(masks, s.degree))
                sim.do(circuit)
                return sim

            sim = simulate(extraction)
            extracted_words = read_words(sim, native_array(extracted))
            trailing_poles = sim.read_across_shots(km.array([pole]))[0]
            sim = simulate(prefix)
            a_words, b_words = read_words(sim, native_array(a)), read_words(sim, native_array(b))
            for case in batch["shots"] + batch["controls"]:
                offset = case["index"] - batch["batch_start"]
                if (syndromes[offset].tolist(), masks[offset].tolist(), bool(phases[offset])) != (
                    case["syndrome"], case["mask"], case["expected_phase"]
                ):
                    raise ValueError("Official batch reconstruction disagrees with the captured shot")
                chart = b_words[offset].tolist()
                rows.append({
                    "draw": draw.name, "index": case["index"], "phase_error": case["phase_error"],
                    "value_error": case["value_error"], "convert_a": a_words[offset].tolist(), "convert_b": chart,
                    "extraction_words": extracted_words[offset].tolist(), "trailing_pole": bool(trailing_poles[offset]),
                    **degree_profile(chart, field),
                })
    write_json(output, {
        "circuit_sha256": build_record["sha256"], "banked_sha256": bank["sha256"],
        "build": build_record, "homogeneous_ablation": groups, "replay_request": sha256(replay / "request.json"),
        "source_sha256": bank["source_sha256"], "backend_sha256": sha256(backend),
        "backend_inventory_sha256": backend_pin, "batch_receipts": receipts,
        "extraction_operations": len(extraction), "prefix_operations": len(prefix), "profiles": rows,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", type=Path)
    parser.add_argument("backend", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("bank", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--homogeneous", type=int, nargs="+", default=[])
    args = parser.parse_args()
    profile(args.component, args.backend, args.replay, args.bank, args.output, tuple(args.homogeneous))


if __name__ == "__main__":
    main()
