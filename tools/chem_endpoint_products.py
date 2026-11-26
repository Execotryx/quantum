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


def rewrite(lines: list[str], words: Words, block: int) -> tuple[list[str], dict[str, int]]:
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
    eliminated = replaced = 0
    for line in lines:
        parts = line.split()
        if not parts:
            output.append(line)
            continue
        op, *args = parts
        if op in {"CCX", "CCZ"} and len(args) == 3:
            a, b, target = args
            product = state[a] & state[b]
            if op == "CCX":
                # The replacement's control must see the pre-operation state.
                substitute = next((wire for wire, value in state.items() if wire != target and value == product), None)
                state[target] ^= product
            else:
                substitute = next((wire for wire, value in state.items() if value == product), None)
                if not product & state[target]:
                    product = 0
            if not product:
                eliminated += 1
                continue
            if product == full or (op == "CCZ" and substitute == target):
                line = f"{'X' if op == 'CCX' else 'Z'} {target}\n"
                replaced += 1
            elif substitute:
                line = f"{'CX' if op == 'CCX' else 'CZ'} {substitute} {target}\n"
                replaced += 1
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
    return output, {"eliminated": eliminated, "replaced_by_clifford": replaced, "endpoint_rows": 2 * len(words)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "factorization", "output", "receipt"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args()
    if args.block < 0:
        parser.error("block must be nonnegative")
    with np.load(args.factorization, allow_pickle=False) as data:
        words = np.asarray(data["angle_words"], dtype=np.int64)
    lines, stats = rewrite(args.assembly.read_text().splitlines(keepends=True), words, args.block)
    with args.output.open("x", newline="\n") as stream:
        stream.writelines(lines)
    write_json(args.receipt, {
        **stats, "block": args.block, "input_assembly_sha256": sha256(args.assembly),
        "factorization_sha256": sha256(args.factorization), "output_assembly_sha256": sha256(args.output),
        "classification": "exact_forward_and_reverse_endpoint_product_rewrite",
    })


if __name__ == "__main__":
    main()
