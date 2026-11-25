"""Audit the compact D4 fold's degree and storage promises on exact rational inputs."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from random import Random

from dqi_extraction_oracle import ExternalField, doubled_node_fixtures, node_polynomial, original_pair

from qcompile.dqi.decoder import _add, _divide, _multiply, decode
from qcompile.dqi.double_node_pole import synthesize_pair
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json


@dataclass(frozen=True)
class Fold:
    first: list[int]
    second: list[int]
    u: list[int]
    v: list[int]
    kappa: int
    incoming_pole: bool
    collapse: bool

    @property
    def minimum_v_slots(self) -> int:
        """Minimum capacity for V with U using two additional slots."""
        return max(1, len(self.v), len(self.u) - (2 if self.collapse else 1))

    def join(self, pair: tuple[list[int], list[int]], field: GF4096):
        second = [1] if self.collapse else self.second
        n, d = synthesize_pair(pair, (self.first, second), self.kappa, False, field)
        if self.collapse:
            n = _add(n, _multiply([self.kappa, 1, 1], d, field))
        return (d, n) if self.incoming_pole else (n, d)


def split_pair(n: list[int], d: list[int], coordinate: int, extension: ExternalField) -> Fold:
    field = extension.base
    kappa = field.mul(coordinate, coordinate) ^ coordinate ^ 2048
    q = [kappa, 1, 1]
    node = coordinate | 4096
    incoming_pole = not extension.evaluate(d, node)
    if incoming_pole:
        n, d = d, n

    def split(numerator, denominator):
        pivot = extension.evaluate(denominator, node)
        if not pivot:
            raise ValueError("Both projective coordinates vanish at the active chart")
        value = extension.mul(extension.evaluate(numerator, node), extension.inv(pivot))
        first = (value & 4095) ^ field.mul(value >> 12, coordinate)
        head = [first, value >> 12]
        quotient, remainder = _divide(_add(numerator, _multiply(head, denominator, field)), q, field)
        if remainder != [0]:
            raise ValueError("Finite head failed to cancel at the active node")
        return head, quotient

    first, residual = split(n, d)
    collapse = not extension.evaluate(residual, node)
    if collapse:
        # At the local pole, F+q gives a unit second head. The same
        # substitution also represents exact first-head termination.
        residual = _add(residual, d)
    second, v = split(d, residual)
    if collapse and second != [1, 0]:
        raise ValueError("Collapsed chart did not obtain its unit pivot")
    return Fold(first, [0, 0] if collapse else second, residual, v, kappa, incoming_pole, collapse)


def reconstruct(tail, folds: list[Fold], field: GF4096):
    for fold in reversed(folds):
        tail = fold.join(tail, field)
    return tail


def coefficient(poly: list[int], power: int) -> int:
    return poly[power] if power < len(poly) else 0


def degree_envelope(folds: list[Fold]) -> tuple[int, int]:
    """Upper bounds from exact division by each quadratic in extraction."""
    n, d = 34, 35
    for fold in folds:
        if fold.incoming_pole:
            n, d = d, n
        if fold.collapse:
            n = max(n - 2, d)
            d = max(d, n) - 2
        else:
            n = max(n, d + 1) - 2
            d = max(d, n + 1) - 2
    return n, d


def recover_tail(jet: tuple[int, int, int], folds: list[Fold], field: GF4096):
    """Recover the mixed-chart tail using its jet and the root degree bounds."""
    n0, d0, derivative = jet
    if not (n0 or d0):
        raise ValueError("Both projective tail coordinates vanish at zero")
    bounds = degree_envelope(folds)
    unknowns = [(bank, power) for bank, bound in enumerate(bounds) for power in range(1, bound + 1)]
    columns = []
    for bank, power in unknowns:
        unit = [0] * power + [1]
        basis = (unit, [0]) if bank == 0 else ([0], unit)
        columns.append(reconstruct(basis, folds, field))
    columns.append(reconstruct(([n0], [d0]), folds, field))
    rows = [[*((d0, n0)[bank] if power == 1 else 0 for bank, power in unknowns), derivative]]
    for bank, limit in enumerate((35, 36)):
        polynomials = [pair[bank] for pair in columns]
        for power in range(limit, max(map(len, polynomials))):
            rows.append([coefficient(poly, power) for poly in polynomials])

    def solve(indices):
        restricted = [[*(row[column] for column in indices), row[-1]] for row in rows]
        rank = 0
        for column in range(len(indices)):
            pivot = next((index for index in range(rank, len(restricted)) if restricted[index][column]), None)
            if pivot is None:
                continue
            restricted[rank], restricted[pivot] = restricted[pivot], restricted[rank]
            scale = field.inv(restricted[rank][column])
            reduced_pivot = [field.mul(value, scale) for value in restricted[rank]]
            restricted[rank] = reduced_pivot
            for index, row in enumerate(restricted):
                if index == rank:
                    continue
                factor = row[column]
                row[:] = [value ^ field.mul(factor, pivot_value)
                          for value, pivot_value in zip(row, reduced_pivot, strict=True)]
            rank += 1
        if any(row[-1] for row in restricted[rank:]) or rank != len(indices):
            return rank, None
        recovered = [n0], [d0]
        for index, row in zip(indices, restricted[:rank], strict=True):
            recovered[unknowns[index][0]].append(row[-1])
        return rank, recovered

    linear = ([n0, field.div(derivative, d0)], [d0]) if d0 else ([n0], [0, field.div(derivative, n0)])
    linear_root = reconstruct(linear, folds, field)
    indices = list(range(len(unknowns)))
    if len(linear_root[0]) <= 35 and len(linear_root[1]) <= 36:
        rank, _ = solve(indices)
        return linear, rank, "linear"
    quadratic = [index for index, (bank, power) in enumerate(unknowns) if power <= (2, 1)[bank]]
    if quadratic != indices:
        rank, recovered = solve(quadratic)
        if recovered is not None:
            return recovered, rank, "quadratic"
    rank, recovered = solve(indices)
    if recovered is None:
        raise ValueError("No uniquely recovered nonlinear tail satisfies the constraints")
    return recovered, rank, "full_rank"


def audit_tail(tail: tuple[list[int], list[int]], folds: list[Fold], field: GF4096) -> dict:
    n, d = tail
    bounds = degree_envelope(folds)
    if any(len(poly) - 1 > bound for poly, bound in zip(tail, bounds, strict=True)):
        raise ValueError("Tail lies outside the chart degree envelope")
    jet = n[0], d[0], field.mul(d[0], coefficient(n, 1)) ^ field.mul(n[0], coefficient(d, 1))
    recovered, rank, branch = recover_tail(jet, folds, field)
    if reconstruct(recovered, folds, field) != reconstruct(tail, folds, field):
        raise ValueError("Tail recovered from the jet does not reproduce the original pair")
    return {
        "rank": rank,
        "branch": branch,
        "degree_bounds": bounds,
    }


def forced_outer_pole(weight: int, rng: Random, field: GF4096) -> dict[int, int]:
    """Use two free error symbols to force the first node's local pole."""
    extension = ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    geometry = node_polynomial(kappas, field)
    positions = rng.sample(range(4095), weight)
    rows = []
    for position in positions:
        root = field.exp[position]
        residue = field.mul(root, field.evaluate(geometry, root))
        inverse = extension.inv(4096 ^ root)
        value = extension.mul(residue, inverse)
        term = extension.mul(value, inverse) ^ (value >> 12)
        rows.append((term & 4095, term >> 12))
    for index in range(1, len(rows)):
        a, c = rows[0]
        b, d = rows[index]
        determinant = field.mul(a, d) ^ field.mul(b, c)
        if determinant:
            break
    else:
        raise ValueError("Forced pole fixture has no independent symbol columns")
    values = [rng.randrange(1, 4096) for _ in positions]
    x = y = 0
    for column, ((lo, hi), value) in enumerate(zip(rows, values, strict=True)):
        if column not in (0, index):
            x ^= field.mul(lo, value)
            y ^= field.mul(hi, value)
    values[0] = field.div(field.mul(d, x) ^ field.mul(b, y), determinant)
    values[index] = field.div(field.mul(c, x) ^ field.mul(a, y), determinant)
    if not all(values):
        raise ValueError("Forced pole fixture lost weight")
    return dict(zip(positions, values, strict=True))


