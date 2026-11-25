# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Own exact mathematical loader retaining useful product coordinates.

The helper chart is changed by invertible Clifford frames. Required live
output values, upcoming AND controls and the unfinished output sum are always
retained. A discarded direction is X-measured with its complete table phase
deferred. Individual AND results survive when space permits; otherwise the
next product is XORed into the existing partial sum. No native code emitted.
"""
import argparse
import json
import random
import resource
import signal
import time
from bank_frontier import checked_model,raw_functions,make_bank,serialize,HERE,MODEL,MODEL_SHA,CODE_SHA,cb
from subspace_frontier import product_subspace,plan_expression,improve_coset,independent_complement
from atomic_io import atomic_text

FULL=(1<<128)-1


def affine_product(functions,left_truth,right_truth):
    span=cb.BinarySpan([FULL]+list(functions));left=span.solve(left_truth);right=span.solve(right_truth)
    assert left is not None and right is not None
    lc,rc=left&1,right&1;left>>=1;right>>=1
    linear=(right if lc else 0)^(left if rc else 0)^(left&right);edges=set()
    for a in cb.bits(left):
        for b in cb.bits(right):
            if a!=b:
                edge=tuple(sorted((a,b)))
                if edge in edges:edges.remove(edge)
                else:edges.add(edge)
    plan=cb.factor_polynomial(len(functions),bool(lc&rc),linear,edges)
    assert plan.and_count<=1 and plan.evaluate_factored_functions(functions,FULL)==left_truth&right_truth
    return plan


class Chart:
    def __init__(self,raw,work,steps,cap,rng):
        self.raw=raw;self.work=work;self.steps=steps;self.cap=cap;self.peak=len(work);self.rng=rng;self.ands=len(work)

    def clean_affine(self):
        span=cb.BinarySpan([FULL]+self.raw);i=0
        while i<len(self.work):
            solution=span.solve(self.work[i])
            if solution is not None:
                self.steps.append(dict(kind='Clifford_zero_dependent_coordinate',index=i,truth=hex(self.work[i]),expression=solution,retained_before=[hex(t) for t in self.work[:i]],Toffolis=0))
                self.work.pop(i)
            else:span.add(self.work[i]);i+=1

    def frame(self,required,limit,*,label):
        """Return false without mutation if required quotient rank exceeds limit."""
        self.clean_affine();old=list(self.work)
        fullspan=cb.BinarySpan([FULL]+self.raw+old);assert len(fullspan.pivots)==8+len(old)
        selected=[];span=cb.BinarySpan([FULL]+self.raw)
        for truth in required:
            assert fullspan.solve(truth) is not None
            if span.add(truth):selected.append(truth)
        if len(selected)>limit:return False
        remaining=list(old)
        while len(selected)<min(limit,len(old)):
            candidates=[]
            for truth in remaining:
                if span.solve(truth) is not None:continue
                rank=len(cb.Codebook(self.raw+selected+[truth],128).span.pivots)
                candidates.append((rank,self.rng.random(),truth))
            if not candidates:break
            _,_,truth=max(candidates);selected.append(truth);assert span.add(truth);remaining.remove(truth)
        # Complete the desired rows to an invertible physical work-wire frame.
        rowspan=cb.BinarySpan();rows=[];truths=[]
        for truth in selected:
            expression=fullspan.solve(truth);workrow=expression>>8
            assert rowspan.add(workrow);rows.append(expression);truths.append(truth)
        for i,truth in enumerate(old):
            if rowspan.add(1<<i):rows.append(1<<(8+i));truths.append(truth)
        assert len(rows)==len(old)==len(rowspan.pivots)
        for expression,truth in zip(rows,truths):assert cb.parity_function(expression,[FULL]+self.raw+old)==truth
        self.steps.append(dict(kind='Clifford_frame_then_HMR',label=label,old_work=[hex(t) for t in old],full_affine_rows=rows,
                               retained_count=len(selected),retained_truths=[hex(t) for t in selected],
                               discarded_truths=[hex(t) for t in truths[len(selected):]],
                               phase_debts='Every discarded coordinate is X-measured; outcome times its exact original-address truth is deferred to the certified final cleanup.',
                               frame_matrix_rank=len(old),Toffolis=0))
        self.work=selected;return True

    def emit_plan(self,plan,functions,loaded_truths,target_truth):
        factors=[(cb.parity_function(left,functions),cb.parity_function(right,functions)) for left,right,_,_ in plan.products]
        affine=(FULL if plan.constant else 0)^cb.parity_function(plan.product_linear,functions)
        accumulation=0;before=self.ands
        for stage,(left,right) in enumerate(factors):
            controls=[truth for pair in factors[stage:] for truth in pair]
            required=list(loaded_truths)+controls+[affine,accumulation]
            if self.frame(required,self.cap-1,label=f'product{stage}_new_target'):
                variables=self.raw+self.work
                product=left&right;linear=cb.BinarySpan([FULL]+variables).solve(product)
                if linear is not None:
                    self.steps.append(dict(kind='virtual_affine_product',truth=hex(product),expression=linear,Toffolis=0))
                else:
                    actual=affine_product(variables,left,right);assert actual.and_count==1
                    self.steps.append(dict(kind='CCX_new_coordinate',inputs=[hex(t) for t in variables],truth=hex(product),plan=serialize(actual),Toffolis=1))
                    self.work.append(product);self.ands+=1;self.peak=max(self.peak,len(self.work));assert len(self.work)<=self.cap
            else:
                # The current sum is the single essential nonlinear owner that
                # can absorb this product without allocating another target.
                others=list(loaded_truths)+controls+[affine]
                assert cb.BinarySpan([FULL]+self.raw+others).solve(accumulation) is None
                assert self.frame([accumulation]+others,self.cap,label=f'product{stage}_accumulator')
                assert self.work[0]==accumulation
                variables=self.raw+self.work[1:];actual=affine_product(variables,left,right)
                self.steps.append(dict(kind='XOR_product_existing_coordinate',target_index=0,old_truth=hex(accumulation),inputs=[hex(t) for t in variables],product_truth=hex(left&right),plan=serialize(actual),Toffolis=actual.and_count))
                self.work[0]^=left&right;self.ands+=actual.and_count;self.clean_affine()
            accumulation^=left&right
        assert affine^accumulation==target_truth
        assert self.frame(list(loaded_truths)+[target_truth],self.cap,label='retain_complete_output_and_useful_products')
        return self.ands-before


def choose_plan(book,outputs,loaded,rng,rounds,factor_seconds):
    complement=independent_complement(loaded,len(outputs));outspan=cb.BinarySpan(outputs)
    linear=cb.BinarySpan([FULL]+list(book.functions));linear_choices=[]
    for mask in complement:
        expression=linear.solve(cb.parity_function(mask,outputs))
        if expression is not None:
            plan=cb.factor_polynomial(book.width,bool(expression&1),expression>>1,[])
            return plan,mask,dict(status='AFFINE_OUTPUT')
    span=cb.BinarySpan(book.columns);base=len(book.columns)
    for truth in outputs:span.add(truth)
    directions=cb.BinarySpan(loaded);expressions=[]
    for relation in span.nullspace:
        mask=relation>>base
        if mask and directions.add(mask):expressions.append((mask,relation&((1<<base)-1)))
    if not expressions:return None,None,dict(status='NO_QUADRATIC_DIRECTION')
    candidates=[]
    for mask,expression in expressions:
        plan=book.represent(cb.parity_function(mask,outputs),trials=16,seed=rng.randrange(1<<30))
        candidates.append((plan.and_count,rng.random(),mask,plan_expression(book,plan)))
    candidates.sort();best=None
    for _,tie,anchor,expression in candidates[:2]:
        relations=list(book.span.nullspace)+[e for m,e in expressions if m!=anchor]
        plan=improve_coset(book,expression,relations,rounds=rounds,subspace_bits=7,seed=rng.randrange(1<<30))
        truth=plan.evaluate_factored_functions(book.functions,FULL);mask=outspan.solve(truth)
        assert mask is not None and cb.BinarySpan(loaded).solve(mask) is None
        candidate=(plan.and_count,tie,plan,mask)
        if best is None or candidate[:2]<best[:2]:best=candidate
    searches=[]
    for count in ([3,4] if book.width>=26 else [4]):
        if best[0]<=count:continue
        plan,meta=product_subspace(book,[cb.parity_function(m,outputs) for m in complement],products=count,trials=2000000,seconds=factor_seconds,seed=rng.randrange(1<<30))
        searches.append(dict(products=count,**meta))
        if plan is not None:
            mask=outspan.solve(plan.evaluate_factored_functions(book.functions,FULL));assert mask is not None and cb.BinarySpan(loaded).solve(mask) is None
            candidate=(plan.and_count,rng.random(),plan,mask)
            if candidate[:2]<best[:2]:best=candidate
    return best[2],best[3],dict(status='CERTIFIED_HEURISTIC_PLAN',searches=searches)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--work-cap',type=int,required=True)
    ap.add_argument('--seed',type=int,default=0);ap.add_argument('--seconds',type=int,default=900)
    ap.add_argument('--rounds',type=int,default=32);ap.add_argument('--factor-seconds',type=float,default=8)
    ap.add_argument('--bits',default='0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15')
    args=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));signal.alarm(args.seconds+10)
    began=time.monotonic();rng=random.Random(args.seed);model=checked_model();raw=raw_functions(False)
    alloutputs=cb.word_functions(model['A'],13)+cb.word_functions(model['stored_slope'],4)
    output_bits=list(map(int,args.bits.split(',')));outputs=[alloutputs[i] for i in output_bits]
    bank=json.loads((HERE/'phase_bank7_seed0.json').read_text());helpers,steps=make_bank(raw,bank)
    chart=Chart(raw,helpers,steps,args.work_cap,rng);loaded=[];summaries=[];path=HERE/'search'/f'{args.name}.json'

    def save(status):
        result=dict(status=status,model=MODEL,model_sha256=MODEL_SHA,codebook_source_sha256=CODE_SHA,
                    raw_address=True,output_bits=output_bits,loaded_output_masks=loaded,
                    Toffolis=chart.ands,T=0,rotations=0,work_cap=args.work_cap,work_peak=chart.peak,
                    current_work_truths=[hex(t) for t in chart.work],output_summaries=summaries,steps=chart.steps,
                    phase_debt_scope='All discarded basis directions are exact pure-table functions. Pay at restored raw+A/H chart and use the separately certified9E final cleanup.',
                    seed=args.seed,elapsed_seconds=time.monotonic()-began,memory_guard_MiB=768,wall_limit_seconds=args.seconds,
                    physical_native_proof=False,official_verifier=False)
        atomic_text(path,json.dumps(result,indent=2)+'\n');return result
    save('RUNNING')
    while len(loaded)<len(outputs):
        if time.monotonic()-began>=args.seconds:save('BOUNDED_PARTIAL');break
        loaded_truths=[cb.parity_function(mask,outputs) for mask in loaded]
        assert chart.frame(loaded_truths,args.work_cap-1,label='reserve_initial_product_target')
        functions=raw+chart.work;book=cb.Codebook(functions,128)
        plan,mask,meta=choose_plan(book,outputs,loaded,rng,args.rounds,args.factor_seconds)
        if plan is None:save('STUCK_NO_QUADRATIC_DIRECTION');break
        target=cb.parity_function(mask,outputs)
        assert plan.evaluate_factored_functions(functions,FULL)==target
        charge=chart.emit_plan(plan,functions,loaded_truths,target)
        loaded.append(mask);assert len(cb.BinarySpan(loaded).pivots)==len(loaded)
        summaries.append(dict(output_index=len(loaded)-1,target_mask=mask,planned_products=plan.and_count,actual_Toffolis=charge,plan=serialize(plan),inputs=[hex(t) for t in functions],search=meta,work_after=len(chart.work)))
        save('RUNNING');print(json.dumps(dict(outputs=len(loaded),charge=charge,total=chart.ands,work=len(chart.work),seconds=time.monotonic()-began)),flush=True)
    else:
        truths=[cb.parity_function(mask,outputs) for mask in loaded]
        assert chart.frame(truths,len(outputs),label='erase_all_helpers_and_leave_joint_output_basis')
        assert chart.work==truths
        inverse=cb.BinarySpan(loaded);rows=[]
        for bit in range(len(outputs)):
            expression=inverse.solve(1<<bit);assert expression is not None
            assert cb.parity_function(expression,chart.work)==outputs[bit];rows.append(expression)
        chart.steps.append(dict(kind='final_output_Clifford_frame',matrix_rows=rows,output_bits=output_bits,Toffolis=0,extra_helpers=0))
        result=save('COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE')
        print(json.dumps({k:result[k] for k in ('status','Toffolis','work_peak','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
