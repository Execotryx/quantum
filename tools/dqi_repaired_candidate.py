"""Emit the candidate D4 pole-repair circuit on the pinned Linux backend."""

import argparse
import importlib
import sys
from pathlib import Path

from dqi_phase_profile import load_decoder

from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored.dqi_d4 import (
    paired_external_extraction,
    paired_residue_scan,
    paired_tail,
    synthesize_linear_tail,
)
from qcompile.vendored.dqi_d4_validation import xor_invalid_rational, xor_quotient

WIDTH = 54
ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = (
    "tools/dqi_repaired_candidate.py", "tools/dqi_phase_profile.py",
    "src/qcompile/vendored/dqi_d4.py", "src/qcompile/vendored/dqi_d4_validation.py",
    "src/qcompile/dqi/decoder.py", "src/qcompile/dqi/field.py",
)


def build(component: Path, backend: Path, bank: Path, output: Path):
    source = component / "SOURCE.json"
    member = read_json(bank)
    settings = read_json(backend)
    validate_backend(settings)
    registration = read_json(bank.with_name("salts.json"))
    signature = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if (
        sha256(source) != member["source_sha256"]
        or sha256(bank.with_name("salts.json")) != member["registration_sha256"]
        or signature != registration["backend_inventory_sha256"]
    ):
        raise ValueError("Source and verifier inventory must match the banked D4 provenance")
    for row in read_json(source)["files"]:
        if sha256(component / row["path"]) != row["sha256"]:
            raise ValueError(f"Vendored source changed: {row['path']}")
    output.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    reference = load_decoder(component / "src", km).replay_erase.ref
    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    invalid = builder.alloc_qubits(1)[0]
    repeated = builder.alloc_qubits(6)
    quotient = [builder.alloc_qubits(12) for _ in words]

    with builder.mark("moment_certificate_input"):
        xor_quotient(builder, reference, words, quotient, reference.P)
    with builder.mark("initial"):
        reference.linear_words(builder, words, reference.matrix)
    with builder.mark("extract"):
        token = paired_external_extraction(builder, reference, words)
        charts = [row[0] for row in token]
        denominator = paired_tail(builder, reference, words, charts)
    tail = words[-2], denominator, words[-1]
    with builder.mark("synthesis"):
        banks = synthesize_linear_tail(builder, reference, words, tail, charts, WIDTH, regular_solver=True)
    with builder.mark("moment_certificate"):
        xor_invalid_rational(builder, reference, quotient, banks, reference.P, invalid)
    with builder.mark("scan"):
        paired_residue_scan(
            builder, reference, (banks[0][:36], banks[1][:36]), masks, repeated_root_count=repeated,
        )
    with builder.mark("unsynthesis"):
        synthesize_linear_tail(
            builder, reference, words, tail, charts, WIDTH, reverse=True, banks=banks, regular_solver=True,
        )
    with builder.mark("unextract"):
        paired_tail(builder, reference, words, charts, reverse=True, denominator=denominator)
        paired_external_extraction(builder, reference, words, reverse=True, token=token)
    with builder.mark("uninitial"):
        reference.linear_words(builder, words, reference.matrix, True)
    with builder.mark("clear_certificate_input"):
        xor_quotient(builder, reference, words, quotient, reference.P)
        for word in quotient:
            builder.free(word)

    metadata = []
    for kind, label, count, first in (("q", "S", 70, 0), ("b", "E", 4095, 70)):
        for index in range(count):
            register = first + index
            metadata.append(f'REGISTER r{register} "{label}{index}"')
            metadata.extend(f"APPEND_TO_REGISTER {kind}{12 * index + bit} r{register}" for bit in range(12))
    circuit = km.Circuit("\n".join(metadata)) + builder.finish_circuit()
    artifact = output / "dqi.kmb"
    circuit.to_file(str(artifact), format="kmb")
    write_json(output / "build.json", {
        "circuit_sha256": sha256(artifact), "source_sha256": sha256(source),
        "backend_sha256": sha256(backend), "driver_sha256": sha256(Path(__file__)),
        "banked_d4_sha256": member["sha256"], "qubits": circuit.num_qubits,
        "static_toffoli_like": circuit.operation_statistics().num_toffoli_like,
        "polynomial_bank_width": WIDTH, "visible_failure_bits": 7, "scan_count": 4095,
        "status": "experimental",
        "implementation_sha256": {name: sha256(ROOT / name) for name in IMPLEMENTATION},
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("component", "backend", "bank", "output"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    build(args.component, args.backend, args.bank, args.output)


if __name__ == "__main__":
    main()
