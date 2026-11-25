"""Plan and emit reversible checkpointed queries of D4 leading coefficients."""

import argparse
import sys
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path

import numpy as np
from dqi_compact_constraints import extend_map
from dqi_compact_layout import coefficient, split_pair
from dqi_compact_leading_basis import leading_queries
from dqi_extraction_oracle import ExternalField, original_pair
from dqi_phase_profile import load_decoder

from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored import dqi_d4_leading

Window = tuple[set[int], set[int]]


@dataclass(frozen=True)
class Plan:
    windows: list[Window]
    scratch_words: int
    factor_calls: int
    estimated_toffoli: int
    split: dict[tuple[int, int], int]


def plan_window(output: Window, initial_bank: int, length: int) -> Plan:
    # For (A,B) times one factor, supports of A->(U,V) and B->(U,V).
    # The first chart has no incoming swap. Every later factor can exchange A,B.
    support = ((range(3), range(5)), (range(2), range(3)))
    reachable: list[Window] = [({0}, set()) if initial_bank == 0 else (set(), {0})]
    for level in range(length):
        previous = reachable[-1]
        if level:
            both = previous[0] | previous[1]
            previous = both, both
        next_banks = [
            {power + offset for bank in range(2) for power in previous[bank] for offset in support[bank][col]}
            for col in range(2)
        ]
        reachable.append((next_banks[0], next_banks[1]))
    windows = [(set(), set()) for _ in range(length)] + [output]
    for level in reversed(range(length)):
        needed = tuple(
            {power - offset for col in range(2) for power in windows[level + 1][col] for offset in support[bank][col]}
            for bank in range(2)
        )
        if level:
            both = (needed[0] | needed[1]) & (reachable[level][0] | reachable[level][1])
            windows[level] = both, both
        else:
            windows[level] = needed[0] & reachable[0][0], needed[1] & reachable[0][1]
    split: dict[tuple[int, int], int] = {}

    def stage_cost(level):
        a, _ = windows[level]
        u, v = windows[level + 1]
        powers = {p - shift for p in u for shift in range(2) if p >= shift}
        powers |= {p - shift for p in v for shift in range(3) if p >= shift}
        products = sum(sum(p - shift in a for shift in range(2))
                       + sum(p + shift in u for shift in range(2)) for p in powers)
        return 42 * products + 12 * len(powers) + (24 * len(a) if level else 0)

    @lru_cache(maxsize=None)
    def cost(start, stop):
        if stop == start + 1:
            return 2, stage_cost(start), 1
        options = []
        for middle in range(start + 1, stop):
            left, right = cost(start, middle), cost(middle, stop)
            options.append((
                sum(map(len, windows[middle])) + max(left[0], right[0]),
                2 * left[1] + right[1], 2 * left[2] + right[2], middle,
            ))
        peak, gates, calls, middle = min(options)
        split[start, stop] = middle
        return peak, gates, calls

    peak, gates, calls = cost(0, length)
    return Plan(windows, peak, calls, gates, split)


def allocate(builder, window):
    return tuple({power: builder.alloc_qubits(12) for power in sorted(bank)} for bank in window)


def emit(builder, reference, plan, heads, flags, kappas, inputs, outputs):
    def section(lo, hi, left, right):
        if hi == lo + 1:
            incoming, collapse = flags[lo]
            dqi_d4_leading.xor_leading_factor(
                builder, reference, heads[lo], left, right, kappas[lo], collapse, incoming,
            )
            return
        mid = plan.split[lo, hi]
        scratch = allocate(builder, plan.windows[mid])
        section(lo, mid, left, scratch)
        section(mid, hi, scratch, right)
        section(lo, mid, left, scratch)
        for bank in scratch:
            for word in bank.values():
                builder.free(word)

    section(0, len(heads), inputs, outputs)


