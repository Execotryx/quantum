"""Price two model-only inverse-square-root geometry/workspace screens."""

import json

from invsqrt_opportunity import ROOT, backend, counts

from qcompile.invsqrt.direct import _load_table
from qcompile.invsqrt.direct_screen import complete_cost
from qcompile.invsqrt.unlookup import unlookup
from qcompile.io import sha256


def prefixes(keys: range, width: int) -> int:
    """Native unary tree ANDs: roots are address bits, not allocated ANDs."""
    return sum(len({key >> (width - depth) for key in keys}) for depth in range(2, width + 1))


def main() -> None:
    km, primitives, _ = backend()
    directory = ROOT / "docs/evidence/invsqrt-lattice-20261108"
    table_path = directory / "28-20-14.json"
    native_path = directory / "native-28-20-14/result.json"
    table_record = json.loads(table_path.read_text(encoding="utf-8"))
    native = json.loads(native_path.read_text(encoding="utf-8"))
    table = tuple(tuple(row) for row in table_record["coefficients"])
    margin = table_record["after"]["minimum_margin_phase64"]
    control = native["cost"]
    fractional = (28, 20, 14)
    widths = (29, 20, 14)

    def row_circuit(stage: int, bit: int, *, extra_control: bool, keep_c2: bool):
        builder = km.CircuitBuilder()
        x = builder.alloc_qubits(22)
        builder.alloc_qubits(4)
        output = builder.alloc_qubits(39)
        c1 = builder.alloc_qubits(20)
        c2 = builder.alloc_qubits(14) if keep_c2 else None
        scratch = builder.alloc_qubits(29)
        target = c1 if stage == 1 else output[:29]
        operand = c2 if stage == 1 else c1
        if operand is None:
            raise ValueError("inner stage needs c2")
        shift = fractional[stage] - fractional[stage + 1] + bit - 20
        terms = [(operand[i], i + shift) for i in range(max(0, -shift),
                 min(len(operand), len(target) - shift))]
        if not terms:
            return builder.finish_circuit()
        if extra_control:
            flag = builder.alloc_qubits(1)[0]
            builder.init_and(x[bit], x[20], flag)
            control_bit = flag
        else:
            control_bit = x[bit]
        primitives._add_row(builder, False, control_bit, terms, target, scratch, subtract=True)
        if extra_control:
            builder.del_and(x[bit], x[20], control_bit)
        return builder.finish_circuit()

    row_peaks = {}
    for label, stage, keep in (("inner", 1, True), ("outer", 0, True), ("outer_without_c2", 0, False)):
        circuits = [row_circuit(stage, bit, extra_control=False, keep_c2=keep) for bit in range(13)]
        row_peaks[label] = max(c.num_qubits for c in circuits)
    extra_rows = [row_circuit(stage, 13, extra_control=True, keep_c2=True) for stage in (1, 0)]
    extra_row_toffolis = 2 * sum(counts(c.operation_statistics())[0] for c in extra_rows)

    c2_table = tuple((row[2],) for row in table)
    builder = km.CircuitBuilder()
    address = builder.alloc_qubits(9)
    c2 = builder.alloc_qubits(widths[2])
    path = builder.alloc_qubits(8)
    _load_table(builder, address, path, [c2], c2_table)
    lookup_toffolis = counts(builder.finish_circuit().operation_statistics())[0]
    builder = km.CircuitBuilder()
    address = builder.alloc_qubits(9)
    c2 = builder.alloc_qubits(widths[2])
    unlookup(builder, address, [c2], c2_table)
    unlookup_toffolis = counts(builder.finish_circuit().operation_statistics())[0]
    # The load-as-you-go arrangement removes c2 only during outer rows. The
    # replacement must still accommodate the full inner peak and all other stages.
    optimistic_peak = max(row_peaks["inner"], row_peaks["outer_without_c2"])
    reload_toffolis = lookup_toffolis + unlookup_toffolis
    load_score = complete_cost(optimistic_peak, (control["toffoli_like"] + reload_toffolis,
                               control["t_like"], control["fine_rotations"]), margin)

    # Current lookup covers 384 addresses in the high 3/4 of a nine-bit tree;
    # the ideal two-octave geometry uses all 256 eight-bit addresses. Repair
    # uses four low bits, eleven shared monomial ANDs, and a high-bank tree.
    # The pinned traversal computes one child AND before discovering that the
    # first quarter of the nine-bit tree is empty.
    old_lookup = prefixes(range(128, 512), 9) + 1
    if old_lookup != lookup_toffolis:
        raise ValueError("lookup tree model differs from the pinned primitive")
    new_lookup = prefixes(range(256), 8)
    old_repair = 11 + prefixes(range(8, 32), 5)
    new_repair = 11 + prefixes(range(16), 4)
    if old_repair != unlookup_toffolis:
        raise ValueError("repair tree model differs from the pinned primitive")
    lookup_saved = old_lookup + old_repair - new_lookup - new_repair
    two_octave = complete_cost(control["qubits"],
        (control["toffoli_like"] - lookup_saved + extra_row_toffolis,
         control["t_like"], control["fine_rotations"]), margin)
    result = {
        "control_kmb_sha256": native["sha256"], "control_table_sha256": sha256(table_path),
        "control_cost": control["score"],
        "two_octave": {
            "lookup_tree_toffolis": {"old": old_lookup, "new": new_lookup},
            "repair_tree_toffolis": {"old": old_repair, "new": new_repair},
            "saved_lookup_toffolis": lookup_saved, "extra_row_toffolis": extra_row_toffolis,
            "optimistic_score": two_octave,
            "assumptions": "Original width and margin; free octave-address selection; "
                           "existing coefficient and repair geometry; ignores extra control workspace. "
                           "The wider segment requires a new fitted table and full-domain model.",
        },
        "load_as_you_go": {
            "isolated_row_qubits": row_peaks, "c2_lookup_toffolis": lookup_toffolis,
            "c2_unlookup_toffolis": unlookup_toffolis, "optimistic_score": load_score,
            "assumptions": "No peak beyond isolated inner and outer rows; unchanged margin, "
                           "fine rotations and other operation counts. Reload and unlookup may add peak width.",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
