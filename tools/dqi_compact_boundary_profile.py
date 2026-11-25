"""Measure compact extraction replays and synthesis boundaries without full pricing."""

import argparse
import importlib
import sys
from pathlib import Path

from dqi_phase_profile import load_decoder

from qcompile.io import identity, read_json, sha256, write_json
from qcompile.official import BACKEND_PATHS, validate_backend
from qcompile.vendored.dqi_d4_compact import (
    absorb_compact_pair,
    absorb_projected_outer,
    compact_tail_jet,
    extract_compact_heads,
)


def summarize(builder, forward) -> dict:
    closed = builder.finish_circuit()
    return {
        "declared_qubits": closed.num_qubits,
        "forward_static": forward.operation_statistics().num_toffoli_like,
        "closed_static": closed.operation_statistics().num_toffoli_like,
        "classical_bits": closed.num_bits,
    }


def extraction(km, reference, scalar: bool) -> dict:
    builder = km.CircuitBuilder()
    words = [builder.alloc_qubits(12) for _ in range(70)]
    reference.linear_words(builder, words, reference.matrix)
    token = extract_compact_heads(builder, reference, words)
    denominator = compact_tail_jet(builder, reference, words, token)
    forward = builder.finish_circuit()
    compact_tail_jet(builder, reference, words, token, reverse=True, denominator=denominator)
    extract_compact_heads(builder, reference, words, reverse=True, token=token, scalar_replay=scalar)
    reference.linear_words(builder, words, reference.matrix, True)
    return summarize(builder, forward)


def synthesis(km, reference, size: int, defer: bool) -> dict:
    builder = km.CircuitBuilder()
    heads = [tuple([builder.alloc_qubits(12) for _ in range(2)] for _ in range(2)) for _ in range(17)]
    collapse = builder.alloc_qubits(17)
    # Reserve the 16 incoming chart wires kept live across synthesis.
    incoming = builder.alloc_qubits(16)
    u = [builder.alloc_qubits(12) for _ in range(size + 2)]
    v = [builder.alloc_qubits(12) for _ in range(size)]
    live = builder.num_allocated_qubits
    phase_masks = [] if defer else None
    layout = []
    for group in reversed(range(1, 17)):
        layout.append((group, u, v))
        u, v = absorb_compact_pair(builder, reference, heads[group], u, v, 2 * group,
                                   collapse[group], incoming_pole=incoming[group - 1], phase_masks=phase_masks)
    absorb_projected_outer(builder, reference, heads[0][1], u, v, collapse[0], phase_masks=phase_masks)
    forward = builder.finish_circuit()
    absorb_projected_outer(builder, reference, heads[0][1], u, v, collapse[0],
                           reverse=True, phase_masks=phase_masks)
    for group, old_u, old_v in reversed(layout):
        absorb_compact_pair(builder, reference, heads[group], old_u, old_v, 2 * group,
                            collapse[group], incoming_pole=incoming[group - 1], reverse=True, phase_masks=phase_masks)
    if phase_masks:
        raise ValueError("Synthesis profile left unpaid phase masks")
    return {"initial_qubits": live, **summarize(builder, forward)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("component", "backend", "controls", "layout_audit", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    settings = read_json(args.backend)
    validate_backend(settings)
    inventory = identity({key: value for key, value in settings.items() if key not in BACKEND_PATHS})
    controls = read_json(args.controls)
    source = args.component / "SOURCE.json"
    if inventory != controls["backend_inventory_sha256"] or (
        sha256(source) != controls["evidence_sha256"]["third_party/dqi-d4/SOURCE.json"]
    ):
        raise ValueError("Profile requires the admitted inventory")
    for record in read_json(source)["files"]:
        if sha256(args.component / record["path"]) != record["sha256"]:
            raise ValueError(f"Source changed: {record['path']}")
    layout = read_json(args.layout_audit)
    size = max(row["minimum_tail_v_slots"] for row in layout["cases"] if row["pairs"] == 17)
    adapters = Path(__file__).resolve().parents[1] / "src/qcompile/vendored"
    adapter_hashes = {name: sha256(adapters / name) for name in ("dqi_d4.py", "dqi_d4_compact.py")}
    sys.path[:0] = [settings["kickmix_root"], settings["verifiers_root"]]
    km = importlib.import_module("kickmix")
    reference = load_decoder(args.component / "src", km).replay_erase.ref
    gates = {}
    for name, scalar in (("derivative_replay", False), ("scalar_replay", True)):
        gates[name] = extraction(km, reference, scalar)
        print(name, gates[name], flush=True)
    for name, defer in (("repaid_immediately", False), ("deferred_phase", True)):
        gates[name] = synthesis(km, reference, size, defer)
        print(name, gates[name], flush=True)
    if any(sha256(adapters / name) != expected for name, expected in adapter_hashes.items()):
        raise ValueError("Adapter changed during native profiling")
    write_json(args.output, {
        "driver_sha256": sha256(Path(__file__)), "source_sha256": sha256(source),
        "backend_inventory_sha256": inventory, "layout_audit_sha256": sha256(args.layout_audit),
        "adapter_sha256": adapter_hashes,
        "minimum_tail_v_slots": size, "boundaries": gates,
    })


if __name__ == "__main__":
    main()
