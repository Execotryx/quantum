"""Freeze circular BM forward and reverse fixture data from a registered seed."""

import argparse
from dataclasses import asdict
from pathlib import Path

import numpy as np
from dqi_history_depth import runtime

from qcompile.dqi.bm_circular import WIDTH, CircularState, reverse_circular, step_circular, template_indices
from qcompile.dqi.bm_reference import discrepancy
from qcompile.dqi.field import GF4096
from qcompile.io import identity, sha256, write_json


def freeze(backend: Path, output: Path, seed: int) -> None:
    if seed < 0:
        raise ValueError("fixture seed must be nonnegative")
    backend_hash = sha256(backend)
    _, _, api, native_field = runtime(backend)
    field = GF4096()
    spec = api.ProblemSpecDQI.benchmark_instance(num_shots=1)
    tables = api.FieldTables(native_field)
    weights = api.optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2
    initial = CircularState((1,) + (0,) * (WIDTH - 1), (1,) + (0,) * (WIDTH - 1), 0)
    cases = []
    for case_seed in (seed, seed + 1, seed + 2, None):
        if case_seed is None:
            sequence = [0] * spec.n
        else:
            sampled, _, _ = api.sample_shots(spec, tables, np.random.default_rng(case_seed), 1, weights)
            sequence = sampled[0].tolist()
        state = initial
        trace = []
        for r in range(1, spec.n + 1):
            previous = state
            state, history = step_circular(previous, sequence, r, field)
            wrap = previous.template[template_indices(r, WIDTH)[0]]
            kind = ("replace" if history.replace else "retain" if history.retained_discrepancy
                    else "zero_wrapped" if wrap else "zero")
            trace.append({"r": r, "case": kind, "offset": (1 - r) % WIDTH, "counter": state.counter,
                          "branch": int(history.replace), "W": history.retained_discrepancy,
                          "sigma_sha256": identity(state.sigma), "template_sha256": identity(state.template)})
        cases.append({"seed": case_seed, "syndromes": sequence, "rounds": trace})

    synthetic = []
    rng = np.random.default_rng(seed + 3)
    for active in (3, 12, 36):
        r = active - 1
        wrap = template_indices(r, WIDTH)[0]
        for kind in ("zero", "zero_wrapped", "retain", "replace"):
            sigma = rng.integers(0, 4096, size=active).tolist() + [0] * (WIDTH - active)
            sigma[0] = int(rng.integers(1, 4096))
            template = rng.integers(0, 4096, size=WIDTH).tolist()
            template[wrap] = int(rng.integers(1, 4096)) if kind == "zero_wrapped" else 0
            sequence = rng.integers(0, 4096, size=70).tolist()
            desired = int(rng.integers(1, 4096)) if kind in ("retain", "replace") else 0
            delta = discrepancy(sigma, sequence, r - 1, field)
            sequence[r - 1] ^= field.div(delta ^ desired, sigma[0])
            state = CircularState(tuple(sigma), tuple(template), -3 if kind == "retain" else 3)
            advanced, history = step_circular(state, sequence, r, field)
            reversed_state = reverse_circular(advanced, history, sequence, r, field)
            synthetic.append({"r": r, "active_width": active, "case": kind, "syndromes": sequence,
                              "initial": asdict(state), "advanced": asdict(advanced),
                              "history": asdict(history), "reversed": asdict(reversed_state)})
    if sha256(backend) != backend_hash:
        raise ValueError("backend changed while freezing round states")
    write_json(output, {"seed": seed, "backend_sha256": backend_hash, "sampled": cases, "synthetic": synthetic})
    print(sha256(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    freeze(args.backend, args.output, args.seed)
