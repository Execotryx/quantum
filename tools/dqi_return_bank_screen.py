"""Optimistically count CCX deletions before X-basis measurements in an affine frame."""

import argparse
from collections import Counter
import lzma
import mmap
from pathlib import Path
import shutil
from tempfile import TemporaryFile

from qcompile.io import sha256, write_json

from tools.dqi_return_measurement_screen import CONTROL


class Displacements:
    """Wire columns for a binary subspace and its annihilator."""

    def __init__(self, width: int) -> None:
        self.vectors = [0] * width
        self.constraints = [1 << wire for wire in range(width)]
        self.free_vectors = (1 << width) - 1
        self.free_constraints = 0

    @property
    def dimension(self) -> int:
        return self.free_constraints.bit_count()

    def require_zero(self, wire: int) -> None:
        signature = self.vectors[wire]
        if signature:
            consumed = signature & -signature
            for idx, old in enumerate(self.vectors):
                if old & consumed:
                    self.vectors[idx] = old ^ signature
            added = self.free_constraints & -self.free_constraints
            self.constraints[wire] ^= added
            self.free_vectors |= consumed
            self.free_constraints ^= added

    def measure(self, wire: int) -> None:
        self.require_zero(wire)
        signature = self.constraints[wire]
        consumed = signature & -signature
        for idx, old in enumerate(self.constraints):
            if old & consumed:
                self.constraints[idx] = old ^ signature
        added = self.free_vectors & -self.free_vectors
        self.vectors[wire] ^= added
        self.free_constraints |= consumed
        self.free_vectors ^= added

    def cx(self, control: int, target: int) -> None:
        self.vectors[target] ^= self.vectors[control]
        self.constraints[control] ^= self.constraints[target]

    def swap(self, left: int, right: int) -> None:
        self.vectors[left], self.vectors[right] = self.vectors[right], self.vectors[left]
        self.constraints[left], self.constraints[right] = self.constraints[right], self.constraints[left]


def screen(source: Path, width: int = 900) -> dict[str, object]:
    counts: Counter[str] = Counter()
    space: Displacements | None = None
    first_opportunity: dict[str, int] | None = None
    depth = 0
    with TemporaryFile() as assembly:
        with lzma.open(source, "rb") as compressed:
            shutil.copyfileobj(compressed, assembly, length=1 << 20)
        assembly.flush()
        with mmap.mmap(assembly.fileno(), 0, access=mmap.ACCESS_READ) as body:
            end = len(body) - int(body[-1] == 10)
            while end > 0:
                start = body.rfind(b"\n", 0, end) + 1
                op, _, operands = body[start:end].rstrip().partition(b" ")
                end = start - 1
                counts["lines"] += 1
                if op == b"CCX":
                    counts["ccx"] += 1
                if op == b"POP_CONDITION":
                    depth += 1
                elif op == b"PUSH_CONDITION":
                    depth -= 1
                    if depth < 0:
                        raise ValueError("Return-stage guard stack underflow")
                if depth or op in (b"PUSH_CONDITION", b"POP_CONDITION") or b" if " in operands:
                    space = None
                elif op == b"HMR":
                    if space is None:
                        space = Displacements(width)
                    wire = int(operands.split(b" ", 1)[0][1:])
                    space.measure(wire)
                    counts["unguarded_measurements"] += 1
                    counts["peak_dimension"] = max(counts["peak_dimension"], space.dimension)
                elif space is not None:
                    if op == b"CCX":
                        left, right, target = (int(wire[1:]) for wire in operands.split())
                        if space.constraints[target] == 0:
                            counts["ccx_savings_ceiling"] += 1
                            first_opportunity = {"byte_offset": start, "target": target}
                        else:
                            space.require_zero(left)
                            space.require_zero(right)
                            if space.dimension == 0:
                                space = None
                    elif op in (b"CX", b"SWAP"):
                        left, right = (int(wire[1:]) for wire in operands.split())
                        if op == b"CX":
                            space.cx(left, right)
                        else:
                            space.swap(left, right)
                    elif op != b"X":
                        space = None
    if depth:
        raise ValueError("Return-stage guard stack left open")
    return {
        **counts,
        "ccx_savings_ceiling": counts["ccx_savings_ceiling"],
        "first_opportunity": first_opportunity,
    }


def run(source: Path, output: Path) -> None:
    if sha256(source) != CONTROL:
        raise ValueError("Unexpected DQI return source")
    result = screen(source)
    if result["ccx"] != 107422 or result["unguarded_measurements"] != 18460:
        raise ValueError("Return-stage operation counts differ from the control")
    write_json(output, {
        "scope": "optimistic deletions through unguarded affine gates and HMR; phase repairs granted; no emitted circuit",
        "source_sha256": CONTROL,
        "driver_sha256": sha256(Path(__file__)),
        **result,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
