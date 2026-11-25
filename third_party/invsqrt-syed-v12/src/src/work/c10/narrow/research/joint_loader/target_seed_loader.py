# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Short, resumable mathematical loader search from target-aligned seeds.

No native files or models are changed. The default job is capped at three
seconds and 128 MiB. Each completed output has a saved exact 128-row witness.
The older adaptive chart implementation is reused, but no C++ factor search
or subprocess is launched here.
"""
import argparse
import hashlib
import json
import random
import resource
import signal
import time
from pathlib import Path

from bank_frontier import checked_model, raw_functions, serialize, restore, HERE, MODEL, MODEL_SHA, CODE_SHA, cb
from adaptive_product_bank import Chart, FULL
from subspace_frontier import plan_expression, improve_coset, independent_complement
from atomic_io import atomic_text


def small_plan(book, outputs, loaded, rng, rounds):
    linear = cb.BinarySpan([FULL] + list(book.functions))
    for mask in independent_complement(loaded, len(outputs)):
        expression = linear.solve(cb.parity_function(mask, outputs))
        if expression is not None:
            return cb.factor_polynomial(book.width, bool(expression & 1), expression >> 1, []), mask
    span = cb.BinarySpan(book.columns)
    base = len(book.columns)
    for truth in outputs:
        span.add(truth)
    directions = cb.BinarySpan(loaded)
    expressions = []
    for relation in span.nullspace:
        mask = relation >> base
        if mask and directions.add(mask):
            expressions.append((mask, relation & ((1 << base) - 1)))
    if not expressions:
        return None, None
    candidates = []
    for mask, expression in expressions:
        plan = book.represent(cb.parity_function(mask, outputs), trials=2, seed=rng.randrange(1 << 30))
        candidates.append((plan.and_count, rng.random(), mask, plan_expression(book, plan)))
    candidates.sort()
    best = None
    outspan = cb.BinarySpan(outputs)
    for _, tie, anchor, expression in candidates[:2]:
        relations = list(book.span.nullspace) + [e for m, e in expressions if m != anchor]
        plan = improve_coset(book, expression, relations, rounds=rounds, subspace_bits=5, seed=rng.randrange(1 << 30))
        truth = plan.evaluate_factored_functions(book.functions, FULL)
        mask = outspan.solve(truth)
        assert mask is not None and cb.BinarySpan(loaded).solve(mask) is None
        candidate = plan.and_count, tie, plan, mask
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2], best[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--work-cap', required=True, type=int)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--seed-prefix', type=int, default=12)
    ap.add_argument('--seed-certificate', default=str(HERE / 'search' / 'target_seed_extended_s0.json'))
    ap.add_argument('--seconds', type=float, default=3)
    ap.add_argument('--rounds', type=int, default=4)
    ap.add_argument('--resume')
    args = ap.parse_args()
    assert 0 < args.seconds <= 5, 'This short-job runner is deliberately capped at five seconds.'
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    signal.alarm(8)
    began = time.monotonic()
    rng = random.Random(args.seed)
    model = checked_model()
    raw = raw_functions(False)
    outputs = cb.word_functions(model['A'], 13) + cb.word_functions(model['stored_slope'], 3)
    path = HERE / 'search' / f'{args.name}.json'
    seed_path = Path(args.seed_certificate)
    seed_data = json.loads(seed_path.read_text())
    assert seed_data['model_sha256'] == MODEL_SHA
    work, steps = [], []
    for item in seed_data['steps'][:args.seed_prefix]:
        plan = restore(item['plan'])
        truth = plan.evaluate_factored_functions(raw + work, FULL)
        assert truth == int(item['truth'], 16) and plan.and_count == 1
        steps.append(dict(kind='bank', name=item['name'], truth=hex(truth), plan=serialize(plan), Toffolis=1))
        work.append(truth)
    loaded = [1 << 11, 1 << 12]
    summaries = []
    assert work[5:7] == [outputs[11], outputs[12]]
    chart = Chart(raw, work, steps, args.work_cap, rng)
    if args.resume:
        previous = json.loads(Path(args.resume).read_text())
        assert previous['model_sha256'] == MODEL_SHA and previous['work_cap'] == args.work_cap
        assert previous['output_bits'] == list(range(16)) and previous['status'] != 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
        chart.work = list(map(lambda v: int(v, 16), previous['current_work_truths']))
        chart.steps = previous['steps']
        chart.peak = previous['work_peak']
        chart.ands = previous['Toffolis']
        loaded = previous['loaded_output_masks']
        summaries = previous['output_summaries']

    def save(status):
        result = dict(
            status=status, model=MODEL, model_sha256=MODEL_SHA, codebook_source_sha256=CODE_SHA,
            raw_address=True, output_bits=list(range(16)), loaded_output_masks=loaded,
            Toffolis=chart.ands, T=0, rotations=0, work_cap=args.work_cap, work_peak=chart.peak,
            current_work_truths=[hex(t) for t in chart.work], output_summaries=summaries, steps=chart.steps,
            seed_certificate=str(seed_path), seed_certificate_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
            initial_target_output_bits=[11, 12], initial_seed_prefix=args.seed_prefix,
            phase_debt_scope='All helper directions depend only on original raw address. The already certified retained-table cleanup9 pays their complete debts.',
            seed=args.seed, elapsed_seconds_this_slice=time.monotonic()-began,
            memory_guard_MiB=128, wall_limit_seconds=args.seconds, hard_alarm_seconds=8,
            physical_native_proof=False, official_verifier=False,
        )
        atomic_text(path, json.dumps(result, indent=2) + '\n')
        return result

    save('RUNNING_SHORT_MATHEMATICAL_SLICE')
    while len(loaded) < len(outputs):
        if time.monotonic() - began >= args.seconds:
            save('BOUNDED_PARTIAL')
            break
        loaded_truths = [cb.parity_function(mask, outputs) for mask in loaded]
        assert chart.frame(loaded_truths, args.work_cap-1, label='target_seed_reserve_initial_product_target')
        functions = raw + chart.work
        book = cb.Codebook(functions, 128)
        plan, mask = small_plan(book, outputs, loaded, rng, args.rounds)
        if plan is None:
            save('STUCK_NO_QUADRATIC_DIRECTION')
            break
        target = cb.parity_function(mask, outputs)
        assert plan.evaluate_factored_functions(functions, FULL) == target
        charge = chart.emit_plan(plan, functions, loaded_truths, target)
        loaded.append(mask)
        assert len(cb.BinarySpan(loaded).pivots) == len(loaded)
        summaries.append(dict(output_index=len(loaded)-1, target_mask=mask, planned_products=plan.and_count,
                              actual_Toffolis=charge, plan=serialize(plan), inputs=[hex(t) for t in functions],
                              work_after=len(chart.work)))
        save('RUNNING_SHORT_MATHEMATICAL_SLICE')
        print(json.dumps(dict(outputs=len(loaded), charge=charge, total=chart.ands, work=len(chart.work),
                              seconds=time.monotonic()-began)), flush=True)
    else:
        truths = [cb.parity_function(mask, outputs) for mask in loaded]
        assert chart.frame(truths, len(outputs), label='erase_target_seed_helpers_leave_output_basis')
        assert chart.work == truths
        inverse = cb.BinarySpan(loaded)
        rows = []
        for bit in range(len(outputs)):
            expression = inverse.solve(1 << bit)
            assert expression is not None and cb.parity_function(expression, chart.work) == outputs[bit]
            rows.append(expression)
        chart.steps.append(dict(kind='final_output_Clifford_frame', matrix_rows=rows,
                                output_bits=list(range(16)), Toffolis=0, extra_helpers=0))
        result = save('COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE')
        print(json.dumps({k:result[k] for k in ('status', 'Toffolis', 'work_peak', 'elapsed_seconds_this_slice')}), flush=True)


if __name__ == '__main__':
    main()
