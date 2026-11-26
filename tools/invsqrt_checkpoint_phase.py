"""Find exact obstructions to affine phase recovery from a divider checkpoint."""

import argparse
from hashlib import sha256 as digest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR, verify_rotation_prefix
from qcompile.invsqrt.direct_screen import beta_one_targets
from qcompile.io import sha256, write_json


CUT = 5856
SEED = 39
SAMPLE_COUNT = 262144
MAX_PER_BUCKET = 128
OCTAVE_START = 1 << 20
ADDRESSES = (tuple(range(14, 22)), (*range(14, 23), 25, 26, 27, 28), (*range(12, 23), 25, 26, 27, 28))
# These four checkpoint wires feed the first product after the cut,
# (q7 XOR q12) AND (q9 XOR q10), at line 5875.
CARRY_CONTROLS = (7, 9, 10, 12)


def find_witness(xs: NDArray[np.int64], states: NDArray[np.uint64], wires: tuple[int, ...],
                 joint_wires: tuple[int, ...] = ()) -> dict:
    mask = np.uint64(sum(1 << wire for wire in wires))
    address = states & mask
    order = np.argsort(address, kind="stable")
    keys = address[order]
    groups = np.split(order, np.flatnonzero(keys[:-1] != keys[1:]) + 1)
    values = xs.astype(np.float64)**-0.5
    joint_mask = np.uint64(sum(1 << wire for wire in joint_wires))
    joint = states & joint_mask
    best_ratio = 0.0
    best = None
    for group in groups:
        if len(group) < 4:
            continue
        if len(group) > MAX_PER_BUCKET:
            group = group[np.linspace(0, len(group) - 1, MAX_PER_BUCKET, dtype=np.int64)]
        i, j = np.triu_indices(len(group), 1)
        a, b = group[i], group[j]
        xor, both = states[a] ^ states[b], states[a] & states[b]
        sums = values[a] + values[b]
        joint_lo, joint_hi = np.minimum(joint[a], joint[b]), np.maximum(joint[a], joint[b])
        ordering = np.lexsort((sums, joint_hi, joint_lo, both, xor))
        sx, sb = xor[ordering], both[ordering]
        sl, sh = joint_lo[ordering], joint_hi[ordering]
        borders = np.flatnonzero((sx[1:] != sx[:-1]) | (sb[1:] != sb[:-1])
                                 | (sl[1:] != sl[:-1]) | (sh[1:] != sh[:-1])) + 1
        first = np.concatenate(([0], borders))
        last = np.concatenate((borders - 1, [len(ordering) - 1]))
        valid = first < last
        if not valid.any():
            continue
        lo, hi = ordering[first[valid]], ordering[last[valid]]
        ratio = (sums[hi] - sums[lo]) * (1 << 24) / (sums[hi] + sums[lo])
        at = int(ratio.argmax())
        if ratio[at] > best_ratio:
            best_ratio = float(ratio[at])
            best = [int(a[lo[at]]), int(b[lo[at]]), int(a[hi[at]]), int(b[hi[at]])]

    result: dict = {"address_wires": wires, "additional_joint_wires": joint_wires,
                    "sample_address_count": len(groups), "witness": None}
    if best is not None:
        packed = [int(word) for word in states[best]]
        a, b, c, d = packed
        if len({word & int(mask) for word in packed}) != 1:
            raise AssertionError("Witness uses different table addresses")
        if (a ^ b, a & b) != (c ^ d, c & d):
            raise AssertionError("Witness does not cancel every affine coefficient")
        if sorted([a & int(joint_mask), b & int(joint_mask)]) != sorted([c & int(joint_mask), d & int(joint_mask)]):
            raise AssertionError("Witness does not cancel the extra joint term")
        target, tolerance = beta_one_targets(xs[best])
        t0, t1, t2, t3 = map(int, target)
        # In turns, prefix and Clifford-only cleanup contribute multiples
        # of a quarter. Keep the distance to that lattice exact in phase64.
        quarter_turn = 1 << 62
        residue = (t0 + t1 - t2 - t3) % quarter_turn
        forced = min(residue, quarter_turn - residue)
        allowed = sum(map(int, tolerance))
        result["witness"] = {"inputs": xs[best].tolist(), "packed_checkpoint_values": packed,
                             "target_phase64": target.tolist(), "tolerance_phase64": tolerance.tolist(),
                             "absolute_mixed_difference_phase64": forced, "sum_tolerance_phase64": allowed,
                             "minimum_worst_tolerance_fraction": forced / allowed, "excludes_family": forced > allowed}
    return result


def run(assembly: Path, simulator: Path, output: Path) -> None:
    if sha256(assembly) != CONTROL or sha256(simulator) != SIMULATOR:
        raise ValueError("Wrong pinned assembly or source simulator")
    spec = spec_from_file_location("checkpoint_simulator", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the pinned source simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(assembly)
    verify_rotation_prefix(ops, {CUT})
    prefix = [op for op in ops if op.line <= CUT]
    if any(op.name == "Z_POW" and op.units % (1 << 62) for op in prefix):
        raise ValueError("The prefix contains a phase outside the quarter-turn lattice")
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
        "driver_sha256": sha256(Path(__file__)), "prefix_inclusive_last_line": CUT, "legal_inputs": MAX_X,
        "search_range": [OCTAVE_START, MAX_X], "sample_seed": SEED, "sample_count": SAMPLE_COUNT,
        "maximum_inputs_per_address": MAX_PER_BUCKET, "address_wires": ADDRESSES,
        "joint_control_wires": CARRY_CONTROLS,
        "family": "address-specific affine function plus an optional joint term and quarter-turn phase"})
    sim = km.Sim(39, "zero")
    sim.load_x(register)
    sim.run(prefix)
    clean = [wire for wire, plane in enumerate(sim.Q) if not plane.any()]
    rng = np.random.default_rng(SEED)
    # Sample legal inputs without replacement and keep the source's padded
    # bit-plane ordering, where input x occupies bit x-1.
    xs = np.sort(rng.choice(MAX_X - OCTAVE_START + 1, SAMPLE_COUNT, replace=False)) + OCTAVE_START
    states = np.zeros(SAMPLE_COUNT, dtype=np.uint64)
    for wire, plane in enumerate(sim.Q):
        if wire not in clean:
            states |= km.unpack(plane)[xs - 1].astype(np.uint64) << np.uint64(wire)
    write_json(output / "screen.json", {"registration_sha256": sha256(registration),
        "clean_wires_for_all_legal_inputs": clean, "prefix_unconditional_toffoli_like": sim.count["toffoli"] // sim.n,
        "sample_sha256": digest(xs.tobytes()).hexdigest(),
        "addresses": [*(find_witness(xs, states, wires) for wires in ADDRESSES),
                      find_witness(xs, states, ADDRESSES[1], CARRY_CONTROLS)]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
