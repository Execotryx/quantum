"""Register and run a bounded GF(64) bilinear flip-graph search."""

import argparse
from pathlib import Path

from qcompile.dqi.bilinear_search import search
from qcompile.dqi.tower import tower
from qcompile.io import identity, sha256, write_json


def run(output: Path, *, seed: int, max_steps: int, max_seconds: float, restart_steps: int) -> None:
    if max_steps < 1 or max_seconds <= 0 or restart_steps < 1:
        raise ValueError("search limits must be positive")
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    sources = {
        "search": root / "src/qcompile/dqi/bilinear_search.py",
        "tower": root / "src/qcompile/dqi/tower.py",
        "field": root / "src/qcompile/dqi/field.py",
        "runner": Path(__file__).resolve(),
    }
    for name, source in sources.items():
        (output / f"{name}.py.txt").write_bytes(source.read_bytes())
    registration = {
        "seed": seed, "max_steps": max_steps, "max_seconds": max_seconds,
        "restart_steps": restart_steps, "scope": "development rank search",
        "initial_terms_sha256": identity(tower().subfield_terms),
        "source_sha256": {name: sha256(source) for name, source in sources.items()},
    }
    write_json(output / "registration.json", registration)
    result = search(seed, max_steps, max_seconds, restart_steps)
    write_json(output / "result.json", {**result, "registration_sha256": sha256(output / "registration.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--max-seconds", type=float, required=True)
    parser.add_argument("--restart-steps", type=int, required=True)
    args = parser.parse_args()
    run(args.output, seed=args.seed, max_steps=args.max_steps,
        max_seconds=args.max_seconds, restart_steps=args.restart_steps)
