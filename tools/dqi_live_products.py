"""Reuse exact live conjunctions in native decoder fragments."""

import argparse
import lzma
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO

from qcompile.invsqrt.scratch import ScratchProof
from qcompile.io import sha256, write_json

AFFINE = {b"X", b"CX", b"CCX"}
PHASE = {b"Z", b"CZ", b"CCZ", b"Z_POW", b"NEG"}
RESET_INTERVAL = 8192


def rewrite(source: Iterable[bytes], output: BinaryIO | None = None) -> dict[str, int]:
    proof = ScratchProof(0)
    values: dict[bytes, int] = {}
    locations: dict[int, set[bytes]] = defaultdict(set)
    counts: Counter[str] = Counter()
    last_use: dict[int, int] = {}
    cache_end = -1
    depth = 0
    interval = 0

    def assign(wire: bytes, value: int) -> None:
        if wire in values:
            prior = values[wire]
            locations[prior].remove(wire)
            if not locations[prior]:
                del locations[prior]
        values[wire] = value
        locations[value].add(wire)

    def known(wire: bytes) -> int:
        if wire not in values:
            assign(wire, proof.atom())
        return values[wire]

    for line in source:
        # Classical instructions do not change a quantum value. Their guards
        # are modeled as unknown whenever a quantum update uses one.
        opcode = line.split(b" ", 1)[0].strip()
        if opcode.startswith(b"BIT_") or not opcode or opcode.startswith(b"#"):
            if output is not None:
                output.write(line)
            continue
        parts = line.split()
        guarded = len(parts) > 2 and parts[-2] == b"if"
        operands = parts[1:-2] if guarded else parts[1:]
        if opcode == b"PUSH_CONDITION":
            depth += 1
        elif opcode == b"POP_CONDITION":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced decoder conditions")
        elif opcode in AFFINE or opcode == b"CCZ":
            if opcode in (b"CCX", b"CCZ"):
                a, b, target = operands
                product = proof.product(known(a), known(b))
                counts["product_gates"] += 1
                if product == 0:
                    line = b""
                    counts["zero_products"] += 1
                elif product == 1:
                    replacement = b"X" if opcode == b"CCX" else b"Z"
                    line = b" ".join([replacement, target, *parts[len(operands) + 1:]]) + b"\n"
                    counts["constant_products"] += 1
                else:
                    wires = locations.get(product)
                    # A target alias for CCX is singular. Do not use it as a control.
                    alias = min((wire for wire in wires if wire != target), default=None) if wires else None
                    if opcode == b"CCZ" and wires and target in wires:
                        line = b" ".join([b"Z", target, *parts[4:]]) + b"\n"
                        counts["live_products"] += 1
                    elif alias is not None:
                        replacement = b"CX" if opcode == b"CCX" else b"CZ"
                        line = b" ".join([replacement, alias, target, *parts[4:]]) + b"\n"
                        counts["live_products"] += 1
                    elif not (depth or guarded):
                        earlier = last_use.get(product)
                        if earlier is not None:
                            counts["repeated_products"] += 1
                            if earlier > cache_end:
                                counts["disjoint_repeated_product_pairs"] += 1
                                cache_end = interval
                        last_use[product] = interval
            else:
                target = operands[-1]
                product = proof.product(*(known(wire) for wire in operands[:-1]))
            if opcode in AFFINE and product:
                value = proof.atom() if depth or guarded else known(target) ^ product
                assign(target, value)
        elif opcode in (b"HMR", b"R"):
            assign(operands[0], proof.atom() if depth or guarded else 0)
        elif opcode == b"SWAP" and not (depth or guarded):
            left, right = operands
            a, b = known(left), known(right)
            assign(left, b)
            assign(right, a)
        elif opcode in (b"SWAP", b"CSWAP"):
            for target in operands[-2:]:
                assign(target, proof.atom())
        elif opcode not in PHASE and opcode not in (b"INFO_TAG", b"REGISTER", b"APPEND_TO_REGISTER"):
            raise ValueError(f"Unsupported decoder opcode {opcode!r}")
        if output is not None:
            output.write(line)
        interval += 1
        if interval == RESET_INTERVAL:
            proof = ScratchProof(0)
            values.clear()
            locations.clear()
            last_use.clear()
            cache_end = -1
            interval = 0
    if depth:
        raise ValueError("Unbalanced decoder conditions")
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fragment", type=Path, nargs="+")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for fragment in args.fragment:
        with lzma.open(fragment, "rb") as source:
            counts = rewrite(source)
        rows.append({"fragment": fragment.name, "sha256": sha256(fragment), "counts": counts})
    write_json(args.receipt, {"classification": "static_exact_live_product_screen",
                              "symbolic_interval": RESET_INTERVAL, "fragments": rows})


if __name__ == "__main__":
    main()
