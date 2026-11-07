"""Reversible DQI field primitives and the runtime-mask phase kernel."""

from typing import Any, Sequence


def _check_width(field: Any, *registers: Sequence[Any]) -> None:
    if any(len(reg) != field.degree for reg in registers):
        raise ValueError("register width must match the field degree")


def multiply_xor(builder: Any, field: Any, left: Sequence[Any], right: Sequence[Any],
                 target: Sequence[Any]) -> None:
    """Accumulate a field product into an arbitrary target on disjoint wires."""
    _check_width(field, left, right, target)
    degree = field.degree
    monomials = [field.mul(1 << min(k, degree - 1), 1 << max(0, k - degree + 1))
                 for k in range(2 * degree - 1)]
    destinations = [[target[k] for k in range(degree) if word & (1 << k)] for word in monomials]
    temporary = builder.alloc_qubits(1)
    flag = temporary[0]
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            wires = destinations[i + j]
            if len(wires) == 1:
                builder.ccx(a, b, wires[0])
            else:
                builder.init_and(a, b, flag)
                for wire in wires:
                    builder.cx(flag, wire)
                builder.del_and(a, b, flag)
    builder.free(temporary)


def inverse_xor(builder: Any, field: Any, source: Sequence[Any], target: Sequence[Any]) -> None:
    """Accumulate x^(2^12-2), mapping zero to zero, and erase the addition chain."""
    _check_width(field, source, target)
    if field.degree != 12:
        raise ValueError("inverse addition chain is specific to GF(4096)")
    # For A_k = x^(2^k-1), A_(i+j) = A_i * (A_j)^(2^i).
    chain = ((1, 1), (1, 2), (2, 3), (5, 5), (1, 10))
    powers = {1: source}
    shifted = builder.alloc_qubits(field.degree)
    maps = {count: [field.pow(1 << bit, 1 << count) for bit in range(field.degree)]
            for count in {i for i, _ in chain}}

    def frobenius_xor(inputs: Sequence[Any], outputs: Sequence[Any], count: int) -> None:
        for wire, column in zip(inputs, maps[count], strict=True):
            for bit, target_wire in enumerate(outputs):
                if column & (1 << bit):
                    builder.cx(wire, target_wire)

    def accumulate(i: int, j: int) -> None:
        frobenius_xor(powers[j], shifted, i)
        multiply_xor(builder, field, powers[i], shifted, powers[i + j])
        frobenius_xor(powers[j], shifted, i)

    for i, j in chain:
        powers[i + j] = builder.alloc_qubits(field.degree)
        accumulate(i, j)
    frobenius_xor(powers[11], target, 1)
    for i, j in reversed(chain):
        accumulate(i, j)
        builder.free(powers.pop(i + j))
    builder.free(shifted)


def phase_for_position(builder: Any, field: Any, located: Any, numerator: Sequence[Any],
                       denominator: Sequence[Any], mask: Sequence[Any]) -> None:
    """Apply parity(mask & (numerator / denominator)) when the locator is set.

    The caller supplies the runtime classical mask and the coherent locator
    flag. The zero denominator convention is inverse(0) = 0.
    """
    _check_width(field, numerator, denominator, mask)
    inverse = builder.alloc_qubits(field.degree)
    enabled = builder.alloc_qubits(field.degree)
    _, scaffold = builder.init_gf2_inverse_with_scaffold(denominator, target=inverse, field=field)
    builder.init_and(located, numerator, enabled)
    builder.gf2_phase_by_product(enabled, inverse, mask=mask, field=field)
    builder.del_and(located, numerator, enabled)
    builder.del_gf2_inverse_with_scaffold(denominator, target=inverse, scaffold=scaffold, field=field)
    builder.free(scaffold)
    builder.free(enabled)
    builder.free(inverse)


def locator_update(builder: Any, field: Any, current: Sequence[Any], previous: Sequence[Any],
                   ratio: Sequence[Any], shift: int) -> None:
    """XOR the shifted, scaled previous row into the current polynomial row."""
    if len(current) != len(previous) or not 0 <= shift < len(current):
        raise ValueError("invalid locator slice shape or monomial shift")
    for source, target in zip(previous[:len(current) - shift], current[shift:], strict=True):
        multiply_xor(builder, field, ratio, source, target)


def eea_locator_slice(builder: Any, field: Any, current: Sequence[Any], previous: Sequence[Any],
                      ratio: Sequence[Any], shift: int, swap: Any, *, adjoint: bool = False) -> None:
    """One EEA elimination and conditional row swap, given retained metadata."""
    def swap_rows() -> None:
        for left, right in zip(current, previous, strict=True):
            for a, b in zip(left, right, strict=True):
                builder.cswap(swap, a, b)

    if adjoint:
        swap_rows()
    locator_update(builder, field, current, previous, ratio, shift)
    if not adjoint:
        swap_rows()


def bm_locator_slice(builder: Any, field: Any, current: Sequence[Any], previous: Sequence[Any],
                     saved: Sequence[Any], ratio: Sequence[Any], shift: int, replace: Any, *,
                     adjoint: bool = False) -> None:
    """One BM update, retaining the displaced backup row on a degree increase."""
    if len(saved) != len(current):
        raise ValueError("saved row must match the locator width")

    def save_current() -> None:
        for row, history in zip(current, saved, strict=True):
            for a, c in zip(row, history, strict=True):
                builder.ccx(replace, a, c)

    def swap_backup() -> None:
        for backup, history in zip(previous, saved, strict=True):
            for b, c in zip(backup, history, strict=True):
                builder.cswap(replace, b, c)

    # Compute the same polynomial using the old backup until after the update.
    # The zero-initialized history then makes B' equal the old C on replacement.
    (swap_backup if adjoint else save_current)()
    locator_update(builder, field, current, previous, ratio, shift)
    (save_current if adjoint else swap_backup)()
