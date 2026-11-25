"""Audit reversible degree-aligned leading windows for D4."""

import argparse
import sys
from importlib import import_module
from pathlib import Path
from random import Random

from dqi_compact_constraints import extend_map
from dqi_compact_layout import Fold, coefficient, degree_envelope, forced_outer_pole
from dqi_compact_leading_basis import leading_queries
from dqi_compact_tail_basis import chart_matrix
from dqi_extraction_oracle import original_pair
from dqi_phase_profile import load_decoder

from qcompile.dqi.decoder import decode
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored import dqi_d4_leading


def geometry(fold: Fold, bounds: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the next degree origins and the two shear shifts."""
    a, b = bounds[::-1] if fold.incoming_pole else bounds
    h0_degree, h1_degree = (2, 0) if fold.collapse else (1, 1)
    c = max(b, a + h0_degree)
    u = max(a + 2, c + h1_degree)
    return (u, c + 2), (c - b, u - a - 2)


def shear_terms(fold: Fold, bounds: tuple[int, int]):
    a, b = bounds[::-1] if fold.incoming_pole else bounds
    (u, v), (db, da) = geometry(fold, bounds)
    c = v - 2
    if fold.collapse:
        h0 = [fold.first[0] ^ fold.kappa, fold.first[1] ^ 1, 1]
        h1 = [1]
    else:
        h0, h1 = fold.first, fold.second
    return (
        (db, [c - a - i for i in range(len(h0))], h0),
        (da, [u - c - i for i in range(len(h1))], h1),
    )


def shear_product(target, source, offsets, factors, field: GF4096):
    for offset, factor in zip(offsets, factors, strict=True):
        if factor:
            for depth in range(offset, len(target)):
                target[depth] ^= field.mul(factor, source[depth - offset])


def apply_shear(target, source, terms, field: GF4096, *, saved=None):
    shift, offsets, factors = terms
    shift = min(shift, len(target))
    active = len(target) - shift
    if saved is None:
        displaced = target[active:]
        target[:] = [0] * shift + target[:active]
        shear_product(target, source, offsets, factors, field)
        return displaced
    shear_product(target, source, offsets, factors, field)
    if any(target[:shift]):
        raise ValueError("Inverse shear found a nonzero shifted-in coefficient")
    target[:] = target[shift:] + saved
    return saved


def times_quadratic(bank, kappa, field: GF4096, *, reverse=False):
    # Reversed monic q is (1,t,kappa*t^2). The two traversal directions
    # make the same operation triangular in both directions.
    indices = range(1, len(bank)) if reverse else range(len(bank) - 1, 0, -1)
    for i in indices:
        bank[i] ^= bank[i - 1]
        if i >= 2:
            bank[i] ^= field.mul(kappa, bank[i - 2])


def update(banks, bounds, fold: Fold, field: GF4096, *, saved=None):
    a, b = banks
    first, second = shear_terms(fold, bounds)
    if saved is None:
        if fold.incoming_pole:
            a, b = b, a
        lost_b = apply_shear(b, a, first, field)
        times_quadratic(a, fold.kappa, field)
        lost_a = apply_shear(a, b, second, field)
        times_quadratic(b, fold.kappa, field)
        return (a, b), (lost_b, lost_a)
    lost_b, lost_a = saved
    times_quadratic(b, fold.kappa, field, reverse=True)
    apply_shear(a, b, second, field, saved=lost_a)
    times_quadratic(a, fold.kappa, field, reverse=True)
    apply_shear(b, a, first, field, saved=lost_b)
    return ((b, a) if fold.incoming_pole else (a, b)), saved


def band(poly, bound: int, width: int) -> list[int]:
    return [coefficient(poly, power) if power >= 0 else 0 for power in range(bound, bound - width, -1)]


def prepare(support, field: GF4096):
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in range(0, 34, 2) for _ in range(2)]
    tail, folds, matrix = chart_matrix(original_pair(support, kappas, field), field)
    bounds = [(0, 0)]
    for fold in folds:
        bounds.append(geometry(fold, bounds[-1])[0])
    end_queries: set[tuple[int, int, int]] = set()
    leading_queries(folds, field, end_queries=end_queries)
    width = 1 + max(bounds[-1][bank] - power for _, bank, power in end_queries)
    return folds, matrix, bounds, end_queries, width, tail


def inspect(support, field: GF4096) -> dict:
    folds, _, bounds, end_queries, width, tail = prepare(support, field)
    matrix = [([1], [0]), ([0], [1])]
    initial = [tuple(band(poly, 0, width) for poly in row) for row in matrix]
    pairs = [tuple(bank[:] for bank in row) for row in initial]
    history = []
    for i, fold in enumerate(folds):
        matrix = extend_map(matrix, fold, field)
        captured = []
        for row, pair in enumerate(pairs):
            pairs[row], saved = update(pair, bounds[i], fold, field)
            captured.append(saved)
            expected = tuple(band(poly, bound, width) for poly, bound in zip(matrix[row], bounds[i + 1], strict=True))
            if pairs[row] != expected:
                raise ValueError("Aligned band differs from independent polynomial factor product")
        history.append(captured)
    for i in reversed(range(len(folds))):
        for row, pair in enumerate(pairs):
            pairs[row], _ = update(pair, bounds[i], folds[i], field, saved=history[i][row])
    if pairs != initial:
        raise ValueError("Aligned inverse changed its initial bands")
    shifts = [geometry(fold, bounds[i])[1] for i, fold in enumerate(folds)]
    count = 0
    for fold in reversed(folds):
        if not (fold.incoming_pole and fold.collapse and not any(fold.first)):
            break
        count += 1
    d_bound = degree_envelope(folds[:len(folds) - count])[1]
    # Each suffix fold outputs V=D/q². Distinct monic quadratics
    # whose combined degree exceeds the starting bound force V=0.
    shortcut = count > 0 and 4 * count > d_bound
    if shortcut and (tail[1] != [0] or len(tail[0]) != 1 or not tail[0][0]):
        raise ValueError("Certified termination must end on a nonzero constant numerator")

    def words(row: int, *, populated: bool) -> int:
        return sum(sum(bool(v) for v in bank) if populated else len(bank)
                   for snapshot in history for bank in snapshot[row])
    return {
        "weight": len(support),
        "requested_words": len(end_queries),
        "degree_origins": [list(pair) for pair in bounds],
        "required_band_words": width,
        "shear_shifts": [list(pair) for pair in shifts],
        "retained_words_per_row": words(0, populated=False),
        "nonzero_history_by_row": [words(row, populated=True) for row in range(2)],
        "row_storage_words": 2 * width + words(0, populated=False),
        "termination_suffix": {"count": count, "input_denominator_bound": d_bound, "certified": shortcut},
    }


def native_row(km, api, reference, prepared, row):
    """Emit the leading replay with a single preselected chart schedule."""
    np = import_module("numpy")
    folds, matrix, bounds, queries, width, _ = prepared
    builder = km.CircuitBuilder()
    heads = [[builder.alloc_qubits(12) for _ in range(4)] for _ in folds]
    head_wires = reference.combine([word for group in heads for word in group])
    head_values = api.to_bits(np.array([[v for fold in folds for v in fold.first + fold.second]]), 12)
    initial = tuple([builder.alloc_qubits(12) for _ in range(width)] for _ in range(2))
    builder.x(initial[row][0][0])
    a, b = initial
    replay = []
    for i, fold in enumerate(folds):
        if fold.incoming_pole:
            a, b = b, a
        (db, ob, _), (da, oa, _) = shear_terms(fold, bounds[i])
        add_b = [builder.alloc_qubits(12) for _ in range(min(db, width))]
        b = (add_b + b)[:width]
        h0 = list(zip(ob[:2], heads[i][:2], strict=True))
        constants0 = list(zip(ob, (fold.kappa, 1, 1), strict=True)) if fold.collapse else []
        dqi_d4_leading.aligned_shear(builder, reference, a, b, h0, constants0)
        dqi_d4_leading.aligned_quadratic(builder, reference, a, fold.kappa)
        add_a = [builder.alloc_qubits(12) for _ in range(min(da, width))]
        a_next = (add_a + a)[:width]
        h1 = [] if fold.collapse else list(zip(oa, heads[i][2:], strict=True))
        constants1 = [(oa[0], 1)] if fold.collapse else []
        dqi_d4_leading.aligned_shear(builder, reference, b, a_next, h1, constants1)
        dqi_d4_leading.aligned_quadratic(builder, reference, b, fold.kappa)
        replay.append((a, b, a_next, add_a, add_b, h0, h1, constants0, constants1, fold.kappa))
        a = a_next

    words = reference.combine(a + b)
    readout = [band(poly, bound, width) for poly, bound in zip(matrix[row], bounds[-1], strict=True)]
    expected = [v for values in readout for v in values]
    forward = builder.finish_circuit()
    # Fingerprint a requested nonzero coefficient so a missing phase is visible.
    col, power = next((col, p) for r, col, p in sorted(queries)
                      if r == row and coefficient(matrix[row][col], p))
    depth = bounds[-1][col] - power
    word = (a, b)[col][depth]
    value = readout[col][depth]
    builder.z(word[(value & -value).bit_length() - 1])
    for a, b, next_a, add_a, add_b, h0, h1, c0, c1, kappa in reversed(replay):
        dqi_d4_leading.aligned_quadratic(builder, reference, b, kappa, reverse=True)
        dqi_d4_leading.aligned_shear(builder, reference, b, next_a, h1, c1)
        for word in add_a:
            builder.free(word)
        dqi_d4_leading.aligned_quadratic(builder, reference, a, kappa, reverse=True)
        dqi_d4_leading.aligned_shear(builder, reference, a, b, h0, c0)
        for word in add_b:
            builder.free(word)
    builder.x(initial[row][0][0])
    closed = builder.finish_circuit()
    scratch = km.array([km.q(i) for i in range(len(head_wires), closed.num_qubits)])
    counts: dict[str, list[int]] = {"forward": [], "closed": []}
    for seed in (111, 112):
        for name, circuit in (("forward", forward), ("closed", closed)):
            sim = km.Simulator(batch_size=1, seed=seed, counting_operations=True)
            sim.use_same_registers_as(circuit)
            sim.write_across_shots(head_wires, head_values)
            sim.do(circuit)
            if not np.array_equal(sim.read_across_shots(head_wires), head_values):
                raise ValueError("Native aligned replay changed the heads")
            if circuit is forward and not np.array_equal(sim.read_across_shots(words), api.to_bits(np.array([expected]), 12)):
                raise ValueError("Native aligned replay disagrees with the full polynomial")
            if circuit is closed and sim.read_across_shots(scratch).any():
                raise ValueError("Native aligned inverse retained scratch")
            if bool(sim.read_phase_flipped_across_shots()[0]) != (circuit is closed):
                raise ValueError("Native aligned replay disagrees with the phase fingerprint")
            counts[name].append(sim.operation_statistics().num_toffoli_like)
    return {"qubits": closed.num_qubits, "forward_gates": forward.operation_statistics().num_toffoli_like,
            "closed_gates": closed.operation_statistics().num_toffoli_like, "executed": counts}


def load_native(component: Path, backend: Path, controls: Path):
    settings = read_json(backend)
    validate_backend(settings)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    pins = read_json(controls)
    source = component / "SOURCE.json"
    if inventory != pins["backend_inventory_sha256"] or (
        sha256(source) != pins["evidence_sha256"]["third_party/dqi-d4/SOURCE.json"]
    ):
        raise ValueError("Aligned probe requires the admitted inventory")
    for record in read_json(source)["files"]:
        if sha256(component / record["path"]) != record["sha256"]:
            raise ValueError(f"Source changed: {record['path']}")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = import_module("kickmix")
    api = import_module("dqi.verify_submission_dqi")
    return (km, api, load_decoder(component / "src", km).replay_erase.ref), inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("historical", "residual", "multiple_poles", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--native", nargs=3, type=Path, metavar=("COMPONENT", "BACKEND", "CONTROLS"))
    args = parser.parse_args()
    field = GF4096()
    cases = {}
    captures = {}
    for directory in (args.historical, args.residual):
        for path in sorted(directory.glob("s*/batch-*.json")):
            captures[f"{directory.name}/{path.parent.name}/{path.name}"] = sha256(path)
            batch = read_json(path)
            for shot in batch["shots"] + batch["controls"]:
                cases[f"{path.parent.name}/{shot['index']}"] = decode(shot["syndrome"], field)
    for index, case in enumerate(read_json(args.multiple_poles)["cases"], 1):
        cases[f"multiple/{index}"] = {int(position): symbol for position, symbol in case["support"].items()}
    rng = Random(8935)
    for weight in range(36):
        cases[f"sample/{weight}"] = {position: rng.randrange(1, 4096) for position in rng.sample(range(4095), weight)}
    for weight in (34, 35):
        cases[f"forced/{weight}"] = forced_outer_pole(weight, rng, field)
    native = None
    if args.native:
        runtime, inventory = load_native(*args.native)
        selected = {"sample/35", "multiple/1", "multiple/2", "multiple/3", "s2/45440", "s6/102316", "s7/52983"}
        native = {"backend_inventory_sha256": inventory, "rows": {}}
        for name in sorted(selected):
            prepared = prepare(cases[name], field)
            native["rows"][name] = [native_row(*runtime, prepared, row) for row in range(2)]
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)),
        "adapter_sha256": sha256(Path(dqi_d4_leading.__file__)),
        "captures": captures,
        "multiple_poles_sha256": sha256(args.multiple_poles),
        "cases": [{"case": name, **inspect(support, field)} for name, support in cases.items()],
        "native": native,
    })


if __name__ == "__main__":
    main()
