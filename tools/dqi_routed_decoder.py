"""Emit a routed decoder only after the registered backend and depth gates."""

import argparse
import time
from pathlib import Path

from dqi_history_depth import CHUNKS, SHOTS, pins, read_chunk, runtime

from qcompile.dqi.routed_decoder import routed_decoder
from qcompile.io import read_json, sha256, write_json


def registered_depth(backend: Path, probe: Path, campaign: Path) -> tuple[int, dict]:
    registration_path = campaign / "registration.json"
    decision_path = campaign / "decision.json"
    registration, decision = read_json(registration_path), read_json(decision_path)
    depth = decision.get("depth")
    histogram = decision.get("histogram", [])
    chunks = decision.get("chunk_sha256", {})
    if (registration["pins"] != pins(backend, probe) or decision["registration_sha256"] != sha256(registration_path)
            or decision["status"] != "complete" or type(depth) is not int or depth not in (1, 2, 3)
            or registration["chunks"] != CHUNKS or registration["shots_per_chunk"] != SHOTS
            or len(chunks) != CHUNKS or len(histogram) != 71 or sum(histogram) != CHUNKS * SHOTS):
        raise ValueError("routed emission requires a complete registered history campaign")
    totals = [0] * 71
    for i in range(CHUNKS):
        path = campaign / f"chunk-{i:03}.json"
        if sha256(path) != chunks.get(path.name):
            raise ValueError("history chunk receipt changed")
        record = read_chunk(path, decision["registration_sha256"], i, registration["base_seed"] + i)
        degrees = record["max_degree_by_round"]
        if (record["status"] != "complete" or record["shots"] != SHOTS or sum(record["histogram"]) != SHOTS
                or len(degrees) != 70 or any(degree > min(r, 35) for r, degree in enumerate(degrees, 1))
                or record["max_active_shifted_degree"] > 35):
            raise ValueError("history chunk did not pass the registered sampling gates")
        totals = [a + b for a, b in zip(totals, record["histogram"], strict=True)]
    exceedances = [sum(totals[h + 1:]) for h in (1, 2, 3)]
    selected = next((h for h, count in enumerate(exceedances, 1) if count <= 10), 3)
    if totals != histogram or exceedances != decision["exceedances"] or selected != depth:
        raise ValueError("history decision does not follow the measured depth rule")
    return depth, {"depth_registration_sha256": sha256(registration_path),
                   "depth_decision_sha256": sha256(decision_path), **registration["pins"]}


def build(backend: Path, probe: Path, campaign: Path, output: Path, *, m: int, n: int) -> None:
    if not 2 <= n <= 70 or not n < m <= 4095:
        raise ValueError("require n in [2,70] and n < m <= 4095")
    depth, evidence = registered_depth(backend, probe, campaign)
    _, km, api, field = runtime(backend)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(n)]
    masks = [builder.create_classical_register(12, f"E{i}") for i in range(m)]
    routed_decoder(builder, field, syndromes, masks, depth=depth)
    circuit = builder.finish_circuit()
    spec = api.ProblemSpecDQI.benchmark_instance(m=m, n=n, degree=12)
    api.validate_registers(circuit, spec)
    artifact = output / "decoder.kmb"
    with artifact.open("xb") as stream:
        circuit.to_file(stream, format="kmb")
    write_json(output / "emission.json", {
        "m": m, "n": n, "history_depth": depth, "inputs": evidence, "kmb_sha256": sha256(artifact),
        "qubits": circuit.num_qubits, "bits": circuit.num_bits, "size_bytes": artifact.stat().st_size,
        "operations": dict(circuit.operation_statistics()), "wall_seconds": time.monotonic() - start,
        "scope": "routed decoder emission only",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("backend", "probe", "campaign", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--n", type=int, required=True)
    args = parser.parse_args()
    build(args.backend, args.probe, args.campaign, args.output, m=args.m, n=args.n)
