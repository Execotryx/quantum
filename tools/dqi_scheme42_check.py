"""Regenerate the admitted rank-42 tensor and check every 0x1053 product."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from qcompile.dqi.field import GF4096

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "third_party" / "dqi-scheme42"


def verify(terms: list[tuple[int, int, int]]) -> None:
    field = GF4096()
    values = np.arange(4096, dtype=np.intp)
    log = np.asarray(field.log, dtype=np.intp)
    exp = np.asarray(field.exp, dtype=np.uint16)
    parity = np.asarray([i.bit_count() % 2 for i in range(4096)], dtype=np.uint16)
    forms = [(parity[values & a], parity[values & b] * word) for a, b, word in terms]
    for start in range(0, 4096, 128):
        rows = slice(start, start + 128)
        actual = np.zeros((128, 4096), dtype=np.uint16)
        for left, right in forms:
            actual ^= left[rows, None] * right[None, :]
        expected = exp[(log[rows, None] + log[None, :]) % 4095]
        expected[:, 0] = 0
        if start == 0:
            expected[0, :] = 0
        if not np.array_equal(actual, expected):
            raise ValueError(f"Mismatch within left operand block starting at {start}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    source = COMPONENT / "SOURCE.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = COMPONENT / record["path"]
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Source integrity failed for {path}")

    builds = []
    for index in (1, 2):
        path = args.output / f"scheme42-{index}.txt"
        subprocess.run([sys.executable, "-B", str(COMPONENT / "src" / "scheme42.py"), str(path)], check=True)
        builds.append(path.read_bytes())
    digest = hashlib.sha256(builds[0]).hexdigest()
    if builds[0] != builds[1] or digest != manifest["published_outputs"][0]["sha256"]:
        raise ValueError("Generated tensor differs from the published output")

    terms = []
    for term in builds[0].decode("ascii").split():
        a, b, word = (int(part, 16) for part in term.split(","))
        terms.append((a, b, word))
    if len(terms) != 42:
        raise ValueError("Generated tensor must have 42 terms")
    verify(terms)
    result = {
        "status": "pass",
        "basis": "0x1053 polynomial",
        "conversion": "identity",
        "pairs": 4096**2,
        "term_count": len(terms),
        "tensor_sha256": digest,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    (args.output / "scheme42.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
