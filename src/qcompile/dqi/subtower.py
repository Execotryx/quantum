"""GF(4096) inverse through a GF(64)/GF(8) subtower.

Product-only registers are erased with measurement-conditioned Clifford repair.
All coordinates are internal to this implementation; inputs and outputs use the
pinned 0x1053 polynomial basis.
"""

from dataclasses import dataclass
from functools import cache
from typing import Any

from .bilinear import erase_product_tensor
from .field import GF4096
from .tower import BilinearTerm, _cubic_products, _product_xor, _xor_map, linear, tower


@dataclass(frozen=True)
class Subtower:
    to_subtower: tuple[int, ...]
    square8: tuple[int, ...]
    square_norm8: tuple[int, ...]
    inverse8_linear: tuple[int, ...]
    inverse8_quadratic: tuple[tuple[int, int, int], ...]
    product8: tuple[BilinearTerm, ...]
    low_output: tuple[int, ...]
    high_output: tuple[int, ...]


@cache
def subtower() -> Subtower:
    field = GF4096()
    outer = tower()
    basis64 = outer.basis[:6]
    sub64 = {linear(basis64, i): i for i in range(64)}
    generator = field.exp[585]
    basis8 = (1, generator, field.mul(generator, generator))
    sub8 = {linear(basis8, i): i for i in range(8)}
    z = next(v for v in sub64 if v not in sub8 and field.exp[(field.log[v] * 8) % 4095] ^ v == 1)
    norm = field.mul(z, z ^ 1)
    if norm not in sub8:
        raise ValueError("subtower norm outside GF(8)")
    basis = basis8 + tuple(field.mul(z, value) for value in basis8)
    coordinates = {linear(basis, i): i for i in range(64)}
    if len(coordinates) != 64:
        raise ValueError("dependent GF(64) subtower basis")
    to_subtower = tuple(coordinates[value] for value in basis64)
    square8 = tuple(sub8[field.mul(v, v)] for v in basis8)
    square_norm8 = tuple(sub8[field.mul(norm, field.mul(v, v))] for v in basis8)
    powers8 = [1]
    for _ in range(4):
        powers8.append(field.mul(powers8[-1], generator))
    product8 = tuple((mask, mask, sub8[linear(powers8, polynomial)])
                     for mask, polynomial in _cubic_products())

    def inv8(value: int) -> int:
        external = linear(basis8, value)
        return sub8[field.inv(external)] if external else 0

    inverse_linear = tuple(inv8(1 << i) for i in range(3))
    quadratic = tuple((i, j, inv8((1 << i) | (1 << j)) ^ inverse_linear[i] ^ inverse_linear[j])
                      for i in range(3) for j in range(i + 1, 3))
    for value in range(8):
        result = linear(inverse_linear, value)
        for i, j, word in quadratic:
            if value >> i & value >> j & 1:
                result ^= word
        if result != inv8(value):
            raise ValueError("GF(8) inverse is not the expected quadratic map")
    return Subtower(to_subtower, square8, square_norm8, inverse_linear, quadratic, product8,
                    tuple(sub64[value] for value in basis8),
                    tuple(sub64[field.mul(z, value)] for value in basis8))


@cache
def _product_tensor(terms: tuple[BilinearTerm, ...], width: int) -> tuple[tuple[int, ...], ...]:
    def basis_product(i: int, j: int) -> int:
        word = 0
        for left, right, output in terms:
            if left >> i & right >> j & 1:
                word ^= output
        return word
    return tuple(tuple(basis_product(i, j) for j in range(width)) for i in range(width))


def erase_bilinear(builder: Any, left: Any, right: Any, product: Any,
                   terms: tuple[BilinearTerm, ...]) -> None:
    """Erase a fresh bilinear product, repairing each measured X-basis phase."""
    if len(left) != len(right):
        raise ValueError("bilinear operand widths differ")
    erase_product_tensor(builder, left, right, product, _product_tensor(terms, len(left)))


