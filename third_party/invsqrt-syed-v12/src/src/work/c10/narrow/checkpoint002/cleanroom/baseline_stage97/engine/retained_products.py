# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Deferred fan-in through retained one-product intermediate functions.

Every selected quadratic decoder is factored. Its products are materialized on
distinct wires and remain available to subsequent decoders. Only a final
Clifford basis change turns one product wire into the requested output.
When width is full, a consumed-coordinate direction in the radical of the
remaining quadratic exposes a wire absent from that decoder; it can be HMR
erased and reused. Future-target quadratic coverage is checked before any
frame or erasure is emitted. No reference circuit or precomputed gate list is
accepted by this compiler.
"""
from dataclasses import replace
import random
import kickmix as km
from codebook import (BinarySpan,Codebook,bits,emit_xor,factor_polynomial,
                      parity_function)
from transition_codebook import LiveFunction,_word_table
from universal_phase_basis import product_plan


def structured_intersection(functions,structured_functions):
    """Expose a surviving algebraic subspace even after Clifford rebasing."""
    if not structured_functions:return None
    full=(1 << 256)-1;width=len(functions)
    columns=[full]+list(functions)
    span=BinarySpan(columns+list(structured_functions))
    accepted=BinarySpan([full]);truths=[];expressions=[]
    for relation in span.nullspace:
        if not relation >> (width+1):continue
        expression=relation&((1 << (width+1))-1)
        truth=parity_function(expression,columns)
        if accepted.add(truth):truths.append(truth);expressions.append(expression)
    if len(truths)<2:return None
    return Codebook(truths),expressions


def embed_affine_plan(plan,expressions,width):
    affine=int(plan.constant)
    for i in bits(plan.product_linear):affine ^= expressions[i]
    constant=bool(affine&1);linear=affine >> 1;edges=set()
    for left,right,_,_ in plan.products:
        a=parity_function(left,expressions);b=parity_function(right,expressions)
        if (a&1) and (b&1):constant=not constant
        if a&1:linear^=b >> 1
        if b&1:linear^=a >> 1
        linear^=(a >> 1)&(b >> 1)
        for i in bits(a >> 1):
            for j in bits(b >> 1):
                if i==j:continue
                edge=tuple(sorted((i,j)))
                if edge in edges:edges.remove(edge)
                else:edges.add(edge)
    return factor_polynomial(width,constant,linear,edges)


def representation(code,target,subspace=None,*,trials=0,seed=0):
    plan=code.represent(target)
    if plan is None:return None
    if subspace is not None:
        sub,expressions=subspace
        candidate=sub.represent(target)
        if candidate is not None:
            candidate=embed_affine_plan(candidate,expressions,code.width)
            if candidate.evaluate_factored_functions(code.functions,code.full)!=target:
                raise AssertionError('A rebased algebraic-subspace decoder is not exact.')
            if candidate.and_count<plan.and_count:plan=candidate
    if trials:plan=code.represent(target,trials=trials,seed=seed,initial_plan=plan)
    return plan


def cnot_polynomial(plan,control,target):
    linear=plan.linear
    if (linear >> target)&1:linear ^=1 << control
    edges=set(plan.edges)
    for i,j in plan.edges:
        if target not in (i,j):continue
        other=j if i==target else i
        if other==control:linear ^=1 << control
        else:
            edge=tuple(sorted((control,other)))
            if edge in edges:edges.remove(edge)
            else:edges.add(edge)
    return factor_polynomial(plan.width,plan.constant,linear,edges)


def drop_coordinate(plan,index):
    if (plan.linear >> index)&1 or any(index in edge for edge in plan.edges):
        raise ValueError('A retired coordinate still occurs in the exact decoder.')
    def lower(i):return i-(i>index)
    return factor_polynomial(plan.width-1,plan.constant,
        sum(1 << lower(i) for i in bits(plan.linear)),
        [(lower(i),lower(j)) for i,j in plan.edges])


def zero_directions(plan,consumed,*,limit=16,seed=0):
    matrix=[0]*plan.width
    for i,j in plan.edges:matrix[i]^=1 << j;matrix[j]^=1 << i
    null=BinarySpan([matrix[i] for i in consumed]).nullspace
    raw=[sum(1 << consumed[i] for i in bits(v)) for v in null]
    even=[];odd=[]
    for direction in raw:
        (odd if plan.evaluate_bits(direction)^plan.constant else even).append(direction)
    if odd:even +=[odd[0]^other for other in odd[1:]]
    candidates=list(even)
    rng=random.Random(seed)
    for _ in range(limit*2):
        choice=rng.getrandbits(len(even));value=0
        for i in bits(choice):value^=even[i]
        if value:candidates.append(value)
    return sorted(set(candidates),key=lambda v:(v.bit_count(),v))[:limit]


def affine_materialize(builder,old,kept,remaining):
    """Return a free desired output, preserving all other live coordinates."""
    live=kept+old;full=(1 << 256)-1
    span=BinarySpan([full]+[x.truth for x in live])
    candidates=[]
    for name,truth in remaining.items():
        expression=span.solve(truth)
        if expression is None:continue
        pivots=[i for i in bits(expression >> 1) if i>=len(kept)]
        if not pivots:continue
        pivot=min(pivots,key=lambda i:(not live[i].name.startswith('product:'),live[i].name,i))
        candidates.append(((expression.bit_count(),name),name,truth,expression,pivot))
    if not candidates:return None
    _,name,truth,expression,pivot=min(candidates)
    item=live[pivot]
    if expression&1:builder.x(item.wire)
    for i in bits(expression >> 1):
        if i!=pivot:builder.cx(live[i].wire,item.wire)
    old.pop(pivot-len(kept))
    out=LiveFunction(name,item.wire,truth);kept.append(out);remaining.pop(name)
    return out


def choose_retirement(kept,old,plan,remaining,current_helpers,*,limit,seed,structured_functions=()):
    live=kept+old;functions=[x.truth for x in live]
    consumed=[i for i in range(len(kept),len(live)) if live[i].wire not in current_helpers]
    directions=zero_directions(plan,consumed,limit=limit,seed=seed)
    best=None
    for direction in directions:
        # Each pivot yields a different physical frame of the same quotient.
        # Try two sparse representatives to avoid a fixed basis preference.
        for pivot in list(bits(direction))[:2]:
            framed=list(live);changed=plan;frame=[]
            for i in bits(direction ^(1 << pivot)):
                frame.append((pivot,i))
                framed[i]=LiveFunction(framed[i].name,framed[i].wire,
                                      framed[i].truth^framed[pivot].truth)
                changed=cnot_polynomial(changed,pivot,i)
            if (changed.linear >> pivot)&1 or any(pivot in edge for edge in changed.edges):
                raise AssertionError('A zero-derivative radical frame did not remove its pivot.')
            reduced=drop_coordinate(changed,pivot)
            reduced_live=framed[:pivot]+framed[pivot+1:]
            if not reduced.products:continue
            left,right,_,_=reduced.products[0]
            product=product_plan(reduced.width,left,right)
            truth=product.evaluate_factored_functions([x.truth for x in reduced_live],(1 << 256)-1)
            future_functions=[x.truth for x in reduced_live]+[truth]
            code=Codebook(future_functions)
            sub=structured_intersection(future_functions,structured_functions)
            future=[representation(code,t,sub) for t in remaining.values()]
            if any(p is None for p in future):continue
            score=(sum(p.and_count for p in future),-len(code.span.pivots),
                   len(frame),live[pivot].name,direction)
            if best is None or score<best[0]:
                best=(score,pivot,frame,framed,reduced,reduced_live,product,truth)
    return best


def scalar_finish(builder,kept,old,remaining,debts,*,trials,seed,structured_functions=()):
    """Certified fallback when no safe product-preserving frame is available."""
    free=builder.max_qubits-builder.num_allocated_qubits
    choices=[None] if free else list(range(len(old)))
    best=None
    for retired in choices:
        live=kept+[x for i,x in enumerate(old) if i!=retired]
        code=Codebook([x.truth for x in live])
        sub=structured_intersection(code.functions,structured_functions)
        for name,truth in remaining.items():
            future=Codebook([x.truth for x in live]+[truth])
            if any(future.span.solve(t) is None for t in remaining.values()):continue
            plan=representation(code,truth,sub)
            if plan is None:continue
            key=(plan.and_count,name,'' if retired is None else old[retired].name)
            if best is None or key<best[0]:best=(key,retired,live,code,name,truth,plan)
    if best is None:raise ValueError('No scalar completion preserves the remaining target domain.')
    _,retired,live,code,name,truth,plan=best
    plan=code.represent(truth,trials=trials,seed=seed,initial_plan=plan)
    if retired is None:wire=builder.alloc_qubits(1)[0]
    else:
        item=old.pop(retired);wire=item.wire
        debts.erase(builder,_word_table([item.truth]),[wire])
    emit_xor(builder,[x.wire for x in live],wire,plan)
    out=LiveFunction(name,wire,truth);kept.append(out);remaining.pop(name)
    return out,plan.and_count


def finish_on_product(builder,kept,old,remaining,name,truth,plan,product_wire,*,trials,seed):
    """Keep the selected products, fan the remaining terms into just one."""
    live=kept+old
    pivot=next(i for i,x in enumerate(live) if x.wire==product_wire)
    if not (plan.linear >> pivot)&1 or any(pivot in edge for edge in plan.edges):
        raise AssertionError('A retained product lost its linear fan-in coordinate.')
    updated=factor_polynomial(plan.width,plan.constant,plan.linear^(1 << pivot),plan.edges)
    updated=drop_coordinate(updated,pivot)
    item=old[pivot-len(kept)]
    variables=live[:pivot]+live[pivot+1:]
    code=Codebook([x.truth for x in variables])
    updated=code.represent(truth^item.truth,trials=trials,seed=seed,initial_plan=updated)
    emit_xor(builder,[x.wire for x in variables],item.wire,updated)
    old.pop(pivot-len(kept));out=LiveFunction(name,item.wire,truth)
    kept.append(out);remaining.pop(name)
    return out,updated.and_count


def convert_retained_products(builder,consumed,desired,debts,*,trials=80,
                              seed=2026110609,direction_limit=16,maximum_products=600,
                              retain_products=True,progress=None,structured_functions=(),
                              basis_trials=0,retained_helpers=None):
    old=list(consumed);kept=[];remaining=dict(desired);produced={};steps=[];ands=0
    original_desired=list(desired)
    formal={name:1 << i for i,(name,_) in enumerate(original_desired)}
    produced_formal={}
    if len(set(x.wire for x in old))!=len(old):raise ValueError('Each code coordinate needs its own wire.')
    while remaining:
        out=affine_materialize(builder,old,kept,remaining)
        if out is not None:
            produced[out.name]=out
            produced_formal[out.name]=formal.pop(out.name)
            steps.append({'kind':'affine_output','name':out.name,'ands':0})
            if progress:progress(len(produced),ands,out.name)
            continue
        live=kept+old;functions=[x.truth for x in live];code=Codebook(functions)
        sub=structured_intersection(functions,structured_functions)
        choices=[]
        for name,truth in remaining.items():
            plan=representation(code,truth,sub)
            if plan is not None:choices.append((plan.and_count,name,truth,plan))
        if not choices:raise ValueError('The live mathematical code lost all pending outputs.')
        _,name,truth,plan=min(choices)
        plan=code.represent(truth,trials=trials,seed=seed+len(steps),initial_plan=plan)
        if basis_trials and plan.and_count>1 and len(remaining)>1:
            from minrank_lookup import natural_subspace_decoder,subspace_decoder
            previous=list(remaining.items());targets=[f for _,f in previous]
            hit=None
            for products in range(1,min(3,plan.and_count-1)+1):
                candidate,mask,meta=natural_subspace_decoder(code.functions,targets,
                    products=products,subset_limit=256)
                if candidate is not None and candidate.and_count<plan.and_count:
                    hit=(candidate,mask,meta);break
            if hit is None:
                for products in range(4,min(5,plan.and_count-1)+1):
                    candidate,mask,meta=subspace_decoder(code.functions,targets,products=products,
                        trials=basis_trials,seed=seed+100000+ands+products*1000)
                    if candidate is not None and candidate.and_count<plan.and_count:
                        hit=(candidate,mask,meta);break
            if hit is not None:
                candidate,mask,meta=hit
                requested=[label for label,_ in previous].index(name)
                combined=parity_function(mask,targets)
                combined_formal=parity_function(mask,[formal[label] for label,_ in previous])
                pivot=requested if (mask >> requested)&1 else next(bits(mask))
                if pivot!=requested:
                    pivot_name=previous[pivot][0]
                    remaining[pivot_name]=truth;formal[pivot_name]=formal[name]
                remaining[name]=combined;formal[name]=combined_formal
                truth=combined;plan=candidate
                steps.append({'kind':'target_basis','name':name,'ands':0,
                              'target_mask':mask,'formal':combined_formal,
                              'products':plan.and_count})
        current_helpers=set();helper_order=[];initial_products=plan.and_count
        selected_finished=False
        while plan.and_count and ands<maximum_products:
            live=kept+old;functions=[x.truth for x in live]
            if plan.evaluate_factored_functions(functions,(1 << 256)-1)!=truth:
                raise AssertionError('The retained-product partial fan-in changed its selected output.')
            free=builder.max_qubits-builder.num_allocated_qubits
            if free:
                product=product_plan(plan.width,*plan.products[0][:2])
                product_truth=product.evaluate_factored_functions(functions,(1 << 256)-1)
                target=builder.alloc_qubits(1)[0]
                frame=[];retired_name=None
            else:
                chosen=choose_retirement(kept,old,plan,remaining,current_helpers,
                    limit=direction_limit,seed=seed+10000+ands,
                    structured_functions=structured_functions)
                if chosen is None:break
                _,pivot,frame,framed,reduced,reduced_live,product,product_truth=chosen
                for control,destination in frame:builder.cx(live[control].wire,live[destination].wire)
                # Only consumed coordinates were changed, so produced numeric
                # output wires retain their exact requested meanings.
                old[:]=framed[len(kept):]
                retired=old.pop(pivot-len(kept));target=retired.wire;retired_name=retired.name
                debts.erase(builder,_word_table([retired.truth]),[target])
                live=kept+old;functions=[x.truth for x in live];plan=reduced
            emit_xor(builder,[x.wire for x in live],target,product)
            ands+=1;current_helpers.add(target)
            helper_order.append(target)
            new_name=f'product:{ands}'
            old.append(LiveFunction(new_name,target,product_truth))
            plan=factor_polynomial(plan.width+1,plan.constant,
                plan.linear^product.linear^(1 << plan.width),set(plan.edges)^set(product.edges))
            if plan.evaluate_factored_functions([x.truth for x in kept+old],(1 << 256)-1)!=truth:
                raise AssertionError('A new product feature does not preserve the decoder polynomial.')
            steps.append({'kind':'retained_product','target':name,'feature':new_name,'ands':1,
                          'retired':retired_name,'frame_cnots':len(frame),
                          'remaining_products':plan.and_count,'live':builder.num_allocated_qubits})
            # Prefer exact affine completion as soon as the code enables it.
            affine=BinarySpan([(1 << 256)-1]+[x.truth for x in kept+old])
            if affine.solve(truth) is not None:break
            if retained_helpers is not None and len(helper_order)>=int(retained_helpers)+1:break
        if helper_order and plan.and_count:
            out,count=finish_on_product(builder,kept,old,remaining,name,truth,plan,helper_order[0],
                trials=trials,seed=seed+30000+ands)
            produced[out.name]=out;produced_formal[out.name]=formal.pop(out.name);ands+=count
            steps.append({'kind':'partial_fan_in','name':out.name,'ands':count,
                          'retained_helpers':len(helper_order)-1})
            if progress:progress(len(produced),ands,out.name)
            continue
        out=affine_materialize(builder,old,kept,remaining)
        if out is not None:
            produced[out.name]=out;produced_formal[out.name]=formal.pop(out.name)
            steps.append({'kind':'affine_output','name':out.name,'ands':0})
        else:
            out,count=scalar_finish(builder,kept,old,remaining,debts,trials=trials,
                                    seed=seed+20000+ands,structured_functions=structured_functions)
            produced[out.name]=out;produced_formal[out.name]=formal.pop(out.name);ands+=count
            steps.append({'kind':'scalar_fallback','name':out.name,'ands':count})
        if ands>maximum_products:
            raise ValueError('Retained-product search exceeded its explicit AND budget.')
        if progress:progress(len(produced),ands,out.name)
    if old:
        debts.erase(builder,_word_table([x.truth for x in old]),[x.wire for x in old])
        builder.free(km.array([x.wire for x in old]))
    frame_cnots=0
    if basis_trials:
        names=[name for name,_ in original_desired]
        rows=[produced_formal[name] for name in names]
        wires=[produced[name].wire for name in names]
        truths=[produced[name].truth for name in names]
        for bit in range(len(names)):
            pivot=next(i for i in range(bit,len(names)) if (rows[i] >> bit)&1)
            rows[bit],rows[pivot]=rows[pivot],rows[bit]
            wires[bit],wires[pivot]=wires[pivot],wires[bit]
            truths[bit],truths[pivot]=truths[pivot],truths[bit]
            for i in range(len(names)):
                if i!=bit and (rows[i] >> bit)&1:
                    builder.cx(wires[bit],wires[i]);rows[i]^=rows[bit];truths[i]^=truths[bit]
                    frame_cnots+=1
        for i,(name,truth) in enumerate(original_desired):
            if rows[i]!=1 << i or truths[i]!=truth:
                raise AssertionError('The final retained-product target frame is incorrect.')
            produced[name]=LiveFunction(name,wires[i],truth)
    return produced,{'and_count':ands,'steps':steps,
                    'product_features_created':sum(s['kind']=='retained_product' for s in steps),
                    'scalar_fallbacks':sum(s['kind']=='scalar_fallback' for s in steps),
                    'qubits_after':builder.num_allocated_qubits,'output_basis_cnots':frame_cnots}
