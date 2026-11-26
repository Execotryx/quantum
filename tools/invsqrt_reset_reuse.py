"""Reuse zeroed scratch wires in single-register inverse-square-root assembly."""

import argparse
import heapq
import re
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from pathlib import Path

from qcompile.invsqrt.scratch import ScratchProof
from qcompile.io import sha256, write_json

QUBIT = re.compile(r"\bq(\d+)\b")
WIRE = re.compile(r"\b[qb]\d+\b")
HEADER = {"REGISTER", "APPEND_TO_REGISTER", "INFO_TAG"}


def advance_resets(lines: list[str]) -> tuple[list[str], int]:
    """Move a straight-line HMR across independent gates without changing RNG order."""
    last: dict[str, int] = {}
    early: dict[int, list[str]] = {}
    moved = set()
    depth = 0
    barrier = -1
    for index, line in enumerate(lines):
        parts = line.split()
        if not parts:
            continue
        op = parts[0]
        wires = WIRE.findall(line)
        if op == "HMR" and depth == 0 and len(parts) == 3 and len(wires) == 2:
            after = max(barrier, *(last.get(wire, -1) for wire in wires))
            if after + 1 < index:
                early.setdefault(after + 1, []).append(line)
                moved.add(index)
        if op in {"PUSH_CONDITION", "POP_CONDITION", "HMR", "R", "REGISTER", "APPEND_TO_REGISTER"}:
            barrier = index
        depth += int(op == "PUSH_CONDITION") - int(op == "POP_CONDITION")
        last.update(dict.fromkeys(wires, index))
    result = []
    for index, line in enumerate(lines):
        result.extend(early.get(index, ()))
        if index not in moved:
            result.append(line)
    return result, len(moved)


def lend_zeroed_inputs(lines: list[str]) -> tuple[list[str], dict[str, int]]:
    """Color exact live intervals while fixing the named input and output locations."""
    proof = ScratchProof(22)
    active = dict.fromkeys(range(22), 0)
    intervals: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for index, line in enumerate(lines):
        parts = line.split()
        if not parts or parts[0] in HEADER:
            continue
        touched = {int(wire) for wire in QUBIT.findall(line)}
        for wire in touched:
            active.setdefault(wire, index)
        proof.step(parts)
        for wire in touched:
            if proof.values[f"q{wire}"] == 0:
                intervals[wire].append((active.pop(wire), index))
    for wire, first in active.items():
        intervals[wire].append((first, len(lines)))
    for wire in range(22):
        if intervals[wire][-1][1] < len(lines):
            intervals[wire].append((len(lines), len(lines)))

    occupied: dict[int, list[tuple[int, int]]] = defaultdict(list)
    labels: dict[tuple[int, int, int], int] = {}
    for wire in range(22):
        for first, last in sorted({intervals[wire][0], intervals[wire][-1]}):
            occupied[wire].append((first, last))
            labels[wire, first, last] = wire
    ordered = sorted((first, last, wire) for wire, spans in intervals.items() for first, last in spans)
    for first, last, wire in ordered:
        if (wire, first, last) in labels:
            continue
        label = 0
        while True:
            spans = occupied[label]
            point = bisect_left(spans, (first, -1))
            if (point == 0 or spans[point - 1][1] < first) and (point == len(spans) or spans[point][0] > last):
                spans.insert(point, (first, last))
                labels[wire, first, last] = label
                break
            label += 1

    result = []
    for index, line in enumerate(lines):
        parts = line.split()
        if not parts or parts[0] in HEADER:
            result.append(line)
            continue

        def label_for(match: re.Match[str]) -> str:
            wire = int(match[1])
            spans = intervals[wire]
            first, last = spans[bisect_right(spans, (index, len(lines))) - 1]
            assert first <= index <= last
            return f"q{labels[wire, first, last]}"

        result.append(QUBIT.sub(label_for, line))
    events: Counter[int] = Counter()
    for first, last, _ in ordered:
        events[first] += 1
        events[last + 1] -= 1
    live = peak = 0
    for index in sorted(events):
        live += events[index]
        peak = max(peak, live)
    return result, {"lent_input_segments": sum(wire < 22 and wire != label
                                              for (wire, _, _), label in labels.items()),
                    "interval_peak": peak, "width": max(labels.values()) + 1}


