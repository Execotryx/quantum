#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Search a smaller quadratically universal, reversibly erasable helper bank.

Each helper is one AND of two affine forms in earlier live functions. Its
complete truth is calculated from the address truth table; no circuit is read.
All pending table phases can be repaid with Clifford gates when the quadratic
span of the final bank has full rank. Reverse helper erasure needs only HMR and
the product of its two still-available affine parents, hence zero further ANDs.
"""
from pathlib import Path
import argparse
import json
import random
import time
from functools import lru_cache
import sys
from codebook import (BinarySpan, Codebook, bits, parity_function, word_functions,
                      factor_polynomial,emit_xor,emit_erase)


def extend_rank(pivots, columns):
    basis = dict(pivots)
    for column in columns:
        value=column
        while value:
            pivot=value.bit_length()-1
            old=basis.get(pivot)
            if old is None:
                basis[pivot]=value
                break
            value ^= old
    return basis


def search(address_width=8, maximum_helpers=22, candidates=512, seed=0):
    rng=random.Random(seed)
    size=1 << address_width
    functions=word_functions(range(size),address_width)
    full=(1 << size)-1
    steps=[]
    pivots=extend_rank({},[full]+functions+
        [functions[i]&functions[j] for i in range(address_width) for j in range(i)])
    began=time.perf_counter()
    while len(pivots)<size and len(steps)<maximum_helpers:
        n=len(functions)
        linear=BinarySpan([full]+functions)
        best=None
        tested=set()
        for trial in range(candidates):
            if trial < n*(n-1)//2:
                i,j=next(((i,j) for i in range(n) for j in range(i)
                          if (1 << i,1 << j) not in tested),(None,None))
                if i is None:continue
                left,right=1 << i,1 << j
            else:
                left,right=rng.getrandbits(n),rng.getrandbits(n)
                if left==0 or right==0 or left==right:continue
            if (left,right) in tested:continue
            tested.add((left,right))
            truth=parity_function(left,functions)&parity_function(right,functions)
            if linear.solve(truth) is not None:continue
            new_pivots=extend_rank(pivots,[truth]+[truth&f for f in functions])
            score=(len(new_pivots),-left.bit_count()-right.bit_count(),-left,-right)
            if best is None or score>best[0]:best=(score,left,right,truth,new_pivots)
        if best is None:break
        score,left,right,truth,pivots=best
        steps.append({'left':left,'right':right,'truth':truth,'quadratic_rank':len(pivots)})
        functions.append(truth)
    code=Codebook(functions,size)
    if len(code.span.pivots)!=len(pivots):
        raise AssertionError('Incremental quadratic-rank certificate differs from full recomputation.')
    return {'status':'UNIVERSAL' if len(pivots)==size else 'INCOMPLETE',
            'address_width':address_width,'seed':seed,'candidates':candidates,
            'helper_ands':len(steps),'quadratic_rank':len(pivots),'steps':steps,
            'seconds':time.perf_counter()-began}


def product_plan(width,left,right):
    edges=set()
    for a in bits(left):
        for b in bits(right):
            if a==b:continue
            edge=tuple(sorted((a,b)))
            if edge in edges:edges.remove(edge)
            else:edges.add(edge)
    return factor_polynomial(width,False,left&right,edges)


@lru_cache(maxsize=16)
def universal_plan(address_width=8,seed=0,candidates=1000):
    plan=search(address_width=address_width,seed=seed,candidates=candidates)
    if plan['status']!='UNIVERSAL':
        raise ValueError('The bounded deterministic search did not reach universal quadratic rank.')
    return plan


def build_bank(builder,address,*,seed=0,candidates=1000):
    """Return wires, exact functions and an erasable, from-search helper DAG."""
    plan=universal_plan(len(address),seed,candidates)
    if builder.max_qubits-builder.num_allocated_qubits < plan['helper_ands']:
        raise ValueError('Insufficient workspace for the certified universal phase bank.')
    wires=list(address)
    functions=word_functions(range(1 << len(address)),len(address))
    polynomials=[]
    for step in plan['steps']:
        polynomial=product_plan(len(wires),step['left'],step['right'])
        truth=polynomial.evaluate_factored_functions(functions,(1 << (1 << len(address)))-1)
        if truth!=step['truth'] or polynomial.and_count!=1:
            raise AssertionError('A universal-bank product is not the certified one-AND function.')
        target=builder.alloc_qubits(1)[0]
        emit_xor(builder,wires,target,polynomial)
        polynomials.append(polynomial)
        wires.append(target);functions.append(truth)
    return wires,functions,polynomials


def erase_bank(builder,wires,polynomials,*,omit_last_repayment=False):
    """Reverse-delete every helper, with both outcomes fully repaid."""
    import kickmix as km
    wires=list(wires)
    for i,polynomial in enumerate(reversed(polynomials)):
        target=wires.pop()
        if omit_last_repayment and i==0:
            outcome=builder.alloc_bits(1)[0]
            builder.hmr(target,outcome);builder.free(outcome)
        else:
            emit_erase(builder,wires,[target],[polynomial])
        builder.free(target)


def flush_universal(builder,address,debts,*,seed=0,candidates=1000):
    """Drop-in final table-phase flush using17 ANDs for eight address bits."""
    if not debts.pending:
        return {'and_count':0,'workspace_qubits':0,'erased_words':0}
    if len(address)!=debts.address_bits:
        raise ValueError('The recovered logical address differs from the phase ledger.')
    wires,functions,polynomials=build_bank(builder,address,seed=seed,candidates=candidates)
    metadata=debts.flush_on_code(builder,wires,functions)
    erase_bank(builder,wires,polynomials)
    return {**metadata,'and_count':len(polynomials),'workspace_qubits':len(polynomials),
            'bank':'deterministic affine-product DAG','bank_seed':seed,
            'bank_search_candidates':candidates,'helpers_erased_for_all_outcomes':True}


def seed_factory(frame=None,*,seed=0,candidates=1000):
    """Initial-lookup factory, optionally built in the original address frame."""
    from affine_labels import emit_address_frame
    from transition_codebook import LiveFunction
    def build(builder,address):
        if frame is not None:emit_address_frame(builder,address,frame,inverse=True)
        wires,functions,_=build_bank(builder,address,seed=seed,candidates=candidates)
        if frame is not None:emit_address_frame(builder,address,frame)
        if frame is not None:
            perm=[frame.transform(x) for x in range(256)]
            functions=[sum(((f >> old)&1)<<new for old,new in enumerate(perm)) for f in functions]
        return [LiveFunction(f'universal{i}',wire,truth)
                for i,(wire,truth) in enumerate(zip(wires[len(address):],functions[len(address):]))]
    return build


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0)
    ap.add_argument('--candidates',type=int,default=512)
    ap.add_argument('--maximum',type=int,default=22)
    args=ap.parse_args()
    result=search(candidates=args.candidates,seed=args.seed,maximum_helpers=args.maximum)
    path=Path(__file__).with_name(f'universal_basis_{args.seed}.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='steps'},indent=2))
    print('ranks', [x['quadratic_rank'] for x in result['steps']])
