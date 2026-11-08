"""Non-emitting resource model for the pinned direct phasing architecture.

The formulas describe the current native primitives and allocation order.
They are valid only for the supported uniform dyadic layouts and must be
calibrated against emitted receipts before use for candidate admission.
"""

from math import gcd
from typing import Any

from .direct import DirectFormat
from .direct_screen import complete_cost


def _lookup(bits: int, sibling_cnot: bool) -> int:
    # Three quarters of the b+2-bit tree are used. The legacy traversal also
    # computes one flag for the empty quarter. The shared walk uses one AND per live parent.
    return (3 if sibling_cnot else 6) * (1 << bits) - (1 if sibling_cnot else 2)


def _unlookup(bits: int, sibling_cnot: bool) -> tuple[int, int]:
    address_width = bits + 2
    low = min(4, address_width - 1)
    high = address_width - low
    monomials = (1 << low) - low - 1
    banks = range(1 << max(0, high - 2), 1 << high)
    depths = range(1, high) if sibling_cnot else range(2, high + 1)
    tree = sum(len({bank >> (high - depth) for bank in banks}) for depth in depths)
    return monomials + tree, monomials + max(high - 1, 0)


def _rotation(width: int, distance: int) -> int:
    return width - 1 if gcd(width, distance) == 1 else width


def predict(fmt: DirectFormat, margin: int, *, trimmed: bool = False) -> dict[str, Any]:
    """Predict stage counts, declared width and complete cost without emission."""
    if type(fmt) is not DirectFormat:
        raise ValueError("pass the unmodified DirectFormat and select trimmed explicitly")
    if fmt.n_p != 10 or fmt.segment_bits not in (5, 6, 7) or not 3 <= len(fmt.fractional) <= 5:
        raise ValueError("model is calibrated only for n_p=10, segment bits 5-7, and degree 2-4")
    if trimmed and not (fmt.fused and fmt.reuse_lookup and fmt.binary_normalization and fmt.measurement_unlookup):
        raise ValueError("trimmed model requires the supported v4 architecture")
    widths = tuple(width - 1 for width in fmt.widths) if trimmed else fmt.widths
    output_width = fmt.output_fractional + (0 if trimmed else 1)
    x_width = 2 * fmt.n_p + 2
    flags = fmt.n_p.bit_length() if fmt.binary_normalization else fmt.n_p
    base = x_width + flags + output_width + sum(widths[1:])
    path = fmt.segment_bits + 1
    lookup = _lookup(fmt.segment_bits, fmt.sibling_cnot)
    repair, repair_workspace = _unlookup(fmt.segment_bits, fmt.sibling_cnot)
    unlookup = repair if fmt.measurement_unlookup else lookup

    rows = 0
    rows_by_stage = []
    carry_workspace = 0
    low_width = 2 * fmt.n_p - fmt.segment_bits
    for stage in range(len(widths) - 1):
        stage_rows = 0
        target, operand = widths[stage], widths[stage + 1]
        for bit in range(low_width):
            shift = fmt.fractional[stage] - fmt.fractional[stage + 1] + bit - 2 * fmt.n_p
            start = max(0, -shift)
            stop = min(operand, target - shift)
            if start >= stop:
                continue
            low = start + shift
            adder_width = target - low
            single = stop - start + max(adder_width - 1, 0)
            stage_rows += single * (2 if fmt.fused else 4)
            carry_workspace = max(carry_workspace, adder_width - 2)
        if not fmt.fused:
            stage_rows += 2 * max(target - 1, 0)
            carry_workspace = max(carry_workspace, target - 2)
        rows_by_stage.append(stage_rows)
        rows += stage_rows

    if fmt.binary_normalization:
        count = 2 * (3 * fmt.n_p - 2)
        input_shift = 4 * sum(_rotation(fmt.n_p + 1, 1 << i) for i in range(flags))
        output_shift = 2 * sum(_rotation(output_width, 1 << i) for i in range(flags))
        normalization_peak = x_width + flags + fmt.n_p + 1
    else:
        count = fmt.n_p
        input_shift = 2 * fmt.n_p * (fmt.n_p + 1)
        output_shift = 2 * fmt.n_p * (output_width - fmt.n_p)
        normalization_peak = x_width + flags
    arithmetic_base = base + max(widths) + (0 if fmt.fused else max(widths))
    if not (fmt.reuse_lookup or fmt.measurement_unlookup):
        arithmetic_base += path
    width = max(base + path, arithmetic_base + carry_workspace,
                base + repair_workspace if fmt.measurement_unlookup else 0, normalization_peak)
    stages = {"coefficient_lookup": lookup, "coefficient_unlookup": unlookup, "horner": rows,
              "normalization_flags": count, "input_shift": input_shift, "output_shift": output_shift}
    rotations = fmt.output_fractional - 3
    score = complete_cost(width, (sum(stages.values()), 1, rotations), margin)
    return {"stages": stages, "horner_by_stage": rows_by_stage, "cost": score,
            "assumptions": "Pinned direct primitives, uniform dyadic table and uncapped allocator. "
                           "Unseen precisions extrapolate the formulas; trimmed widths additionally "
                           "require a separately proved zero-bit invariant. Fitted-coefficient "
                           "accuracy and phase-branch correctness are not implied."}
