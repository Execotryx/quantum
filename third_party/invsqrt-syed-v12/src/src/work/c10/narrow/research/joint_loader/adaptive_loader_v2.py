# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Bounded fixed-table loader construction at the new physical cuts.

The first cut has ordinary raw inputs. The second cut has R at address slot3
and treats four other input owners as mutable work. Both load15 independent
outputs, then finish A12 with the already exact one-AND identity.
"""
import argparse
import hashlib
import json
import math
import random
import resource
import signal
import time
from pathlib import Path
from bank_frontier import checked_model, raw_functions, make_bank, restore, serialize, HERE, MODEL, MODEL_SHA, CODE_SHA, cb
from adaptive_product_bank import affine_product, FULL, choose_plan
from input_retiring_loader import RetiringChart, distinct_rows
from atomic_io import atomic_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--mode', choices=('first_raw','second_framed'), required=True)
    ap.add_argument('--work-cap', type=int, required=True)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--rounds', type=int, default=8)
    ap.add_argument('--factor-seconds', type=float, default=0.3)
    ap.add_argument('--tail-seconds', type=float, default=2.0)
    ap.add_argument('--resume')
    args = ap.parse_args()
    assert 0 < args.seconds <= 40 and 0 < args.factor_seconds <= 1 and 0 < args.tail_seconds <= 3
    resource.setrlimit(resource.RLIMIT_AS, (128*1024**2,128*1024**2))
    signal.alarm(math.ceil(args.seconds)+12)
    began = time.monotonic()
    rng = random.Random(args.seed)
    model = checked_model()
    original = raw_functions(False)
    physical = list(original)
    if args.mode == 'second_framed':
        physical[3] = original[3]^original[2]^(original[1]&(original[2]^original[5]))
        fixed_bits, reusable_bits, other = [3,5,6], [0,1,2,4], 27
    else:
        fixed_bits, reusable_bits, other = list(range(7)), [], 26
    assert distinct_rows(physical) == 128
    raw = [physical[i] for i in fixed_bits]
    work = [physical[i] for i in reusable_bits]
    alloutputs = cb.word_functions(model['A'],13)+cb.word_functions(model['stored_slope'],3)
    output_bits = list(range(12))+[13,14,15]
    outputs = [alloutputs[i] for i in output_bits]
    bank_path = HERE/'phase_bank7_seed0.json'
    bank = json.loads(bank_path.read_text())
    helpers, original_steps = make_bank(physical,bank)
    functions = list(physical)
    steps = []
    for record in original_steps:
        plan = restore(record['plan'])
        assert plan.and_count == 1
        left,right,_,_ = plan.products[0]
        left_truth = cb.parity_function(left,functions)
        right_truth = cb.parity_function(right,functions)
        affine = (FULL if plan.constant else 0)^cb.parity_function(plan.product_linear,functions)
        variables = raw+work
        actual = affine_product(variables,left_truth,right_truth)
        expression = cb.BinarySpan([FULL]+variables).solve(affine)
        assert expression is not None
        actual = cb.factor_polynomial(len(variables), actual.constant^bool(expression&1),
                                      actual.linear^(expression>>1),actual.edges)
        truth = actual.evaluate_factored_functions(variables,FULL)
        assert actual.and_count == 1 and truth == int(record['truth'],16)
        steps.append(dict(kind='bank',name=record['name'],truth=hex(truth),plan=serialize(actual),Toffolis=1))
        work.append(truth)
        functions.append(truth)
    assert helpers == work[len(reusable_bits):]
    chart = RetiringChart(raw,work,steps,args.work_cap,rng)
    chart.ands = len(helpers)
    loaded, summaries = [], []
    if args.resume:
        previous = json.loads(Path(args.resume).read_text())
        assert previous['model_sha256'] == MODEL_SHA and previous['mode'] == args.mode
        assert previous['work_cap'] == args.work_cap and previous['output_bits'] == output_bits
        assert previous['status'] != 'COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
        chart.work = [int(t,16) for t in previous['current_work_truths']]
        chart.steps, chart.ands, chart.peak = previous['steps'],previous['Toffolis'],previous['work_peak']
        loaded, summaries = previous['loaded_output_masks'],previous['output_summaries']
    path = HERE/'search'/f'{args.name}.json'

    def save(status):
        result = dict(
            status=status, mode=args.mode, model=MODEL, model_sha256=MODEL_SHA, codebook_source_sha256=CODE_SHA,
            address_chart='R_at_a3_other_coordinates_raw' if args.mode=='second_framed' else 'original_raw_address',
            fixed_address_slots=fixed_bits, reusable_input_slots=reusable_bits,
            original_order_fixed_truths=[hex(t) for t in raw],
            initial_reusable_input_truths=[hex(physical[i]) for i in reusable_bits],
            output_bits=output_bits, loaded_output_masks=loaded, Toffolis=chart.ands,T=0,rotations=0,
            work_cap=args.work_cap,work_peak=chart.peak,complete_other_owner_count=other,
            complete_peak=other+chart.peak,current_work_truths=[hex(t) for t in chart.work],
            output_summaries=summaries,steps=chart.steps,seed=args.seed,
            bank_source_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest(),
            input_frame_charge='The existing one-CCX R frame is moved before the second loader; its lifecycle charge is already paid, and no extra frame is added.' if args.mode=='second_framed' else 'No input frame.',
            phase_debt_scope='All mixed input/helper HMR signs are functions in ORIGINAL raw-address row order. Pay them once through existing table cleanup9; root value decoder21 restores early inputs without duplicate direct per-bit sign corrections.',
            exact_rows_at_every_cut=128,elapsed_seconds_this_slice=time.monotonic()-began,
            memory_guard_MiB=128,wall_limit_seconds=args.seconds,hard_alarm_seconds=math.ceil(args.seconds)+12,
            physical_native_proof=False,official_verifier=False,
        )
        atomic_text(path,json.dumps(result,indent=2)+'\n')
        return result

    save('RUNNING_BOUNDED_MATHEMATICAL_SEARCH')
    while len(loaded) < 15:
        if time.monotonic()-began >= args.seconds:
            save('BOUNDED_PARTIAL')
            break
        loaded_truths = [cb.parity_function(mask,outputs) for mask in loaded]
        assert chart.frame(loaded_truths,args.work_cap-1,label='v2_reserve_product_target')
        functions = raw+chart.work
        book = cb.Codebook(functions,128)
        factor_time = args.tail_seconds if 15-len(loaded)<=3 else args.factor_seconds
        plan,mask,meta = choose_plan(book,outputs,loaded,rng,args.rounds,factor_time)
        if plan is None:
            save('STUCK_NO_QUADRATIC_DIRECTION')
            break
        truth = cb.parity_function(mask,outputs)
        assert plan.evaluate_factored_functions(functions,FULL) == truth
        charge = chart.emit_plan(plan,functions,loaded_truths,truth)
        loaded.append(mask)
        assert len(cb.BinarySpan(loaded).pivots) == len(loaded)
        summaries.append(dict(output_index=len(loaded)-1,target_mask=mask,planned_products=plan.and_count,
                              actual_Toffolis=charge,plan=serialize(plan),inputs=[hex(t) for t in functions],
                              search=meta,work_after=len(chart.work)))
        save('RUNNING_BOUNDED_MATHEMATICAL_SEARCH')
        print(json.dumps(dict(outputs=len(loaded),charge=charge,total=chart.ands,work=len(chart.work),
                              seconds=time.monotonic()-began)),flush=True)
    else:
        truths = [cb.parity_function(mask,outputs) for mask in loaded]
        assert chart.frame(truths,15,label='v2_retain_fifteen_output_basis')
        assert chart.work == truths
        inverse = cb.BinarySpan(loaded)
        rows = []
        for bit in range(15):
            expression = inverse.solve(1<<bit)
            assert expression is not None and cb.parity_function(expression,chart.work)==outputs[bit]
            rows.append(expression)
        chart.steps.append(dict(kind='final_output_Clifford_frame',matrix_rows=rows,output_bits=list(output_bits),Toffolis=0,extra_helpers=0))
        chart.work = list(outputs)
        variables = raw+chart.work
        i5,i6,i11 = raw.index(original[5]),raw.index(original[6]),len(raw)+11
        finish = cb.factor_polynomial(len(variables),True,1<<i6,[(i5,i6),(i5,i11)])
        assert finish.and_count==1 and finish.evaluate_factored_functions(variables,FULL)==alloutputs[12]
        chart.steps.append(dict(kind='CCX_new_coordinate',inputs=[hex(t) for t in variables],truth=hex(alloutputs[12]),plan=serialize(finish),Toffolis=1))
        chart.work.append(alloutputs[12]);chart.ands+=1;chart.peak=max(chart.peak,16)
        assert chart.peak<=args.work_cap
        reorder=[1<<i for i in range(12)]+[1<<15,1<<12,1<<13,1<<14]
        assert [cb.parity_function(row,chart.work) for row in reorder] == alloutputs
        chart.steps.append(dict(kind='final_output_Clifford_frame',matrix_rows=reorder,output_bits=list(range(16)),Toffolis=0,extra_helpers=0))
        chart.work = list(alloutputs)
        def embed(mask):
            return (mask&((1<<12)-1))|((mask>>12)<<13)
        loaded[:] = [embed(mask) for mask in loaded]+[1<<12]
        for summary in summaries:
            summary['target_mask']=embed(summary['target_mask'])
        summaries.append(dict(output_index=15,target_mask=1<<12,planned_products=1,actual_Toffolis=1,
                              plan=serialize(finish),inputs=[hex(t) for t in variables],
                              search=dict(status='EXACT_ONE_AND_A12_FINISH'),work_after=16))
        output_bits = list(range(16))
        result=save('COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE')
        print(json.dumps({k:result[k]for k in ('status','mode','Toffolis','complete_peak','elapsed_seconds_this_slice')}),flush=True)


if __name__=='__main__':
    main()
