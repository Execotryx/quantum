"""Deterministic GF(4096) tower maps and reversible bilinear multiplication."""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

from .field import GF4096

BilinearTerm = tuple[int, int, int]


def linear(columns: Sequence[int], value: int) -> int:
    result = 0
    while value:
        bit = value & -value
        result ^= columns[bit.bit_length() - 1]
        value ^= bit
    return result


def parity_map(columns: Sequence[int], mask: int) -> int:
    return sum(((column & mask).bit_count() & 1) << i for i, column in enumerate(columns))


def _basis_table(columns: Sequence[int]) -> dict[int, int]:
    table = {linear(columns, v): v for v in range(1 << len(columns))}
    if len(table) != 1 << len(columns):
        raise ValueError("dependent tower basis")
    return table


def _cubic_products() -> tuple[tuple[int, int], ...]:
    # The diagonal products also cancel the square terms in the pair parities.
    diagonal = [1 << (2 * i) for i in range(3)]
    pairs = []
    for i in range(3):
        for j in range(i + 1, 3):
            word = 1 << (i + j)
            diagonal[i] ^= word
            diagonal[j] ^= word
            pairs.append(((1 << i) | (1 << j), word))
    return tuple((1 << i, word) for i, word in enumerate(diagonal)) + tuple(pairs)


@dataclass(frozen=True)
class Tower:
    """External polynomial coordinates, internal GF(64) + z GF(64)."""

    basis: tuple[int, ...]
    coordinates: tuple[int, ...]
    trace_dual: tuple[int, ...]
    terms: tuple[BilinearTerm, ...]

    def multiply(self, left: int, right: int) -> int:
        result = 0
        for a, b, word in self.terms:
            if ((left & a).bit_count() & (right & b).bit_count()) & 1:
                result ^= word
        return result


@cache
def tower() -> Tower:
    field = GF4096()
    generator = field.exp[65]
    powers = tuple(field.exp[65 * i] for i in range(11))
    subfield = _basis_table(powers[:6])
    assert all(v == 0 or field.exp[(field.log[v] * 64) % 4095] == v for v in subfield)
    z = next(v for v in range(2, 4096) if v not in subfield
             and field.exp[(field.log[v] * 64) % 4095] ^ v == 1)
    norm = field.mul(z, z ^ 1)
    basis = powers[:6] + tuple(field.mul(z, p) for p in powers[:6])
    inverse = _basis_table(basis)
    coordinates = tuple(inverse[1 << i] for i in range(12))

    def trace(value: int) -> int:
        result = value
        for _ in range(11):
            value = field.mul(value, value)
            result ^= value
        return result

    dual = {
        sum(trace(field.mul(v, 1 << i)) << i for i in range(12)): v
        for v in range(4096)
    }
    if len(dual) != 4096 or field.mul(generator, generator) != powers[2]:
        raise ValueError("invalid field trace or subfield generator")
    gf64_terms = []
    for mask, polynomial in _cubic_products():
        for form, word in (
            (mask, polynomial ^ (polynomial << 3)),
            (mask << 3, (polynomial << 3) ^ (polynomial << 6)),
            (mask | (mask << 3), polynomial << 3),
        ):
            gf64_terms.append((form, linear(powers, word)))
    terms = []
    for mask, word in gf64_terms:
        for form, scale in ((mask, z ^ 1), (mask << 6, norm), (mask | (mask << 6), z)):
            parity = parity_map(coordinates, form)
            terms.append((parity, parity, field.mul(word, scale)))
    return Tower(basis, coordinates, tuple(dual[1 << i] for i in range(12)), tuple(terms))


def multiply_xor(builder: Any, left: Sequence[Any], right: Sequence[Any], target: Sequence[Any]) -> None:
    """Apply the 54-term product on disjoint external polynomial registers."""
    if any(len(reg) != 12 for reg in (left, right, target)):
        raise ValueError("tower multiplication requires three 12-bit registers")
    scratch = builder.alloc_qubits(3)
    a, b, product = scratch
    for left_mask, right_mask, word in tower().terms:
        l_wires = [wire for i, wire in enumerate(left) if left_mask >> i & 1]
        r_wires = [wire for i, wire in enumerate(right) if right_mask >> i & 1]
        for wire in l_wires:
            builder.cx(wire, a)
        for wire in r_wires:
            builder.cx(wire, b)
        builder.init_and(a, b, product)
        for i, wire in enumerate(target):
            if word >> i & 1:
                builder.cx(product, wire)
        builder.del_and(a, b, product)
        for wire in reversed(r_wires):
            builder.cx(wire, b)
        for wire in reversed(l_wires):
            builder.cx(wire, a)
    builder.free(scratch)
