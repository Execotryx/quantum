"""Construct exact weight-35 D4 inputs with several genuine local poles."""

import argparse
from pathlib import Path
from random import Random

from dqi_compact_constraints import echelon
from dqi_compact_layout import audit_input, coefficient
from dqi_extraction_oracle import node_polynomial, original_pair

from qcompile.dqi.decoder import _add, _divide, _multiply, decode, syndrome
from qcompile.dqi.field import GF4096
from qcompile.io import sha256, write_json


def forced_sequence(
    field: GF4096, collapse: tuple[bool, ...], *, seed: int = 89342,
    heads: tuple[tuple[tuple[int, int], tuple[int, int]], ...] | None = None,
) -> dict[int, int]:
    rng = Random(seed)
    nodes = range(0, 34, 2)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in nodes for _ in range(2)]
    factors = [[kappas[2 * group], 1, 1] for group in range(len(collapse))]
    squares = [_multiply(q, q, field) for q in factors]
    positions = rng.sample(range(4095), 35)
    _, denominator = original_pair(dict.fromkeys(positions, 0), kappas, field)
    geometry = node_polynomial(kappas, field)
    head_pairs = (((0, 1), (0, 1)),) * len(collapse) if heads is None else heads

    def coordinates(n, d):
        entries = []
        for q, square, local_pole, pair in zip(factors, squares, collapse, head_pairs, strict=True):
            first, second = pair
            residual = _add(n, _multiply(list(first), d, field))
            qd = _multiply(q, d, field)
            if local_pole:
                constraint = residual
                residual = _add(residual, qd)
                next_d = _add(qd, residual)
            else:
                next_d = _add(qd, _multiply(list(second), residual, field))
                constraint = next_d
            _, remainder = _divide(constraint, square, field)
            entries.extend(coefficient(remainder, i) for i in range(4))
            n, d = _multiply(q, residual, field), next_d
        return entries

    columns = []
    for position in positions:
        root = field.exp[position]
        quotient, remainder = _divide(denominator, [root, 1], field)
        if remainder != [0]:
            raise ValueError("Witness support root did not divide its locator")
        residue = field.mul(root, field.evaluate(geometry, root))
        columns.append(coordinates([field.mul(value, residue) for value in quotient], [0]))
    target = coordinates([0], denominator)
    rows = [[*[column[index] for column in columns], value] for index, value in enumerate(target)]
    pivots, reduced = echelon(rows, range(len(positions)), field)
    if len(pivots) != 4 * len(collapse):
        raise ValueError("Multi-pole fixture did not have independent constraints")
    free = [index for index in range(len(positions)) if index not in pivots]
    symbols = [rng.randrange(1, 4096) for _ in positions]
    for pivot, row in zip(pivots, reduced, strict=True):
        value = row[-1]
        for index in free:
            value ^= field.mul(row[index], symbols[index])
        symbols[pivot] = value
    if not all(symbols):
        raise ValueError("Multi-pole fixture lost weight")
    return dict(zip(positions, symbols, strict=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sequence", action="append", metavar="BITS",
                        help="Fixed prefix where 1 requests a local pole and 0 a regular fold")
    args = parser.parse_args()
    sequences = args.sequence or ("11", "101", "10101")
    if any(not 1 <= len(sequence) <= 8 or set(sequence) - {"0", "1"} for sequence in sequences):
        parser.error("each sequence must contain one to eight bits")
    field = GF4096()
    results = []
    for sequence in sequences:
        collapse = tuple(bit == "1" for bit in sequence)
        errors = forced_sequence(field, collapse)
        words = syndrome(errors, field)
        if decode(words, field) != errors:
            raise ValueError("Witness is outside the native DQI decoding radius")
        result = audit_input(errors, field, emit_folds=True)
        expected = [group for group, local in enumerate(collapse) if local]
        if [g for g in result["local_poles"] if g < len(collapse)] != expected or (
            any(g < len(collapse) for g in result["incoming_poles"])
        ):
            raise ValueError("Prescribed genuine local poles did not reproduce")
        results.append({"support": errors, "syndrome": words, **result})
    write_json(args.output, {"driver_sha256": sha256(Path(__file__)), "cases": results})


if __name__ == "__main__":
    main()
