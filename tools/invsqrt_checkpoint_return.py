"""Join and verify the incumbent divider checkpoints with a Clifford bridge."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import numpy as np

from invsqrt_checkpoint_phase import CUT
from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR, verify_rotation_prefix
from qcompile.io import sha256, write_json


RETURN_CUT = 18900
BRIDGE_WIRE = 28
PREFIX_PHASE = 177
SEED = 37109
WRITE_BITS = {"HMR", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}
CHARGED = {"CCX", "CCZ", "CSWAP"}


def charged(ops: list[Any]) -> dict[str, int]:
    depth = unconditional = guarded = 0
    for op in ops:
        depth += (op.name == "PUSH_CONDITION") - (op.name == "POP_CONDITION")
        if depth < 0:
            raise ValueError("The retained region closes a prior branch")
        if op.name in CHARGED:
            if depth or op.cond is not None:
                guarded += 1
            else:
                unconditional += 1
    if depth:
        raise ValueError("The retained region has an open branch")
    return {"unconditional": unconditional, "guarded": guarded}


def suffix_inputs(ops: list[Any]) -> set[int]:
    """Find bits the retained suffix might read before assigning them."""
    depth = 0
    written: set[int] = set()
    inputs: set[int] = set()
    for op in ops:
        if op.cond is not None and op.cond not in written:
            inputs.add(op.cond)
        if op.name == "BIT_INVERT" and op.b not in written:
            inputs.add(op.b)
        if op.name in WRITE_BITS and op.cond is None and not depth:
            written.add(op.b)
        depth += (op.name == "PUSH_CONDITION") - (op.name == "POP_CONDITION")
    return inputs


def run(assembly: Path, simulator: Path, output: Path) -> None:
    if sha256(assembly) != CONTROL or sha256(simulator) != SIMULATOR:
        raise ValueError("Wrong pinned assembly or simulator")
    spec = spec_from_file_location("pinned_return_simulator", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the pinned simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(assembly)
    verify_rotation_prefix(ops, {CUT})
    prefix = [op for op in ops if op.line <= CUT]
    skipped = [op for op in ops if CUT < op.line <= RETURN_CUT]
    suffix = [op for op in ops if op.line > RETURN_CUT]
    outputs = {op.b for op in skipped if op.name in WRITE_BITS}
    reads = suffix_inputs(suffix)
    if outputs & reads:
        raise ValueError("The return reads a discarded measurement or updated bit")
    pre_cost, return_cost = charged(prefix), charged(suffix)
    lines = assembly.read_text(encoding="ascii").splitlines()
    if lines[PREFIX_PHASE - 1] != "Z_POW q33 0.5":
        raise ValueError("The retained quarter-turn phase differs from the zero-phase control")
    output.mkdir(parents=True, exist_ok=False)
    registration = output / "registration.json"
    write_json(registration, {"assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
        "driver_sha256": sha256(Path(__file__)), "prefix_end": CUT, "return_after_line": RETURN_CUT,
        "bridge": f"X q{BRIDGE_WIRE}", "removed_prefix_rotation_line": PREFIX_PHASE, "legal_inputs": MAX_X,
        "source_replay": {"measurement_modes": ["zero", "rand"], "seed": SEED},
        "native": {"shots_per_x": 2, "batch_size": 292, "control_beta": 1, "skeleton_beta": 0,
                   "control_salt": "checkpoint-return-control-20261127-dev",
                   "skeleton_salt": "checkpoint-return-zero-20261127-dev"}})
    for mode in ("zero", "rand"):
        sim = km.Sim(39, mode, seed=SEED)
        sim.load_x(register)
        sim.run(prefix)
        expected = sim.Q.copy()
        expected[BRIDGE_WIRE] ^= km.ALL
        sim.run(skipped)
        if sim.stack or not np.array_equal(sim.Q, expected):
            raise ValueError(f"Checkpoint values differ after the bridge in {mode} replay")
    path = output / "skeleton.kmx"
    drop = PREFIX_PHASE - 1
    path.write_text("\n".join([*lines[:drop], *lines[PREFIX_PHASE:CUT], f"X q{BRIDGE_WIRE}", *lines[RETURN_CUT:]]) + "\n",
                    encoding="ascii", newline="\n")
    write_json(output / "screen.json", {"registration_sha256": sha256(registration),
        "skeleton_assembly_sha256": sha256(path), "prefix_toffoli_like": pre_cost,
        "return_toffoli_like": return_cost, "suffix_input_bits": sorted(reads),
        "suffix_inputs_written_in_discarded_region": [],
        "cross_cut_values_match_after_bridge": True})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
