"""Generate the two optimized members of the verified parent hybrid."""

import argparse
from pathlib import Path

import banked_chemistry
import invsqrt_opportunity
import numpy as np

from qcompile.io import read_json, sha256

ROOT = invsqrt_opportunity.ROOT
PARENT = ROOT / "docs/evidence/invsqrt-chemistry-20261107"
REFERENCE = ROOT / "vendor/official/sample_submission"


def chemistry(output: Path, source: Path) -> None:
    pinned = read_json(ROOT / "docs/evidence/step3-chemistry-words.json")
    if sha256(source) != pinned["words_sha256"]:
        raise ValueError("recovered chemistry words changed")
    if sha256(REFERENCE / "dfthcsos/submission.npz") != pinned["factorization_sha256"]:
        raise ValueError("chemistry factorization changed")
    _, km, api, builder, _ = banked_chemistry.backend()
    with np.load(source, allow_pickle=False) as recovered:
        deltas = builder.batch_deltas(recovered["words"], 9)
    directory = output / "dfthcsos"
    directory.mkdir(exist_ok=False)
    expected = read_json(PARENT / "archive.json")["hashes"]
    for index, delta in enumerate(deltas):
        circuit = banked_chemistry.banked_circuit(km, api, delta, pinned["brot"])
        if circuit.num_qubits > 128:
            raise ValueError("rebuild exceeded the ANGLE cap")
        name = f"dfthcsos/angle_k_{index}.kmb"
        with (output / name).open("xb") as stream:
            circuit.to_file(stream, format="kmb")
        if sha256(output / name) != expected[name]:
            raise ValueError(f"rebuild differs from parent: {name}")
    if len(deltas) != 9:
        raise ValueError("rebuild must emit nine banked ANGLE circuits")


def invsqrt(output: Path) -> None:
    _, builder, official = invsqrt_opportunity.backend()
    protocol = read_json(invsqrt_opportunity.CONFIG)
    circuit = builder.build_nr_circuit(protocol["n_p"], prec=builder.Precision(*protocol["widths"]["lead"]))
    path = output / "invsqrt.kmb"
    with path.open("xb") as stream:
        circuit.to_file(stream, format="kmb")
    if sha256(path) != read_json(PARENT / "archive.json")["hashes"]["invsqrt.kmb"]:
        raise ValueError("Newton inverse-square-root rebuild differs from parent")
    if official._circuit_sha256(circuit) != sha256(path):
        raise ValueError("noncanonical inverse-square-root rebuild")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", choices=("invsqrt", "dfthcsos"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--words", type=Path, default=ROOT / "runs/step3-chemistry/recovered-words.npz")
    args = parser.parse_args()
    if args.benchmark == "invsqrt":
        invsqrt(args.output)
    else:
        chemistry(args.output, args.words)


if __name__ == "__main__":
    main()
