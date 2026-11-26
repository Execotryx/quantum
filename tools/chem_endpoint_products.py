"""Replace loader products using equal live predicates on both legal endpoints."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import numpy.typing as npt

from qcompile.io import sha256, write_json

Words = npt.NDArray[np.int64]


def word_masks(arrays: Words, width: int) -> list[int]:
    return [
        int.from_bytes(np.packbits((column >> bit) & 1, bitorder="little").tobytes(), "little")
        for column in arrays.T for bit in range(width)
    ]


def _affine_controls(function: int, state: dict[str, int], target: str, active: int
                     ) -> tuple[bool, list[str]] | None:
    """Find an affine expression on the relevant endpoint rows."""
    wires = [wire for wire in state if wire != target and state[wire] & active]
    pivots = {active.bit_length() - 1: (active, 1)}
    for index, wire in enumerate(wires, 1):
        vector, expression = state[wire] & active, 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (vector, expression)
                break
            other, combination = pivots[pivot]
            vector ^= other
            expression ^= combination
    vector, expression = function & active, 0
    while vector:
        row = pivots.get(vector.bit_length() - 1)
        if row is None:
            return None
        vector ^= row[0]
        expression ^= row[1]
    return bool(expression & 1), [wire for index, wire in enumerate(wires, 1) if expression >> index & 1]


def rewrite(lines: list[str], words: Words, block: int, *,
            linear_span: bool = False) -> tuple[list[str], dict[str, int]]:
    members: dict[str, list[str]] = defaultdict(list)
    registers = {}
    for line in lines:
        parts = line.split()
        if parts[:1] == ["APPEND_TO_REGISTER"]:
            members[parts[2]].append(parts[1])
        elif parts[:1] == ["REGISTER"]:
            registers[parts[2].strip('"')] = members[parts[1]]

    address = registers.pop("selection")
    slots = [registers[f"word_{index}"] for index in range(len(registers))]
    width = len(slots[0])
    if any(len(slot) != width for slot in slots):
        raise ValueError("ANGLE word slots must have equal precision")
    wires = [wire for slot in slots for wire in slot]
    size = len(slots)
    start = block * size
    before = np.zeros((len(words), size), dtype=np.int64) if block == 0 else words[:, start-size:start]
    after = words[:, start:start+size]
    if not 0 < after.shape[1] <= size or np.any(words < 0) or np.any(words >= 1 << width):
        raise ValueError("Angle words or batch bounds differ from the loader layout")
    after = np.pad(after, ((0, 0), (0, size - after.shape[1])))
    addresses = np.tile(np.arange(len(words), dtype=np.int64), (2, 1)).reshape(-1, 1)
    selection = dict(zip(address, word_masks(addresses, len(address)), strict=True))
    expected = {**selection, **dict(zip(wires, word_masks(np.vstack((after, before)), width), strict=True))}
    state: dict[str, int] = defaultdict(int, {
        **selection, **dict(zip(wires, word_masks(np.vstack((before, after)), width), strict=True)),
    })
    full = (1 << (2 * len(words))) - 1
    output = []
    eliminated = replaced = screened = 0
    for line in lines:
        parts = line.split()
        if not parts:
            output.append(line)
            continue
        op, *args = parts
        conditioned_phase = linear_span and op == "CCZ" and len(args) == 5 and args[3] == "if"
        if (op in {"CCX", "CCZ"} and len(args) == 3) or conditioned_phase:
            screened += 1
            a, b, target = args[:3]
            guard = " " + " ".join(args[3:]) if conditioned_phase else ""
            product = state[a] & state[b]
            active = full if op == "CCX" else state[target]
            substitute = next((wire for wire, value in state.items()
                               if (wire != target or op == "CCZ") and value == product), None)
            affine = None
            if linear_span and product & active and product != full and substitute is None:
                affine = _affine_controls(product, state, target, active)
            if op == "CCX":
                state[target] ^= product
            if not product & active:
                eliminated += 1
                continue
            if product == full or (op == "CCZ" and substitute == target):
                line = f"{'X' if op == 'CCX' else 'Z'} {target}{guard}\n"
                replaced += 1
            elif substitute:
                line = f"{'CX' if op == 'CCX' else 'CZ'} {substitute} {target}{guard}\n"
                replaced += 1
            elif affine is not None:
                offset, controls = affine
                flip, controlled = ("X", "CX") if op == "CCX" else ("Z", "CZ")
                if offset:
                    output.append(f"{flip} {target}{guard}\n")
                output.extend(f"{controlled} {wire} {target}{guard}\n" for wire in controls)
                replaced += 1
                continue
        elif op == "X" and len(args) == 1:
            state[args[0]] ^= full
        elif op == "CX" and len(args) == 2:
            state[args[1]] ^= state[args[0]]
        elif op == "HMR" and len(args) == 2:
            state[args[0]] = 0
        elif op not in {"APPEND_TO_REGISTER", "REGISTER", "Z", "CZ", "CCZ", "NEG", "INFO_TAG"}:
            raise ValueError(f"Unsupported value operation in ANGLE endpoint proof: {line.strip()}")
        output.append(line)
    if any(state[wire] != value for wire, value in expected.items()):
        raise ValueError("Original ANGLE circuit disagrees with either registered endpoint")
    if any(value for wire, value in state.items() if wire not in expected):
        raise ValueError("Original ANGLE circuit leaves dirty scratch")
    stats = {"eliminated": eliminated, "replaced_by_clifford": replaced, "endpoint_rows": 2 * len(words)}
    if linear_span:
        stats["screened_products"] = screened
    return output, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "factorization", "output", "receipt"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--block", type=int, required=True)
    parser.add_argument("--linear-span", action="store_true")
    args = parser.parse_args()
    if args.block < 0:
        parser.error("block must be nonnegative")
    with np.load(args.factorization, allow_pickle=False) as data:
        words = np.asarray(data["angle_words"], dtype=np.int64)
    lines, stats = rewrite(args.assembly.read_text().splitlines(keepends=True), words, args.block,
                           linear_span=args.linear_span)
    with args.output.open("x", newline="\n") as stream:
        stream.writelines(lines)
    write_json(args.receipt, {
        **stats, "block": args.block, "input_assembly_sha256": sha256(args.assembly),
        **({"linear_span": True} if args.linear_span else {}),
        "factorization_sha256": sha256(args.factorization), "output_assembly_sha256": sha256(args.output),
        "classification": "exact_forward_and_reverse_endpoint_product_rewrite",
    })


if __name__ == "__main__":
    main()
