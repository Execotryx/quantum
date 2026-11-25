"""Run the full compact synthesis, converter, and projected scan on supplied states."""

import argparse
import importlib
import sys
from pathlib import Path
from random import Random

import numpy as np
from dqi_compact_layout import forced_outer_pole, split_pair
from dqi_extraction_oracle import ExternalField, original_pair
from dqi_phase_profile import load_decoder

from qcompile.dqi.decoder import _add, _divide, _multiply, decode, syndrome
from qcompile.dqi.field import GF4096
from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored.dqi_d4_compact import (
    absorb_compact_pair,
    absorb_projected_outer,
    compact_tail_jet,
    extract_compact_heads,
)


def pad(values, width):
    if len(values) > width:
        raise ValueError(f"Coefficient vector of length {len(values)} exceeds {width}")
    return [*values, *([0] * (width - len(values)))]


def prepare(support, field: GF4096):
    coordinates = range(0, 34, 2)
    kappas = [field.mul(c, c) ^ c ^ 2048 for c in coordinates for _ in range(2)]
    n, d = original_pair(support, kappas, field)
    locator = d
    extension = ExternalField(field)
    heads, flags = [], []
    evaluator = None
    for group, c in enumerate(coordinates):
        fold = split_pair(n, d, c, extension)
        b = 35 - 2 * group
        if fold.minimum_v_slots > b or (
            fold.incoming_pole and max(len(n), len(d)) > b + 2
        ):
            raise ValueError(f"Raw layout cannot carry the supplied chart at group {group}")
        if group == 0:
            evaluator, remainder = _divide(
                _add(n, _multiply(fold.first, d, field)), [2048, 1, 1], field,
            )
            if remainder != [0] or fold.incoming_pole:
                raise ValueError("Projected outer boundary requires a finite first head")
        heads.extend(fold.first + fold.second)
        flags.extend((fold.collapse,) if group == 0 else (fold.incoming_pole, fold.collapse))
        n, d = fold.u, fold.v
    assert evaluator is not None
    return heads + pad(n, 5) + pad(d, 3), flags, pad(evaluator, 37) + pad(locator, 37)


def padding_polynomial(weight: int, field: GF4096):
    missing = 35 - weight
    polynomial = [0, 1] if missing % 2 else [1]
    for c in range(34, 34 + missing - (missing % 2), 2):
        q = [field.mul(c, c) ^ c ^ 2048, 1, 1]
        polynomial = _multiply(polynomial, q, field)
    return polynomial


def apply_padding(builder, ref, words, polynomial, *, reverse=False):
    """Multiply with a known monic polynomial using the zero high slots."""
    degree = len(polynomial) - 1

    def rotate(undo=False):
        for _ in range(degree):
            order = range(1, len(words)) if undo else reversed(range(1, len(words)))
            for i in order:
                builder.swap(words[i], words[i - 1])

    if not reverse:
        rotate()
    positions = range(len(words) - degree)
    for offset in reversed(positions) if reverse else positions:
        for shift, coefficient in enumerate(polynomial[:-1]):
            ref.cx(builder, words[offset + degree], words[offset + shift], coefficient)
    if reverse:
        rotate(True)


def build(km, ref, padding):
    builder = km.CircuitBuilder()
    initial = [builder.alloc_qubits(12) for _ in range(76)]
    original = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    pad_cases = builder.alloc_bits(len(padding))
    flags = builder.alloc_qubits(33)
    phases = []
    history = []
    u, v = initial[68:73], initial[73:]
    for group in reversed(range(1, 17)):
        start = 4 * group
        heads = initial[start:start + 2], initial[start + 2:start + 4]
        history.append((group, heads, u, v))
        u, v = absorb_compact_pair(
            builder, ref, heads, u, v, 2 * group, flags[2 * group],
            incoming_pole=flags[2 * group - 1], phase_masks=phases,
        )
    evaluator, locator = absorb_projected_outer(builder, ref, initial[2:4], u, v, flags[0], phase_masks=phases)
    forward = builder.finish_circuit()
    def normalize(reverse=False):
        for bit, polynomial in zip(pad_cases, padding, strict=True):
            builder.push_condition(bit)
            apply_padding(builder, ref, evaluator, polynomial, reverse=reverse)
            apply_padding(builder, ref, locator, polynomial, reverse=reverse)
            builder.pop_condition()

    normalize()
    converter = importlib.import_module("high_stream").convert_safe
    mask_token = ref.baseline.project(builder, original, masks)
    token = converter(builder, evaluator[:35], locator[:35], monic_root=True)
    ref.baseline.scan(builder, evaluator[:35], locator[:35], masks,
                      skip_points=ref.baseline.SELECTED, node_polynomial=ref.Pscan)
    converter(builder, evaluator[:35], locator[:35], True, phase_token=token, monic_root=True)
    ref.baseline.restore(builder, masks, mask_token)
    normalize(True)
    absorb_projected_outer(builder, ref, initial[2:4], u, v, flags[0], reverse=True, phase_masks=phases)
    for group, heads, before_u, before_v in reversed(history):
        absorb_compact_pair(
            builder, ref, heads, before_u, before_v, 2 * group, flags[2 * group],
            incoming_pole=flags[2 * group - 1], reverse=True, phase_masks=phases,
        )
    if phases:
        raise ValueError("Ladder left unpaid phase masks")
    return (
        forward, builder.finish_circuit(), ref.combine(initial), ref.combine(original),
        ref.combine(masks), km.array(flags), ref.combine(evaluator + locator), km.array(pad_cases),
    )


