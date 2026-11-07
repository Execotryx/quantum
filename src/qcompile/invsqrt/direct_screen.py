"""Full-domain phase64 evidence and rotation-inclusive screening cost."""

from math import isqrt, log2, pi
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from qcompile.invsqrt.direct import Words

UnsignedWords = NDArray[np.uint64]
PhaseModel = Callable[[Words], UnsignedWords]
PhaseTargets = Callable[[Words], tuple[UnsignedWords, UnsignedWords]]


def beta_one_targets(xs: Words) -> tuple[UnsignedWords, UnsignedWords]:
    """Independent integer evaluation of the official beta=1, 24-bit rule."""
    doubled = [isqrt((1 << 130) // x) for x in xs.tolist()]
    target = np.fromiter((((r + 1) // 2) % (1 << 64) for r in doubled), np.uint64, len(xs))
    tolerance = np.fromiter((r >> 25 for r in doubled), np.uint64, len(xs))
    return target, tolerance


def scan_phase(
    evaluate: PhaseModel, last: int, targets: PhaseTargets = beta_one_targets, chunk=65536
) -> dict:
    if last < 1 or chunk < 1:
        raise ValueError("invalid scan range")
    minimum = (1 << 64, 0)
    worst = (-1.0, 0)
    failures = nonpositive = over_guard = 0
    first_failures: list[int] = []
    completed = 0
    for start in range(1, last + 1, chunk):
        xs = np.arange(start, min(last + 1, start + chunk), dtype=np.int64)
        observed = evaluate(xs)
        target, allowed = targets(xs)
        if observed.shape != xs.shape or observed.dtype != np.uint64:
            raise ValueError("incomplete or invalid phase model output")
        used = np.abs((observed - target).view(np.int64)).view(np.uint64)
        # Unsigned subtraction avoids the signed abs(-2**63) overflow case.
        margin = (allowed - used).view(np.int64)
        index = int(margin.argmin())
        minimum = min(minimum, (int(margin[index]), int(xs[index])))
        ratio = used / allowed
        index = int(ratio.argmax())
        worst = max(worst, (float(ratio[index]), -int(xs[index])))
        failed = used > allowed
        failures += int(failed.sum())
        nonpositive += int((used >= allowed).sum())
        over_guard += int((10 * np.minimum(used, allowed) > 9 * allowed).sum())
        if len(first_failures) < 16:
            first_failures.extend(xs[np.flatnonzero(failed)[: 16 - len(first_failures)]].tolist())
        completed += len(xs)
    return {
        "input_count": completed,
        "failed_inputs": failures,
        "first_failed_inputs": first_failures,
        "nonpositive_margins": nonpositive,
        "above_90_percent": over_guard,
        "minimum_margin_phase64": minimum[0],
        "minimum_margin_x": minimum[1],
        "worst_tolerance_fraction": worst[0],
        "worst_x": -worst[1],
    }


def complete_cost(qubits: int, counts: tuple[int, int, int], margin: int) -> dict:
    toffoli, base_t, rotations = counts
    if qubits < 1 or min(counts) < 0 or margin <= 0:
        raise ValueError("positive margin and valid resource counts required")
    epsilon = pi * margin / 2**64 / rotations if rotations else None
    rotation_t = rotations * (0.56 * log2(1 / epsilon) + 5.3) if epsilon is not None else 0
    return {
        "qubits": qubits,
        "toffoli_like": toffoli,
        "t_like": base_t,
        "fine_rotations": rotations,
        "rotation_epsilon_radians": epsilon,
        "rotation_t": rotation_t,
        "score": qubits * (toffoli + (base_t + rotation_t) / 4),
    }
