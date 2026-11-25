"""Reversibly exchange a common factor of a projected DQI pair."""

from dataclasses import dataclass

from qcompile.dqi.decoder import _divide, _multiply
from qcompile.dqi.field import GF4096


@dataclass(frozen=True)
class Padding:
    original: tuple[int, ...]
    replacement: tuple[int, ...]

    def __post_init__(self):
        if (len(self.original) < 3 or len(self.original) != len(self.replacement)
                or self.original[-1] != 1 or self.replacement[-1] != 1):
            raise ValueError("The two padding factors must be monic and have the same degree")


def selected_padding(field: GF4096, finish_modulus: list[int]) -> tuple[Padding, ...]:
    """Build the two fixed exchanges selected by the scalar development screen."""
    replacements = (
        ((1043, 1591, 1), (1975, 613, 1), (3858, 2432, 1)),
        ((900, 1213, 1), (1431, 3176, 1), (1813, 3411, 1)),
    )
    branches = []
    for parity, factors in enumerate(replacements):
        original, replacement = [1], [1]
        for index in range(4 + parity, 10 + parity, 2):
            coordinate = 2 * index
            original = _multiply(original, [2048 ^ field.mul(coordinate, coordinate) ^ coordinate, 1, 1], field)
        for constant, linear, monic in factors:
            term = field.div(constant, field.mul(linear, linear))
            trace = term
            for _ in range(11):
                term = field.mul(term, term)
                trace ^= term
            factor = [constant, linear, monic]
            if trace != 1 or linear == 1 or _divide(finish_modulus, factor, field)[1] == [0]:
                raise ValueError("Replacement factor collides with the physical or finish geometry")
            if _divide(replacement, factor, field)[1] == [0]:
                raise ValueError("Replacement factors must be distinct")
            replacement = _multiply(replacement, factor, field)
        branches.append(Padding(tuple(original), tuple(replacement)))
    return tuple(branches)


def _basis(builder, bank, padding, field, xor_linear, *, inverse, flag=None):
    """Split or join remainder and quotient, optionally using alternate coefficients.

    The leading coefficient of each monomial stays in its own wire slot.
    Higher-to-lower shears divide. Their reverse order multiplies.
    """
    degree = len(padding.original) - 1
    offsets = range(len(bank) - degree)
    original = [field.fixed_map(coefficient) for coefficient in padding.original[:-1]]
    delta = [field.fixed_map(p ^ q) for p, q in zip(padding.original[:-1], padding.replacement[:-1], strict=True)]
    masked = builder.alloc_qubits(12) if flag is not None else None
    for i in reversed(offsets) if inverse else offsets:
        source = bank[i + degree]
        if masked is not None:
            builder.init_and(flag, source, masked)
        for j, columns in enumerate(original):
            xor_linear(builder, source, bank[i + j], columns)
            if masked is not None:
                xor_linear(builder, masked, bank[i + j], delta[j])
        if masked is not None:
            builder.del_and(flag, source, masked)
    if masked is not None:
        builder.free(masked)


def _toggle_common_factor(builder, banks, degree, target, zero_xor):
    words = [word for bank in banks for word in bank[:degree]]
    zeroes = builder.alloc_qubits(len(words))
    for word, zero in zip(words, zeroes, strict=True):
        zero_xor(builder, word, zero)
    builder.x(zeroes)
    zero_xor(builder, zeroes, target)
    builder.x(zeroes)
    for word, zero in zip(words, zeroes, strict=True):
        zero_xor(builder, word, zero)
    builder.free(zeroes)


def exchange_padding(builder, banks, padding, field, xor_linear, zero_xor, *, flag=None):
    """Replace a common factor and return a one-bit inverse token.

    The inverse consumes that token after restoring the original factor.
    The pair is unchanged on every input with a nonzero original remainder.
    """
    degree = len(padding.original) - 1
    reversing = flag is not None
    for bank in banks:
        _basis(builder, bank, padding, field, xor_linear, inverse=True, flag=flag[0] if reversing else None)
    if flag is None:
        flag = builder.alloc_qubits(1)
    _toggle_common_factor(builder, banks, degree, flag[0], zero_xor)
    for bank in banks:
        _basis(builder, bank, padding, field, xor_linear, inverse=False, flag=None if reversing else flag[0])
    if reversing:
        builder.free(flag)
        return None
    return flag
