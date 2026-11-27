"""Count write-only return-stage suffixes ending at an X-basis measurement."""

import argparse
from collections import Counter
import lzma
from pathlib import Path
import re

from qcompile.io import sha256, write_json


CONTROL = "b2da55202f6b574ee9af452f25f34772c2a0e90bfc5ce102129c0861faaf1fcf"
WIRES = re.compile(rb"\bq(\d+)\b")


def screen(source: Path) -> dict[str, int]:
    eligible: dict[int, int] = {}
    counts: Counter[str] = Counter()
    guard_depth = 0
    with lzma.open(source, "rb") as operations:
        for line in operations:
            op, _, operands = line.rstrip().partition(b" ")
            if op == b"PUSH_CONDITION":
                guard_depth += 1
                continue
            if op == b"POP_CONDITION":
                guard_depth -= 1
                if guard_depth < 0:
                    raise ValueError("Return-stage guard stack underflow")
                continue
            if op == b"CCX":
                counts["ccx"] += 1
            guarded = guard_depth != 0 or b" if " in operands
            if not guarded and op in (b"CX", b"CCX"):
                *controls, target = (int(wire[1:]) for wire in operands.split())
                for control in controls:
                    eligible.pop(control, None)
                if op == b"CCX":
                    counts["unconditional_ccx"] += 1
                    eligible[target] = eligible.get(target, 0) + 1
            elif not guarded and op == b"HMR":
                target, = (int(wire) for wire in WIRES.findall(operands))
                savings = eligible.pop(target, 0)
                counts["unconditional_measurements"] += 1
                if savings:
                    counts["nontrivial_suffixes"] += 1
                    counts["ccx_savings_ceiling"] += savings
                    counts["largest_suffix"] = max(counts["largest_suffix"], savings)
            elif eligible:
                for wire in WIRES.findall(operands):
                    eligible.pop(int(wire), None)
    if guard_depth:
        raise ValueError("Return-stage guard stack left open")
    if counts["ccx"] != 107422:
        raise ValueError("Return-stage CCX count differs from the source census")
    return {key: counts[key] for key in (
        "ccx", "unconditional_ccx", "unconditional_measurements", "nontrivial_suffixes",
        "ccx_savings_ceiling", "largest_suffix",
    )}


def run(source: Path, output: Path) -> None:
    if sha256(source) != CONTROL:
        raise ValueError("Unexpected DQI return source")
    write_json(output, {
        "scope": "unguarded CX and CCX suffixes before existing unguarded HMR; no emitted circuit",
        "source_sha256": CONTROL,
        "driver_sha256": sha256(Path(__file__)),
        **screen(source),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