def measure_extraction(km, api, ref, field, original, prepared, charts):
    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    syndrome_wires = ref.combine(words)
    ref.linear_words(builder, words, ref.matrix)
    token = extract_compact_heads(builder, ref, words)
    denominator = compact_tail_jet(builder, ref, words, token)
    head_wires = ref.combine(words[:68])
    tail_wires = ref.combine([words[-2], denominator, words[-1]])
    chart_wires = km.array([
        wire for collapse, _, chain in token for wire in ([collapse] if chain is None else [chain["pole"], collapse])
    ])
    forward = builder.finish_circuit()
    compact_tail_jet(builder, ref, words, token, reverse=True, denominator=denominator)
    extract_compact_heads(builder, ref, words, reverse=True, token=token)
    ref.linear_words(builder, words, ref.matrix, True)
    closed = builder.finish_circuit()
    expected = api.to_bits(np.asarray([row[:68] for row in prepared]), 12)
    scratch = km.array([km.q(i) for i in range(840, closed.num_qubits)])
    means = []
    for seed in (991, 992):
        sim = km.Simulator(batch_size=len(prepared), seed=seed)
        sim.use_same_registers_as(forward)
        sim.write_across_shots(syndrome_wires, original)
        sim.do(forward)
        if not np.array_equal(sim.read_across_shots(head_wires), expected) or (
            not np.array_equal(sim.read_across_shots(chart_wires), charts)
        ):
            raise ValueError("Native extraction differs from the supplied synthesis heads or charts")
        vectors = sim.read_across_shots(tail_wires).T.reshape(len(prepared), 3, 12) @ (1 << np.arange(12))
        for observed, row in zip(vectors, prepared, strict=True):
            n0, n1, d0, d1 = row[68], row[69], row[73], row[74]
            n, d, slope = map(int, observed)
            scale = field.div(d, d0) if d0 else field.div(n, n0)
            derivative = field.mul(n0, d1) ^ field.mul(d0, n1)
            expected_tail = field.mul(scale, n0), field.mul(scale, d0), field.mul(field.mul(scale, scale), derivative)
            if not scale or (n, d, slope) != expected_tail:
                raise ValueError("Native tail jet differs from the supplied synthesis tail")
        sim = km.Simulator(batch_size=len(prepared), seed=seed, counting_operations=True)
        sim.use_same_registers_as(closed)
        sim.write_across_shots(syndrome_wires, original)
        sim.do(closed)
        if not np.array_equal(sim.read_across_shots(syndrome_wires), original) or (
            sim.read_across_shots(scratch).any() or sim.read_phase_flipped_across_shots().any()
        ):
            raise ValueError("Compact extraction did not close cleanly")
        means.append(sim.operation_statistics().num_toffoli_like / len(prepared))
    return {"declared_qubits": closed.num_qubits, "executed_means": means}


