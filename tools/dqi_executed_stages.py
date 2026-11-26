"""Attribute executed gates to the audited Tony Li DQI source stages."""

import argparse
import hashlib
import importlib
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

RELEASE = "4b5721411adc239f61fc11c773a2358b75dfe7cb15586efae4f0459c77d77e52"
ASSEMBLY = "1d5e4bfbedd0f33859331765b1cb293ef374da206184e4d2c4cc6d7fc8e3da8e"
SEEDS = (36071, 36073)


def stages(source: Path, scratch: Path):
    sys.path.insert(0, str(source))
    build = importlib.import_module("build")
    if build.__file__ is None or Path(build.__file__).resolve() != source / "build.py":
        raise ValueError("Unexpected publisher build module")
    indexed = read_json(source / "stages.json")
    digest = hashlib.sha256()
    result = []
    for index, stage in enumerate(indexed):
        path = scratch / f"stage-{index:02}.kmx"
        with path.open("wb") as stream:
            if "field" in stage:
                name = f"d16_field_{stage['field']}"
                for part in stage["d16"]:
                    if "product" in part:
                        build.emit_product(stream, source / part["product"])
                    else:
                        build.append_native(stream, part["kmx"])
            elif "kmx" in stage:
                name = Path(stage["kmx"]).name.removesuffix(".kmx.xz")
                build.append_native(stream, stage["kmx"])
            else:
                name = stage["generate"]
                if name == "lambda_selector":
                    build.emit_selector(stream)
                elif name == "lambda_phase":
                    build.emit_lambda_phase(stream)
                elif name == "restore_gauges":
                    build.gauges(build.Classical(stream), restore=True)
                else:
                    raise ValueError(f"Unexpected source stage {name}")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        result.append((name, path))
    if digest.hexdigest() != ASSEMBLY:
        raise ValueError("Stage concatenation differs from the previously rebuilt complete assembly")
    return result


def profile(source: Path, circuit: Path, backend: Path, output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    if sha256(circuit) != RELEASE:
        raise ValueError("Wrong complete circuit")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    api = importlib.import_module("dqi.verify_submission_dqi")
    full = km.Circuit.from_file(circuit, format="kmb")
    batch_size = api.DEFAULT_BATCH_SIZE
    spec = api.ProblemSpecDQI.benchmark_instance()
    syndrome, masks, ancilla = api.validate_registers(full, spec)
    syndrome, masks = km.array(syndrome), km.array(masks)
    tables = api.FieldTables(km.GF2Field(spec.degree))
    weights = api.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    with tempfile.TemporaryDirectory(prefix="qcompile-dqi-stages-") as work:
        segments = stages(source.resolve(), Path(work))
        lane = []
        for seed in SEEDS:
            sampled, mbuc, expected_phase = api.sample_shots(
                spec, tables, np.random.default_rng(seed), batch_size, weights,
            )
            inputs = api.to_bits(sampled, spec.degree)
            mask_bits = api.to_bits(mbuc, spec.degree)

            def simulator():
                sim = km.Simulator(batch_size=batch_size, counting_operations=True, seed=seed)
                sim.use_same_registers_as(full)
                sim.write_across_shots(syndrome, inputs)
                sim.write_across_shots(masks, mask_bits)
                return sim

            control = simulator()
            control.do(full)
            split = simulator()
            rows = []
            operation_counts: Counter[str] = Counter()
            for name, path in segments:
                part = km.Circuit.from_file(path, format="kmx")
                split.clear_operation_statistics()
                split.do(part)
                stats = split.operation_statistics()
                operation_counts.update(dict(stats))
                occupied = split.read_across_shots(ancilla)
                rows.append({"stage": name, "instructions": len(part),
                             "static_toffolis": int(part.operation_statistics().num_toffoli_like),
                             "executed_toffolis": int(stats.num_toffoli_like),
                             "sampled_nonzero_ancilla_ordinals": np.flatnonzero(occupied.any(axis=1)).tolist(),
                             "sampled_peak_nonzero_ancillas": int(occupied.sum(axis=0).max())})
            phase = split.read_phase_flipped_across_shots()
            final_syndrome = split.read_across_shots(syndrome)
            scratch = split.read_across_shots(ancilla)
            total = int(control.operation_statistics().num_toffoli_like)
            if (sum(row["executed_toffolis"] for row in rows) != total
                    or operation_counts != Counter(dict(control.operation_statistics()))
                    or sum(row["static_toffolis"] for row in rows) != full.operation_statistics().num_toffoli_like
                    or not np.array_equal(phase, control.read_phase_flipped_across_shots())
                    or not np.array_equal(final_syndrome, control.read_across_shots(syndrome))
                    or not np.array_equal(scratch, control.read_across_shots(ancilla))
                    or not np.array_equal(split.read_across_shots(masks), control.read_across_shots(masks))):
                raise ValueError("Stage execution does not reconcile with the complete circuit")
            value_errors = (final_syndrome ^ inputs).any(axis=0) | scratch.any(axis=0)
            lane.append({"seed": seed, "stages": rows, "full_executed_toffolis": total,
                         "value_errors": int(value_errors.sum()),
                         "phase_errors": int(((phase ^ expected_phase) & ~value_errors).sum())})
    write_json(output, {"classification": "source_stage_development_profile", "circuit_sha256": RELEASE,
                        "assembly_sha256": ASSEMBLY, "backend_sha256": sha256(backend),
                        "ancilla_scope": "Observed nonzero ancillas use verifier ordering. "
                                          "Zero on sampled trajectories does not prove an available scratch slot.",
                        "qubits": full.num_qubits, "batch_size": batch_size, "batches": lane})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "circuit", "backend", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    profile(args.source, args.circuit, args.backend, args.output)


if __name__ == "__main__":
    main()
