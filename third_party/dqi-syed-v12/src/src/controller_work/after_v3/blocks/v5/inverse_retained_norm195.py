# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Closed K24 inverse with a retained original norm and child reciprocal.

The caller supplies twenty-four owned zero bits. They hold the original
twelve-bit norm, its six-bit norm, and that child's reciprocal. All return
to zero. Two exact HMR debts use these retained witnesses before their
owners are reset; only the scalar GF64 inverse phase costs additional T.
Static195, at most24 extra helpers; no unit or nonzero-half promise.
"""
from __future__ import annotations

import kickmix as km
import gf24_nested_norm as Arithmetic
import cubic_inverse130 as Cubic
import scalar_inverse_phase as Scalar
from quantum_reciprocal import xor_linear
from tower_inverse import (quadratic_basis, apply_inplace_linear, norm_columns,
                           xor_product, phase_product, erase_norm, kernel)


def _xor_norm(builder, left, right, target, delta):
    squares_left, squares_right = norm_columns(len(left), delta)
    xor_product(builder, left, right, target)
    xor_linear(builder, left, target, squares_left)
    xor_linear(builder, right, target, squares_right)


def inverse_closed_with_bank(builder, source, clean_bank,
                             delta=Arithmetic.DEFAULT_DELTA):
    """Invert a K24 word and restore its twenty-four owned clean storage bits.

The output is inv0(source) in the original polynomial extension encoding.
Internal allocated outputs belong to this call and are erased before return.
The caller-owned bank is never freed or treated as allocator scratch.
"""
    if len(source) != 24 or len(clean_bank) != 24:
        raise ValueError('one K24 source and twenty-four clean owned bits are required')
    quantum = [*source, *clean_bank]
    if not all(isinstance(wire, km.q) for wire in quantum):
        raise TypeError('source and clean storage bank must be quantum')
    if len(set(quantum)) != len(quantum):
        raise ValueError('source and clean storage bank must be disjoint')
    if delta != Arithmetic.DEFAULT_DELTA:
        raise ValueError('this provider is bound to the production extension')
    before = builder.num_allocated_qubits
    original_norm, child_norm, child_inverse = clean_bank[:12], clean_bank[12:18], clean_bank[18:]
    _xor_norm(builder, source[:12], source[12:], original_norm, delta)
    info = quadratic_basis(12)
    apply_inplace_linear(builder, original_norm, info['to_tower'])
    left, right = original_norm[:6], original_norm[6:]
    _xor_norm(builder, left, right, child_norm, info['delta'])
    returned = Cubic.inverse_six_cubic(builder, child_norm, target=child_inverse)
    assert tuple(returned) == tuple(child_inverse)
    assert builder.num_allocated_qubits == before

    inverse_norm = builder.alloc_qubits(12)
    builder.cx(right, left)
    xor_product(builder, left, child_inverse, inverse_norm[:6])
    builder.cx(right, left)
    xor_product(builder, right, child_inverse, inverse_norm[6:])
    apply_inplace_linear(builder, inverse_norm, info['from_tower'])
    apply_inplace_linear(builder, original_norm, info['from_tower'])
    temporary = builder.alloc_qubits(12)
    masks = []
    for half in (source[:12], source[12:]):
        xor_product(builder, half, inverse_norm, temporary)
        builder.swap(half, temporary)
        mask = builder.alloc_bits(12)
        builder.hmr(temporary, mask)
        masks.append(mask)
    builder.free(temporary)
    for half, mask in zip((source[:12], source[12:]), masks):
        phase_product(builder, half, original_norm, mask, kernel(12))
        builder.free(mask)

    # HMR the original norm in the exact tower coordinates used by its
    # retained-child reconstruction. If inverse_norm=(X,Y), the original
    # norm is((X+Y)*child_norm, Y*child_norm), also when both are zero.
    apply_inplace_linear(builder, original_norm, info['to_tower'])
    norm_mask = builder.alloc_bits(12)
    builder.hmr(original_norm, norm_mask)
    apply_inplace_linear(builder, inverse_norm, info['to_tower'])
    inverse_left, inverse_right = inverse_norm[:6], inverse_norm[6:]
    builder.cx(inverse_right, inverse_left)
    phase_product(builder, inverse_left, child_norm, norm_mask[:6], kernel(6))
    builder.cx(inverse_right, inverse_left)
    phase_product(builder, inverse_right, child_norm, norm_mask[6:], kernel(6))
    builder.free(norm_mask)

    # This mask belongs to tower(child_norm), not its polynomial encoding.
    # The accepted scalar phase explicitly expects this tower-mask ABI.
    child_info = quadratic_basis(6)
    apply_inplace_linear(builder, child_norm, child_info['to_tower'])
    child_mask = builder.alloc_bits(6)
    builder.hmr(child_norm, child_mask)
    Scalar.phase_inverse_six(builder, child_inverse, child_mask)
    builder.free(child_mask)
    erase_norm(builder, inverse_left, inverse_right, child_inverse, info['delta'])
    apply_inplace_linear(builder, inverse_norm, info['from_tower'])
    builder.cx(source[12:], source[:12])
    erase_norm(builder, source[:12], source[12:], inverse_norm, delta)
    builder.free(inverse_norm)
    assert builder.num_allocated_qubits == before
    return dict(inverse_static_T=195, retained_storage_bits=24,
                original_norm_bits=12, child_norm_bits=6, child_inverse_bits=6,
                scalar_inverse_phase_static_T=4, maximum_additional_helpers=24,
                all_owned_storage_bits_reset=True)


def source_ledger():
    return dict(status='SOURCE_MODEL_NATIVE_PENDING', inverse_static_T=195,
        maximum_additional_helpers=24, separately_owned_clean_storage_bits=24,
        parts=dict(original_norm=42, child_norm=15, child_inverse=20,
                   reciprocal_reassembly=30, consuming_half_products=84,
                   scalar_inverse_phase=4),
        exact_execution='191+4*[fresh six-bit child-norm HMR mask is nonzero]',
        mean_under_fresh_HMR='195-4/64', eligible_production_calls=3,
        production_static_saving_from_selected_v4=243,
        production_mean_saving_from_selected_v4='243+12/64-252/16777216',
        existing_scalar_event_hook_counts_cleanup=True,
        additional_event_hook_must_not_duplicate_cleanup=True,
        new_population_event=False)
