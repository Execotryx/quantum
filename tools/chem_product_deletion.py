"""Screen deletion of independent products from the pinned terminal ANGLE loader."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from chem_endpoint_products import word_masks
from chem_zero_angle_words import BATCH, BROT, CONTROL, LOW_BITS, zero_rotation_mask
from qcompile.io import sha256, write_json


ASSEMBLY = "e2a384b6d45239be17d363a7050a49f1a5a4ae241705eaa4b69f6f09059dfde6"
SLOT = 14


def reduce_vector(basis: dict[int, tuple[int, int]], value: int, tag: int = 0) -> tuple[int, int]:
    while value:
        row = basis.get(value.bit_length())
        if row is None:
            break
        value ^= row[0]
        tag ^= row[1]
    return value, tag


def indispensable(columns: list[int], wanted: list[int], active: int) -> int:
    """Identify columns with a forced coefficient of one in some required output."""
    basis: dict[int, tuple[int, int]] = {}
    flexible = 0
    for index, vector in enumerate(columns):
        rest, tag = reduce_vector(basis, vector & active, 1 << index)
        if rest:
            basis[rest.bit_length()] = (rest, tag)
        else:
            # Each dependent column produces one independent nullspace direction.
            flexible |= tag
    required = 0
    for vector in wanted:
        rest, tag = reduce_vector(basis, vector & active)
        if rest:
            raise ValueError("The frozen dictionary cannot reproduce the original outputs")
        required |= tag
    return required & ~flexible


def run(assembly: Path, factorization: Path, output: Path) -> None:
    if (sha256(assembly), sha256(factorization)) != (ASSEMBLY, CONTROL):
        raise ValueError("Unexpected terminal loader or factorization")
    with np.load(factorization, allow_pickle=False) as source:
        words, edges = source["angle_words"], source["tree_edges"]
    start = SLOT * BATCH
    before, after = words[:, start - BATCH:start], words[:, start:start + BATCH]
    free = zero_rotation_mask(words, edges)[:, start:start + BATCH]
    addresses = np.arange(len(words), dtype=np.int64)
    codes = assembly.read_text(encoding="ascii").splitlines()
    members: dict[str, list[str]] = defaultdict(list)
    registers = {}
    for line in codes:
        args = line.split()
        if args[:1] == ["APPEND_TO_REGISTER"]:
            members[args[2]].append(args[1])
        elif args[:1] == ["REGISTER"]:
            registers[args[2].strip('"')] = members[args[1]]
    selection = registers["selection"]
    sinks = [wire for i in range(BATCH) for wire in registers[f"word_{i}"]]
    values = defaultdict(int, zip(selection, word_masks(np.tile(addresses, 2)[:, None], len(selection)), strict=True))
    values.update(zip(sinks, word_masks(np.vstack((before, after)), BROT), strict=True))
    reference = dict(values)
    reference.update(zip(sinks, word_masks(np.vstack((after, before)), BROT), strict=True))
    full = (1 << (2 * len(words))) - 1
    influence: dict[str, int] = defaultdict(int)
    observed = 0
    products = []
    for index, line in enumerate(codes, 1):
        args = line.split()
        match args:
            case ["X", target]:
                values[target] ^= full
            case ["CX", left, target]:
                values[target] ^= values[left]
                influence[target] ^= influence[left]
            case ["CCX", left, right, target]:
                observed |= influence[left] | influence[right]
                function = values[left] & values[right]
                values[target] ^= function
                influence[target] ^= 1 << len(products)
                products.append((index, function))
            case ["HMR", target, _]:
                observed |= influence[target]
                values[target] = influence[target] = 0
            case ["CZ", left, right, "if", _]:
                observed |= influence[left] | influence[right]
            case ["APPEND_TO_REGISTER" | "REGISTER", *_] | []:
                pass
            case _:
                raise ValueError(f"Unexpected KMX instruction at line {index}")
    if any(values[wire] != value for wire, value in reference.items()):
        raise ValueError("The pinned loader did not restore the original endpoint contract")
    if any(value for wire, value in values.items() if wire not in reference):
        raise ValueError("The pinned loader left scratch dirty")
    for wire, flags in influence.items():
        if wire not in sinks:
            observed |= flags

    eligible = [(i, line, fn) for i, (line, fn) in enumerate(products) if not (observed >> i) & 1]
    one_pass = (1 << len(words)) - 1
    # Free pure address functions enlarge the dictionary and make rejection conservative.
    pure = [int.from_bytes(np.packbits(groups == g, bitorder="little").tobytes(), "little")
            for groups in (addresses >> LOW_BITS, addresses & ((1 << LOW_BITS) - 1))
            for g in np.unique(groups)]
    columns = [fn & one_pass for _, _, fn in eligible]
    wanted = [0] * len(sinks)
    for j, wire in enumerate(sinks):
        for i, _, fn in eligible:
            if (influence[wire] >> i) & 1:
                wanted[j] ^= fn & one_pass
    must_keep = 0
    for word in range(BATCH):
        active = int.from_bytes(np.packbits(~free[:, word], bitorder="little").tobytes(), "little")
        must_keep |= indispensable(columns + pure, wanted[word * BROT:(word + 1) * BROT], active)

    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "screen.json", {"scope": "forward relaxed deletion feasibility; frozen product controls and cache",
        "assembly_sha256": ASSEMBLY, "factorization_sha256": CONTROL, "driver_sha256": sha256(Path(__file__)),
        "slot": SLOT, "addresses": len(words), "free_words": int(np.count_nonzero(free)),
        "charged_products": len(products), "protected_products": observed.bit_count(),
        "independent_products": len(eligible), "pure_address_indicators": len(pure),
        "products_with_equal_endpoint_functions": sum((fn & one_pass) == (fn >> len(words))
                                                       for _, _, fn in eligible),
        "indispensable_independent_products": sum((must_keep >> i) & 1 for i in range(len(eligible))),
        "relaxed_deletion_lines": [line for i, (_, line, _) in enumerate(eligible) if not (must_keep >> i) & 1]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "factorization", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
