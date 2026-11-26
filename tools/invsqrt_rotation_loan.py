"""Verify and emit the q19 loan at the incumbent's first major rotation."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR, verify_rotation_prefix
from invsqrt_reset_reuse import advance_resets, lend_zeroed_inputs, reuse
from qcompile.io import sha256, write_json


START = 9870
WINDOW = (
    "CCX q20 q2 q21",
    "Z_POW q21 0.031249999448353475207419693848720498863258399069309234619140625",
    "HMR q21 b489",
    "CZ q20 q2 if b489",
    "HMR q20 b490",
)
LOAN = "CCX q20 q24 q19"
SALTS = {"control": "rotation-loan-control-20261127-dev", "loan": "rotation-loan-candidate-20261127-dev"}


def run(control: Path, simulator: Path, output: Path) -> None:
    if sha256(control) != CONTROL or sha256(simulator) != SIMULATOR:
        raise ValueError("The assembly or simulator differs from its pinned identity")
    lines = control.read_text(encoding="ascii").splitlines()
    if tuple(lines[START:START + len(WINDOW)]) != WINDOW:
        raise ValueError("The loan must restore q19 before measuring q20")
    spec = spec_from_file_location("pinned_invsqrt_sim", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the pinned source simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(control)
    verify_rotation_prefix(ops, {START + 1})
    output.mkdir(parents=True, exist_ok=False)
    receipt = output / "registration.json"
    write_json(receipt, {"classification": "development_rotation_wire_loan",
                         "assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
                         "driver_sha256": sha256(Path(__file__)), "first_edited_line": START + 1,
                         "legal_inputs": MAX_X, "unconditional_toffoli_delta": 2,
                         "verifier": {"shots_per_x": 2, "batch_size": 292, "salts": SALTS}})
    sim = km.Sim(39, "zero")
    sim.load_x(register)
    for op in ops:
        if op.line > START:
            break
        sim.apply(op)
    # With measurement-independent values through the cut, the exact
    # bit-sliced check applies to every classical outcome at each legal x.
    if km.MAX_X != MAX_X or sim.Q[21].any() or (sim.Q[19] ^ (sim.Q[20] & sim.Q[24])).any():
        raise ValueError("The loan or the original clean rotation target failed the prefix check")

    splice = [LOAN, *(line.replace("q21", "q19") for line in WINDOW[:3]), WINDOW[3], LOAN, WINDOW[4]]
    outcomes = {}
    for name, body in (("control", lines), ("loan", lines[:START] + splice + lines[START + len(WINDOW):])):
        early, _ = advance_resets([line + "\n" for line in body])
        normalized, _ = reuse(early, symbolic=True, prune=True)
        compact, width = lend_zeroed_inputs(normalized)
        path = output / f"{name}.kmx"
        with path.open("x", newline="\n", encoding="ascii") as stream:
            stream.writelines(compact)
        outcomes[name] = {"assembly_sha256": sha256(path), **width}
    write_json(output / "screen.json", {"registration_sha256": sha256(receipt),
                                         "prefix_identity": "q19=q20 AND q24; q21=0 for all legal x and outcomes",
                                         "width_screen": outcomes})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
