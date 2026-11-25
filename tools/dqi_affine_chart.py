"""Audit a local affine denominator chart on captured D4 syndromes."""

import argparse
from pathlib import Path

from dqi_compact_layout import split_pair
from dqi_extraction_oracle import ExternalField, original_pair

from qcompile.dqi.decoder import _add, _multiply, decode
from qcompile.dqi.field import GF4096
from qcompile.io import read_json, sha256, write_json


def trace(root: tuple[list[int], list[int]], field: GF4096, group: int, *, escape: bool) -> dict:
    """Replay one selected affine escape and its exact inverse."""
    n, d = root
    extension = ExternalField(field)
    trace_rows = []
    history = []
    for index in range(17):
        coordinate = 2 * index
        before = [len(n) - 1, len(d) - 1]
        fold = split_pair(n, d, coordinate, extension)
        original = fold
        shear = None
        incoming = False
        if escape and index == group and fold.collapse and any(fold.first):
            incoming = fold.incoming_pole
            a, b = (d, n) if incoming else (n, d)
            node = coordinate | 4096
            for shift in (0, 1):
                candidate = _add(b, _multiply(a, [shift, 1], field))
                if extension.evaluate(candidate, node):
                    shear = shift
                    fold = split_pair(a, candidate, coordinate, extension)
                    break
            if shear is None or fold.incoming_pole or fold.collapse:
                raise ValueError("Nonzero local head failed both affine charts")
        history.append((fold, shear, incoming))
        n, d = fold.u, fold.v
        trace_rows.append({
            "group": index, "degree_in": before, "degree_out": [len(n) - 1, len(d) - 1],
            "original_first_head": original.first, "heads": fold.first + fold.second,
            "incoming": original.incoming_pole, "collapse": fold.collapse,
            "translation": shear, "prefix_reciprocal": incoming,
            "within_regular_caps": len(n) - 1 <= 34 - 2 * index and len(d) - 1 <= 33 - 2 * index,
        })
    tail = [n, d]
    for fold, shear, incoming in reversed(history):
        n, d = fold.join((n, d), field)
        if shear is not None:
            d = _add(d, _multiply(n, [shear, 1], field))
            if incoming:
                n, d = d, n
    if (n, d) != root:
        raise ValueError("Affine chart replay did not recover the original pair")
    return {"folds": trace_rows, "tail": tail}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("historical", type=Path)
    parser.add_argument("residual", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--group", type=int, default=6, choices=range(17))
    args = parser.parse_args()
    field = GF4096()
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    cases = []
    for directory in (args.historical, args.residual):
        for capture in sorted(directory.glob("s*/batch-*.json")):
            data = read_json(capture)
            for row in data["shots"] + data["controls"]:
                support = decode(row["syndrome"], field)
                root = original_pair(support, kappas, field)
                cases.append({
                    "capture_sha256": sha256(capture), "draw": capture.parent.name,
                    "shot": row["index"], "weight": len(support),
                    "ordinary": trace(root, field, args.group, escape=False),
                    "affine": trace(root, field, args.group, escape=True),
                })
    write_json(args.output, {"driver_sha256": sha256(Path(__file__)), "group": args.group, "cases": cases})


if __name__ == "__main__":
    main()