def audit_input(errors: dict[int, int], field: GF4096, *, emit_folds=False) -> dict:
    extension = ExternalField(field)
    coordinates = range(0, 34, 2)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in coordinates for _ in range(2)]
    original = original_pair(errors, kappas, field)
    n, d = original
    folds = []
    for coordinate in coordinates:
        fold = split_pair(n, d, coordinate, extension)
        if fold.join((fold.u, fold.v), field) != (n, d):
            raise ValueError("Finite chart did not invert exactly")
        folds.append(fold)
        n, d = fold.u, fold.v
        if d == [0]:
            # Further nodes would require an explicit inactive circuit
            # chart. Measure the active prefix separately.
            break
    tail = n, d
    b = max(fold.minimum_v_slots - 2 * depth for depth, fold in enumerate(reversed(folds)))
    if reconstruct(tail, folds, field) != original:
        raise ValueError("Complete reconstruction changed the input rational function")
    tail_result = None
    if d != [0]:
        try:
            tail_result = audit_tail(tail, folds, field)
        except ValueError as error:
            tail_result = {"error": str(error)}
    return {
        "weight": len(errors), "pairs": len(folds), "tail_lengths": list(map(len, tail)),
        "incoming_poles": [index for index, fold in enumerate(folds) if fold.incoming_pole],
        "local_poles": [index for index, fold in enumerate(folds) if fold.collapse and fold.v != [0]],
        "terminal_pair": folds[-1].v == [0],
        "nonterminal_tail": tail_result,
        "minimum_tail_v_slots": b,
        "minimum_root_polynomial_slots": 2 * b + 2 + 4 * len(folds),
        **({"folds": [
            {
                "u": fold.u, "v": fold.v, "heads": [fold.first, fold.second], "incoming_pole": fold.incoming_pole,
                "collapse": fold.collapse, "minimum_v_slots": fold.minimum_v_slots,
            }
            for fold in folds
        ]} if emit_folds else {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("historical", type=Path)
    parser.add_argument("residual", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    field = GF4096()
    captures = {}
    records = []
    for label, directory in (("historical", args.historical), ("residual", args.residual)):
        for path in sorted(directory.glob("s*/batch-*.json")):
            captures[f"{label}/{path.parent.name}/{path.name}"] = sha256(path)
            batch = read_json(path)
            for shot in batch["shots"] + batch["controls"]:
                observations = audit_input(decode(shot["syndrome"], field), field, emit_folds=True)
                records.append({"origin": label, "draw": path.parent.name, "shot": shot["index"], **observations})
    for row in doubled_node_fixtures():
        fixture = dict(zip(row["error_positions"], row["error_values"], strict=True))
        records.append({"origin": "constructed", "group": row["group"], **audit_input(fixture, field)})
    rng = Random(84112)
    for weight in range(36):
        for _ in range(4):
            errors = {position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)}
            records.append({"origin": "deterministic", **audit_input(errors, field)})
    for weight in (34, 35):
        for _ in range(2):
            errors = forced_outer_pole(weight, rng, field)
            measured = audit_input(errors, field, emit_folds=True)
            if 0 not in measured["local_poles"]:
                raise ValueError("Constructed full-weight second-head pole did not reproduce")
            records.append({"origin": "forced_outer_pole", "support": errors, **measured})
    write_json(args.output, {"driver_sha256": sha256(Path(__file__)), "captures": captures, "cases": records})


if __name__ == "__main__":
    main()