def run_probe(component: Path, backend: Path, controls: Path, batches: list[Path], output: Path) -> None:
    settings = read_json(backend)
    validate_backend(settings)
    manifest = component / "SOURCE.json"
    pins = read_json(controls)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    if inventory != pins["backend_inventory_sha256"] or (
        sha256(manifest) != pins["evidence_sha256"]["third_party/dqi-d4/SOURCE.json"]
    ):
        raise ValueError("Synthesis probe requires the admitted D4 inventory")
    for record in read_json(manifest)["files"]:
        if sha256(component / record["path"]) != record["sha256"]:
            raise ValueError(f"Upstream source changed: {record['path']}")
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    api = importlib.import_module("dqi.verify_submission_dqi")
    ref = load_decoder(component / "src", km).replay_erase.ref
    field = GF4096()
    fixtures = []
    capture_hashes = {}
    for path in batches:
        capture_hashes[f"{path.parent.name}/{path.name}"] = sha256(path)
        batch = read_json(path)
        for shot in batch["shots"] + batch["controls"]:
            fixtures.append((f'{path.parent.name}/{shot["index"]}', shot["syndrome"], shot["mask"], shot["expected_phase"]))
    rng = Random(55022)
    for weight in (0, 34, 35):
        errors = forced_outer_pole(weight, rng, field) if weight else {}
        fixtures.append((f"constructed/{weight}", syndrome(errors, field), [rng.randrange(4096) for _ in range(4095)], None))
    decoded = [decode(words, field) for _, words, _, _ in fixtures]
    staged, charts, projected = zip(*(prepare(support, field) for support in decoded), strict=True)
    weights = sorted({len(support) for support in decoded})
    forward, closed, states, original, masks, flags, root, pad_cases = build(
        km, ref, [padding_polynomial(weight, field) for weight in weights],
    )
    heads_bits = api.to_bits(np.asarray(staged), 12)
    symbol_bits = api.to_bits(np.asarray([words for _, words, _, _ in fixtures]), 12)
    root_bits = api.to_bits(np.asarray(projected), 12)
    chart_bits = np.asarray(charts, dtype=bool).T
    pad_bits = np.asarray([[len(support) == weight for support in decoded] for weight in weights])
    scratch = km.array([km.q(i) for i in range(76 * 12 + 70 * 12 + 33, closed.num_qubits)])
    rows = []
    for seed in (991, 992):
        sim = km.Simulator(batch_size=len(fixtures), seed=seed)
        sim.use_same_registers_as(forward)
        sim.write_across_shots(states, heads_bits)
        sim.write_across_shots(flags, chart_bits)
        sim.do(forward)
        if not np.array_equal(sim.read_across_shots(root), root_bits):
            raise ValueError("Native synthesis changed a projected coefficient")
        mask_values = np.asarray([mask for _, _, mask, _ in fixtures], dtype=np.int64)
        if seed == 992:
            mask_values ^= np.random.default_rng(488).integers(0, 4096, size=mask_values.shape, dtype=np.int64)
        expected = np.asarray([
            sum((symbol & int(mask[position])).bit_count() for position, symbol in support.items()) % 2
            for mask, support in zip(mask_values, decoded, strict=True)
        ])
        if seed == 991 and any(
            case[-1] is not None and phase != case[-1] for case, phase in zip(fixtures, expected, strict=True)
        ):
            raise ValueError("Reconstructed phase disagrees with the retained capture")
        mask_bits = api.to_bits(mask_values, 12)
        sim = km.Simulator(batch_size=len(fixtures), seed=seed, counting_operations=True)
        sim.use_same_registers_as(closed)
        live = ((states, heads_bits), (original, symbol_bits), (flags, chart_bits), (masks, mask_bits),
                (pad_cases, pad_bits))
        for wires, bits in live:
            sim.write_across_shots(wires, bits)
        sim.do(closed)
        restored = all(np.array_equal(sim.read_across_shots(wires), bits) for wires, bits in live)
        if not restored or sim.read_across_shots(scratch).any():
            raise ValueError("Synthesis probe failed to restore its inputs or scratch")
        if not np.array_equal(sim.read_phase_flipped_across_shots(), expected):
            raise ValueError("Projected conversion changed a fixture phase")
        rows.append({"seed": seed, "count": len(fixtures),
                     "executed_mean": sim.operation_statistics().num_toffoli_like / len(fixtures)})
    synthesis_width = closed.num_qubits
    synthesis_static = closed.operation_statistics().num_toffoli_like
    del forward, closed, sim
    extraction = measure_extraction(km, api, ref, field, symbol_bits, staged, chart_bits)
    write_json(output, {
        "driver_sha256": sha256(Path(__file__)), "backend_inventory_sha256": inventory,
        "source_sha256": sha256(manifest), "captures": capture_hashes, "inputs": [case[0] for case in fixtures],
        "supplied_head_and_tail": True, "diagnostic_syndrome_copy_qubits": 840,
        "diagnostic_prepared_padding_weights": weights,
        "declared_qubits": synthesis_width, "static_toffoli_like": synthesis_static,
        "runs": rows, "extraction": extraction,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("component", "backend", "controls", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("batches", type=Path, nargs="+")
    args = parser.parse_args()
    run_probe(args.component, args.backend, args.controls, args.batches, args.output)


if __name__ == "__main__":
    main()
