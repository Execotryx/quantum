"""Rebuild the pinned, attributed public DQI source and run its official check.

The decoder is SomeJoint / Agniv Banerjee's Apache-2.0 J-fraction decoder.
The classical mask projection is Manwithacat's public addition.  This wrapper
adds source authentication and a fresh, unchanged competition verifier call.
It makes no claim to originate either algorithm.  See NOTICE.txt.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SALT = "vqcc-signed-digit-memory-v1-20261023"
EXPECTED_CIRCUIT = "7aeb66ef64b55273ca1a38498220c442f03be5237bf059c03c147474ef9dd53f"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def authenticate(source_dir: Path) -> dict:
    manifest = json.loads((HERE / "pinned_sources.json").read_text(encoding="utf-8"))
    checked = []
    for entry in manifest["files"]:
        path = source_dir / entry["path"]
        actual = sha256(path)
        # Notebook %%writefile cells normalize Windows CRLF to LF. Authenticate
        # the exact text modulo newline encoding, retaining raw byte provenance.
        normalized = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if normalized != entry["canonical_text_sha256"]:
            raise ValueError(f"Source mismatch: {entry['path']}: {normalized}")
        checked.append({**entry, "actual_sha256": actual,
                        "actual_canonical_text_sha256": normalized})
    return {"status": "PASS", "notebook": manifest["notebook"], "files": checked}


def load_runtime(official_root: Path, source_dir: Path):
    # Insert the real official locations before importing upstream common.py.
    # Upstream common.py adds nonexistent notebook-relative paths; no upstream
    # source needs modification, because the official locations remain here.
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(official_root / "kickmix"),
                   str(official_root / "verifiers" / "dqi"), str(source_dir),
                   str(source_dir / "continued_fraction"),
                   str(source_dir / "continued_fraction" / "keyeq")]
    km = importlib.import_module("kickmix")
    verifier = importlib.import_module("verify_submission_dqi")
    projection = importlib.import_module("mask_projection")
    field = km.GF2Field(12)
    if field.primitive_element != 2:
        raise ValueError("Pinned source model expects the official primitive element 2")
    return km, verifier, projection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, default=PROJECT / "data/competition")
    parser.add_argument("--source-dir", type=Path, default=HERE / "upstream/dqi")
    parser.add_argument("--output-dir", type=Path, default=HERE / "local_candidate")
    parser.add_argument("--workers", type=int, default=2)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true", help="Authenticate and import; emit no circuit")
    mode.add_argument("--build-only", action="store_true", help="Build a source candidate; defer full verification")
    mode.add_argument("--verify-only", action="store_true", help="Verify this output directory's existing authenticated circuit")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    source_dir, official_root = args.source_dir.resolve(), args.official_root.resolve()
    output = args.output_dir.resolve()
    pins = authenticate(source_dir)
    km, verifier, projection = load_runtime(official_root, source_dir)
    official_path = Path(verifier.__file__).resolve()
    official_pin = {"module": str(official_path), "sha256": sha256(official_path)}
    if args.check_only:
        print(json.dumps({"status": "PASS", "check": "source authentication and runtime imports",
                          "source_files": len(pins["files"]), "official": official_pin,
                          "seed": None, "salt": SALT, "no_circuit_built": True}, indent=2), flush=True)
        return
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "source_authentication.json", pins)
    circuit_path = output / "dqi.kmb"
    if not args.verify_only:
        start = time.monotonic()
        print("SOURCE_BUILD_START", flush=True)
        builder = projection.StaticArithmeticBuilder()
        circuit = projection.build(builder, iterations=35,
                                   decoder_type=projection.ProjectedGapDecoder)
        stats = circuit.operation_statistics()
        # These checks authenticate resource/layout structure, not correctness.
        assert circuit.num_qubits == 932
        assert circuit.num_bits == 99145
        assert len(circuit) == 110834205
        assert stats.num_toffoli_like == 1424536
        assert "Z_POW" not in stats
        circuit.to_file(str(circuit_path), format="kmb")
        digest = sha256(circuit_path)
        if digest != EXPECTED_CIRCUIT:
            raise ValueError(f"Pinned generator produced different circuit bytes: {digest}")
        build_report = {"status": "BUILT_NOT_VERIFIED", "source": pins["notebook"],
                        "circuit_sha256": digest, "circuit_bytes": circuit_path.stat().st_size,
                        "num_qubits": circuit.num_qubits, "num_bits": circuit.num_bits,
                        "static_toffoli_count": stats.num_toffoli_like,
                        "num_ops": len(circuit), "stages": builder.stage_records,
                        "build_seconds": time.monotonic() - start,
                        "official": official_pin}
        write_json(output / "dqi_build.json", build_report)
        print(json.dumps(build_report, indent=2), flush=True)
        del builder
        gc.collect()
        if args.build_only:
            return
    else:
        if sha256(circuit_path) != EXPECTED_CIRCUIT:
            raise ValueError("Existing circuit does not match the pinned source candidate")
        circuit = km.Circuit.from_file(str(circuit_path), format="kmb")
    spec = verifier.ProblemSpecDQI.benchmark_instance()
    assert (spec.m, spec.n, spec.degree, spec.r, spec.num_shots) == (4095, 70, 12, 2016, 102400)
    assert verifier.DEFAULT_BATCH_SIZE == 256 and verifier.DEFAULT_LOG2_DELTA == -128.0
    start = time.monotonic()
    print("FRESH_OFFICIAL_VERIFY_START fixed_salt seed=None shots=102400", flush=True)
    try:
        report = verifier.verify(circuit, spec, seed=None, salt=SALT,
                                 batch_size=verifier.DEFAULT_BATCH_SIZE,
                                 log2_delta=verifier.DEFAULT_LOG2_DELTA,
                                 max_workers=args.workers)
    except Exception as error:
        write_json(output / "dqi_full_failure.json",
                   {"status": "FAIL", "error": repr(error), "salt": SALT, "seed": None,
                    "official": official_pin, "wall_seconds": time.monotonic() - start})
        raise
    report["verification_context"] = {"fresh": True, "salt": SALT, "seed": None,
        "batch_size": verifier.DEFAULT_BATCH_SIZE, "num_shots": spec.num_shots,
        "log2_delta": verifier.DEFAULT_LOG2_DELTA, "workers": args.workers,
        "official": official_pin, "wall_seconds": time.monotonic() - start,
        "source_notebook": pins["notebook"], "no_pregenerated_shots": True}
    write_json(output / "dqi_full.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
