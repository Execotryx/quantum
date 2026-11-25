"""Recover D4's degree-constrained rational pair using tail basis coordinates."""

import argparse
from pathlib import Path
from random import Random

from dqi_compact_constraints import echelon, extend_map
from dqi_compact_layout import coefficient, degree_envelope, forced_outer_pole, reconstruct, split_pair
from dqi_extraction_oracle import ExternalField, original_pair

from qcompile.dqi.decoder import _add, _divide, _multiply, _trim, decode
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json


def basis_from_constraints(rows, width: int, field: GF4096) -> tuple[list[int], list[list[int]]]:
    """Return free slots and one exact kernel column per free slot."""
    pivots, reduced = echelon(rows, range(width), field)
    free = [index for index in range(width) if index not in pivots]
    basis = []
    for slot in free:
        vector = [0] * width
        vector[slot] = 1
        for pivot, row in zip(pivots, reduced, strict=False):
            vector[pivot] = row[slot]
        basis.append(vector)
    return free, basis


def leading(pair) -> tuple[int, int]:
    """Rank root pairs by degree, with one extra weight on the numerator."""
    lead = max((len(word) - 1 + (bank == 0), bank)
               for bank, word in enumerate(pair) if word != [0])
    return lead


def reduced_root_basis(matrix, field: GF4096):
    """Cancel same-position leading terms and retain the change of tail basis."""
    root = [tuple(column) for column in zip(*matrix, strict=True)]
    change = [([1], [0]), ([0], [1])]
    steps = 0
    while True:
        left, right = map(leading, root)
        if left[1] != right[1]:
            break
        small, large = (0, 1) if left <= right else (1, 0)
        before = leading(root[large])
        slot = before[1]
        shift = before[0] - leading(root[small])[0]
        factor = field.div(root[large][slot][-1], root[small][slot][-1])
        polynomial = [0] * shift + [factor]
        for family in (root, change):
            a, b = family[large]
            c, d = family[small]
            family[large] = (
                _add(a, _multiply(polynomial, c, field)),
                _add(b, _multiply(polynomial, d, field)),
            )
        if leading(root[large]) >= before:
            raise ValueError("Polynomial basis reduction did not decrease the leading term")
        steps += 1
    order = sorted(range(2), key=lambda index: leading(root[index]))
    return [root[index] for index in order], [change[index] for index in order], steps


def jet_equations(root, change, n0: int, d0: int, slope: int, field: GF4096):
    """Express the tail jet in the admissible reduced root coordinates."""
    columns = [
        (index, power)
        for index, column in enumerate(root)
        for power in range(36 - leading(column)[0])
    ]
    rows = [[], [], []]
    for index, power in columns:
        n, d = change[index]
        rows[0].append(coefficient(n, 0) if power == 0 else 0)
        rows[1].append(coefficient(d, 0) if power == 0 else 0)
        n1 = coefficient(n, 1 - power) if power <= 1 else 0
        d1 = coefficient(d, 1 - power) if power <= 1 else 0
        rows[2].append(field.mul(d0, n1) ^ field.mul(n0, d1))
    for row, target in zip(rows, (n0, d0, slope), strict=True):
        row.append(target)
    return columns, rows


def assemble_root(root, columns, values, field: GF4096):
    n, d = [0], [0]
    for (index, power), value in zip(columns, values, strict=True):
        polynomial = [0] * power + [value]
        n = _add(n, _multiply(polynomial, root[index][0], field))
        d = _add(d, _multiply(polynomial, root[index][1], field))
    return n, d


def recover_from_basis(root, change, n0: int, d0: int, slope: int, field: GF4096):
    columns, rows = jet_equations(root, change, n0, d0, slope, field)
    pivots, reduced = echelon(rows, range(len(columns)), field)
    if any(row[-1] for row in reduced[len(pivots):]):
        raise ValueError("Reduced root basis contradicts the tail jet")
    values = [0] * len(columns)
    for pivot, row in zip(pivots, reduced, strict=False):
        values[pivot] = row[-1]
    return assemble_root(root, columns, values, field), len(columns), len(pivots)


def interpolate_reduced(reference, field: GF4096):
    """Apply the original syndrome's value and derivative constraints online."""
    n, d = reference
    extension = ExternalField(field)
    columns = [([1], [0]), ([0], [1])]
    cancellations = 0
    peak_slots = 4

    def derivative(poly):
        return [value if power % 2 else 0 for power, value in enumerate(poly[1:], 1)] or [0]

    def impose(discrepancies, q, coordinates):
        nonlocal columns, cancellations, peak_slots
        arithmetic, coordinate = coordinates
        pivot = min((index for index in range(2) if discrepancies[index]),
                    key=lambda index: leading(columns[index]), default=None)
        if pivot is None:
            raise ValueError("Interpolation lost an independent constraint")
        other = 1 - pivot
        value = arithmetic.mul(discrepancies[other], arithmetic.inv(discrepancies[pivot]))
        if coordinate is None:
            head = [value]
        else:
            head = [(value & 4095) ^ field.mul(coordinate, value >> 12), value >> 12]
        a, b = columns[pivot]
        c, d = columns[other]
        columns[other] = _add(c, _multiply(head, a, field)), _add(d, _multiply(head, b, field))
        columns[pivot] = _multiply(q, a, field), _multiply(q, b, field)
        peak_slots = max(peak_slots, sum(len(poly) for column in columns for poly in column))
        columns, _, reduced = reduced_root_basis(list(zip(*columns, strict=True)), field)
        cancellations += reduced

    for coordinate in (*range(0, 34, 2), None):
        if coordinate is None:
            arithmetic, node, q = field, 0, [0, 1]
        else:
            arithmetic, node = extension, coordinate | 4096
            q = [field.mul(coordinate, coordinate) ^ coordinate ^ 2048, 1, 1]
        evaluate = arithmetic.evaluate
        inverse = arithmetic.inv(evaluate(d, node))
        value = arithmetic.mul(evaluate(n, node), inverse)
        slope = arithmetic.mul(
            evaluate(derivative(n), node) ^ arithmetic.mul(value, evaluate(derivative(d), node)), inverse,
        )
        impose([evaluate(a, node) ^ arithmetic.mul(value, evaluate(b, node)) for a, b in columns],
               q, (arithmetic, coordinate))
        impose([
            evaluate(derivative(a), node)
            ^ arithmetic.mul(value, evaluate(derivative(b), node))
            ^ arithmetic.mul(slope, evaluate(b, node))
            for a, b in columns
        ], q, (arithmetic, coordinate))
    chosen = min(columns, key=leading)
    if leading(chosen)[0] > 35 or primitive_pair(chosen, field) != reference:
        raise ValueError("Online rational interpolation did not recover the primitive root")
    return {"cancellations": cancellations, "peak_explicit_coefficients": peak_slots,
            "shifted_degrees": [leading(column)[0] for column in columns]}


