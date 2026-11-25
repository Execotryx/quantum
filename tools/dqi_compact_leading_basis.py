"""Recover the reduced D4 change of basis from leading coefficient queries."""

import argparse
from collections import defaultdict
from pathlib import Path
from random import Random

from dqi_compact_constraints import extend_map
from dqi_compact_layout import forced_outer_pole
from dqi_compact_tail_basis import chart_matrix, leading, reduced_root_basis
from dqi_extraction_oracle import original_pair

from qcompile.dqi.decoder import _add, _multiply, decode
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json


def leading_queries(folds, field: GF4096, *, end_queries=None):
    identity = [([1], [0]), ([0], [1])]
    factors = [extend_map(identity, fold, field) for fold in folds]
    bounds = [[[0, -1], [-1, 0]]]
    for matrix in factors:
        bounds.append([
            [max(
                (bounds[-1][row][i] + len(matrix[i][col]) - 1 for i in range(2)
                 if bounds[-1][row][i] >= 0 and matrix[i][col] != [0]),
                default=-1,
            ) for col in range(2)]
            for row in range(2)
        ])
    values = {}
    requested = defaultdict(set)

    def at(step, row, col, power):
        if power < 0 or power > bounds[step][row][col]:
            return 0
        key = step, row, col, power
        if key in values:
            return values[key]
        requested[step].add((row, col, power))
        value = int(row == col and power == 0) if step == 0 else 0
        if step:
            for i, entries in enumerate(factors[step - 1]):
                for shift, factor in enumerate(entries[col]):
                    if factor:
                        value ^= field.mul(factor, at(step - 1, row, i, power - shift))
        values[key] = value
        return value

    change = [([1], [0]), ([0], [1])]
    last = len(factors)

    def top(column):
        bound = max(
            bounds[last][row][i] + len(poly) - 1 + (row == 0)
            for row in range(2) for i, poly in enumerate(column)
            if bounds[last][row][i] >= 0 and poly != [0]
        )
        for degree in reversed(range(bound + 1)):
            for row in (1, 0):
                value = 0
                for i, poly in enumerate(column):
                    for shift, factor in enumerate(poly):
                        if factor:
                            value ^= field.mul(factor, at(last, row, i, degree - (row == 0) - shift))
                if value:
                    return (degree, row), value
        raise ValueError("Leading query found a zero module column")

    tops = list(map(top, change))
    count = 0
    while tops[0][0][1] == tops[1][0][1]:
        small, large = (0, 1) if tops[0][0] <= tops[1][0] else (1, 0)
        shift = tops[large][0][0] - tops[small][0][0]
        factor = field.div(tops[large][1], tops[small][1])
        polynomial = [0] * shift + [factor]
        a, b = change[large]
        c, d = change[small]
        change[large] = _add(a, _multiply(polynomial, c, field)), _add(b, _multiply(polynomial, d, field))
        former = tops[large][0]
        tops[large] = top(change[large])
        if tops[large][0] >= former:
            raise ValueError("Leading query did not reduce the column")
        count += 1
    order = sorted(range(2), key=lambda index: tops[index][0])
    widths = [len(requested[step]) for step in range(last + 1)]
    if end_queries is not None:
        end_queries.update(requested[last])
    return [change[index] for index in order], [tops[index][0] for index in order], count, widths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("historical", "residual", "multiple_poles", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    field = GF4096()
    inputs = {}
    captures = {}
    for directory in (args.historical, args.residual):
        for path in sorted(directory.glob("s*/batch-*.json")):
            captures[f"{directory.name}/{path.parent.name}/{path.name}"] = sha256(path)
            batch = read_json(path)
            for shot in batch["shots"] + batch["controls"]:
                inputs[f'{path.parent.name}/{shot["index"]}'] = decode(shot["syndrome"], field)
    for index, case in enumerate(read_json(args.multiple_poles)["cases"], 1):
        inputs[f"multiple/{index}"] = {int(position): symbol for position, symbol in case["support"].items()}
    rng = Random(8935)
    for weight in range(36):
        inputs[f"sample/{weight}"] = {position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)}
    for weight in (34, 35):
        inputs[f"forced/{weight}"] = forced_outer_pole(weight, rng, field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    rows = []
    for name, support in inputs.items():
        _, folds, matrix = chart_matrix(original_pair(support, kappas, field), field)
        root, expected, cancellations = reduced_root_basis(matrix, field)
        change, tops, count, requested = leading_queries(folds, field)
        if (change, tops, count) != (expected, list(map(leading, root)), cancellations):
            raise ValueError("Leading-only reduction disagrees with explicit polynomial columns")
        rows.append({"case": name, "weight": len(support), "requested_by_step": requested,
                     "peak_coefficients": max(requested), "cancellations": count})
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)), "captures": captures,
        "multiple_poles_sha256": sha256(args.multiple_poles), "cases": rows,
    })


if __name__ == "__main__":
    main()