def inverse8_xor(builder: Any, source: Any, target: Any, maps: Subtower) -> None:
    """XOR the quadratic three-bit inverse, including 0 -> 0."""
    _xor_map(builder, source, target, maps.inverse8_linear)
    scratch = builder.alloc_qubits(1)[0]
    for i, j, word in maps.inverse8_quadratic:
        if not word:
            continue
        builder.init_and(source[i], source[j], scratch)
        for bit, output in enumerate(target):
            if word >> bit & 1:
                builder.cx(scratch, output)
        builder.del_and(source[i], source[j], scratch)
    builder.free(scratch)


def inverse64_xor(builder: Any, source: Any, target: Any, maps: Subtower) -> None:
    """XOR the GF(64) inverse in the original six-bit tower coordinates."""
    ab = builder.alloc_qubits(6)
    a, b = ab[:3], ab[3:]
    norm = builder.alloc_qubits(3)
    inv = builder.alloc_qubits(3)
    _xor_map(builder, source, ab, maps.to_subtower)
    _xor_map(builder, a, norm, maps.square8)
    _xor_map(builder, b, norm, maps.square_norm8)
    _product_xor(builder, a, b, norm, maps.product8)
    inverse8_xor(builder, norm, inv, maps)
    _xor_map(builder, b, a, (1, 2, 4))
    for factor, columns in ((a, maps.low_output), (b, maps.high_output)):
        terms = tuple((x, y, linear(columns, word)) for x, y, word in maps.product8)
        _product_xor(builder, factor, inv, target, terms)
    _xor_map(builder, b, a, (1, 2, 4))
    inverse8_xor(builder, norm, inv, maps)
    _xor_map(builder, a, norm, maps.square8)
    _xor_map(builder, b, norm, maps.square_norm8)
    erase_bilinear(builder, a, b, norm, maps.product8)
    _xor_map(builder, source, ab, maps.to_subtower)
    for register in (inv, norm, ab):
        builder.free(register)


def inverse_xor(builder: Any, source: Any, target: Any) -> None:
    """XOR the GF(4096) inverse on disjoint registers, with clean scratch."""
    if len(source) != 12 or len(target) != 12:
        raise ValueError("subtower inversion requires two 12-bit registers")
    field = GF4096()
    outer = tower()
    maps = subtower()
    low_basis, high_basis = outer.basis[:6], outer.basis[6:]
    square = tuple(linear(outer.coordinates, field.mul(v, v)) for v in low_basis)
    square_norm = tuple(linear(outer.coordinates, field.mul(outer.quadratic_norm, field.mul(v, v)))
                        for v in low_basis)
    ab = builder.alloc_qubits(12)
    a, b = ab[:6], ab[6:]
    norm = builder.alloc_qubits(6)
    inv = builder.alloc_qubits(6)
    _xor_map(builder, source, ab, outer.coordinates)
    _xor_map(builder, a, norm, square)
    _xor_map(builder, b, norm, square_norm)
    _product_xor(builder, a, b, norm, outer.subfield_terms)
    inverse64_xor(builder, norm, inv, maps)
    _xor_map(builder, b, a, tuple(1 << i for i in range(6)))
    for factor, columns in ((a, low_basis), (b, high_basis)):
        terms = tuple((x, y, linear(columns, word)) for x, y, word in outer.subfield_terms)
        _product_xor(builder, factor, inv, target, terms)
    _xor_map(builder, b, a, tuple(1 << i for i in range(6)))
    inverse64_xor(builder, norm, inv, maps)
    _xor_map(builder, a, norm, square)
    _xor_map(builder, b, norm, square_norm)
    erase_bilinear(builder, a, b, norm, outer.subfield_terms)
    _xor_map(builder, source, ab, outer.coordinates)
    for register in (inv, norm, ab):
        builder.free(register)
