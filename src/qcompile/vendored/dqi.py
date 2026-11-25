"""Regenerate admitted public DQI circuits with the pinned native backend."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend

ROOT = Path(__file__).resolve().parents[3]
BUILDERS = {"d5": ("--output",), "d4": ()}


def build(candidate: str, output: Path, backend_path: Path) -> None:
    if sys.version_info[:2] != (3, 13):
        raise ValueError("public DQI regeneration requires Python 3.13")
    if candidate == "d5" and np.__version__ != "2.5.4":
        raise ValueError("Q880 regeneration requires NumPy 2.5.4")
    component = ROOT / "third_party" / f"dqi-{candidate}"
    backend = read_json(backend_path)
    validate_backend(backend)
    provenance_path = component / "SOURCE.json"
    source = read_json(provenance_path)
    source_hash = sha256(provenance_path)
    for item in source["files"]:
        path = component / item["path"]
        if path.is_symlink() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"vendored byte mismatch: {path}")
    expected = {item["name"]: item["sha256"] for item in source["published_outputs"]}
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "dqi.kmb"
    runtime_paths = [backend["kickmix_root"], str(Path(backend["verifiers_root"]) / "dqi")]
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join(runtime_paths), "PYTHONDONTWRITEBYTECODE": "1",
                   "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    with (output / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run(
            [sys.executable, str(component / "src/build.py"), *BUILDERS[candidate], str(archive)],
            cwd=output, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True,
        )
    result = sha256(archive)
    require_match = expected.get(archive.name)
    status = "go" if require_match is None or result == require_match else "origin_hash_mismatch"
    build_record = output / "dqi.build.json"
    write_json(output / "regeneration.json", {
        "status": status, "sha256": result, "published_sha256": require_match,
        "source_sha256": source_hash, "backend_sha256": sha256(backend_path),
        "python": sys.version, "numpy": np.__version__,
        "build_record_sha256": sha256(build_record) if build_record.exists() else None,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", choices=BUILDERS)
    parser.add_argument("output", type=Path)
    parser.add_argument("backend", type=Path)
    args = parser.parse_args()
    build(args.candidate, args.output, args.backend)
