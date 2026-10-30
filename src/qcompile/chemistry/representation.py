"""Parameterized independent models; angular units and tree root await G0.

These are not silently substituted for official tensor reconstruction/matching.
"""

import math
from fractions import Fraction

import numpy as np

from qcompile.errors import ValidationError
from qcompile.io import positive_int


def validate_tree(edges, vertices: int, root: int):
    positive_int(vertices, "vertices")
    edges = np.asarray(edges)
    if edges.shape != (vertices - 1, 2) or edges.dtype.kind not in "iu":
        raise ValidationError("tree must have N-1 ordered integer edges")
    if type(root) is not int or not 0 <= root < vertices:
        raise ValidationError("invalid tree root")
    seen = {root}
    for parent, child in edges.tolist():
        if parent not in seen or not 0 <= child < vertices or child in seen:
            raise ValidationError("tree must be connected, acyclic and parent-before-child")
        seen.add(child)
    return edges


def encode_angle(value, bits: int, *, rounding: str):
    positive_int(bits, "angle bits")
    value = Fraction(value) % 2
    scaled = value * (1 << (bits - 1))
    if rounding == "nearest_even":
        word = round(scaled)
    elif rounding == "floor":
        word = scaled.numerator // scaled.denominator
    else:
        raise ValidationError("explicit supported angle rounding is required")
    return word % (1 << bits)


def decode_angle(word: int, bits: int):
    positive_int(bits, "angle bits")
    if type(word) is not int or not 0 <= word < 1 << bits:
        raise ValidationError("angle word outside unsigned range")
    return Fraction(word, 1 << (bits - 1))


def reconstruct(words, bits, edges, vertices, root, *, radians_per_unit):
    validate_tree(edges, vertices, root)
    if not math.isfinite(radians_per_unit) or radians_per_unit <= 0:
        raise ValidationError("explicit positive angular conversion is required")
    if len(words) != vertices - 1:
        raise ValidationError("angle count must match tree edges")
    vector = np.zeros(vertices)
    vector[root] = 1
    for (parent, child), word in zip(edges, words, strict=True):
        theta = float(decode_angle(int(word), bits)) * radians_per_unit
        a, b = vector[parent], vector[child]
        vector[parent] = math.cos(theta) * a - math.sin(theta) * b
        vector[child] = math.sin(theta) * a + math.cos(theta) * b
    return vector


def batch_words(words, batch_size, bits):
    """Rows are addresses. Explicit zero padding, first load then XOR deltas."""
    positive_int(batch_size, "batch size")
    positive_int(bits, "bits")
    table = np.asarray(words)
    if table.ndim != 2 or table.size == 0 or table.dtype.kind not in "iu":
        raise ValidationError("angle table must be a nonempty integer matrix")
    if np.any(table < 0) or any(int(x) >= 1 << bits for x in table.flat):
        raise ValidationError("angle table contains out-of-range words")
    count = (table.shape[1] + batch_size - 1) // batch_size
    padded = np.zeros((table.shape[0], count * batch_size), dtype=table.dtype)
    padded[:, : table.shape[1]] = table
    batches = [padded[:, k * batch_size : (k + 1) * batch_size].copy() for k in range(count)]
    deltas = [batches[0]] + [a ^ b for a, b in zip(batches[:-1], batches[1:], strict=True)]
    return batches, deltas


def residual_frobenius(blocks):
    """Stream pre-shifted tensor differences, never omitting the symmetry shift."""
    total = 0.0
    for candidate, target, shift in blocks:
        a, b, s = map(np.asarray, (candidate, target, shift))
        if a.shape != b.shape or a.shape != s.shape or not all(np.isfinite(x).all() for x in (a, b, s)):
            raise ValidationError("residual block shape/finite check failed")
        difference = a - b - s
        total += float(np.vdot(difference.ravel(), difference.ravel()).real)
    if not math.isfinite(total):
        raise ValidationError("residual overflow")
    return math.sqrt(total)


def workspace_cost(persistent: int, sequential_temporaries: dict[str, int]):
    positive_int(persistent, "persistent workspace")
    if not sequential_temporaries or any(
        type(v) is not int or v < 0 for v in sequential_temporaries.values()
    ):
        raise ValidationError("explicit sequential workspace terms are required")
    return persistent + max(sequential_temporaries.values())


def canonical_signs(vectors):
    """Opt-in real-vector sign policy; associated-array legality still needs G0."""
    array = np.array(vectors, dtype=float, copy=True)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValidationError("expected finite real vector rows")
    for row in array:
        if not np.any(row):
            raise ValidationError("zero vector has no sign convention")
        pivot = int(np.argmax(np.abs(row)))
        if row[pivot] < 0:
            row *= -1
    return array
