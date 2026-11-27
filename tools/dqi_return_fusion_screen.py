"""Screen paired CCX fusions in a pinned DQI return using an affine frame."""

import argparse
from collections import Counter
import lzma
from pathlib import Path

from qcompile.io import sha256, write_json


CONTROL = "b2da55202f6b574ee9af452f25f34772c2a0e90bfc5ce102129c0861faaf1fcf"
WIDTH = 900
IDENTITY = tuple(1 << i for i in range(WIDTH))


def screen(source: Path) -> dict:
    totals: Counter[str] = Counter()
    directions: Counter[int] = Counter()
    intersections: Counter[tuple[int, int]] = Counter()
    equal_planes: Counter[tuple[int, tuple[int, ...]]] = Counter()
    rows = list(IDENTITY)
    inverse = list(IDENTITY)
    previous: tuple[int, int, int] | None = None
    adjacent = 0
    without_previous = 0
    adjacent_savings = 0
    savings_without_previous = 0

    def boundary() -> None:
        nonlocal previous, adjacent, without_previous, adjacent_savings, savings_without_previous
        if not directions:
            return
        all_pairs = sum(directions.values()) // 2
        totals["unrestricted_pair_ceiling"] += all_pairs
        totals["same_direction_pair_ceiling"] += sum(count // 2 for count in directions.values())
        overlap: Counter[int] = Counter()
        for (direction, _), count in intersections.items():
            overlap[direction] += count // 2
        same_direction = sum(
            min(count // 2, overlap[direction]) for direction, count in directions.items()
        )
        plane_sizes: Counter[tuple[int, ...]] = Counter()
        largest_direction: dict[tuple[int, ...], int] = {}
        for (_, plane), count in equal_planes.items():
            plane_sizes[plane] += count
            largest_direction[plane] = max(largest_direction.get(plane, 0), count)
        fanout = sum(min(count // 2, count - largest_direction[plane])
                     for plane, count in plane_sizes.items())
        two_gate_savings = sum(count // 2 for count in equal_planes.values())
        totals["same_direction_rank_pair_ceiling"] += same_direction
        totals["different_direction_equal_plane_pair_ceiling"] += fanout
        totals["combined_gate_savings_ceiling"] += min(all_pairs, same_direction + fanout) + two_gate_savings
        totals["disjoint_adjacent_fusions"] += adjacent
        totals["adjacent_gate_savings"] += adjacent_savings
        totals["extra_savings_from_equal_planes_ceiling"] += two_gate_savings
        directions.clear()
        intersections.clear()
        equal_planes.clear()
        rows[:] = inverse[:] = IDENTITY
        previous = None
        adjacent = without_previous = 0
        adjacent_savings = savings_without_previous = 0

    with lzma.open(source, "rb") as operations:
        for line in operations:
            op, _, operands = line.rstrip().partition(b" ")
            if op == b"CCX" and b" if " not in operands:
                left, right, target = (int(wire[1:]) for wire in operands.split())
                u, v, direction = rows[left], rows[right], inverse[target]
                forms = {u, v, u ^ v}
                directions[direction] += 1
                for form in forms:
                    intersections[direction, form] += 1
                equal_planes[direction, tuple(sorted(forms))] += 1
                score = adjacent
                savings = adjacent_savings
                if previous is not None:
                    a, b, old_direction = previous
                    old_forms = {a, b, a ^ b}
                    same_plane = forms == old_forms
                    if same_plane or (direction == old_direction and forms & old_forms):
                        totals["adjacent_fusible_pairs"] += 1
                        score = max(score, without_previous + 1)
                        savings = max(savings, savings_without_previous + 1 + int(same_plane and direction == old_direction))
                adjacent, without_previous = score, adjacent
                adjacent_savings, savings_without_previous = savings, adjacent_savings
                previous = u, v, direction
                totals["unconditional_ccx"] += 1
            elif op in (b"X", b"CX", b"SWAP") and b" if " not in operands:
                if directions and op != b"X":
                    left, right = (int(wire[1:]) for wire in operands.split())
                    if op == b"CX":
                        rows[right] ^= rows[left]
                        inverse[left] ^= inverse[right]
                    else:
                        rows[left], rows[right] = rows[right], rows[left]
                        inverse[left], inverse[right] = inverse[right], inverse[left]
            else:
                boundary()
    boundary()
    return {key: totals[key] for key in ("unconditional_ccx", "unrestricted_pair_ceiling",
        "same_direction_pair_ceiling", "same_direction_rank_pair_ceiling", "adjacent_fusible_pairs",
        "disjoint_adjacent_fusions", "adjacent_gate_savings", "extra_savings_from_equal_planes_ceiling",
        "different_direction_equal_plane_pair_ceiling", "combined_gate_savings_ceiling")}


def run(source: Path, output: Path) -> None:
    if sha256(source) != CONTROL:
        raise ValueError("Unexpected DQI return source")
    result = screen(source)
    if (result["unconditional_ccx"], result["unrestricted_pair_ceiling"]) != (107045, 51524):
        raise ValueError("The returned gate census differs from the registered control")
    write_json(output, {"scope": "static bounds and adjacent algebraic opportunities; no emitted circuit",
        "source_sha256": CONTROL, "driver_sha256": sha256(Path(__file__)), **result})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
