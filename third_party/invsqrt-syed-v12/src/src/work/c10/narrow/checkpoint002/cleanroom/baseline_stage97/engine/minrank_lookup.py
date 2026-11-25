#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Search a desired-output subspace for low-product quadratic decoders.

All truth tables come from fitted mathematical coefficient parameters. This
module never accepts circuit files. It differs from scalar rank search by
allowing the newly decoded bit to be an XOR of several desired output bits;
an invertible output basis can later be restored using Clifford gates.
Every accepted polynomial and factorization is verified on every address.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[0].parent
sys.path[:0]=[str(ROOT/'official'),str(ROOT/'engine'),str(ROOT/'tests'),str(ROOT)]
from codebook import BinarySpan,Codebook,bits,parity_function,factor_polynomial


def factored_plan(width,factors,expression):
    constant=bool(expression&1)
    linear=(expression >> 1)&((1 << width)-1)
    edges=set()
    for i,left in enumerate(factors):
        right=(expression >> (1+width+i*width))&((1 << width)-1)
        for a in bits(left):
            for b in bits(right):
                if a==b:linear^=1 << a
                elif (edge:=tuple(sorted((a,b)))) in edges:edges.remove(edge)
                else:edges.add(edge)
    return factor_polynomial(width,constant,linear,edges)


def _update_relations(span,ncolumns,update_constant,complete_update_space):
    if not update_constant:
        return [relation for relation in span.nullspace if relation >> ncolumns]
    particular=span.solve(int(update_constant))
    if particular is None:return []
    if not complete_update_space:return [particular]
    # A particular solution can use no requested-output columns even though
    # another solution does. The target-bearing kernel directions parameterize
    # exactly those additional affine-solution alternatives.
    candidates=[particular]
    candidates += [particular^relation for relation in span.nullspace
                   if relation >> ncolumns]
    return list(dict.fromkeys(candidates))


def subspace_decoder(functions,targets,*,products=4,trials=4096,seed=1729,
                       update_constant=0,stop_first=True,size=256,
                       complete_update_space=False):
    """Find an output combination outside the existing affine feature span.

    With update_constant=old, the returned decoder updates a wire containing
    old in place to the desired combination. Otherwise its target starts0.
    The returned target_mask indexes the supplied target sequence.
    """
    functions=list(map(int,functions));targets=list(map(int,targets))
    full=(1 << size)-1;width=len(functions)
    if any(value&~full for value in functions+targets+[int(update_constant)]):
        raise ValueError('A truth table exceeds the declared complete address domain.')
    affine=BinarySpan([full]+functions)
    target_span=BinarySpan([full]+functions+targets)
    target_dimension=len(target_span.pivots)-len(affine.pivots)
    rng=random.Random(seed)
    began=time.perf_counter();hits=[];histogram={}
    best=None
    for trial in range(trials):
        independence=BinarySpan()
        factors=[]
        while len(factors)<products:
            factor=rng.getrandbits(width)
            if independence.add(factor):factors.append(factor)
        left=[parity_function(mask,functions) for mask in factors]
        columns=[full]+functions+[a&b for a in left for b in functions]
        span=BinarySpan(columns)
        rank=len(span.pivots)
        histogram[rank]=histogram.get(rank,0)+1
        ncolumns=len(columns)
        for target in targets:span.add(target)
        relations=_update_relations(span,ncolumns,update_constant,complete_update_space)
        for relation in relations:
            target_mask=relation >> ncolumns
            if not target_mask:continue
            truth=parity_function(target_mask,targets)
            if affine.solve(truth) is not None:continue
            expression=relation&((1 << ncolumns)-1)
            plan=factored_plan(width,factors,expression)
            wanted=truth^int(update_constant)
            if plan.evaluate_functions(functions,full)!=wanted or \
               plan.evaluate_factored_functions(functions,full)!=wanted:
                raise AssertionError('Target-space factorization failed its complete truth certificate.')
            hit=dict(trial=trial+1,products=plan.and_count,target_mask=target_mask,
                     target_weight=target_mask.bit_count(),factor_span_rank=rank,
                     constant=plan.constant,linear=plan.linear,edges=plan.edges,
                     factored_products=plan.products,truth_hex=hex(truth),
                     checked_addresses=size)
            hits.append(hit)
            key=(plan.and_count,target_mask.bit_count(),target_mask)
            if best is None or key<best[0]:best=(key,plan,target_mask)
            if stop_first:break
        if best is not None and stop_first:break
    metadata=dict(status='CERTIFIED_HIT' if best else 'NO_HIT',width=width,
                  affine_rank=len(affine.pivots),target_dimension=target_dimension,
                  left_factors=products,trials=trial+1 if trials else 0,
                  complete_update_space=bool(complete_update_space),
                  factor_span_rank_histogram=histogram,hits=hits,
                  wall_seconds=time.perf_counter()-began)
    return (best[1],best[2],metadata) if best else (None,0,metadata)


