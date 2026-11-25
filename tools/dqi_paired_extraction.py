"""Exercise pole-aware external extraction and uncomputation on the frozen batches."""

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
from dqi_phase_profile import load_decoder

from qcompile.dqi.decoder import decode
from qcompile.dqi.double_node_pole import matches_dqi_rational
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend
from qcompile.vendored.dqi_d4 import (
    paired_external_extraction,
    paired_residue_scan,
    paired_tail,
    synthesize_linear_tail,
)


def probe(
    component: Path, backend: Path, captures: Path, profile: Path, output: Path,
    synthesis_width: int = 0, focused_scan: bool = False, regular_solver: bool = False,
) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    control = read_json(profile)
    if sha256(backend) != control["backend_sha256"] or sha256(component / "SOURCE.json") != control["source_sha256"]:
        raise ValueError("Extraction probe inputs differ from the native control")
    for record in read_json(component / "SOURCE.json")["files"]:
        if sha256(component / record["path"]) != record["sha256"]:
            raise ValueError(f"Vendored source hash mismatch: {record['path']}")
    if focused_scan and not synthesis_width:
        raise ValueError("The focused scan requires synthesized coefficient banks")
    inputs, positions = [], set()
    field = GF4096()
    for draw, receipt in control["batch_receipts"].items():
        for name, digest in receipt["batches"].items():
            path = captures / draw / name
            if sha256(path) != digest:
                raise ValueError("Frozen input batch changed")
            batch = read_json(path)
            inputs.append((draw, batch))
            if focused_scan:
                for case in batch["shots"] + batch["controls"]:
                    positions.update(decode(case["syndrome"], field))
    points = sorted(positions)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = importlib.import_module("dqi.verify_submission_dqi")
    km = importlib.import_module("kickmix")
    spec = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(spec.degree))
    batch_size = api.DEFAULT_BATCH_SIZE
    reference = load_decoder(component / "src", km).replay_erase.ref
    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    mask_registers = {point: builder.alloc_bits(12) for point in points}
    reference.linear_words(builder, words, reference.matrix)
    token = paired_external_extraction(builder, reference, words)
    chart_wires = [row[0] for row in token]
    denominator = paired_tail(builder, reference, words, chart_wires)
    forward = builder.finish_circuit()
    synthesized = banks = None
    if synthesis_width:
        tail = (words[-2], denominator, words[-1])
        banks = synthesize_linear_tail(
            builder, reference, words, tail, chart_wires, synthesis_width, regular_solver=regular_solver,
        )
        synthesized = builder.finish_circuit()
        if focused_scan:
            paired_residue_scan(builder, reference, banks, mask_registers, points)
        synthesize_linear_tail(
            builder, reference, words, tail, chart_wires, synthesis_width, reverse=True,
            banks=banks, regular_solver=regular_solver,
        )
    paired_tail(builder, reference, words, chart_wires, reverse=True, denominator=denominator)
    paired_external_extraction(builder, reference, words, reverse=True, token=token)
    reference.linear_words(builder, words, reference.matrix, True)
    closed = builder.finish_circuit()
    syndrome = km.array([wire for word in words for wire in word])
    charts = km.array(chart_wires)
    mask_wires = km.array([wire for point in points for wire in mask_registers[point]]) if focused_scan else None
    scratch = km.array([km.q(index) for index in range(len(syndrome), closed.num_qubits)])
    rows = []
    diagnostics = []
    for draw, batch in inputs:
        rng = np.random.default_rng(batch["rng_seed"])
        samples, masks, phases = api.sample_shots(spec, tables, rng, batch_size)
        initial = api.to_bits(samples, spec.degree)
        mask_bits = api.to_bits(masks[:, points], spec.degree) if focused_scan else None

        def simulate(circuit, scan=False):
            sim = km.Simulator(batch_size=batch_size, seed=batch["sim_seed"])
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(syndrome, initial)
            if scan:
                sim.write_across_shots(mask_wires, mask_bits)
            sim.do(circuit)
            return sim

        def read_words(sim, wires):
            bits = sim.read_across_shots(wires).T.reshape(batch_size, -1, 12)
            return bits @ (1 << np.arange(12))

        sim = simulate(forward)
        values = read_words(sim, syndrome)
        chart_values = sim.read_across_shots(charts).T
        denominator_values = sim.read_across_shots(km.array(denominator)).T @ (1 << np.arange(12))
        coefficients = []
        if synthesized is not None and banks is not None:
            sim = simulate(synthesized)
            coefficients = [read_words(sim, km.array([wire for word in bank for wire in word])) for bank in banks]
        sim = simulate(closed, focused_scan)
        actual_phase = sim.read_phase_flipped_across_shots()
        tested_offsets = []
        for case in batch["shots"] + batch["controls"]:
            offset = case["index"] - batch["batch_start"]
            if (samples[offset].tolist(), masks[offset].tolist(), bool(phases[offset])) != (
                case["syndrome"], case["mask"], case["expected_phase"],
            ):
                raise ValueError("Reconstructed original shot differs")
            tested_offsets.append(offset)
            row = {
                "draw": draw, "index": case["index"], "extraction_words": values[offset].tolist(),
                "local_zero_charts": chart_values[offset].tolist(),
                "tail_jet": [int(values[offset, -2]), int(denominator_values[offset]), int(values[offset, -1])],
            }
            if coefficients:
                numerator, denominator_words = (bank[offset].tolist() for bank in coefficients)
                row["synthesized_banks"] = [numerator, denominator_words]
                row["matches_original_moments"] = matches_dqi_rational(
                    numerator, denominator_words, case["syndrome"], reference.P, field,
                )
            if focused_scan:
                row["observed_phase"] = bool(actual_phase[offset])
                row["expected_phase"] = bool(phases[offset])
            rows.append(row)
        phase_errors = actual_phase[tested_offsets] != phases[tested_offsets] if focused_scan else actual_phase
        diagnostics.append({
            "draw": draw, "batch_start": batch["batch_start"],
            "syndrome_errors": int((sim.read_across_shots(syndrome) != initial).any(axis=0).sum()),
            "mask_errors": int((sim.read_across_shots(mask_wires) != mask_bits).any(axis=0).sum()) if focused_scan else 0,
            "scratch_errors": int(sim.read_across_shots(scratch).any(axis=0).sum()),
            "phase_errors": int(phase_errors.sum()),
            "phase_checks": len(tested_offsets) if focused_scan else batch_size,
        })
    write_json(output, {
        "control_sha256": sha256(profile), "source_sha256": control["source_sha256"],
        "forward_qubits": forward.num_qubits, "closed_qubits": closed.num_qubits,
        "synthesis_width": synthesis_width, "scan_points": points, "regular_solver": regular_solver,
        "closed_static_toffoli_like": closed.operation_statistics().num_toffoli_like,
        "shots": len(diagnostics) * batch_size, "diagnostics": diagnostics, "profiles": rows,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("component", "backend", "captures", "profile", "output"):
        parser.add_argument(arg, type=Path)
    parser.add_argument("--synthesis-width", type=int, choices=range(2, 72))
    parser.add_argument("--focused-scan", action="store_true")
    parser.add_argument("--regular-solver", action="store_true")
    args = parser.parse_args()
    probe(
        args.component, args.backend, args.captures, args.profile, args.output,
        args.synthesis_width or 0, args.focused_scan, args.regular_solver,
    )


if __name__ == "__main__":
    main()
