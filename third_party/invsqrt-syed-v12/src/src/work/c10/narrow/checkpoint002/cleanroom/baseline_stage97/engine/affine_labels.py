# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Exhaustive affine address-label selection for mathematical fit freedom.

Each address supplies the set of coefficient residues that its numerical
error certificate permits. We seek up to3 independent affine address bits
whose value is an allowed residue everywhere. This creates genuine physical
address/output aliases using Clifford gates only; no nonlinear encoding or
compiled circuit is an input.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path


def _bits(value):
    while value:
        bit = value & -value
        yield bit.bit_length()-1
        value ^= bit


def _rank(rows):
    basis = {}
    for row in rows:
        value = row
        while value:
            pivot = value.bit_length()-1
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return len(basis)


def _affine_solutions(force_zero, force_one, input_bits):
    """Return ALL affine forms satisfying the specified truth values."""
    if force_zero & force_one:
        return []
    pivots = {}
    for address in _bits(force_zero | force_one):
        row = address | (1 << input_bits)
        value = (force_one >> address) & 1
        while row:
            pivot = row.bit_length()-1
            if pivot not in pivots:
                pivots[pivot] = (row, value)
                break
            old, target = pivots[pivot]
            row ^= old
            value ^= target
        if not row and value:
            return []
    free = [bit for bit in range(input_bits+1) if bit not in pivots]
    results = []
    for assignment in range(1 << len(free)):
        solution = sum(((assignment >> i) & 1) << bit for i, bit in enumerate(free))
        for pivot in sorted(pivots):
            row, value = pivots[pivot]
            if ((row & solution).bit_count() & 1) != value:
                solution ^= 1 << pivot
        results.append(solution)
    return results


@dataclass(frozen=True)
class AffineAddressPlan:
    input_bits: int
    alias_bits: int
    # Low input_bits bits give the linear row; bit input_bits is its constant.
    rows: tuple[int, ...]
    # Row reductions taking the linear map to identity. Gate tuple(op,i,j).
    reduction: tuple[tuple[str, int, int], ...]
    constants: tuple[int, ...]
    pairs_examined: int

    def transform(self, address):
        mask = (1 << self.input_bits)-1
        return sum(((((address & (row & mask)).bit_count() & 1)
                     ^ ((row >> self.input_bits) & 1)) << i)
                   for i, row in enumerate(self.rows))

    @property
    def labels(self):
        mask = (1 << self.alias_bits)-1
        return tuple(self.transform(a) & mask for a in range(1 << self.input_bits))


def _make_plan(rows, input_bits, alias_bits, pairs):
    mask = (1 << input_bits)-1
    rows = list(rows)
    for bit in range(input_bits):
        if _rank([row & mask for row in rows]+[1 << bit]) > len(rows):
            rows.append(1 << bit)
    if len(rows) != input_bits or _rank([row & mask for row in rows]) != input_bits:
        raise AssertionError('Affine labels did not extend to an invertible frame.')
    matrix = [row & mask for row in rows]
    operations = []
    for column in range(input_bits):
        pivot = next(i for i in range(column, input_bits) if matrix[i] >> column & 1)
        if pivot != column:
            matrix[pivot], matrix[column] = matrix[column], matrix[pivot]
            operations.append(('swap', pivot, column))
        for row in range(input_bits):
            if row != column and matrix[row] >> column & 1:
                matrix[row] ^= matrix[column]
                operations.append(('cx', column, row))
    if matrix != [1 << bit for bit in range(input_bits)]:
        raise AssertionError('Linear address-frame synthesis failed.')
    constants = tuple(i for i, row in enumerate(rows) if row >> input_bits & 1)
    plan = AffineAddressPlan(input_bits, alias_bits, tuple(rows), tuple(operations), constants, pairs)
    if len({plan.transform(a) for a in range(1 << input_bits)}) != 1 << input_bits:
        raise AssertionError('Address-frame permutation certificate failed.')
    return plan


