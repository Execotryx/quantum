"""Test whether D4's root degree constraints identify reclaimable coefficient slots."""

import argparse
from pathlib import Path
from random import Random

from dqi_compact_layout import coefficient, forced_outer_pole, split_pair
from dqi_extraction_oracle import ExternalField, original_pair

from qcompile.dqi.decoder import _add, _multiply, decode
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json


def extend_map(matrix, fold, field: GF4096):
    q = [fold.kappa, 1, 1]
    h0 = _add(fold.first, q) if fold.collapse else fold.first
    h1 = [1] if fold.collapse else fold.second
    output = []
    for a, b in matrix:
        if fold.incoming_pole:
            a, b = b, a
        d = _add(_multiply(a, h0, field), b)
        output.append((_add(_multiply(a, q, field), _multiply(d, h1, field)), _multiply(d, q, field)))
    return output


def echelon(rows, indices, field: GF4096):
    matrix = [row[:] for row in rows]
    pivots = []
    for col in indices:
        rank = len(pivots)
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][col]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        scale = field.inv(matrix[rank][col])
        row = [field.mul(value, scale) for value in matrix[rank]]
        matrix[rank] = row
        for i, other in enumerate(matrix):
            if i != rank and other[col]:
                factor = other[col]
                matrix[i] = [value ^ field.mul(factor, v) for value, v in zip(other, row, strict=True)]
        pivots.append(col)
    return pivots, matrix


def inspect_case(errors: dict[int, int], field: GF4096) -> list[dict]:
    nodes = range(0, 34, 2)
    geometry = [field.mul(c, c) ^ c ^ 2048 for c in nodes for _ in range(2)]
    n, d = original_pair(errors, geometry, field)
    extension = ExternalField(field)
    matrix = [([1], [0]), ([0], [1])]
    output = []
    for group, node in enumerate(nodes):
        fold = split_pair(n, d, node, extension)
        n, d = fold.u, fold.v
        matrix = extend_map(matrix, fold, field)
        b = 35 - 2 * group
        capacities = b + 2, b
        if max(len(n) - capacities[0], len(d) - capacities[1]) > 0:
            raise ValueError("Witness exceeds the raw fold capacity")
        columns = [(bank, power) for bank, width in enumerate(capacities) for power in range(width)]
        values = [coefficient((n, d)[bank], power) for bank, power in columns]
        rows = []
        for target, row in enumerate(matrix):
            degree_limit = (35, 36)[target]
            max_length = max(len(poly) + width - 1 for poly, width in zip(row, capacities, strict=True))
            for power in range(degree_limit, max_length):
                equations = [coefficient(row[bank], power - index) if power >= index else 0 for bank, index in columns]
                if any(equations):
                    rows.append(equations)
        order = sorted(range(len(columns)), key=lambda i: (columns[i][1] - capacities[columns[i][0]], i), reverse=True)
        pivots, reduced = echelon(rows, order, field)
        # Validate exact recovery from the remaining words and root zeros.
        free = [i for i in range(len(columns)) if i not in pivots]
        recipes = []

        def from_top(index):
            bank, power = columns[index]
            return [bank, capacities[bank] - 1 - power]

        for pivot, row in zip(pivots, reduced[:len(pivots)], strict=True):
            recovered = 0
            terms = []
            for index in free:
                if row[index]:
                    recovered ^= field.mul(row[index], values[index])
                    terms.append([*from_top(index), row[index]])
            if recovered != values[pivot]:
                raise ValueError("Root degree equations failed to recover an omitted coefficient")
            recipes.append({"word": from_top(pivot), "terms": terms})
        output.append({
            "group": group,
            "capacity": capacities,
            "recovery": recipes,
            "incoming_pole": fold.incoming_pole,
            "collapse": fold.collapse,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("historical", type=Path)
    parser.add_argument("residual", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    field = GF4096()
    rng = Random(55022)
    fixtures = {}
    cases = {}
    for directory in (args.historical, args.residual):
        for path in sorted(directory.glob("s*/batch-*.json")):
            fixtures[f"{directory.name}/{path.parent.name}/{path.name}"] = sha256(path)
            batch = read_json(path)
            for shot in batch["shots"] + batch["controls"]:
                cases[f'{path.parent.name}/{shot["index"]}'] = decode(shot["syndrome"], field)
    for weight in (34, 35):
        for index in range(8):
            cases[f"forced-{weight}/{index}"] = forced_outer_pole(weight, rng, field)
            cases[f"regular-{weight}/{index}"] = {
                position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)
            }
    results = [{"case": name, "weight": len(errors), "boundaries": inspect_case(errors, field)}
               for name, errors in cases.items()]
    summary = []
    for group in range(17):
        boundaries = [case["boundaries"][group] for case in results]
        layouts = [set(tuple(row["word"]) for row in stage["recovery"]) for stage in boundaries]
        shared = sorted(set.intersection(*layouts))
        literal_zeros = sorted(set.intersection(*[
            {tuple(row["word"]) for row in stage["recovery"] if not row["terms"]} for stage in boundaries
        ]))
        summary.append({
            "group": group, "minimum_rank": min(map(len, layouts)), "maximum_rank": max(map(len, layouts)),
            "shared_words_from_top": shared, "always_zero_from_top": literal_zeros,
            "maximum_terms": max(sum(len(row["terms"]) for row in stage["recovery"]) for stage in boundaries),
        })
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)), "captures": fixtures, "summary": summary, "cases": results,
    })


if __name__ == "__main__":
    main()