def natural_subspace_decoder(functions,targets,*,products=3,size=256,update_constant=0,
                              subset_limit=None,complete_update_space=False):
    """Exhaust natural-wire left factors, allowing any desired output XOR."""
    functions=list(map(int,functions));targets=list(map(int,targets))
    width=len(functions);full=(1 << size)-1
    affine=BinarySpan([full]+functions)
    expanded=BinarySpan(affine.columns+targets)
    columns=[[left&right for right in functions] for left in functions]
    if subset_limit is not None and subset_limit<0:
        raise ValueError('The natural-subset limit must be nonnegative.')
    tested=0;best=None;stopped=False;began=time.perf_counter()
    def clone(span):
        result=object.__new__(BinarySpan)
        result.pivots=dict(span.pivots);result.columns=list(span.columns);result.nullspace=[]
        return result
    def visit(span,selected,start):
        nonlocal tested,best,stopped
        if len(selected)==products:
            if subset_limit is not None and tested>=subset_limit:
                stopped=True
                return True
            tested+=1;ncolumns=len(span.columns);rank=len(span.pivots)
            for target in targets:span.add(target)
            relations=_update_relations(span,ncolumns,update_constant,complete_update_space)
            for relation in relations:
                mask=relation >> ncolumns
                if not mask:continue
                truth=parity_function(mask,targets)
                if affine.solve(truth) is not None:continue
                plan=factored_plan(width,[1 << i for i in selected],relation&((1 << ncolumns)-1))
                wanted=truth^update_constant
                if plan.evaluate_functions(functions,full)!=wanted or \
                   plan.evaluate_factored_functions(functions,full)!=wanted:
                    raise AssertionError('Natural target-space certificate failed.')
                best=(plan,mask,dict(left_wire_indices=selected,products=plan.and_count,
                    target_mask=mask,target_weight=mask.bit_count(),factor_span_rank=rank,
                    constant=plan.constant,linear=plan.linear,edges=plan.edges,
                    factored_products=plan.products,truth_hex=hex(truth),checked_addresses=size))
                return True
            return False
        for index in range(start,width-(products-len(selected))+1):
            child=clone(span)
            for column in columns[index]:child.add(column)
            if visit(child,selected+[index],index+1):return True
        return False
    visit(clone(affine),[],0)
    metadata=dict(status='CERTIFIED_HIT' if best else 'BOUNDED_NO_HIT' if stopped else 'EXHAUSTIVE_NO_HIT',
                  width=width,affine_rank=len(affine.pivots),
                  target_dimension=len(expanded.pivots)-len(affine.pivots),
                  left_factors=products,natural_left_subsets=tested,
                  complete_update_space=bool(complete_update_space),
                  subset_limit=subset_limit,
                  hits=[best[2]] if best else [],wall_seconds=time.perf_counter()-began)
    return (best[0],best[1],metadata) if best else (None,0,metadata)