def search_affine_labels(allowed, *, alias_bits=3):
    """Exhaustively decide feasibility for <=3 affine residue bits.

    With8 address inputs this explores at most512² ordered pairs. The final
    bit is solved as a9-variable linear system, including all free solutions,
    rather than guessed. The returned address map is bijective on all inputs.
    """
    allowed = list(map(int, allowed))
    size = len(allowed)
    input_bits = size.bit_length()-1
    if size != 1 << input_bits or not 1 <= alias_bits <= min(3, input_bits):
        raise ValueError('Expected a power-of-two domain and1–3 label bits.')
    residue_mask = (1 << (1 << alias_bits))-1
    if any(value <= 0 or value & ~residue_mask for value in allowed):
        return None
    full = (1 << size)-1
    linear_mask = size-1
    forms = sorted(range(1, size*2),
                   key=lambda row: ((row & linear_mask).bit_count() + (row >> input_bits), row))
    forms = [row for row in forms if row & linear_mask]
    truth = {row: sum(((((a & (row & linear_mask)).bit_count() & 1)
                       ^ (row >> input_bits)) << a) for a in range(size))
             for row in forms}
    allowed_lsb = [sum(int(any((mask >> label) & 1
                              for label in range(1 << alias_bits) if label & 1 == value)) << a
                       for a, mask in enumerate(allowed)) for value in range(2)]
    if alias_bits == 1:
        for first in forms:
            yes = truth[first]
            if not ((full ^ yes) & (full ^ allowed_lsb[0]) or yes & (full ^ allowed_lsb[1])):
                return _make_plan([first], input_bits, alias_bits, 0)
        return None
    allowed_pair = []
    only_zero = []
    only_one = []
    for pair in range(4):
        flags = [(bool(mask & (1 << pair)),
                  bool(alias_bits == 3 and mask & (1 << (pair | 4)))) for mask in allowed]
        allowed_pair.append(sum(int(zero or one) << a for a, (zero, one) in enumerate(flags)))
        only_zero.append(sum(int(zero and not one) << a for a, (zero, one) in enumerate(flags)))
        only_one.append(sum(int(one and not zero) << a for a, (zero, one) in enumerate(flags)))
    pairs = 0
    for first in forms:
        left = truth[first]
        if ((full ^ left) & (full ^ allowed_lsb[0]) or left & (full ^ allowed_lsb[1])):
            continue
        for second in forms:
            if (first & linear_mask) == (second & linear_mask):
                continue
            right = truth[second]
            regions = ((full ^ left) & (full ^ right), left & (full ^ right),
                       (full ^ left) & right, left & right)
            pairs += 1
            if any(region & (full ^ permitted) for region, permitted in zip(regions, allowed_pair)):
                continue
            if alias_bits == 2:
                plan = _make_plan([first, second], input_bits, alias_bits, pairs)
            else:
                zero = one = 0
                for region, z, o in zip(regions, only_zero, only_one):
                    zero |= region & z
                    one |= region & o
                forbidden_linear = {0, first & linear_mask, second & linear_mask,
                                    (first ^ second) & linear_mask}
                thirds = _affine_solutions(zero, one, input_bits)
                thirds.sort(key=lambda row: ((row & linear_mask).bit_count() + (row >> input_bits), row))
                third = next((row for row in thirds if row & linear_mask not in forbidden_linear), None)
                if third is None:
                    continue
                plan = _make_plan([first, second, third], input_bits, alias_bits, pairs)
            if any(not (mask >> label & 1) for mask, label in zip(allowed, plan.labels)):
                raise AssertionError('Allowed-residue certificate failed.')
            return plan
    return None


def emit_address_frame(builder, address, plan, *, inverse=False):
    """Apply the selected reversible CNOT/X frame with no ancillas."""
    address = list(address)
    if len(address) != plan.input_bits:
        raise ValueError('Wrong address-frame width.')
    if inverse:
        for bit in plan.constants:
            builder.x(address[bit])
        operations = plan.reduction
    else:
        operations = reversed(plan.reduction)
    for operation, source, target in operations:
        if operation == 'cx':
            builder.cx(address[source], address[target])
        else:
            builder.swap(address[source], address[target])
    if not inverse:
        for bit in plan.constants:
            builder.x(address[bit])


def permute_table(values, plan):
    """Reindex a mathematical table by the new physical address frame."""
    values = list(values)
    if len(values) != 1 << plan.input_bits:
        raise ValueError('Wrong mathematical table size.')
    result = [None]*len(values)
    for old, value in enumerate(values):
        result[plan.transform(old)] = value
    return result





