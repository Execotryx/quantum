# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Recover the address and curvature from a restored low constant codeword.

The main result rows may run with every raw address wire measured and freed.
After their inverse, the restored L0 is an injective code of the address.
Small, explicitly computed products extend its quadratic feature space;
subsequent coefficient transitions are certified on every mathematical row.
"""
from __future__ import annotations
from itertools import combinations
import kickmix as km
from codebook import BinarySpan, Codebook, pack_bits, word_functions
from transition_codebook import LiveFunction, convert_codebook


def helper_plan(low_values, targets, *, width=20, maximum=6):
    """Greedily choose AND helpers by exact codebook rank and target coverage."""
    low_values = list(map(int, low_values))
    if len(low_values) != 256 or len(set(low_values)) != 256:
        raise ValueError('L0 must be an injective256-entry mathematical codebook.')
    original = word_functions(low_values, width)
    functions = list(original)
    targets = list(map(int, targets))
    selected, ranks = [], []
    while True:
        code = Codebook(functions)
        covered = sum(code.span.solve(target) is not None for target in targets)
        ranks.append({'variables': len(functions), 'quadratic_rank': len(code.span.pivots),
                      'targets_covered': covered})
        if covered == len(targets):
            return {'pairs': selected, 'ranks': ranks, 'and_count': len(selected),
                    'injective_rows_checked': 256}
        if len(selected) >= maximum:
            raise ValueError('The configured helper budget cannot decode all requested functions.')
        best = None
        linear = BinarySpan([(1 << 256)-1]+functions)
        for i, j in combinations(range(width), 2):
            function = original[i] & original[j]
            if linear.solve(function) is not None:
                continue
            candidate = Codebook(functions+[function])
            score = (len(candidate.span.pivots),
                     sum(candidate.span.solve(target) is not None for target in targets), -i, -j)
            if best is None or score > best[0]:
                best = (score, i, j, function)
        if best is None or best[0][0] <= len(code.span.pivots):
            raise ValueError('No new helper increases the reachable quadratic feature space.')
        _, i, j, function = best
        selected.append((i, j))
        functions.append(function)


def _place_address(builder, returned, destination, curvature, preserved):
    """Route recovered data to the original register wires using SWAPs only.

    All free slots are temporarily allocated, so even original input slots
    reused during arithmetic are explicitly owned during routing. The maximum
    remains the caller's existing width budget. Logical zero slots are freed
    after routing, wherever the swaps moved them.
    """
    padding = list(builder.alloc_qubits(builder.max_qubits-builder.num_allocated_qubits))
    words = {'address': list(returned), 'curvature': list(curvature), 'padding': padding}
    words.update({name: list(wires) for name, wires in preserved.items()})
    for bit, target in enumerate(destination):
        source = words['address'][bit]
        if source == target:
            continue
        builder.swap(source, target)
        for values in words.values():
            for i, wire in enumerate(values):
                if wire == source:
                    values[i] = target
                elif wire == target:
                    values[i] = source
    if words['address'] != list(destination):
        raise AssertionError('Address register restoration failed.')
    builder.free(km.array(words.pop('padding')))
    return words


def return_from_low(builder, low, low_values, curvature_values, phase_debts,
                    *, address_destination=None, preserved=None, decoder_trials=400,
                    compress_low_code=True, extra_outputs=None, rank_rounds=64):
    """Consume restored L0, return8 address bits and the curvature word.

    `low_values` and `curvature_values` are indexed by the logical address used
    by the phase ledger. R and residual wires are never used as code features.
    An optional original-address destination is restored by a Clifford wire
    permutation; any overlapping preserved word must be supplied for remapping.
    """
    low = list(low)
    low_values, curvature_values = list(map(int, low_values)), list(map(int, curvature_values))
    compression = None
    if compress_low_code:
        # A sign-extension bit can add only a rare-exception feature while
        # consuming a full qubit. Its measured value may be deferred just like
        # any other consumed table bit, if the remaining code is injective.
        original_rank = len(Codebook(word_functions(low_values, len(low))).span.pivots)
        candidates = []
        for bit in range(len(low)):
            projected = [(value & ((1 << bit)-1)) | ((value >> (bit+1)) << bit)
                         for value in low_values]
            if len(set(projected)) != 256:
                continue
            rank = len(Codebook(word_functions(projected, len(low)-1)).span.pivots)
            if rank >= original_rank-2:
                candidates.append((-rank, -bit, projected))
        if candidates:
            negative_rank, negative_bit, projected = min(candidates)
            bit = -negative_bit
            phase_debts.erase(builder, [(value >> bit) & 1 for value in low_values], [low[bit]])
            builder.free(low.pop(bit))
            low_values = projected
            compression = {'removed_bit': bit, 'old_quadratic_rank': original_rank,
                           'new_quadratic_rank': -negative_rank,
                           'remaining_code_injective': True, 'and_count': 0}
    low_functions = word_functions(low_values, len(low))
    address_functions = word_functions(range(256), 8)
    cw = max(curvature_values).bit_length()
    curvature_functions = word_functions(curvature_values, cw)
    desired = [(f'address{bit}', function) for bit, function in enumerate(address_functions)]
    desired += [(f'curvature{bit}', function) for bit, function in enumerate(curvature_functions)]
    extras = {str(name): (int(values) if isinstance(values, int) else pack_bits(values))
              for name, values in (extra_outputs or {}).items()}
    if set(extras) & {'address', 'curvature', 'padding'}:
        raise ValueError('An extra output name conflicts with a reserved word name.')
    desired += [(f'extra:{name}', function) for name, function in extras.items()]
    helpers = helper_plan(low_values, [function for _, function in desired], width=len(low))
    helper_wires = list(builder.alloc_qubits(len(helpers['pairs'])))
    consumed = [LiveFunction(f'low{bit}', wire, function)
                for bit, (wire, function) in enumerate(zip(low, low_functions))]
    for index, ((i, j), wire) in enumerate(zip(helpers['pairs'], helper_wires)):
        builder.ccx(low[i], low[j], wire)
        consumed.append(LiveFunction(f'helper{index}', wire, low_functions[i] & low_functions[j]))
    produced, transition = convert_codebook(builder, [], consumed, desired, phase_debts,
                                            trials=decoder_trials, seed=161803,
                                            kernel_trials=15000,
                                            preserving_rounds=rank_rounds)
    address = [produced[f'address{bit}'].wire for bit in range(8)]
    curvature = [produced[f'curvature{bit}'].wire for bit in range(cw)]
    returned = {'address': address, 'curvature': curvature}
    returned.update({name: list(wires) for name, wires in (preserved or {}).items()})
    returned.update({name: [produced[f'extra:{name}'].wire] for name in extras})
    if address_destination is not None:
        other_words = {name: wires for name, wires in returned.items() if name not in ('address', 'curvature')}
        returned = _place_address(builder, address, address_destination, curvature, other_words)
    metadata = {'code_compression': compression, 'helpers': helpers, 'transition': transition,
                'and_count': helpers['and_count']+transition['and_count'],
                'qubits_after': builder.num_allocated_qubits,
                'extra_output_names': list(extras)}
    return {name: km.array(wires) for name, wires in returned.items()}, metadata

