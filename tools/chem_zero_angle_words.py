"""Screen loader words for rotations acting on two exactly zero coordinates."""

import argparse
from importlib import import_module
from pathlib import Path
import sys

import numpy as np
from numpy.typing import NDArray

from qcompile.chemistry.angle_order import _mixed_forms, _rank
from qcompile.chemistry.representation import batch_words, validate_tree
from qcompile.io import read_json, sha256, write_json
from qcompile.official import validate_backend


BROT = 7
BATCH = 5
LOW_BITS = 4
CONTROL = "25cab2c621e78711480aa975f42a8386414f1f2e1466c3d1f01d5be3e31cae20"
Words = NDArray[np.int64]
Mask = NDArray[np.bool_]


def zero_rotation_mask(words: Words, edges: Words) -> Mask:
    """Propagate exact support on an ordered root-to-child Givens tree."""
    validate_tree(edges, words.shape[1] + 1, 0)
    support = np.zeros((len(words), words.shape[1] + 1), dtype=np.bool_)
    support[:, 0] = True
    free = np.empty(words.shape, dtype=np.bool_)
    for col, (parent, child) in enumerate(edges):
        active = support[:, parent].copy()
        free[:, col] = ~active
        angle = words[:, col] % (1 << (BROT - 1))
        support[:, parent] = active & (angle != 1 << (BROT - 2))
        support[:, child] = active & (angle != 0)
    return free


def fill(words: Words, free: Mask, step: int) -> Words:
    """Carry the adjacent packet value into unconstrained cells on its lane."""
    result = words.copy()
    order = range(words.shape[1]) if step > 0 else range(words.shape[1] - 1, -1, -1)
    for col in order:
        neighbor = col - step * BATCH
        mask = free[:, col]
        result[mask, col] = result[mask, neighbor] if 0 <= neighbor < words.shape[1] else 0
    return result


def prices(words: Words) -> tuple[list[int], int]:
    """Compute the existing mixed-ANF rank proxy on each XOR transition."""
    _, deltas = batch_words(words, BATCH, BROT)
    ranks = []
    toggles = 0
    for delta in deltas:
        forms = _mixed_forms(delta, BROT, LOW_BITS)
        ranks.append(sum(_rank([c[start + bit] for c in forms for bit in range(BROT)])
                         for start in range(0, len(forms[0]), BROT)))
        toggles += sum(int(x).bit_count() for x in delta.flat)
    return ranks, toggles


def run(factorization: Path, inventory: Path, output: Path) -> None:
    if sha256(factorization) != CONTROL:
        raise ValueError("Unexpected seven-bit factorization")
    settings = read_json(inventory)
    validate_backend(settings)
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    api = import_module("dfthcsos.verify")
    math = import_module("dfthcsos.scoreinfra.dfthc_math")
    with np.load(factorization, allow_pickle=False) as archive:
        words, edges = archive["angle_words"], archive["tree_edges"]
    inputs = api.load_inputs(factorization)
    if words.shape != (1219, 75) or np.any((words < 0) | (words >= 1 << BROT)):
        raise ValueError("Unexpected packed angle word table")
    free = zero_rotation_mask(words, edges)
    scale = 1 << (BROT - 1)
    reference = math.reconstruct_u_vectors(words / scale, edges)
    variants = {"control": words, "zero": np.where(free, 0, words),
                "previous_packet": fill(words, free, 1), "next_packet": fill(words, free, -1)}
    output.mkdir(parents=True, exist_ok=False)
    rows = {}
    for name, candidate in variants.items():
        if np.any((candidate != words) & ~free):
            raise ValueError("The assignment changed an active rotation")
        delta = float(np.max(np.abs(math.reconstruct_u_vectors(candidate / scale, edges) - reference)))
        if delta > 1e-13:
            raise ValueError("The assignment changed the prepared vectors")
        metrics = api.evaluate_words(inputs, candidate, edges, BROT)
        ranks, toggles = prices(candidate)
        out = output / f"{name}.npy"
        np.save(out, candidate, allow_pickle=False)
        rows[name] = {"words_sha256": sha256(out), "changed_words": int(np.count_nonzero(candidate != words)),
                      "maximum_vector_error": delta, "accuracy_passed": bool(api.passes_accuracy(metrics)),
                      "mixed_ranks": ranks, "mixed_rank_sum": sum(ranks), "xor_bit_toggles": toggles,
                      "metrics": metrics}
    if not rows["control"]["accuracy_passed"]:
        raise ValueError("The seven-bit control did not pass")
    write_json(output / "screen.json", {"scope": "decoded accuracy and rank proxy only",
        "factorization_sha256": CONTROL, "backend_sha256": sha256(inventory),
        "driver_sha256": sha256(Path(__file__)), "brot": BROT, "batch": BATCH, "low_bits": LOW_BITS,
        "free_words": int(np.count_nonzero(free)), "variants": rows})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("factorization", "inventory", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
