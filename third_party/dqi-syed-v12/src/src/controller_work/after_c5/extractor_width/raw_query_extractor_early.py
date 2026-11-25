# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""C5 raw-query arithmetic, with only the rolling flag lifetime changed.

All arithmetic calls/order are the C5 emitter's exact calls/order.  The local
Tail implementation moves zero(v/u) queries to the equal predicate zero(v).
The optional padded seed return is a separate +1-T caller-owned component.
"""
import ew_paths  # noqa: F401
import gf24_arithmetic as A
import rolling_tail_early as Tail
import raw_query_extractor as Base
from raw_query_extractor import Record, node, node_view, public_scale, query_step


def emit_prefix(builder, raw_words, carry, *, j_min=15, stop_index=35,
                stage=lambda _: None):
    words = list(raw_words)
    assert len(words) == 35 and all(len(word) == 24 for word in words)
    assert len(carry) == 24 and 1 <= stop_index <= 35 and 0 <= j_min < 35
    assert len(set([*carry, *(q for word in words for q in word)])) == 864
    tail = Tail.RollingTail(builder, j_min, stop_index) if stop_index > j_min else None
    inputs, inverses, normalizers = [None]*stop_index, [], []
    for i in range(stop_index):
        current = words[i]
        if i:
            inputs[i] = A.emit_prefix(builder, carry, current)
        for old in range(i):
            query_step(builder, words[old], current, carry, old, i)
        token = tail.begin_slot(current, carry, i) if i >= j_min else None
        inverses.append(A.inverse_deferred(builder, current))
        normalizers.append(A.emit_prefix(builder, current, carry))
        builder.swap(current, carry)
        if token is not None:
            tail.finish_slot(current, token)
        node_view(builder, current, i)
        stage(f'raw_query_prefix_{i:02d}')
    return Record(id(builder), tuple(tuple(w) for w in words), tuple(carry),
                  j_min, stop_index, tail, inputs, inverses, normalizers)


def emit_closing(builder, raw_words, carry, record, *, stage=lambda _: None):
    words = list(raw_words)
    assert record.builder_id == id(builder) and not record.closed
    assert tuple(tuple(w) for w in words) == record.words and tuple(carry) == record.carry
    tail, stop = record.tail, record.stop_index
    if tail is not None:
        assert tail.return_next == stop-1 and tail.pending is None
    for i in reversed(range(stop)):
        current = words[i]
        node_view(builder, current, i)
        token = tail.begin_return(current, i) if i >= record.j_min else None
        builder.swap(current, carry)
        inverse_return = A.inverse_deferred(builder, current)
        product_return = A.emit_prefix(builder, current, carry)
        targets = [(carry, product_return.old_target_mask)]
        next_return = None
        if i+1 < stop:
            next_return = A.emit_prefix(builder, current, words[i+1])
            targets.append((words[i+1], next_return.old_target_mask))
        A.phase_affine_quotient(builder, current, targets,
                               A.source_mask(inverse_return))
        A.free_source_masks(builder, inverse_return)
        A.free_product_mask(builder, product_return)
        if next_return is not None:
            A.free_product_mask(builder, next_return)
            A.repay_product_input(builder, words[i+1], record.input_scales[i+1])
        A.repay_source_masks(builder, current, record.inverse_masks[i])
        A.repay_product_input(builder, carry, record.normalizer_products[i])
        if token is not None:
            tail.finish_return(current, carry, token)
        for old in reversed(range(i)):
            query_step(builder, words[old], current, carry, old, i, True)
        stage(f'raw_query_return_{i:02d}')
    if tail is not None:
        tail.close()
    assert all(rec is None or rec.closed for rec in record.input_scales)
    assert all(rec.closed for rec in record.inverse_masks+record.normalizer_products)
    record.closed = True


def source_ledger(stop_index=35, j_min=15, *, full_seed_seam=False):
    out = Base.source_ledger(stop_index, j_min, full_seed_seam=full_seed_seam)
    out['status'] = 'SOURCE_MODEL_NOT_YET_NATIVE_CHECKED'
    out['peak_Q'] = 889 if stop_index > j_min else 888
    out['raw_flag_retime_T_delta'] = 0
    out['padded_seed_T_delta'] = int(full_seed_seam)
    out['total_pair_T'] += int(full_seed_seam)
    if full_seed_seam:
        out['scalar_seed_pair_T'] = 261
    return out
