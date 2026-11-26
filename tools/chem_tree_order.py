"""Screen commuting Givens schedules and price shortlisted ANGLE families."""

import argparse
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from importlib import import_module
from pathlib import Path

import numpy as np
import numpy.typing as npt

from qcompile.artifacts import deterministic_npz
from qcompile.chemistry.angle_order import search_angle_order
from qcompile.io import read_json, sha256, write_json

BROT, BATCH, LOW, PROPOSALS = 7, 5, 4, 1600
SEEDS = (36191, 36197)
COMPILER_HASH = "b183352b347455bd121c2e3cd5587f72b82ebfb1c94b0ccce494c5c16465f04f"


def build_slot(compiler: Path, words: npt.NDArray[np.int64], output: Path, slot: int) -> dict:
    sys.path.insert(0, str(compiler.parent.resolve()))
    try:
        build = import_module(compiler.stem)
        if not build.__file__ or Path(build.__file__).resolve() != compiler.resolve():
            raise ValueError("wrong loader compiler")
        setattr(build, "BROT", BROT)
        result = build.compile_circuit((words, slot, LOW, 534, 4, True, "groups"))
    finally:
        sys.path.pop(0)
    artifact = output / f"angle_k_{slot}.kmx"
    artifact.write_text(result.pop("kmx"), encoding="ascii", newline="\n")
    return {"slot": slot, "sha256": sha256(artifact), "qubits": result["qubits"], "toffoli": result["toffoli"]}


def run(factorization: Path, reference: Path, compiler: Path, output: Path, jobs: int, screen: bool) -> None:
    from banked_chemistry import backend

    settings, km, _, _, api = backend()
    anchor = read_json(reference)
    if (sha256(factorization) != anchor["public_comparison"]["member_sha256"]["dfthcsos/submission.npz"]
            or anchor["metric_sha256"] != settings["metric_sha256"] or sha256(compiler) != COMPILER_HASH):
        raise ValueError("unexpected factorization, metric, or loader compiler")
    with np.load(factorization, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    words, edges = arrays["angle_words"], arrays["tree_edges"]
    math_api = import_module("dfthcsos.scoreinfra.dfthc_math")
    control = math_api.reconstruct_u_vectors(words / (1 << (BROT - 1)), edges)
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {
        "factorization_sha256": sha256(factorization), "reference_sha256": sha256(reference),
        "metric_sha256": settings["metric_sha256"], "compiler_sha256": COMPILER_HASH,
        "driver_sha256": sha256(Path(__file__)),
        "search_sha256": sha256(Path(__file__).parent.parent / "src/qcompile/chemistry/angle_order.py"),
        "brot": BROT, "batch": BATCH, "low_bits": LOW, "seeds": SEEDS,
        "proposals_per_seed": PROPOSALS, "compiler_seed": 534, "compiler_effort": 4,
        "compiler_engine": "groups", "salt": "chem-angle-tree-order-36191",
        "selection": "lowest mixed rank among changed orders",
    })
    ranking = []
    for seed in SEEDS:
        order, before, after = search_angle_order(words, edges, brot=BROT, batch=BATCH, low_bits=LOW,
                                                  seed=seed, proposals=PROPOSALS, require_change=True)
        actual = math_api.reconstruct_u_vectors(words[:, order] / (1 << (BROT - 1)), edges[list(order)])
        np.testing.assert_array_equal(actual, control)
        ranking.append({"seed": seed, "order": order, "original_rank": before, "mixed_rank": after,
                        "changed_positions": sum(i != index for i, index in enumerate(order))})
    write_json(output / "screen.json", {
        "classification": "exact_vector_preservation_with_mixed_rank_projection",
        "registration_sha256": sha256(registration), "ranking": ranking,
    })
    if screen:
        return
    choice = min(ranking, key=lambda row: row["mixed_rank"])
    results = {}
    for label, order in (("origin", tuple(range(words.shape[1]))), ("reordered", choice["order"])):
        family = output / label
        family.mkdir()
        assembly_dir = family / "assembly"
        assembly_dir.mkdir()
        table = np.asarray(words[:, order], dtype=np.int64)
        params = family / "submission.npz"
        if label == "origin":
            shutil.copyfile(factorization, params)
        else:
            deterministic_npz(params, {**arrays, "angle_words": table, "tree_edges": edges[list(order)]})
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            tasks = [pool.submit(build_slot, compiler, table, assembly_dir, slot)
                     for slot in range((len(order) + BATCH - 1) // BATCH)]
            slots = []
            for slot, task in enumerate(tasks):
                row = task.result()
                assembly = assembly_dir / f"angle_k_{slot}.kmx"
                binary = family / f"angle_k_{slot}.kmb"
                circuit = km.Circuit.from_file(assembly, format="kmx")
                circuit.to_file(binary, format="kmb")
                if circuit.num_qubits != row["qubits"] or circuit.num_qubits > 128:
                    raise ValueError("compiled ANGLE width differs from the projection")
                row["kmb_sha256"] = sha256(binary)
                slots.append(row)
        verified = api.verify(family, format="kmb", salt="chem-angle-tree-order-36191")
        if verified["resources"]["angles_toffoli_per_pass"] != sum(row["toffoli"] for row in slots):
            raise ValueError("compiled ANGLE counts differ from native execution")
        results[label] = {"factorization_sha256": sha256(family / "submission.npz"), "slots": slots, "verified": verified}
        write_json(output / f"{label}.json", results[label])
    write_json(output / "decision.json", {
        "registration_sha256": sha256(registration), "winner": choice, "comparison": results,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("factorization", "reference", "compiler", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--screen", action="store_true")
    run(**vars(parser.parse_args()))
