# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Freshly synthesized zero-supported normalization at the original width.

The three highest count flags encode six coarse shifts of four-bit blocks.
Two lanes have six positions and two have five. Known leading zero support
permits a cheaper common exchange network than three independent binary
shifts. The network and every control polynomial are freshly derived by a
finite integer search; no saved plan, numerical table, or circuit is read.

An affine selector borrows a count flag in a temporary CNOT frame. A
quadratic selector uses one clean helper with exact X measurement and
conditional Z/CZ repayment. Its inputs are restored before every erasure.
The inverse reverses the certified routing and recomputes its selectors.
"""
from __future__ import annotations
from contextlib import contextmanager
from functools import lru_cache
from itertools import groupby

import prefix_normalization as original
from coarse_normalization_math import search, selector_terms
from cyclic_phase import _erase_polynomial
from quadratic_terms import compile_polynomial, xor_polynomial


@lru_cache(maxsize=1)
def synthesize():
    """Derive a complete deterministic network once in each generator process."""
    result = search(beam=128, depth=10, candidate_limit=200000, maximum_cost=31)
    if result['status'] != 'CERTIFIED_ROUTE_FOUND' or result['total_Toffoli_cost'] >= 32:
        raise AssertionError('Fresh coarse normalization synthesis did not improve its exact reference.')
    if not result['exact_symbolic_forward_and_inverse']:
        raise AssertionError('The synthesized route lacks its complete independent-symbol certificate.')
    return result


@contextmanager
def _selector(builder, variables, mask):
    """Expose one exact label predicate, then restore inputs and clear helpers."""
    variables = list(variables)
    specification = selector_terms(mask)
    terms = tuple(specification['terms'])
    plan = compile_polynomial(len(variables), terms)
    if len(plan.products) != specification['and_count'] or len(plan.products) > 1:
        raise AssertionError('A routing selector exceeded its quadratic one-product bound.')
    if not plan.products:
        if not terms or 0 in terms or any(term.bit_count() != 1 for term in terms):
            raise AssertionError('An affine coarse selector must be a nonzero homogeneous parity.')
        indices = [term.bit_length()-1 for term in terms]
        pivot = indices[0]
        for index in indices[1:]:
            builder.cx(variables[index], variables[pivot])
        try:
            yield variables[pivot]
        finally:
            for index in reversed(indices[1:]):
                builder.cx(variables[index], variables[pivot])
    else:
        helper = builder.alloc_qubits(1)[0]
        xor_polynomial(builder, variables, helper, terms)
        try:
            yield helper
        finally:
            _erase_polynomial(builder, helper, variables, terms)


def _coarse(builder, x, flags, *, inverse):
    certificate = synthesize()
    operations = certificate['coarse_block_exchanges']
    sequence = list(reversed(operations)) if inverse else list(operations)
    block_width = 4
    products = swaps = 0
    for mask, group in groupby(sequence, key=lambda operation: operation[2]):
        products += selector_terms(mask)['and_count']
        with _selector(builder, flags[1:], mask) as control:
            for first, second, _ in group:
                for lane in range(block_width):
                    left, right = block_width*first+lane, block_width*second+lane
                    if left < len(x) and right < len(x):
                        builder.cswap(control, x[left], x[right])
                        swaps += 1
    if products+swaps != certificate['total_Toffoli_cost']:
        raise AssertionError('Actual coarse emission differs from its selector-inclusive cost certificate.')


def _fused_shift(builder, x, flags, *, inverse):
    x, flags, maximum = original._shape(x, flags)
    if len(x) != 22 or len(flags) != 4 or maximum != 10:
        raise ValueError('Fused normalization requires the twenty-two-bit pair-count geometry.')

    def final_pair_shift():
        pairs = [(x[index], x[index-2]) for index in range(len(x)-1, 1, -1)]
        for left, right in reversed(pairs) if inverse else pairs:
            builder.cswap(flags[0], left, right)

    if inverse:
        final_pair_shift()
        _coarse(builder, x, flags, inverse=True)
    else:
        _coarse(builder, x, flags, inverse=False)
        final_pair_shift()


@contextmanager
def installed():
    """Install only this exact shift schedule for one source-emission scope."""
    previous = original._shift
    if previous is _fused_shift:
        raise RuntimeError('The fused normalization scope is already active.')
    original._shift = _fused_shift
    try:
        yield
    finally:
        original._shift = previous


def normalize(builder, x, flags, *, inverse=False, cleanup='branched', original_input_max=None):
    """Keep the selected prefix count and HMR flag cleanup unchanged."""
    options = {} if original_input_max is None else {'original_input_max': original_input_max}
    with installed():
        return original.normalize(builder, x, flags, inverse=inverse, cleanup=cleanup, **options)
