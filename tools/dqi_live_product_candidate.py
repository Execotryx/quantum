"""Emit the exact live-product DQI rewrite and replay the source-control panels."""

import argparse
import importlib
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

from dqi_executed_stages import ASSEMBLY, RELEASE, SEEDS, stages
from dqi_live_products import RESET_INTERVAL, rewrite
from dqi_matched_batches import verify
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

HOT_STAGES = {"quantum_decoder_to_field_1", "field_2_to_root_1330_phase", "decoder_return"}


def run(source: Path, control: Path, backend: Path, output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    if sha256(control) != RELEASE:
        raise ValueError("The exact source control is required")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    api = importlib.import_module("dqi.verify_submission_dqi")
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    rewrite_source = Path(__file__).with_name("dqi_live_products.py")
    write_json(registration, {
        "baseline_circuit_sha256": RELEASE, "baseline_assembly_sha256": ASSEMBLY,
        "backend_sha256": sha256(backend), "driver_sha256": sha256(Path(__file__)),
        "rewrite_sha256": sha256(rewrite_source), "symbolic_interval": RESET_INTERVAL,
        "stages": sorted(HOT_STAGES), "batch_size": api.DEFAULT_BATCH_SIZE, "seeds": SEEDS,
    })
    candidate = output / "dqi.kmb"
    rewrites = {}
    with tempfile.TemporaryDirectory(prefix="qcompile-dqi-live-products-") as work:
        scratch = Path(work)
        assembly = scratch / "candidate.kmx"
        with assembly.open("wb") as destination:
            for stage, path in stages(source.resolve(), scratch):
                with path.open("rb") as fragment:
                    if stage in HOT_STAGES:
                        rewrites[stage] = rewrite(fragment, destination)
                    else:
                        shutil.copyfileobj(fragment, destination, length=1 << 20)
        circuit = km.Circuit.from_file(assembly, format="kmx")
        circuit.to_file(candidate, format="kmb")
        del circuit

    spec = api.ProblemSpecDQI.benchmark_instance()
    tables = api.FieldTables(km.GF2Field(spec.degree))
    weights = api.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    panels = [
        api.sample_shots(spec, tables, np.random.default_rng(seed), api.DEFAULT_BATCH_SIZE, weights)
        for seed in SEEDS
    ]
    observed = {}
    for role, artifact in (("control", control), ("rewrite", candidate)):
        circuit = km.Circuit.from_file(artifact, format="kmb")
        observed[role] = {
            "sha256": sha256(artifact), "qubits": circuit.num_qubits,
            "static_toffoli_like": int(circuit.operation_statistics().num_toffoli_like),
            "panels": [verify(circuit, spec, api, km, syndromes, masks, expected, seed)
                       for seed, (syndromes, masks, expected) in zip(SEEDS, panels, strict=True)],
        }
        del circuit
    errors = ("phase_offsets", "value_offsets", "dirty_offsets", "mask_offsets")
    pairs = list(zip(observed["control"]["panels"], observed["rewrite"]["panels"], strict=True))
    parity = all(before[key] == after[key] for before, after in pairs for key in errors)
    write_json(output / "decision.json", {
        "classification": "matched_development_panels",
        "registration_sha256": sha256(registration), "semantic_error_parity": parity,
        "executed_gate_savings": [before["mean_toffoli_like"] - after["mean_toffoli_like"] for before, after in pairs],
        "stages": rewrites, "observed": observed,
    })
    if not parity:
        raise ValueError("The emitted candidate changed verifier-visible errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "control", "backend", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