def reuse(lines: list[str], *, symbolic: bool = False, prune: bool = False,
          share_products: bool = False) -> tuple[list[str], dict[str, int]]:
    registers = [line.split() for line in lines if line.startswith("REGISTER ")]
    members = [line.split()[1:] for line in lines if line.startswith("APPEND_TO_REGISTER ")]
    if len(registers) != 1 or len(registers[0]) != 3 or registers[0][-1] != '"x"':
        raise ValueError("Expected exactly one inverse-square-root register")
    if members != [[f"q{index}", registers[0][1]] for index in range(22)]:
        raise ValueError("Expected the complete inverse-square-root input register")

    protected = range(22)
    assigned: dict[int, int] = {}
    free: list[int] = []
    events = []
    depth = 0
    width = len(protected)
    original_width = width
    resets = 0
    pruned = 0
    shared = 0
    proof = ScratchProof(width) if symbolic or prune or share_products else None

    def physical(match: re.Match[str]) -> str:
        nonlocal width, original_width
        wire = int(match[1])
        original_width = max(original_width, wire + 1)
        if wire in protected:
            return match[0]
        if wire not in assigned:
            if free:
                assigned[wire] = heapq.heappop(free)
            else:
                assigned[wire] = width
                width += 1
        return f"q{assigned[wire]}"

    for line in lines:
        parts = line.split()
        if not parts or parts[0] in HEADER:
            events.append(line)
            continue
        opcode = parts[0]
        if opcode == "PUSH_CONDITION":
            depth += 1
        elif opcode == "POP_CONDITION":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced KMX condition")
        replacement = proof.shared_product(parts, range(original_width)) if share_products and proof else None
        no_effect = proof.step(parts) if proof else False
        if prune and no_effect:
            original_width = max(original_width, max((int(wire) + 1 for wire in QUBIT.findall(line)), default=0))
            pruned += 1
            continue
        if replacement:
            original_width = max(original_width, *(int(wire) + 1 for wire in QUBIT.findall(line)))
            line = " ".join(replacement) + "\n"
            shared += 1
        events.append(QUBIT.sub(physical, line))
        if symbolic and proof:
            zeroed = [str(wire) for wire in assigned if proof.values[f"q{wire}"] == 0]
        elif opcode == "HMR" and depth == 0 and len(parts) == 3 and (match := QUBIT.fullmatch(parts[1])):
            zeroed = [match[1]]
        else:
            zeroed = []
        for value in zeroed:
            wire = int(value)
            if wire in assigned:
                heapq.heappush(free, assigned.pop(wire))
                resets += 1
    if depth != 0:
        raise ValueError("Unbalanced KMX condition")
    report = {"original_width": original_width, "width": width, "released_scratch_intervals": resets}
    if prune:
        report["pruned_identities"] = pruned
    if share_products:
        report["shared_product_replacements"] = shared
    return events, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "output", "receipt"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--symbolic", action="store_true")
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--early-reset", action="store_true")
    parser.add_argument("--share-products", action="store_true")
    parser.add_argument("--lend-input", action="store_true")
    args = parser.parse_args()
    digest = sha256(args.assembly)
    lines = args.assembly.read_text().splitlines(keepends=True)
    moved = 0
    if args.early_reset:
        lines, moved = advance_resets(lines)
    lines, report = reuse(lines, symbolic=args.symbolic, prune=args.prune, share_products=args.share_products)
    if args.lend_input:
        lines, lending = lend_zeroed_inputs(lines)
        report.update(lending)
    if args.early_reset:
        report["advanced_unconditional_resets"] = moved
    with args.output.open("x", newline="\n") as stream:
        stream.writelines(lines)
    write_json(args.receipt, {
        **report,
        "input_assembly_sha256": digest,
        "output_assembly_sha256": sha256(args.output),
        "classification": "symbolic_width_screen"
        if args.symbolic or args.prune or args.share_products or args.lend_input
        else "reset_delimited_width_screen",
    })


if __name__ == "__main__":
    main()
