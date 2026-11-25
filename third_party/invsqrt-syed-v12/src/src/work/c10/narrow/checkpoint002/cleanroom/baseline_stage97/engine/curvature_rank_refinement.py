# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Bounded rank refinement confined to the forward coefficient transition.

The original transition's exact target functions, choice order, live-code
allocation, consuming addition, and table-measurement owners are retained.
Only the polynomial selected after each original decode choice is refined.
In particular, this enables kernel-preserving search for the existing wide
codes where the generic scalar nullspace search is deliberately disabled.
"""
from __future__ import annotations

from contextlib import contextmanager

import kickmix as km
import new_lookup_design as original
from codebook import word_functions
from new_lookup_design import StaticCode, _stream_delta, coefficient_delta
from r17_lookup import _materialize
from split_lookup import live_word
from transition_codebook import LiveFunction, convert_codebook


class RankRefinedStaticCode(StaticCode):
    def __init__(self, builder, debts, live, *, decoder_trials=80,
                 basis_options=None, preserving_rounds=16):
        super().__init__(builder, debts, live, decoder_trials=decoder_trials,
                         basis_options=basis_options)
        self.preserving_rounds = int(preserving_rounds)
        if self.preserving_rounds < 0:
            raise ValueError('The rank-refinement round count must be nonnegative.')

    def decode(self, desired, seed, *, retire=()):
        retire = set(retire)
        previous_wires = set(self.live)-retire
        if retire:
            retained = [item for wire, item in self.live.items() if wire not in retire]
            consumed = [item for wire, item in self.live.items() if wire in retire]
            produced, meta = convert_codebook(
                self.builder, retained, consumed, desired, self.debts,
                trials=self.decoder_trials, seed=seed, kernel_trials=15000,
                preserving_rounds=self.preserving_rounds, **self.basis_options)
            for wire in retire:
                self.live.pop(wire)
            meta['retired_at_last_fanin'] = [item.name for item in consumed]
        else:
            produced, meta = _materialize(
                self.builder, list(self.live.values()), desired, self.debts,
                decoder_trials=self.decoder_trials, rank_rounds=self.preserving_rounds,
                seed=seed, basis_options=self.basis_options)
        copied = []
        for name, item in list(produced.items()):
            if item.wire in previous_wires:
                target = self.alloc(name)
                self.cx(item.wire, target)
                item = LiveFunction(name, target, item.truth)
                produced[name] = item
                copied.append(name)
            if item.wire not in self.live:
                self.live[item.wire] = item
        if copied:
            meta['consumable_clifford_copies'] = copied
        meta['bounded_preserving_rounds'] = self.preserving_rounds
        self.decoded.append(meta)
        return produced


def forward_residual_high(builder, data, curvature, low, saved_outer, debts,
                          *, saved_inner, decoder_trials=80, basis_options=None,
                          defer_fanin=True, preserving_rounds=16):
    """Preserve the selected C8/L19 transition while refining its decoders."""
    from r17_lookup import stored_low_labels
    labels = stored_low_labels(data)
    if len(curvature) != 8 or len(low) != len(labels):
        raise ValueError('Expected the existing C8 and the stored low coefficient code.')
    values, delta, _ = coefficient_delta(data)
    live = live_word('low', low, values['low'], bit_indices=labels)
    live += live_word('curvature', curvature, values['curvature'])
    live += live_word('outer', [saved_outer], [v >> 9 for v in values['blo']])
    live += live_word('inner', [saved_inner], [v >> 4 for v in values['blo']])
    code = RankRefinedStaticCode(builder, debts, live, decoder_trials=decoder_trials,
                                basis_options=basis_options, preserving_rounds=preserving_rounds)
    target = list(curvature[1:])
    if not defer_fanin:
        code.erase(saved_inner)
        code.erase(curvature[0])
    _stream_delta(code, target, delta, seed=20261106101,
                  retire_at_last=[curvature[0], saved_inner] if defer_fanin else ())
    expected = word_functions(values['bhi'], 7)
    if any(code.live[wire].truth != truth for wire, truth in zip(target, expected)):
        raise AssertionError('Refining the residual decoder changed an exact high coefficient.')
    count = code.and_count+sum(meta['and_count'] for meta in code.decoded)
    return km.array(target), dict(
        and_count=count, arithmetic_ands=code.and_count, decoder_stages=code.decoded,
        delta_interval=[min(delta), max(delta)], independent_delta_bits=[0, 1, 2, 3, 5],
        complement_relation=[4, 5, 1], erased_inner_boundary=True,
        deferred_fanin=bool(defer_fanin), arithmetic_truths_checked=256,
        table_measurements=len(code.measurements), qubits_after=builder.num_allocated_qubits,
        bounded_preserving_rounds=int(preserving_rounds),
        synthesis_parameters=dict(scalar_trials=decoder_trials, kernel_trials=15000,
            preserving_rounds=int(preserving_rounds), preserving_min_products=9,
            preserving_min_width=25, preserving_subspace_bits=9,
            base_seed=20261106101, elapsed_time_selection=False),
        original_function_allocation_and_ledger_owners_unchanged=True,
        saved_synthesis_plan_input=False)


@contextmanager
def installed(*, preserving_rounds=16):
    """Replace only the function imported locally by the forward source region."""
    previous = original.forward_residual_high
    if getattr(previous, '_curvature_rank_refinement', False):
        raise RuntimeError('The forward curvature rank refinement is already installed.')
    calls = []

    def refined(builder, data, curvature, low, saved_outer, debts, **options):
        from r17_lookup import stored_low_labels
        entry = 35+len(stored_low_labels(data))
        if builder.max_qubits not in (56, 57) or builder.num_allocated_qubits != entry:
            raise ValueError('This installation belongs to the selected forward transition cut.')
        if 'preserving_rounds' in options:
            raise ValueError('The installation scope owns its deterministic refinement bound.')
        result, metadata = forward_residual_high(
            builder, data, curvature, low, saved_outer, debts,
            preserving_rounds=preserving_rounds, **options)
        calls.append(dict(
            region='curvature_to_derivative_high', before_ANDs=52,
            after_ANDs=metadata['and_count'], saving=52-metadata['and_count'],
            arithmetic_ANDs=metadata['arithmetic_ands'],
            decoder_ANDs=[stage['and_count'] for stage in metadata['decoder_stages']],
            quantum_entry=entry, quantum_exit=metadata['qubits_after'],
            preserving_rounds=int(preserving_rounds),
            exact_final_functions_and_phase_owners_unchanged=True))
        return result, metadata

    refined._curvature_rank_refinement = True
    original.forward_residual_high = refined
    report = dict(scope='forward curvature transition only', calls=calls,
                  binding='new_lookup_design.forward_residual_high',
                  scheduled_local_import=True, preserving_rounds=int(preserving_rounds))
    try:
        yield report
        if len(calls) != 1:
            raise AssertionError('The selected schedule must execute exactly one refined forward transition.')
    finally:
        original.forward_residual_high = previous
