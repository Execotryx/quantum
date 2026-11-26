"""Replace a proved temporary OR carry with its direct reversible gate sequence."""

import argparse
import re
from collections import Counter
from pathlib import Path

from invsqrt_opportunity import backend
from qcompile.invsqrt.scratch import ScratchProof
from qcompile.io import sha256, write_json

CONTROL_ASSEMBLY = "27ccb62d03bcba70353d382bb94c5dc636acd00b250c83f976df8d1176842146"
BIT = re.compile(r"\bb\d+\b")
CARRY = re.compile(
    r"(?m)^CCX (q\d+) (q\d+) (q\d+)\nCX \1 \3\nCX \2 \3\nCX \3 (q\d+)\n"
    r"CX \2 \3\nCX \1 \3\nHMR \3 (b\d+)\nCZ \1 \2 if \5\n",
)
HEADER = {"INFO_TAG", "REGISTER", "APPEND_TO_REGISTER"}


def replace_carries(assembly: str) -> tuple[str, int]:
    """Match whole gadgets and require a clean temporary and dead outcome."""
    uses = Counter(BIT.findall(assembly))
    proof = ScratchProof(22)
    pieces = []
    cursor = replaced = 0
    for match in CARRY.finditer(assembly):
        before = assembly[cursor:match.start()]
        pieces.append(before)
        for line in before.splitlines():
            parts = line.split()
            if parts and parts[0] not in HEADER:
                proof.step(parts)
        left, right, temporary, target, outcome = match.groups()
        original = match[0]
        if len({left, right, temporary, target}) == 4 and uses[outcome] == 2 and proof.values[temporary] == 0:
            # The HMR reads left*right after the XORs are undone, so the
            # conditional CZ cancels its phase. XOR the OR directly instead.
            pieces.append(f"CCX {left} {right} {target}\nCX {left} {target}\nCX {right} {target}\n")
            replaced += 1
        else:
            pieces.append(original)
        for line in original.splitlines():
            proof.step(line.split())
        cursor = match.end()
    pieces.append(assembly[cursor:])
    return "".join(pieces), replaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    if sha256(args.assembly) != CONTROL_ASSEMBLY:
        raise ValueError("Wrong inverse-square-root source control")
    km, _, _ = backend()
    original = args.assembly.read_text(encoding="ascii")
    revised, changed = replace_carries(original)
    if not changed:
        raise ValueError("No carry gadgets qualified")
    control = km.Circuit(original)
    candidate = km.Circuit(revised)
    with args.output.open("xb") as stream:
        candidate.to_file(stream, format="kmb")
    write_json(args.receipt, {
        "classification": "emitted_or_carry_development_candidate",
        "input_assembly_sha256": CONTROL_ASSEMBLY, "candidate_sha256": sha256(args.output),
        "replaced_gadgets": changed, "control_qubits": control.num_qubits, "qubits": candidate.num_qubits,
        "control_static_operations": dict(control.operation_statistics()),
        "candidate_static_operations": dict(candidate.operation_statistics()),
    })


if __name__ == "__main__":
    main()
