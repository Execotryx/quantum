# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Stream residual coefficient bits into a consuming table-only adder.

The selected mathematical table satisfies Bhi=(Cstored>>1)+D, 20<=D<=37.
Only five independent bits of D are decoded.  Its bits D[4] and D[5]
are complementary.  The low four bits are decoded together, then consumed
by arithmetic before the final independent bit is decoded.  Every erased
source and carry is a known function of the original logical address, so
its exact HMR sign enters the common table-phase ledger.

No circuit or gate-list file is read.  The research CLI takes only our own
coefficient profile and emits a budget plus independent all-outcome proof.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time


import kickmix as km
from affine_table_layout import prepare_lookup_view
from branch_prover import Program, generated_text
from codebook import word_functions
from deferred_phase import DeferredTablePhases
from r17_lookup import table_words, _materialize
from split_lookup import live_word, desired_word, unique_live
from transition_codebook import LiveFunction, _word_table, convert_codebook


FULL = (1 << 256)-1
DEFAULT_BASIS = dict(basis_search_products=3, basis_natural_limit=256,
                     basis_random_trials=256, basis_random_max_products=5,
                     preserve_future=True)


def coefficient_delta(data):
    values = table_words(data)
    d = [b-(c >> 1) for b, c in zip(values['bhi'], values['curvature'])]
    if not (min(d) >= 20 and max(d) <= 37):
        raise ValueError('This conversion needs the certified D interval20..37.')
    if any(((v >> 4) ^ (v >> 5)) & 1 != 1 for v in d):
        raise AssertionError('D4 and D5 must be complementary.')
    negative = [(-v) & 127 for v in d]
    if any(v >> 6 != 1 or (((v >> 4) ^ (v >> 5)) & 1) != 1 for v in negative):
        raise AssertionError('The consumed subtraction operand has the wrong fixed frame.')
    return values, d, negative


class StaticCode:
    """A live, exactly tracked table code; every gate updates its truth table."""

    def __init__(self, builder, debts, live, *, decoder_trials=80, basis_options=None):
        self.builder = builder
        self.debts = debts
        self.live = {item.wire: LiveFunction(item.name, item.wire, item.truth)
                     for item in unique_live(live)}
        self.and_count = 0
        self.measurements = []
        self.decoded = []
        self.decoder_trials = decoder_trials
        self.basis_options = DEFAULT_BASIS if basis_options is None else basis_options

    def alloc(self, name):
        wire = self.builder.alloc_qubits(1)[0]
        self.live[wire] = LiveFunction(name, wire, 0)
        return wire

    def x(self, wire):
        self.builder.x(wire)
        self.live[wire].truth ^= FULL

    def cx(self, control, target):
        self.builder.cx(control, target)
        self.live[target].truth ^= self.live[control].truth

    def ccx(self, left, right, target):
        self.builder.ccx(left, right, target)
        self.live[target].truth ^= self.live[left].truth & self.live[right].truth
        self.and_count += 1

    def erase(self, wire):
        item = self.live.pop(wire)
        self.debts.erase(self.builder, _word_table([item.truth]), [wire])
        self.builder.free(wire)
        self.measurements.append(dict(name=item.name, truth=item.truth))

    def decode(self, desired, seed, *, retire=()):
        retire = set(retire)
        previous_wires = set(self.live)-retire
        if retire:
            retained = [item for wire, item in self.live.items() if wire not in retire]
            consumed = [item for wire, item in self.live.items() if wire in retire]
            produced, meta = convert_codebook(
                self.builder, retained, consumed, desired, self.debts,
                trials=self.decoder_trials, seed=seed, kernel_trials=15000,
                preserving_rounds=0, **self.basis_options)
            for wire in retire:
                self.live.pop(wire)
            meta['retired_at_last_fanin'] = [item.name for item in consumed]
        else:
            produced, meta = _materialize(
                self.builder, list(self.live.values()), desired, self.debts,
                decoder_trials=self.decoder_trials, rank_rounds=0, seed=seed,
                basis_options=self.basis_options)
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
        self.decoded.append(meta)
        return produced

    def add_bit(self, target, source, carry, *, last=False, consume_source=True):
        """One ordinary full-adder row; source may be the constant0 or1.

        Consuming a static source/carry frees its wire immediately after the
        sum is made.  Their phase debts are exact address functions.  The
        row therefore needs only one initial clean carry slot and never a
        reverse ripple.  The final target bit needs no outgoing carry.
        """
        constant = isinstance(source, int)
        if constant and source not in (0, 1):
            raise ValueError('A constant source must be a bit.')
        if last:
            if constant:
                if source:
                    self.x(target)
            else:
                self.cx(source, target)
            if carry is not None:
                self.cx(carry, target)
                self.erase(carry)
            if not constant and consume_source:
                self.erase(source)
            return None
        new = self.alloc('carry')
        if carry is None:
            if constant:
                if source:
                    self.cx(target, new)
                    self.x(target)
            else:
                self.ccx(source, target, new)
                self.cx(source, target)
        elif constant:
            self.ccx(carry, target, new)
            if source:
                self.cx(carry, new)
                self.cx(target, new)
                self.x(target)
            self.cx(carry, target)
        else:
            # carry_out = (a XOR c)*(b XOR c) XOR c.
            self.cx(carry, source)
            self.cx(carry, target)
            self.ccx(source, target, new)
            self.cx(carry, new)
            self.cx(carry, source)
            # target is currently b XOR c; add the restored a.
            self.cx(source, target)
        if carry is not None:
            self.erase(carry)
        if not constant and consume_source:
            self.erase(source)
        return new