def primitive_pair(pair, field: GF4096):
    """Remove common factors and choose a monic denominator."""
    n, d = pair
    if d == [0]:
        raise ValueError("Root denominator vanished")
    a, b = n, d
    while b != [0]:
        a, b = b, _divide(a, b, field)[1]
    n, r = _divide(n, a, field)
    d, s = _divide(d, a, field)
    if r != [0] or s != [0]:
        raise ValueError("Common divisor did not divide both polynomials")
    scale = field.inv(d[-1])
    return [field.mul(value, scale) for value in n], [field.mul(value, scale) for value in d]


def chart_matrix(reference, field: GF4096):
    n, d = reference
    extension = ExternalField(field)
    matrix = [([1], [0]), ([0], [1])]
    folds = []
    for c in range(0, 34, 2):
        fold = split_pair(n, d, c, extension)
        folds.append(fold)
        n, d = fold.u, fold.v
        matrix = extend_map(matrix, fold, field)
    return (n, d), folds, matrix


def inspect(support: dict[int, int], field: GF4096) -> dict:
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    reference = original_pair(support, kappas, field)
    (n, d), folds, matrix = chart_matrix(reference, field)
    capacities = tuple(max(1, bound + 1) for bound in degree_envelope(folds))
    slots = [(bank, power) for bank, width in enumerate(capacities) for power in range(width)]
    constraints = []
    for target, row in enumerate(matrix):
        limit = (35, 36)[target]
        stop = max(len(poly) + width - 1 for poly, width in zip(row, capacities, strict=True))
        for power in range(limit, stop):
            equation = [coefficient(row[bank], power - pos) if power >= pos else 0 for bank, pos in slots]
            if any(equation):
                constraints.append(equation)
    free, basis = basis_from_constraints(constraints, len(slots), field)
    if not basis:
        raise ValueError("Degree constraints have no nonzero tail")
    n0, d0 = n[0], d[0]
    slope = field.mul(d0, coefficient(n, 1)) ^ field.mul(n0, coefficient(d, 1))
    split = capacities[0]
    jet_rows = [
        [vector[0] for vector in basis] + [n0],
        [vector[split] for vector in basis] + [d0],
        [
            field.mul(d0, vector[1] if split > 1 else 0)
            ^ field.mul(n0, vector[split + 1] if capacities[1] > 1 else 0)
            for vector in basis
        ] + [slope],
    ]
    pivots, reduced = echelon(jet_rows, range(len(basis)), field)
    if any(row[-1] for row in reduced[len(pivots):]):
        raise ValueError("Tail jet contradicts the degree constraints")
    # The jet can leave common-factor freedom. Use a particular solution
    # and independently recover its primitive root pair.
    recovered = [0] * len(slots)
    for pivot, row in zip(pivots, reduced, strict=False):
        for index, value in enumerate(basis[pivot]):
            recovered[index] ^= field.mul(value, row[-1])
    chosen = _trim(recovered[:split]), _trim(recovered[split:])
    root = reconstruct(chosen, folds, field)
    if len(root[0]) > 35 or len(root[1]) > 36 or primitive_pair(root, field) != reference:
        raise ValueError("Recovered tail basis changed the primitive rational function")
    marked, change, steps = reduced_root_basis(matrix, field)
    assembled, dimension, rank = recover_from_basis(marked, change, n0, d0, slope, field)
    expected_dimension = max(3, 36 - len(support))
    if dimension != len(basis) or dimension != expected_dimension or rank != len(pivots):
        raise ValueError("Polynomial and coefficient bases disagree on dimension or jet rank")
    if primitive_pair(assembled, field) != reference:
        raise ValueError("Reduced polynomial basis reconstructed the wrong rational function")
    return {
        "weight": len(support),
        "tail_envelope": capacities,
        "tail_actual_lengths": [len(n), len(d)],
        "degree_rank": len(slots) - len(basis),
        "basis_dimension": len(basis),
        "free_slots": [slots[index] for index in free],
        "jet_rank": len(pivots),
        "needs_common_factor_reduction": root != reference,
        "reduced_basis": {
            "shifted_degrees": [leading(column)[0] for column in marked],
            "cancellations": steps,
            "needs_common_factor_reduction": assembled != reference,
        },
        "online_interpolation": interpolate_reduced(reference, field),
        "root_sha256": identity(root),
    }


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
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)), "captures": captures,
        "multiple_poles_sha256": sha256(args.multiple_poles),
        "cases": [{"case": name, **inspect(support, field)} for name, support in inputs.items()],
    })


if __name__ == "__main__":
    main()
