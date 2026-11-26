"""Prove affine replacement of incumbent value gates on its legal inputs."""

import argparse
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import numpy as np

from chem_endpoint_products import _affine_controls
from invsqrt_phase_margin import CONTROL, MAX_X, SIMULATOR
from qcompile.io import sha256, write_json


VALUE_GATES = {"X", "CX", "CCX", "SWAP", "CSWAP", "HMR", "R"}
WIDTH = 39
SAMPLE_SIZE = 8192
SEED = 35149


def affine_update(op: Any, sim: Any, active: int) -> list[str] | None:
    """Find a Clifford update using untouched wires or the two-target parity."""
    targets = op.q[2:] if op.name == "CCX" else op.q[1:]
    state = {f"q{i}": int.from_bytes(plane.tobytes(), "little") for i, plane in enumerate(sim.Q)}
    target_names = [f"q{i}" for i in targets]
    if op.name == "CCX":
        delta = state[f"q{op.q[0]}"] & state[f"q{op.q[1]}"]
    else:
        state["pair_parity"] = state[target_names[0]] ^ state[target_names[1]]
        delta = state[f"q{op.q[0]}"] & state["pair_parity"]
    for target in target_names:
        del state[target]
    expression = _affine_controls(delta, state, "", active)
    if expression is None:
        return None
    invert, wires = expression
    result = []
    if "pair_parity" in wires:
        wires.remove("pair_parity")
        result.append("SWAP " + " ".join(target_names))
    for target in target_names:
        if invert:
            result.append(f"X {target}")
        result.extend(f"CX {wire} {target}" for wire in wires)
    return result


def scan(km: Any, ops: list[Any], register: Any, xs: Any, selected: set[int] | None
         ) -> tuple[dict[int, list[str]], dict[str, int], int]:
    sim = km.Sim(WIDTH, "zero", xs=xs)
    sim.load_x(register)
    active = (1 << sim.n) - 1
    rewrites = {}
    counts: Counter[str] = Counter()
    barrier = 0
    for op in ops:
        guarded = bool(sim.stack) or op.cond is not None
        if guarded and op.name in VALUE_GATES:
            barrier = op.line
            break
        if not guarded and op.name in {"CCX", "CSWAP"} and (selected is None or op.line in selected):
            counts[op.name] += 1
            replacement = affine_update(op, sim, active)
            if replacement is not None:
                rewrites[op.line] = replacement
        sim.apply(op)
    return rewrites, dict(counts), barrier


def run(assembly: Path, simulator: Path, output: Path) -> None:
    if (sha256(assembly), sha256(simulator)) != (CONTROL, SIMULATOR):
        raise ValueError("Unexpected source or simulator")
    spec = spec_from_file_location("affine_routing_simulator", simulator)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load the source simulator")
    km = module_from_spec(spec)
    spec.loader.exec_module(km)
    ops, register = km.parse_kmx(assembly)
    if len(register) != 22 or km.num_wires(ops) != WIDTH or km.MAX_X != MAX_X:
        raise ValueError("Unexpected complete inverse-square-root domain or width")
    output.mkdir(parents=True, exist_ok=False)
    sample = np.sort(np.random.default_rng(SEED).choice(MAX_X, SAMPLE_SIZE, replace=False)) + 1
    sample_hits, counts, barrier = scan(km, ops, register, sample, None)
    exact, exact_counts, exact_barrier = scan(km, ops, register, None, set(sample_hits))
    if barrier != exact_barrier or sum(exact_counts.values()) != len(sample_hits):
        raise ValueError("The full scan used a different measurement-dependence boundary")
    by_line = {op.line: op.name for op in ops}
    result: dict[str, Any] = {
        "classification": "full_legal_domain_affine_value_gate_screen",
        "assembly_sha256": CONTROL, "simulator_sha256": SIMULATOR,
        "driver_sha256": sha256(Path(__file__)), "sample_size": SAMPLE_SIZE, "sample_seed": SEED,
        "legal_inputs": MAX_X, "first_measurement_guarded_value_line": barrier,
        "screened_by_opcode": counts, "sample_only_hits": sorted(sample_hits.keys() - exact.keys()),
        "proven_saved_gates_by_opcode": dict(Counter(by_line[line] for line in exact)),
        "replacements": exact,
    }
    if exact:
        candidate = output / "candidate.kmx"
        lines = assembly.read_text(encoding="ascii").splitlines()
        replacement_lines = (gate for index, line in enumerate(lines, 1) for gate in exact.get(index, [line]))
        candidate.write_text("\n".join(replacement_lines) + "\n", encoding="ascii", newline="\n")
        result["candidate_kmx_sha256"] = sha256(candidate)
    write_json(output / "screen.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly", "simulator", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