def _stream_delta(code, target, operand, *, seed, prefix='delta', retire_at_last=()):
    """Load four low delta bits, consume them, then load the fifth bit."""
    functions = word_functions(operand, 7)
    if retire_at_last:
        produced = code.decode([(f'{prefix}{i}', functions[i]) for i in range(2)], seed)
        carry = None
        for i in range(2):
            carry = code.add_bit(target[i], produced[f'{prefix}{i}'].wire, carry)
        produced = code.decode([(f'{prefix}2', functions[2])], seed+1)
        carry = code.add_bit(target[2], produced[f'{prefix}2'].wire, carry)
        produced = code.decode([(f'{prefix}{i}', functions[i]) for i in (3, 5)], seed+2,
                               retire=retire_at_last)
        carry = code.add_bit(target[3], produced[f'{prefix}3'].wire, carry)
    else:
        produced = code.decode([(f'{prefix}{i}', functions[i]) for i in range(4)], seed)
        carry = None
        for i in range(4):
            carry = code.add_bit(target[i], produced[f'{prefix}{i}'].wire, carry)
        produced = code.decode([(f'{prefix}5', functions[5])], seed+1)
    top = produced[f'{prefix}5'].wire
    code.x(top)
    carry = code.add_bit(target[4], top, carry, consume_source=False)
    code.x(top)
    carry = code.add_bit(target[5], top, carry)
    last = operand[0] >> 6
    if last not in (0, 1) or any(v >> 6 != last for v in operand):
        raise ValueError('The source top bit is not constant.')
    code.add_bit(target[6], last, carry, last=True)


def forward_residual_high(builder, data, curvature, low, saved_outer, debts,
                          *, saved_inner, decoder_trials=80, basis_options=None,
                          defer_fanin=True):
    """Consume C8 and the unused inner boundary; return numeric Bhi7."""
    from r17_lookup import stored_low_labels
    labels = stored_low_labels(data)
    if len(curvature) != 8 or len(low) != len(labels):
        raise ValueError('Expected C8 and the stored nearest-anchor target frame.')
    values, delta, _ = coefficient_delta(data)
    live = live_word('low', low, values['low'], bit_indices=labels)
    live += live_word('curvature', curvature, values['curvature'])
    live += live_word('outer', [saved_outer], [v >> 9 for v in values['blo']])
    live += live_word('inner', [saved_inner], [v >> 4 for v in values['blo']])
    code = StaticCode(builder, debts, live, decoder_trials=decoder_trials,
                      basis_options=basis_options)
    target = list(curvature[1:])
    if not defer_fanin:
        code.erase(saved_inner)
        code.erase(curvature[0])
    _stream_delta(code, target, delta, seed=20261106101,
                  retire_at_last=[curvature[0], saved_inner] if defer_fanin else ())
    expected = word_functions(values['bhi'], 7)
    if any(code.live[wire].truth != truth for wire, truth in zip(target, expected)):
        raise AssertionError('The streamed residual addition did not produce Bhi.')
    count = code.and_count+sum(meta['and_count'] for meta in code.decoded)
    return km.array(target), dict(
        and_count=count, arithmetic_ands=code.and_count, decoder_stages=code.decoded,
        delta_interval=[min(delta), max(delta)], independent_delta_bits=[0, 1, 2, 3, 5],
        complement_relation=[4, 5, 1], erased_inner_boundary=True,
        deferred_fanin=bool(defer_fanin),
        arithmetic_truths_checked=256, table_measurements=len(code.measurements),
        qubits_after=builder.num_allocated_qubits)


def reverse_residual_curvature(builder, data, high, low, saved_outer, debts,
                              *, decoder_trials=80, basis_options=None,
                              defer_fanin=True):
    """Consume Bhi7, restore C8 and the inner boundary before inverse rows."""
    if len(high) != 7 or len(low) != 19:
        raise ValueError('Expected Bhi7 and the19-bit nearest-anchor target frame.')
    values, delta, negative = coefficient_delta(data)
    live = live_word('low', low, values['low'])
    live += live_word('high', high, values['bhi'])
    live += live_word('outer', [saved_outer], [v >> 9 for v in values['blo']])
    code = StaticCode(builder, debts, live, decoder_trials=decoder_trials,
                      basis_options=basis_options)
    target = list(high)
    c0 = word_functions(values['curvature'], 1)[0]
    inner = word_functions(values['blo'], 5)[4]
    if defer_fanin:
        produced = code.decode([('curvature0', c0), ('inner_boundary', inner)], 20261106200)
        restored_c0, restored_inner = produced['curvature0'].wire, produced['inner_boundary'].wire
    _stream_delta(code, target, negative, seed=20261106201, prefix='negative_delta',
                  retire_at_last=[saved_outer] if defer_fanin else ())
    expected = word_functions([c >> 1 for c in values['curvature']], 7)
    if any(code.live[wire].truth != truth for wire, truth in zip(target, expected)):
        raise AssertionError('The streamed residual subtraction did not produce C>>1.')
    if not defer_fanin:
        produced = code.decode([('curvature0', c0), ('inner_boundary', inner)], 20261106203)
        restored_c0, restored_inner = produced['curvature0'].wire, produced['inner_boundary'].wire
    result = km.array([restored_c0, *target])
    count = code.and_count+sum(meta['and_count'] for meta in code.decoded)
    return result, restored_inner, dict(
        and_count=count, arithmetic_ands=code.and_count, decoder_stages=code.decoded,
        delta_interval=[min(delta), max(delta)], negative_delta_interval=[min(negative), max(negative)],
        independent_delta_bits=[0, 1, 2, 3, 5], complement_relation=[4, 5, 1],
        deferred_fanin=bool(defer_fanin), erased_outer_boundary=bool(defer_fanin),
        arithmetic_truths_checked=256, table_measurements=len(code.measurements),
        qubits_after=builder.num_allocated_qubits)


