"""Classical-mask projection wrapper for SomeJoint's J-fraction DQI decoder.

Source adaptation for a private verifier experiment. The underlying decoder
is credited to SomeJoint / Agniv Banerjee, Apache-2.0, public 8.95 notebook.
This file adds a syndrome-span projection of 70 classical measurement masks.
"""

from __future__ import annotations

import argparse
from functools import cache
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "keyeq"), str(HERE.parent)]
from jfraction_gap_decoder import GapJFractionDecoder  # noqa: E402
from common import build, km  # noqa: E402
from static_divisions import StaticArithmeticBuilder  # noqa: E402

GF = km.GF2Field(12)
ORDER = (1 << 12) - 1
ERASE = 70


def trace(value):
    out = 0
    for _ in range(12):
        out ^= value
        value = GF.mul(value, value)
    assert out in (0, 1)
    return out


def dual_basis():
    result = []
    for bit in range(12):
        found = [mu for mu in range(1 << 12)
                 if all(trace(GF.mul(mu, 1 << k)) == int(k == bit)
                        for k in range(12))]
        assert len(found) == 1
        result.append(found[0])
    return result


def inverse_matrix(matrix):
    n = len(matrix)
    rows = [row[:] + [int(i == j) for j in range(n)]
            for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((i for i in range(col, n) if rows[i][col]), None)
        assert pivot is not None
        rows[col], rows[pivot] = rows[pivot], rows[col]
        reciprocal = GF.div(1, rows[col][col])
        rows[col] = [GF.mul(reciprocal, value) for value in rows[col]]
        for i in range(n):
            if i == col or not rows[i][col]:
                continue
            factor = rows[i][col]
            rows[i] = [a ^ GF.mul(factor, b) for a, b in zip(rows[i], rows[col])]
    assert all(rows[i][j] == int(i == j) for i in range(n) for j in range(n))
    return [row[n:] for row in rows]


@cache
def field_to_mask(field_element):
    return sum(trace(GF.mul(field_element, 1 << bit)) << bit for bit in range(12))


def xor_linear(builder, source, target, columns):
    """XOR a known binary matrix into classical target bits."""
    for bit, mask in enumerate(columns):
        for out in range(12):
            if mask >> out & 1:
                builder.cx(source[bit], target[out])


def projected_record(builder, syndromes, outcomes):
    assert len(syndromes) == 70 and len(outcomes) == ORDER
    basis = dual_basis()
    vandermonde = [
        [GF.pow(GF.primitive_element, ((i + 1) * j) % ORDER)
         for i in range(ERASE)]
        for j in range(ERASE)
    ]
    inverse = inverse_matrix(vandermonde)

    lambda_words = [builder.alloc_bits(12) for _ in range(ERASE)]
    for i, row in enumerate(inverse):
        for j, coefficient in enumerate(row):
            if coefficient:
                xor_linear(builder, outcomes[j], lambda_words[i],
                           [GF.mul(coefficient, dual) for dual in basis])

    # Add Tr(sum_i lambda_i * syndrome_i) to the phase. These are classical
    # controls on Z, never quantum-quantum Toffolis.
    for i, word in enumerate(lambda_words):
        for source_bit in range(12):
            for target_bit in range(12):
                if trace(GF.mul(1 << source_bit, 1 << target_bit)):
                    builder.cz(word[source_bit], syndromes[i][target_bit])

    residual = []
    for j, original in enumerate(outcomes):
        changed = builder.alloc_bits(12)
        if j >= ERASE:
            builder.cx(original, changed)
            for i, word in enumerate(lambda_words):
                coefficient = GF.pow(GF.primitive_element, ((i + 1) * j) % ORDER)
                xor_linear(builder, word, changed,
                           [field_to_mask(GF.mul(coefficient, 1 << bit))
                            for bit in range(12)])
        residual.append(changed)
    return residual


class ProjectedGapDecoder(GapJFractionDecoder):
    def build_syndrome_decoding_mbuc(self, builder, *, syndromes, error_mbuc, n_iters):
        residual = projected_record(builder, syndromes, error_mbuc)
        super().build_syndrome_decoding_mbuc(
            builder, syndromes=syndromes, error_mbuc=residual, n_iters=n_iters)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    builder = StaticArithmeticBuilder()
    circuit = build(builder, iterations=35, decoder_type=ProjectedGapDecoder)
    circuit.to_file(str(args.output), format="kmb")
    stats = circuit.operation_statistics()
    with args.output.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    print(json.dumps({"candidate": "70-position classical mask projection",
                      "num_qubits": circuit.num_qubits,
                      "num_bits": circuit.num_bits,
                      "toffoli_count": stats.num_toffoli_like,
                      "num_ops": len(circuit),
                      "sha256": digest,
                      "stages": builder.stage_records}, indent=2))


if __name__ == "__main__":
    main()
