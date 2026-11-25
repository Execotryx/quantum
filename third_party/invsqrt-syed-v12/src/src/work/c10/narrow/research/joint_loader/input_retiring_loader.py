# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Exact bounded mathematical second-loader search with reusable inputs."""
import argparse
import hashlib
import json
import math
import random
import resource
import signal
import time
from pathlib import Path

from bank_frontier import checked_model, raw_functions, make_bank, serialize, HERE, MODEL, MODEL_SHA, CODE_SHA, cb
from adaptive_product_bank import Chart, affine_product, FULL, choose_plan
from target_seed_loader import small_plan
from atomic_io import atomic_text


def distinct_rows(functions):
    rows = [sum(((truth >> row) & 1) << bit for bit, truth in enumerate(functions)) for row in range(128)]
    return len(set(rows))


class RetiringChart(Chart):
    def frame(self, required, limit, *, label):
        self.clean_affine()
        old = list(self.work)
        offset = 1 + len(self.raw)
        fullspan = cb.BinarySpan([FULL] + self.raw + old)
        assert len(fullspan.pivots) == offset + len(old)
        selected = []
        span = cb.BinarySpan([FULL] + self.raw)
        for truth in required:
            assert fullspan.solve(truth) is not None
            if span.add(truth):
                selected.append(truth)
        if len(selected) > limit:
            return False
        remaining = list(old)
        while len(selected) < min(limit, len(old)):
            candidates = []
            for truth in remaining:
                if span.solve(truth) is not None:
                    continue
                rank = len(cb.Codebook(self.raw + selected + [truth], 128).span.pivots)
                candidates.append((rank, self.rng.random(), truth))
            if not candidates:
                break
            _, _, truth = max(candidates)
            selected.append(truth)
            assert span.add(truth)
            remaining.remove(truth)
        # This input-retiring variant explicitly retains the complete original
        # 128-row distinction at every cut, in addition to required controls.
        assert distinct_rows(self.raw + selected) == 128, ('NONINJECTIVE_RETIRED_CHART', label)
        rowspan, rows, truths = cb.BinarySpan(), [], []
        for truth in selected:
            expression = fullspan.solve(truth)
            assert rowspan.add(expression >> offset)
            rows.append(expression)
            truths.append(truth)
        for i, truth in enumerate(old):
            if rowspan.add(1 << i):
                rows.append(1 << (offset+i))
                truths.append(truth)
        assert len(rows) == len(old) == len(rowspan.pivots)
        for expression, truth in zip(rows, truths):
            assert cb.parity_function(expression, [FULL] + self.raw + old) == truth
        self.steps.append(dict(
            kind='Clifford_frame_then_HMR', label=label, affine_fixed_offset=offset,
            old_work=[hex(t) for t in old], full_affine_rows=rows,
            retained_count=len(selected), retained_truths=[hex(t) for t in selected],
            discarded_truths=[hex(t) for t in truths[len(selected):]],
            original_rows_distinguished_after=128,
            phase_debts='Mixed input/helper HMR functions belong to the existing pure-table debt ledger; no direct raw-input sign is assumed.',
            frame_matrix_rank=len(old), Toffolis=0,
        ))
        self.work = selected
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--work-cap', type=int, default=20)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--rounds', type=int, default=8)
    ap.add_argument('--factor-seconds', type=float, default=0)
    ap.add_argument('--resume')
    args = ap.parse_args()
    assert 0 < args.seconds <= 40 and 0 <= args.factor_seconds <= 1
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    signal.alarm(math.ceil(args.seconds) + 10)
    began = time.monotonic()
    rng = random.Random(args.seed)
    model = checked_model()
    original = raw_functions(False)
    fixed_bits, reusable_bits = [1,2,3,5,6], [0,4]
    raw = [original[i] for i in fixed_bits]
    work = [original[i] for i in reusable_bits]
    outputs = cb.word_functions(model['A'], 13) + cb.word_functions(model['stored_slope'], 3)
    bank_path = HERE / 'phase_bank7_seed0.json'
    bank = json.loads(bank_path.read_text())
    helpers, original_steps = make_bank(original, bank)
    functions = list(original)
    steps = []
    for record in original_steps:
        plan = cb.QuadraticCodePlan(record['plan']['width'], record['plan']['constant'],
                                    record['plan']['linear'], tuple(map(tuple, record['plan']['edges'])),
                                    tuple(map(tuple, record['plan']['products'])), record['plan']['product_linear'])
        assert plan.and_count == 1
        left, right, _, _ = plan.products[0]
        left_truth = cb.parity_function(left, functions)
        right_truth = cb.parity_function(right, functions)
        affine = (FULL if plan.constant else 0) ^ cb.parity_function(plan.product_linear, functions)
        physical = raw + work
        actual = affine_product(physical, left_truth, right_truth)
        expression = cb.BinarySpan([FULL] + physical).solve(affine)
        assert expression is not None
        actual = cb.factor_polynomial(len(physical), actual.constant ^ bool(expression & 1),
                                      actual.linear ^ (expression >> 1), actual.edges)
        truth = actual.evaluate_factored_functions(physical, FULL)
        assert actual.and_count == 1 and truth == int(record['truth'], 16)
        steps.append(dict(kind='bank', name=record['name'], truth=hex(truth), plan=serialize(actual), Toffolis=1))
        work.append(truth)
        functions.append(truth)
    assert helpers == work[2:]
    chart = RetiringChart(raw, work, steps, args.work_cap, rng)
    chart.ands = len(helpers)
    assert distinct_rows(raw + work) == 128
    loaded, summaries = [], []
    if args.resume:
        previous = json.loads(Path(args.resume).read_text())
        assert previous['model_sha256'] == MODEL_SHA and previous['work_cap'] == args.work_cap
        assert previous['fixed_address_bits'] == fixed_bits and previous['reusable_input_bits'] == reusable_bits
        assert previous['status'] != 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
        chart.work = [int(t, 16) for t in previous['current_work_truths']]
        chart.steps = previous['steps']
        chart.ands = previous['Toffolis']
        chart.peak = previous['work_peak']
        loaded, summaries = previous['loaded_output_masks'], previous['output_summaries']
    path = HERE / 'search' / f'{args.name}.json'

    def save(status):
        result = dict(
            status=status, model=MODEL, model_sha256=MODEL_SHA, codebook_source_sha256=CODE_SHA,
            raw_address=True, fixed_address_bits=fixed_bits, reusable_input_bits=reusable_bits,
            initial_reusable_input_truths=[hex(original[i]) for i in reusable_bits],
            output_bits=list(range(16)), loaded_output_masks=loaded, Toffolis=chart.ands, T=0, rotations=0,
            work_cap=args.work_cap, work_peak=chart.peak, complete_other_owner_count=29,
            complete_peak=29+chart.peak, current_work_truths=[hex(t) for t in chart.work],
            output_summaries=summaries, steps=chart.steps, seed=args.seed,
            bank_source_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest(),
            phase_debt_scope='All retired mixed input/helper coordinates are pure original-table functions, repaid by retained-table cleanup9. Final root value decoder21 remains required; its direct phase payments for reused a0/a4 are suppressed because those signs are in the table ledger.',
            rows_at_every_retirement=128, elapsed_seconds_this_slice=time.monotonic()-began,
            memory_guard_MiB=128, wall_limit_seconds=args.seconds, hard_alarm_seconds=math.ceil(args.seconds)+10,
            physical_native_proof=False, official_verifier=False,
        )
        atomic_text(path, json.dumps(result, indent=2) + '\n')
        return result

    save('RUNNING_BOUNDED_MATHEMATICAL_SEARCH')
    while len(loaded) < 16:
        if time.monotonic()-began >= args.seconds:
            save('BOUNDED_PARTIAL')
            break
        loaded_truths = [cb.parity_function(mask, outputs) for mask in loaded]
        assert chart.frame(loaded_truths, args.work_cap-1, label='retiring_input_reserve_product_target')
        functions = raw + chart.work
        book = cb.Codebook(functions, 128)
        if args.factor_seconds:
            plan, mask, meta = choose_plan(book, outputs, loaded, rng, args.rounds, args.factor_seconds)
        else:
            plan, mask = small_plan(book, outputs, loaded, rng, args.rounds)
            meta = dict(status='BOUNDED_QUADRATIC_SEARCH_WITHOUT_SUBPROCESSES')
        if plan is None:
            save('STUCK_NO_QUADRATIC_DIRECTION')
            break
        truth = cb.parity_function(mask, outputs)
        assert plan.evaluate_factored_functions(functions, FULL) == truth
        charge = chart.emit_plan(plan, functions, loaded_truths, truth)
        loaded.append(mask)
        assert len(cb.BinarySpan(loaded).pivots) == len(loaded)
        summaries.append(dict(output_index=len(loaded)-1, target_mask=mask, planned_products=plan.and_count,
                              actual_Toffolis=charge, plan=serialize(plan), inputs=[hex(t) for t in functions],
                              search=meta, work_after=len(chart.work)))
        save('RUNNING_BOUNDED_MATHEMATICAL_SEARCH')
        print(json.dumps(dict(outputs=len(loaded), charge=charge, total=chart.ands,
                              work=len(chart.work), seconds=time.monotonic()-began)), flush=True)
    else:
        truths = [cb.parity_function(mask, outputs) for mask in loaded]
        assert chart.frame(truths, 16, label='retired_input_final_output_basis')
        assert chart.work == truths
        inverse, rows = cb.BinarySpan(loaded), []
        for bit in range(16):
            expression = inverse.solve(1 << bit)
            assert expression is not None and cb.parity_function(expression, chart.work) == outputs[bit]
            rows.append(expression)
        chart.steps.append(dict(kind='final_output_Clifford_frame', matrix_rows=rows,
                                output_bits=list(range(16)), Toffolis=0, extra_helpers=0))
        result = save('COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE')
        print(json.dumps({k:result[k] for k in ('status', 'Toffolis', 'complete_peak', 'elapsed_seconds_this_slice')}), flush=True)


if __name__ == '__main__':
    main()
