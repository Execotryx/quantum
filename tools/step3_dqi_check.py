"""Compare DQI statistical controls against the acquired verifier."""

import hashlib
import json
import math
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

from qcompile.dqi.decoder import decode, mask_parity, syndrome
from qcompile.dqi.field import GF4096
from qcompile.reference.scoring import cp_upper, repetition


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "vendor/official/verifiers/dqi/verify_submission_dqi.py"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != "f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65":
        raise ValueError("DQI verifier identity changed")
    sys.path[:0] = [str(root / "vendor/official/kickmix"), str(path.parent)]
    official = import_module("verify_submission_dqi")
    spec = official.ProblemSpecDQI.benchmark_instance()
    tables = official.FieldTables(official.km.GF2Field(spec.degree))
    field = GF4096()
    if list(field.exp[:4095]) != tables.antilog.tolist():
        raise ValueError("field generator powers disagree")
    rng = np.random.default_rng(312)
    phase_counts = [0, 0]
    for weight in range(36):
        probabilities = np.zeros(36)
        probabilities[weight] = 1
        words, masks, phases = official.sample_shots(spec, tables, rng, 2, probabilities)
        for word, mask, phase in zip(words, masks, phases, strict=True):
            values = word.tolist()
            errors = decode(values, field, "bm")
            if (
                len(errors) != weight
                or decode(values, field, "eea") != errors
                or syndrome(errors, field) != values
            ):
                raise ValueError(f"decoder disagreement at weight {weight}")
            packed = sum(int(symbol) << (12 * j) for j, symbol in enumerate(mask))
            if mask_parity(errors, packed) != int(phase):
                raise ValueError(f"mask parity disagreement at weight {weight}")
            phase_counts[int(phase)] += 1
    rows = []
    for k in (0, 1, 2, 35, 100, 4000, 6400, 102400):
        bound = cp_upper(k, 102400)
        expected = official.clopper_pearson_upper_bound(k, 102400)
        if not math.isclose(bound, expected, rel_tol=1e-10):
            raise ValueError(f"confidence discrepancy for {k=}: {bound=} {expected=}")
        rows.append({"failures": k, "independent": bound, "official": expected})
    penalties = []
    for epsilon in (0.0, rows[0]["official"], 0.05, 1 / 16 - 2**-30):
        actual = repetition(epsilon)
        expected = official.repetition_overhead(epsilon)
        if not math.isclose(actual, expected, rel_tol=1e-7):
            raise ValueError(f"repetition discrepancy for {epsilon=}")
        penalties.append({"epsilon": epsilon, "independent": actual, "official": expected})
    print(
        json.dumps(
            {
                "verifier_sha256": digest,
                "shots": 102400,
                "bounds": rows,
                "penalties": penalties,
                "field_powers": 4095,
                "weights": list(range(36)),
                "shots_per_weight": 2,
                "decoder_fixture_seed": 312,
                "phase_counts": phase_counts,
            }
        )
    )


if __name__ == "__main__":
    main()
