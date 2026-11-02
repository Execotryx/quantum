"""Compare the independent target and tolerance against every official input."""

import hashlib
import json
import math
import random
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.reference.invsqrt import MAX_INPUT, phase_floor, phase_nearest_even, scan
from qcompile.reference.scoring import rotation_price


def main():
    root = Path(__file__).resolve().parents[1]
    verifier = root / "vendor/official/verifiers/invsqrt/verify_submission_invsqrt.py"
    digest = hashlib.sha256(verifier.read_bytes()).hexdigest()
    if digest != "ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a":
        raise ValueError("inverse-square-root verifier identity changed")
    sys.path[:0] = [str(root / "vendor/official/kickmix"), str(verifier.parent)]
    official = import_module("verify_submission_invsqrt")
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    assert spec.max_x == MAX_INPUT
    examined = 0
    for start in range(1, MAX_INPUT + 1, 8192):
        xs = np.arange(start, min(start + 8192, MAX_INPUT + 1))
        targets, tolerances = official.reference_values(spec, xs)
        for x, target, tolerance in zip(xs.tolist(), targets, tolerances, strict=True):
            if phase_nearest_even(x) % (1 << 64) != int(target) or phase_floor(x, 40) != int(tolerance):
                raise ValueError(f"reference disagreement at {x}")
            examined += 1
    assert examined == MAX_INPUT
    rng = random.Random(3103)
    cases = [(1, 0), (1, 1), (1 << 63, 37)]
    cases.extend((rng.randrange(1, 1 << 63), rng.randrange(1, 128)) for _ in range(128))
    for margin, rotations in cases:
        turns = margin / 2**64
        estimate = rotation_price(turns, rotations, 3, 5)
        charge = official.rotation_t_count(math.pi * turns / rotations) if rotations else 0
        expected = 3 + (5 + rotations * charge) / official.T_PER_TOFFOLI
        if not math.isclose(estimate["C"], expected, rel_tol=2e-15):
            raise ValueError(f"rotation price disagreement for {margin=} {rotations=}")
    margin_control = scan(lambda x: phase_floor(x) % 2**64)
    if (
        margin_control["nonpositive_margin_count"]
        or sum(margin_control["margin_histogram_eighths_of_tolerance"]) != MAX_INPUT
    ):
        raise ValueError("full-domain margin control failed")
    print(
        json.dumps(
            {
                "inputs_compared": examined,
                "verifier_sha256": digest,
                "margin_control": margin_control,
                "rotation_price_cases": len(cases),
                "rotation_fixture_seed": 3103,
                "target_and_tolerance": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
