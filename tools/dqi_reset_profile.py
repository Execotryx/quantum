"""Stream the reset-delimited scratch width of a complete DQI assembly."""

import argparse
import re
from pathlib import Path
from typing import BinaryIO

from qcompile.io import sha256, write_json

QUBIT = re.compile(rb"\bq(\d+)\b")
SYNDROME_WIDTH = 840


def profile(stream: BinaryIO) -> dict:
    """Count simultaneous leases. An HMR under any condition preserves its lease."""
    protected = set()
    active: set[int] = set()
    all_live: set[int] = set()
    peak: set[int] = set()
    peak_line = depth = resets = maximum = peak_with_lending = input_resets = 0
    started = False
    for line_number, line in enumerate(stream, 1):
        if line.startswith(b"PUSH_CONDITION "):
            depth += 1
        elif line.startswith(b"POP_CONDITION"):
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced KMX condition")
        if b"q" not in line or line.startswith((b"REGISTER ", b"INFO_TAG ")):
            continue
        ids = [int(value) for value in QUBIT.findall(line)]
        maximum = max(maximum, *ids) if ids else maximum
        if line.startswith(b"APPEND_TO_REGISTER "):
            if started:
                raise ValueError("Syndrome declarations must precede the scratch operations")
            protected.update(ids)
            all_live.update(ids)
            continue
        started = True
        active.update(wire for wire in ids if wire not in protected)
        all_live.update(ids)
        peak_with_lending = max(peak_with_lending, len(all_live))
        if len(active) > len(peak):
            peak = active.copy()
            peak_line = line_number
        if ids and depth == 0 and line.startswith(b"HMR ") and len(line.split()) == 3:
            all_live.remove(ids[0])
            if ids[0] in active:
                active.remove(ids[0])
                resets += 1
            else:
                input_resets += 1
    if depth or len(protected) != SYNDROME_WIDTH:
        raise ValueError("Incomplete condition or syndrome layout")
    return {
        "declared_qubit_span": maximum + 1,
        "reset_delimited_width": SYNDROME_WIDTH + len(peak),
        "reset_interval_peak_with_input_lending": peak_with_lending,
        "unconditional_input_resets": input_resets,
        "peak_scratch_ids": sorted(peak),
        "peak_assembly_line": peak_line,
        "unconditional_scratch_resets": resets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    digest = sha256(args.assembly)
    with args.assembly.open("rb") as stream:
        report = profile(stream)
    write_json(args.receipt, {
        **report,
        "input_assembly_sha256": digest,
        "classification": "static_reset_delimited_width",
    })


if __name__ == "__main__":
    main()
