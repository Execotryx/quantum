# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Production-only first-two return with a fully retained norm stack.

Entry carry is the public constant1. The generic index2 return restores it
before the three first-two inverse charts. The carry is
unused until Pipeline resets and frees it. A public X temporarily turns1
into a zero24-bit bank for the three inverses; every bit is restored.
The old arbitrary-initial-carry component interface is deliberately separate.
"""
from dataclasses import dataclass
import direct_carry_first2 as Base
import inverse_retained_norm195 as Phase

A = Base.A
Arithmetic = Base.Arithmetic
Tail = Base.Tail
node_view = Base.node_view
node = Base.node
public_scale = Base.public_scale
_add_first_head_at_second_node = Base._add_first_head_at_second_node


@dataclass
class ProductionRecord:
    inner: object
    builder_id: int
    carry: tuple
    declared_initial_carry: int = 1
    closed_inverse_calls: int = 0
    borrow_receipts: object = None
    clean_carry_seam_reached: bool = False

    def __getattr__(self, name):
        return getattr(self.inner, name)


def emit_prefix(builder, raw_words, carry, *, j_min=15, stop_index=35,
                stage=lambda _: None, production_carry_value=1):
    if production_carry_value != 1:
        raise ValueError('this adapter requires the production constant-one carry')
    assert A is Base.A and Arithmetic is Base.Arithmetic and Tail is Base.Tail
    inner = Base.emit_prefix(builder, raw_words, carry, j_min=j_min,
                             stop_index=stop_index, stage=stage)
    return ProductionRecord(inner, id(builder), tuple(carry), borrow_receipts=[])


def emit_closing(builder, raw_words, carry, production, *, stage=lambda _: None):
    assert isinstance(production, ProductionRecord)
    assert production.builder_id == id(builder) and production.declared_initial_carry == 1
    assert production.carry == tuple(carry) and production.closed_inverse_calls == 0
    record = production.inner
    words = list(raw_words)
    assert record.builder_id == id(builder) and not record.closed
    assert tuple(tuple(w) for w in words) == record.words and tuple(carry) == record.carry
    tail, stop = record.tail, record.stop_index
    if tail is not None:
        assert tail.return_next == stop-1 and tail.pending is None
    for i in reversed(range(2, stop)):
        current = words[i]
        node_view(builder, current, i)
        token = tail.begin_return(current, i) if i >= record.j_min else None
        builder.swap(current, carry)
        Arithmetic.restore_with_shared_norm(builder, current, carry, record.divisions[i],
            next_word=words[i+1] if i+1 < stop else None,
            next_input_record=record.input_scales[i+1] if i+1 < stop else None)
        if token is not None:
            tail.finish_return(current, carry, token)
        for old in reversed(range(i)):
            Base.query_step(builder, words[old], current, carry, old, i, True)
        stage(f'raw_query_return_{i:02d}')
    if tail is not None:
        tail.close()

    # The ordinary inverse loop has restored the declared public carry1.
    # No source/query operation below reads it. Turn it into a zero bank,
    # return all24 storage bits after every inverse, then restore carry1.
    assert not production.clean_carry_seam_reached
    production.clean_carry_seam_reached = True
    stage('first_two_clean_carry_seam')
    builder.x(carry[0])
    clean_bank = carry

    def closed_inverse(word):
        receipt = Phase.inverse_closed_with_bank(builder, word, clean_bank)
        production.borrow_receipts.append(receipt)
        production.closed_inverse_calls += 1
        assert receipt['all_owned_storage_bits_reset']

    first, second_inner, second_outer = record.first_inverses
    node_view(builder, words[1], 1)
    closed_inverse(words[1])
    A.repay_source_masks(builder, words[1], second_outer)
    public_scale(builder, words[1], node(0)[1] ^ node(1)[1])
    _add_first_head_at_second_node(builder, words)
    closed_inverse(words[1])
    A.repay_source_masks(builder, words[1], second_inner)
    stage('raw_query_return_01')
    node_view(builder, words[0], 0)
    closed_inverse(words[0])
    A.repay_source_masks(builder, words[0], first)
    stage('raw_query_return_00')
    assert production.closed_inverse_calls == 3
    builder.x(carry[0])
    assert all(rec is None or rec.closed for rec in record.input_scales)
    assert all(rec is None or rec.closed for rec in record.divisions)
    assert all(rec.closed for rec in record.first_inverses)
    record.closed = True


def source_ledger(*args, **kwargs):
    result = dict(Base.source_ledger(*args, **kwargs))
    result.update(status='PRODUCTION_ONLY_RETAINED_NORM_STACK_MODEL',
                  source_ledger_reference='Immutable first-two ledger before later v4 deltas',
                  incremental_static_delta_from_selected_v4=-243,
                  incremental_mean_delta_from_selected_v4='-243-12/64+252/16777216',
                  production_initial_carry=1, borrowed_physical_indices=list(range(24)),
                  additional_domain_exclusion=False,
                  arbitrary_initial_carry_supported=False)
    return result
