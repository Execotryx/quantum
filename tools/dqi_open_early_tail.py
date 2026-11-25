"""Build a separately identified Syed v12 early-tail ablation."""

import argparse
import importlib
import sys
from pathlib import Path
from unittest.mock import patch

from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json
from qcompile.vendored.dqi_open_padding import exchange_padding, selected_padding


def build(upstream: Path, intake: Path, output: Path, j_min: int, replace_padding: bool) -> None:
    if output.exists():
        raise FileExistsError(output)
    pins = read_json(intake)
    if sha256(Path(pins["pins"]["source_archive"]["path"])) != pins["pins"]["source_archive"]["sha256"]:
        raise ValueError("The source archive differs from the intake record")
    tree = upstream.resolve()
    work = tree / "controller_work"
    sys.path.insert(0, str(work / "after_v3/integration_v7"))
    pipeline = importlib.import_module("v7_pipeline")
    pipeline.configure()

    sys.path.insert(0, str(work / "after_c5/extractor_width"))
    early = importlib.import_module("raw_query_extractor_early")
    km = importlib.import_module("kickmix")
    if early.A is not pipeline.P.BaselineArithmetic or early.node is not pipeline.BaseExtractor.node:
        raise ValueError("Early extraction does not share the decoder's original basis and node map")
    early_file = getattr(early, "__file__", None)
    if early_file is None or not Path(early_file).resolve().is_relative_to(tree):
        raise ValueError("Early extractor was not loaded from the selected source tree")

    def emit_prefix(builder, words, carry, *, j_min: int, stage):
        if j_min != 15:
            raise ValueError("Expected the upstream pipeline's fixed extraction argument")
        return early.emit_prefix(builder, words, carry, j_min=first_slot, stage=stage)

    first_slot = j_min
    builder = km.CircuitBuilder()
    builder.set_max_qubits(891 if replace_padding else 889)
    syndromes = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
    masks = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]
    stages = []

    def stage(message):
        stages.append({"stage": message, "allocated_qubits": builder.num_allocated_qubits})

    field = GF4096()
    padding = selected_padding(field, list(pipeline.P.Finish.geometry()["M"])) if replace_padding else ()
    xor_linear = importlib.import_module("quantum_reciprocal").xor_linear
    zero_xor = importlib.import_module("coherent_border").toggle_zero

    def key_prefix(builder, syndromes, *, j_min, stage):
        key = pipeline.P.emit_key_prefix(builder, syndromes, j_min=j_min, stage=stage)
        banks = (key["N"], key["D"])
        key["padding_flags"] = [
            exchange_padding(builder, banks, branch, field, xor_linear, zero_xor) for branch in padding
        ]
        return key

    def key_closing(builder, key, *, stage):
        banks = (key["N"], key["D"])
        for branch, flag in reversed(list(zip(padding, key["padding_flags"], strict=True))):
            exchange_padding(builder, banks, branch, field, xor_linear, zero_xor, flag=flag)
        pipeline.P.emit_key_closing(builder, key, stage=stage)

    with (
        patch.object(pipeline.First3, "emit_prefix", emit_prefix),
        patch.object(pipeline.First3, "emit_closing", early.emit_closing),
        patch.object(pipeline, "emit_key_prefix", key_prefix),
        patch.object(pipeline, "emit_key_closing", key_closing),
    ):
        contract = pipeline.emit(builder, syndromes, masks, stage=stage)
    if builder.num_allocated_qubits != 840 or not contract["scan"]["full_cycle"]:
        raise ValueError("The ablation did not retire its allocations or emit the full scan")

    circuit = builder.finish_circuit()
    output.mkdir(parents=True)
    path = output / "dqi.kmb"
    circuit.to_file(path, format="kmb")
    write_json(output / "build.json", {
        "sha256": sha256(path),
        "qubits": circuit.num_qubits,
        "static_toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "source_archive_sha256": pins["pins"]["source_archive"]["sha256"],
        "upstream_circuit_sha256": pins["published_candidate_sha256"],
        "early_extractor_sha256": sha256(Path(early_file)),
        "driver_sha256": sha256(Path(__file__)),
        "first_rolling_slot": first_slot,
        "padding_exchange": [
            {"original": branch.original, "replacement": branch.replacement} for branch in padding
        ],
        "padding_source_sha256": sha256(Path(sys.modules[exchange_padding.__module__].__file__ or "")),
        "stages": stages,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("upstream", "intake", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--first-slot", type=int, choices=(0, 15), default=0)
    parser.add_argument("--replace-padding", action="store_true")
    args = parser.parse_args()
    build(args.upstream, args.intake, args.output, args.first_slot, args.replace_padding)


if __name__ == "__main__":
    main()
