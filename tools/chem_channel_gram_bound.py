"""Bound the two-body normalization for all channel bases with the same Gram."""

import argparse
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from qcompile.io import sha256, write_json


class Normalizations(NamedTuple):
    gram_bound: Fraction
    current: Fraction
    weight_gram_bound: Fraction
    negative_weight_gram_sum: Fraction


def exact_group(weights: NDArray[np.float64]) -> Normalizations:
    """The last row contains the identity coefficients."""
    ratios = [[float(value).as_integer_ratio() for value in row] for row in weights]
    denominator = max(scale for row in ratios for _, scale in row)
    integer_rows = [[value * (denominator // scale) for value, scale in row] for row in ratios]
    gram_rows = []
    for later, left in enumerate(integer_rows):
        row_sum = sum(value * value for value in left)
        for earlier in range(later):
            row_sum += 2 * abs(sum(a * b for a, b in zip(left, integer_rows[earlier])))
        gram_rows.append(row_sum)
    lcu_sum = 0
    signed_weight_gram = 0
    for column in zip(*integer_rows):
        lcu_sum += sum(abs(value) for value in column) ** 2
        signed_weight_gram += sum(column[:-1]) ** 2
    weight_gram = sum(gram_rows[:-1])
    scale_squared = denominator ** 2
    return Normalizations(
        Fraction(sum(gram_rows), 4 * scale_squared),
        Fraction(lcu_sum, 4 * scale_squared),
        Fraction(weight_gram, 4 * scale_squared),
        Fraction(weight_gram - signed_weight_gram, 2 * scale_squared),
    )


def run(factorization: Path, expected_sha256: str, output: Path) -> None:
    if sha256(factorization) != expected_sha256:
        raise ValueError("Unexpected factorization")
    with np.load(factorization, allow_pickle=False) as params:
        weights = np.asarray(params["W"], dtype=np.float64)
        identity = np.asarray(params["H2_I"], dtype=np.float64)
    if weights.ndim != 3 or identity.shape != weights.shape[::2] or min(weights.shape) == 0:
        raise ValueError("Expected R-by-B-by-C weights and R-by-C identity")
    groups = [exact_group(group) for group in np.concatenate((weights, identity[:, None, :]), axis=1)]
    lower = sum((group.gram_bound for group in groups), Fraction(0))
    current = sum((group.current for group in groups), Fraction(0))
    weights_lower = sum((group.weight_gram_bound for group in groups), Fraction(0))
    negative = sum((group.negative_weight_gram_sum for group in groups), Fraction(0))
    write_json(output, {
        "scope": "exact two-body normalization bound for an unchanged per-group augmented Gram",
        "factorization_sha256": expected_sha256,
        "driver_sha256": sha256(Path(__file__)),
        "shape": list(weights.shape),
        "lambda_h2_lower": float(lower),
        "lambda_h2_current": float(current),
        "lambda_h2_lower_exact": str(lower),
        "lambda_h2_current_exact": str(current),
        "lambda_h2_weight_gram_lower": float(weights_lower),
        "lambda_h2_weight_gram_lower_exact": str(weights_lower),
        "negative_weight_gram_sum_exact": str(negative),
        "group_lower": [float(group.gram_bound) for group in groups],
        "group_current": [float(group.current) for group in groups],
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("factorization", type=Path)
    parser.add_argument("expected_sha256")
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
