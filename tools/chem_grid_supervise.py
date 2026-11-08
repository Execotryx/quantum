"""Supervise one initializer-ranking worker with an external resource sampler."""

import argparse
import subprocess
import sys
from pathlib import Path

from invsqrt_direct import run_job

from qcompile.io import read_json, sha256, write_json


def run(plan_path: Path, output: Path, timeout: int) -> str:
    if type(timeout) is not int or not 1 <= timeout <= 7200:
        raise ValueError("ranking timeout must be an integer in [1, 7200]")
    plan = read_json(plan_path)
    plan_hash = sha256(plan_path)
    root = Path(__file__).resolve().parents[1]
    sources = (Path(__file__).resolve(), root / "tools/invsqrt_direct.py", root / "src/qcompile/profiling.py")
    source_hashes = {str(path.relative_to(root)): sha256(path) for path in sources}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "supervisor-registration.json", {"plan": plan, "plan_sha256": plan_hash,
                                                         "timeout_seconds": timeout,
                                                         "sampler_interval_seconds": 1,
                                                         "source_hashes": source_hashes})
    try:
        worker = Path(__file__).with_name("chem_fit_grid.py")
        code = run_job([sys.executable, str(worker), "rank", str(plan_path), str(output / "ranking")], output, timeout)
        status = "complete" if code == 0 else f"worker_exit_{code}"
    except subprocess.TimeoutExpired:
        status = "timeout"
    if sha256(plan_path) != plan_hash:
        raise ValueError("ranking plan changed during execution")
    if any(sha256(root / name) != digest for name, digest in source_hashes.items()):
        raise ValueError("ranking supervisor source changed during execution")
    write_json(output / "status.json", {"status": status, "scope": "execution status, not shape eligibility"})
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=int, required=True)
    arguments = parser.parse_args()
    status = run(arguments.plan, arguments.output, arguments.timeout)
    if status != "complete":
        sys.exit(1)
