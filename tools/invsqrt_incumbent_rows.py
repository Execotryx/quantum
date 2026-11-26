"""Recognize and re-emit a complete addition row in the 39-qubit source control."""

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from invsqrt_reset_reuse import HEADER, advance_resets, lend_zeroed_inputs, reuse
from qcompile.invsqrt.scratch import ScratchProof
from qcompile.io import sha256, write_json


CONTROL = "27ccb62d03bcba70353d382bb94c5dc636acd00b250c83f976df8d1176842146"
BIT = re.compile(r"\bb\d+\b")


@dataclass(frozen=True)
class Carry:
    left: str
    right: str
    incoming: str
    outgoing: str


def majority(lines: list[str], start: int) -> Carry | None:
    """Match c XOR ((a XOR c) AND (b XOR c)) into a carry target."""
    block = lines[start:start + 6]
    if len(block) != 6:
        return None
    first, second, product = (line.split() for line in block[:3])
    if [len(parts) for parts in (first, second, product)] != [3, 3, 4]:
        return None
    _, incoming, left = first
    _, _, right = second
    outgoing = product[-1]
    if (first[0] != "CX" or second != ["CX", incoming, right] or product[0] != "CCX"
            or set(product[1:3]) != {left, right} or len({incoming, left, right, outgoing}) != 4):
        return None
    if set(block[3:]) != {f"CX {incoming} {wire}" for wire in (left, right, outgoing)}:
        return None
    # The carry can commute with removing the frames, but the CCX must see both frames.
    return Carry(left, right, incoming, outgoing)


def uncompute(cell: Carry, bit: str) -> list[str]:
    a, b, c, out = cell.left, cell.right, cell.incoming, cell.outgoing
    return [f"CX {c} {b}", f"CX {c} {a}", f"CX {c} {out}", f"HMR {out} {bit}",
            f"CZ {a} {b} if {bit}", f"CX {c} {b}", f"CX {c} {a}", f"CX {a} {b}", f"CX {c} {b}"]


def borrow_carries(cells: list[Carry], high: str, top: str) -> list[str]:
    """Add the six source bits, a fixed high one, and the carry-in into the target."""
    incoming = cells[0].incoming
    rows = []
    for cell in cells:
        rows.append((cell.left, cell.right, incoming))
        incoming = cell.left
    operations = []
    for a, b, c in rows:
        operations.extend((f"CX {a} {b}", f"CX {a} {c}", f"CCX {b} {c} {a}"))
    operations.extend((f"CX {high} {top}", f"CX {incoming} {top}", f"CCX {high} {incoming} {top}",
                       f"X {high}", f"CX {incoming} {high}"))
    for a, b, c in reversed(rows):
        operations.extend((f"CCX {b} {c} {a}", f"CX {a} {b}", f"CX {c} {b}", f"CX {a} {c}"))
    return operations


def match_row(lines: list[str], start: int, complete: dict[int, Carry], uses: Counter[str],
              proof: ScratchProof) -> tuple[int, list[str]] | None:
    cells = [complete[i] for i in range(start, start + 36, 6) if i in complete]
    if len(cells) != 6 or any(a.outgoing != b.incoming for a, b in zip(cells, cells[1:])):
        return None
    end = start + 36
    terminal = lines[end:end + 10]
    if len(terminal) != 10:
        return None
    head, copy, measured = (terminal[i].split() for i in (0, 3, 6))
    if [len(parts) for parts in (head, copy, measured)] != [4, 3, 3]:
        return None
    _, high, carry, temporary = head
    top, bit = copy[-1], measured[-1]
    if carry != cells[-1].outgoing or terminal != [
        f"CCX {high} {carry} {temporary}", f"CX {high} {temporary}", f"CX {carry} {temporary}",
        f"CX {temporary} {top}", f"CX {carry} {temporary}", f"CX {high} {temporary}",
        f"HMR {temporary} {bit}", f"CZ {high} {carry} if {bit}", f"X {high}", f"CX {carry} {high}",
    ] or uses[bit] != 2:
        return None
    end += 10
    for cell in reversed(cells):
        cleanup = lines[end:end + 9]
        if len(cleanup) != 9 or not cleanup[3].startswith("HMR "):
            return None
        outcome = cleanup[3].split()[-1]
        if uses[outcome] != 2 or cleanup != uncompute(cell, outcome):
            return None
        end += 9
    targets = [cell.right for cell in cells] + [high, top]
    live = [cell.left for cell in cells] + targets + [cells[0].incoming]
    scratch = [cell.outgoing for cell in cells] + [temporary]
    if len(set(live + scratch)) != len(live + scratch) or any(proof.values[q] for q in scratch):
        return None
    # This family already conjugates the entire target by a sign-dependent complement.
    prefix = lines[start - 16:start]
    sign = prefix[0].split()[1] if len(prefix) == 16 and prefix[0].startswith("CX ") else ""
    complement = [gate for q in targets for gate in (f"CX {sign} {q}", f"X {q}")]
    if not sign or sign in live + scratch or prefix != complement or lines[end:end + 16] != complement:
        return None
    return end, borrow_carries(cells, high, top)


def rewrite(lines: list[str]) -> tuple[list[str], dict]:
    uses = Counter(BIT.findall("\n".join(lines)))
    proof = ScratchProof(22)
    complete = {}
    rotations = []
    depth = 0
    for index, line in enumerate(lines):
        if line == "POP_CONDITION":
            depth -= 1
        elif line.startswith("PUSH_CONDITION"):
            depth += 1
        elif depth == 0 and line.startswith("CX ") and (cell := majority(lines, index)):
            complete[index] = cell
        elif line.startswith("Z_POW ") and Fraction(line.split()[2]) % Fraction(1, 4):
            rotations.append(index)
    splices = []
    result = []
    index = 0
    while index < len(lines):
        matched = match_row(lines, index, complete, uses, proof) if index in complete else None
        end, replacement = matched if matched is not None else (index + 1, lines[index:index + 1])
        if matched is not None:
            splices.append({"first_line": index + 1, "last_line": end, "original_toffolis": 7,
                            "replacement_toffolis": 13})
        for line in lines[index:end]:
            parts = line.split()
            if parts and parts[0] not in HEADER:
                proof.step(parts)
        result.extend(replacement)
        index = end
    report = {"unconditional_majority_cells": len(complete), "signed_row_splices": splices}
    if rotations:
        report["majority_cells_by_phase_window"] = {
            "before_fine_rotations": sum(i < rotations[0] for i in complete),
            "rotation_window": sum(rotations[0] <= i <= rotations[-1] for i in complete),
            "after_fine_rotations": sum(i > rotations[-1] for i in complete),
        }
    return result, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "output", "receipt"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if sha256(args.assembly) != CONTROL:
        raise ValueError("Source control hash differs from the reviewed assembly")
    lines, report = rewrite(args.assembly.read_text(encoding="ascii").splitlines())
    if not report["signed_row_splices"]:
        raise ValueError("No fully matched signed rows")
    early, _ = advance_resets([line + "\n" for line in lines])
    normalized, _ = reuse(early, symbolic=True, prune=True)
    compact, profile = lend_zeroed_inputs(normalized)
    with args.output.open("x", newline="\n", encoding="ascii") as stream:
        stream.writelines(compact)
    write_json(args.receipt, {
        "classification": "source_signed_row_rewrite_and_width_screen",
        "assembly_sha256": CONTROL, "driver_sha256": sha256(Path(__file__)),
        "candidate_assembly_sha256": sha256(args.output),
        "width": profile, **report,
    })


if __name__ == "__main__":
    main()
