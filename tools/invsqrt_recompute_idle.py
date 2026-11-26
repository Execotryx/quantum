"""Screen and emit nonoverlapping nonlinear recomputations in the pinned incumbent."""

import argparse
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from invsqrt_phase_margin import CONTROL
from invsqrt_reset_reuse import HEADER, QUBIT, advance_resets, lend_zeroed_inputs, reuse
from qcompile.invsqrt.scratch import ScratchProof
from qcompile.io import sha256, write_json


# One extra cost unit buys one Toffoli. At 32 wires this favorable
# budget assumes the current rotation charge and no other changes.
BUDGET = 46
Expression = tuple[int, int, int]
Basis = dict[int, tuple[int, int]]


def bits(mask: int):
    while mask:
        bit = mask & -mask
        yield bit
        mask ^= bit


def eliminate(value: int, basis: Basis) -> tuple[int, int]:
    expression = 0
    while value:
        pivot = basis.get(value.bit_length())
        if pivot is None:
            break
        term, representation = pivot
        value ^= term
        expression ^= representation
    return value, expression


def express(values: tuple[int, ...], target: int, products: dict[int, tuple[int, ...]]) -> Expression | None:
    basis: Basis = {1: (1, 1)}
    for wire, value in enumerate(values):
        if wire != target:
            residual, expression = eliminate(value, basis)
            if residual:
                basis[residual.bit_length()] = residual, expression ^ (2 << wire)
    value = values[target]
    residual, affine = eliminate(value, basis)
    if not residual:
        return affine, 0, 0
    for atom in bits(value):
        if atom not in products:
            continue
        left, right = products[atom]
        left_error, a = eliminate(left, basis)
        right_error, b = eliminate(right, basis)
        remainder, affine = eliminate(value ^ atom, basis)
        if not (left_error or right_error or remainder) and a & ~1 and b & ~1 and (a ^ b) & ~1:
            return affine, a, b
    return None


def toggle(expression: Expression, target: int) -> list[str]:
    def affine_gates(mask: int, output: int) -> list[str]:
        gates = [f"X q{output}\n"] if mask & 1 else []
        gates.extend(f"CX q{bit.bit_length() - 2} q{output}\n" for bit in bits(mask & ~1))
        return gates

    remainder, a, b = expression
    if not a:
        return affine_gates(remainder, target)
    # The left pivot never appears in the right factor. Compute left before
    # modifying the right pivot, then reverse both frames after the CCX.
    if not (a & ~b & ~1):
        a, b = b, a
    left_bit = next(bits(a & ~b & ~1))
    right_bit = next(bits(b & ~1))
    left, right = left_bit.bit_length() - 2, right_bit.bit_length() - 2
    frame = affine_gates(a ^ left_bit, left) + affine_gates(b ^ right_bit, right)
    return [*frame, f"CCX q{left} q{right} q{target}\n", *reversed(frame), *affine_gates(remainder, target)]


@dataclass(frozen=True)
class Gap:
    wire: int
    start: int
    end: int
    covers: int
    erase: Expression
    restore: Expression

    @property
    def cost(self) -> int:
        return int(bool(self.erase[1])) + int(bool(self.restore[1]))


def screen(lines: list[str]) -> tuple[set[int], int, list[Gap]]:
    proof = ScratchProof(22)
    depth = 0
    boundaries = []
    states = []
    peaks = set()
    uses: dict[int, list[int]] = defaultdict(list)
    for i, line in enumerate(lines):
        parts = line.split()
        boundaries.append(depth == 0)
        state = tuple(proof.values[f"q{wire}"] for wire in range(39))
        states.append(state)
        if not parts or parts[0] in HEADER:
            continue
        touched = set(map(int, QUBIT.findall(line)))
        for wire in touched:
            uses[wire].append(i)
        if len(touched | {wire for wire, value in enumerate(state) if value}) == 39:
            peaks.add(i)
        proof.step(parts)
        depth += (parts[0] == "PUSH_CONDITION") - (parts[0] == "POP_CONDITION")

    products = {atom: factors for factors, atom in proof.products.items() if len(factors) == 2}
    gaps = []
    inspected = 0
    for wire, times in uses.items():
        for previous, end in pairwise(times):
            start = previous + 1
            covers = len(peaks.intersection(range(start, end)))
            if end - start < 8 or not covers or not states[start][wire] or not (boundaries[start] and boundaries[end]):
                continue
            inspected += 1
            erase = express(states[start], wire, products)
            if erase is not None and (restore := express(states[end], wire, products)) is not None:
                gaps.append(Gap(wire, start, end, covers, erase, restore))
    return peaks, inspected, gaps


def choose(gaps: list[Gap], budget: int) -> tuple[Gap, ...]:
    """Maximize covered source sites with disjoint idle windows at a fixed cost."""
    ordered = sorted(gaps, key=lambda gap: gap.end)
    ends = [gap.end for gap in ordered]
    choices: list[list[tuple[int, tuple[Gap, ...]]]] = [[(0, ()) for _ in range(budget + 1)]]
    for i, gap in enumerate(ordered):
        prior = bisect_right(ends, gap.start, hi=i)
        row = choices[-1].copy()
        for cap in range(gap.cost, budget + 1):
            score, selected = choices[prior][cap - gap.cost]
            if score + gap.covers > row[cap][0]:
                row[cap] = score + gap.covers, (*selected, gap)
        choices.append(row)
    return choices[-1][-1][1]


def run(control: Path, output: Path) -> None:
    if sha256(control) != CONTROL:
        raise ValueError("The assembly differs from its pinned identity")
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"scope": "development idle-wire recomputation", "source_sha256": CONTROL,
                              "driver_sha256": sha256(Path(__file__)), "extra_toffoli_budget": BUDGET,
                              "minimum_idle_instructions": 8, "shots_per_x": 1, "batch_size": 292,
                              "salts": {"control": "idle-recompute-control-20261127-dev",
                                        "recompute": "idle-recompute-20261127-dev"}})
    lines = control.read_text(encoding="ascii").splitlines(keepends=True)
    scheduled, _ = advance_resets(lines)
    peaks, inspected, gaps = screen(scheduled)
    selected = choose(gaps, BUDGET)
    edits: dict[int, list[str]] = defaultdict(list)
    for gap in selected:
        edits[gap.start].extend(toggle(gap.erase, gap.wire))
        edits[gap.end].extend(toggle(gap.restore, gap.wire))
    adjusted = [gate for i, line in enumerate(scheduled) for gate in (*edits.get(i, []), line)]
    emitted = {}
    for name, original in (("control", scheduled), ("recompute", adjusted)):
        normalized, _ = reuse(original, symbolic=True, prune=True)
        compact, width = lend_zeroed_inputs(normalized)
        path = output / f"{name}.kmx"
        path.write_text("".join(compact), encoding="ascii", newline="\n")
        emitted[name] = {"assembly_sha256": sha256(path), **width}
    eligible_sites = {i for gap in gaps for i in range(gap.start, gap.end) if i in peaks}
    write_json(output / "screen.json", {"registration_sha256": sha256(registration),
        "symbolic_peak_sites": len(peaks), "gaps_inspected": inspected, "gaps_with_endpoint_identities": len(gaps),
        "sites_in_any_eligible_gap": len(eligible_sites), "sites_in_selected_gaps": sum(g.covers for g in selected),
        "selected_signed_toffoli_charge": sum(g.cost for g in selected), "emitted": emitted,
        "selection": [{"wire": g.wire, "clear_before_line": g.start + 1, "restore_before_line": g.end + 1,
                        "covers": g.covers, "extra_toffolis": g.cost} for g in selected]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