def run_native(km, api, reference, plans, fixture_folds, expected):
    length = len(fixture_folds[0])
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(2)] for _ in range(2 * length)]
    flags = [(None if group == 0 else builder.alloc_qubits(1)[0], builder.alloc_qubits(1)[0])
             for group in range(length)]
    live = builder.num_allocated_qubits
    word_wires = reference.combine([word for head in heads for word in head])
    flag_wires = km.array([wire for row in flags for wire in row if wire is not None])
    pairs = [heads[2 * i:2 * i + 2] for i in range(length)]
    kappas = [fold.kappa for fold in fixture_folds[0]]
    outputs = [allocate(builder, plan.windows[-1]) for plan in plans]
    inputs = [allocate(builder, plan.windows[0]) for plan in plans]

    def query():
        for row, (plan, first, last) in enumerate(zip(plans, inputs, outputs, strict=True)):
            if 0 in first[row]:
                builder.x(first[row][0][0])
            emit(builder, reference, plan, pairs, flags, kappas, first, last)
            if 0 in first[row]:
                builder.x(first[row][0][0])

    query()
    forward = builder.finish_circuit()
    out_words = [word for row in outputs for bank in row for word in bank.values()]
    builder.z(out_words[0][0])
    query()
    closed = builder.finish_circuit()
    stored = api.to_bits(np.asarray([[v for f in folds for v in f.first + f.second] for folds in fixture_folds]), 12)
    charts = np.asarray([[v for i, f in enumerate(folds)
                          for v in ((f.incoming_pole, f.collapse) if i else (f.collapse,))]
                         for folds in fixture_folds], dtype=bool).T
    wanted = api.to_bits(np.asarray(expected), 12)
    out_wires = reference.combine(out_words)
    output_set = set(out_wires)
    checked = []
    executed: dict[str, list[float]] = {"forward": [], "closed": []}
    for seed in (111, 112):
        for name, circuit in (("forward", forward), ("closed", closed)):
            sim = km.Simulator(batch_size=len(expected), seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(word_wires, stored)
            sim.write_across_shots(flag_wires, charts)
            sim.do(circuit)
            if not np.array_equal(sim.read_across_shots(word_wires), stored) or (
                not np.array_equal(sim.read_across_shots(flag_wires), charts)
            ):
                raise ValueError("Leading replay did not restore its heads and charts")
            scratch = km.array([km.q(i) for i in range(live, circuit.num_qubits) if
                                circuit is closed or km.q(i) not in output_set])
            if sim.read_across_shots(scratch).any():
                raise ValueError("Leading replay left dirty scratch")
            if circuit is forward and not np.array_equal(sim.read_across_shots(out_wires), wanted):
                raise ValueError("Native leading coefficient disagrees with the polynomial oracle")
            phase = wanted[0] if circuit is closed else np.zeros(len(expected))
            if not np.array_equal(sim.read_phase_flipped_across_shots(), phase):
                raise ValueError("Leading replay changed the recorded phase")
            executed[name].append(sim.operation_statistics().num_toffoli_like / len(expected))
        checked.append(seed)
    return {"declared_qubits": closed.num_qubits, "forward_static": forward.operation_statistics().num_toffoli_like,
            "closed_static": closed.operation_statistics().num_toffoli_like, "simulation_seeds": checked,
            "executed_means": executed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("component", "backend", "controls", "multiple_poles", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--levels", type=int, choices=range(1, 18), default=17)
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    field = GF4096()
    extension = ExternalField(field)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    fixtures = [{int(position): symbol for position, symbol in case["support"].items()}
                for case in read_json(args.multiple_poles)["cases"]]
    fixture_folds, matrices = [], []
    requested: set[tuple[int, int, int]] = set()
    for support in fixtures:
        n, d = original_pair(support, kappas, field)
        matrix = [([1], [0]), ([0], [1])]
        folds = []
        for coordinate in range(0, 2 * args.levels, 2):
            fold = split_pair(n, d, coordinate, extension)
            n, d = fold.u, fold.v
            matrix = extend_map(matrix, fold, field)
            folds.append(fold)
        leading_queries(folds, field, end_queries=requested)
        fixture_folds.append(folds)
        matrices.append(matrix)
    plans = []
    for row in range(2):
        banks = [{power for r, c, power in requested if (r, c) == (row, col)} for col in range(2)]
        plans.append(plan_window((banks[0], banks[1]), row, args.levels))
    expected = [
        [coefficient(matrix[row][col], power) for row, plan in enumerate(plans)
         for col, powers in enumerate(plan.windows[-1]) for power in sorted(powers)]
        for matrix in matrices
    ]
    settings = read_json(args.backend)
    validate_backend(settings)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    controls = read_json(args.controls)
    source = args.component / "SOURCE.json"
    if inventory != controls["backend_inventory_sha256"] or (
        sha256(source) != controls["evidence_sha256"]["third_party/dqi-d4/SOURCE.json"]
    ):
        raise ValueError("Leading probe requires the admitted inventory")
    for record in read_json(source)["files"]:
        if sha256(args.component / record["path"]) != record["sha256"]:
            raise ValueError(f"Source changed: {record['path']}")
    stage = None
    if args.emit:
        sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
        km = import_module("kickmix")
        api = import_module("dqi.verify_submission_dqi")
        ref = load_decoder(args.component / "src", km).replay_erase.ref
        stage = run_native(km, api, ref, plans, fixture_folds, expected)
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)), "witness_sha256": sha256(args.multiple_poles),
        "backend_inventory_sha256": inventory, "source_sha256": sha256(source),
        "leading_factor_sha256": sha256(Path(dqi_d4_leading.__file__)),
        "levels": args.levels, "fixture_count": len(fixtures), "requested_coefficients": len(requested),
        "plans": [{"window_words": [sum(map(len, pair)) for pair in plan.windows],
                   "scratch_words": plan.scratch_words, "calls": plan.factor_calls,
                   "estimated_toffoli": plan.estimated_toffoli} for plan in plans],
        "native": stage,
    })


if __name__ == "__main__":
    main()
