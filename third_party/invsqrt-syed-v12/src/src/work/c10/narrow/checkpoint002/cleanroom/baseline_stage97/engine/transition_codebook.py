# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Bounded-width conversion between mathematical coefficient codebooks.

Consumed offset/anchor bits can be HMR-retired as new coefficient bits are
decoded. Every codebook bit is still a function of the ORIGINAL address;
an arithmetic residual may have changed independently. No gate sequences or
serialized circuits are inputs to this compiler.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import kickmix as km
from codebook import (Codebook, BinarySpan, emit_xor, factor_polynomial, bits,
                      word_functions, parity_function)


@lru_cache(maxsize=None)
def _monomial_truths(address_bits=8):
    size = 1 << address_bits
    address = word_functions(range(size), address_bits)
    values = [(1 << size)-1]
    for mask in range(1, size):
        last = mask.bit_length()-1
        values.append(values[mask ^ (1 << last)] & address[last])
    return frozenset(values)


def _embed_plan(plan, indices, width):
    linear = sum(1 << indices[i] for i in bits(plan.linear))
    edges = [(indices[i], indices[j]) for i, j in plan.edges]
    return factor_polynomial(width, plan.constant, linear, edges)


@dataclass
class LiveFunction:
    name: str
    wire: object
    truth: int


def _word_table(functions, size=256):
    return [sum(((function >> address) & 1) << bit
                for bit, function in enumerate(functions))
            for address in range(size)]


def retire_table_bits(builder, values, word, phase_debts, *, bit_indices=None,
                       remove=None, count=0):
    """Measure selected static table bits and preserve explicit logical indices.

    The caller certifies that each wire contains the listed bit of `values`.
    If `remove` is omitted, retire the highest `count` logical positions.
    The returned partial word need not consist of contiguous low bits.
    """
    word, values = list(word), list(map(int,values))
    indices = list(range(len(word))) if bit_indices is None else list(map(int,bit_indices))
    if len(indices) != len(word) or len(set(indices)) != len(indices):
        raise ValueError('Every partial-word wire requires a distinct logical index.')
    removed = set(sorted(indices,reverse=True)[:count] if remove is None else map(int,remove))
    if not removed <= set(indices):
        raise ValueError('A retired logical bit is absent from the partial word.')
    selected = [(index,wire) for index,wire in zip(indices,word) if index in removed]
    if selected:
        table = [sum(((value >> bit)&1) << j for j,(bit,_) in enumerate(selected))
                 for value in values]
        targets = km.array([wire for _,wire in selected])
        phase_debts.erase(builder,table,targets)
        builder.free(targets)
    kept = [(index,wire) for index,wire in zip(indices,word) if index not in removed]
    return (km.array([wire for _,wire in kept]),[index for index,_ in kept],
            {'and_count':0,'retired_bits':[bit for bit,_ in selected],
             'retained_bits':[bit for bit,_ in kept],
             'qubits_after':builder.num_allocated_qubits})


def _future_quadratic_coverage(code, added_truth, targets):
    """Certify the quadratic span after one new live coordinate is added.

    Only truth vectors are needed here. Reusing the already reduced rows
    avoids rebuilding all old quadratic columns for every scheduling choice.
    """
    rows={pivot:value for pivot,(value,_) in code.span.pivots.items()}
    if len(rows)==code.size:
        return True
    for value in [added_truth]+[added_truth&function for function in code.functions]:
        while value:
            pivot=value.bit_length()-1
            if pivot not in rows:
                rows[pivot]=value
                break
            value^=rows[pivot]
        if len(rows)==code.size:
            return True
    for value in targets:
        while value:
            pivot=value.bit_length()-1
            if pivot not in rows:
                return False
            value^=rows[pivot]
    return True


def convert_codebook(builder, retained, consumed, desired, phase_debts,
                     *, trials=400, seed=314159, kernel_trials=0,
                     preserving_rounds=0, structured_subsets=False,
                     preserving_min_products=9, preserve_future=False,
                     extra_subset_functions=(), affine_rebase=False,
                     basis_search_products=0,basis_random_trials=0,
                     basis_natural_limit=None,basis_random_max_products=4,
                     basis_complete_in_place=False,
                     force_in_place=False,
                     transition_trace=None,surplus_functions=None):
    """Materialize named functions, retiring consumed words only when needed.

    retained/consumed are LiveFunction objects with distinct wires. Desired
    is a sequence of `(name, truth_vector)` pairs. The old consumed functions
    have no further arithmetic uses. They may therefore be measured, and their
    exact phases appended to the supplied logical-address ledger.

    At a full-width step the compiler tries every removable bit and every
    requested output, picks a certified quadratic expression with the fewest
    products, and reuses the measured wire. Unmeasured functions remain exact
    and unchanged. If no valid transition exists it raises instead of emitting
    an unproved conversion.
    """
    kept = list(retained)
    old = list(consumed)
    size = 1 << phase_debts.address_bits
    remaining = [(str(name), int(truth)) for name, truth in desired]
    original_desired=list(remaining)
    formal={name:1 << i for i,(name,_) in enumerate(remaining)}
    produced_formal={}
    all_wires = [item.wire for item in kept+old]
    if len(set(all_wires)) != len(all_wires):
        raise ValueError('Each live function must own a distinct physical wire.')
    if len(set(name for name, _ in remaining)) != len(remaining):
        raise ValueError('Desired output names must be unique.')
    produced = {}
    steps = []
    total_ands = 0
    while remaining:
        # Moving ownership of an already materialized function is free.
        match = next(((i, j) for i, (_, truth) in enumerate(remaining)
                      for j, item in enumerate(old) if item.truth == truth), None)
        if match is not None:
            i, j = match
            name, truth = remaining.pop(i)
            item = old.pop(j)
            replacement = LiveFunction(name, item.wire, truth)
            kept.append(replacement)
            produced[name] = replacement
            produced_formal[name]=formal.pop(name)
            steps.append({'name': name, 'products': 0, 'action': 'rename',
                          'old_name': item.name})
            continue
        deferred_copies = set()
        if affine_rebase:
            live = kept+old
            linear = BinarySpan([(1 << size)-1]+[item.truth for item in live])
            candidate = None
            for requested,(name,truth) in enumerate(remaining):
                expression = linear.solve(truth)
                if expression is None:
                    continue
                pivots = [i for i in range(len(old)) if expression >> (1+len(kept)+i)&1]
                if not pivots:
                    deferred_copies.add(requested)
                    continue
                retired = min(pivots,key=lambda i:old[i].name)
                key = (name,old[retired].name)
                if candidate is None or key<candidate[0]:
                    candidate=(key,requested,retired,expression,live)
            if candidate is not None:
                _,requested,retired,expression,live=candidate
                name,truth=remaining.pop(requested)
                old_item=old.pop(retired)
                pivot=len(kept)+retired
                if expression&1:
                    builder.x(old_item.wire)
                    if transition_trace is not None:transition_trace.append(('x',old_item.wire))
                for i in bits(expression >> 1):
                    if i!=pivot:
                        builder.cx(live[i].wire,old_item.wire)
                        if transition_trace is not None:
                            transition_trace.append(('cx',live[i].wire,old_item.wire))
                replacement=LiveFunction(name,old_item.wire,truth)
                kept.append(replacement)
                produced[name]=replacement
                produced_formal[name]=formal.pop(name)
                new_rank=len(BinarySpan([(1 << size)-1]+[item.truth for item in kept+old]).pivots)
                if new_rank!=len(linear.pivots):
                    raise AssertionError('An affine code rebase lost linear information.')
                steps.append({'name':name,'products':0,'action':'affine_rebase',
                              'old_name':old_item.name,'linear_rank_preserved':new_rank,
                              'all_addresses_checked':size})
                continue
            if len(deferred_copies)==len(remaining):
                deferred_copies.clear()
        free = builder.max_qubits-builder.num_allocated_qubits
        candidates = [None] if free and not force_in_place else list(range(len(old)))
        choice = None
        for retired in candidates:
            live = kept+[item for i, item in enumerate(old) if i != retired]
            # Constant wires carry no additional feature information.
            full = (1 << size)-1
            live = [item for item in live if item.truth not in (0, full)]
            code = Codebook([item.truth for item in live], size=size)
            subset = None
            if structured_subsets:
                monomials = _monomial_truths(phase_debts.address_bits)|frozenset(extra_subset_functions)
                indices = [i for i, item in enumerate(live) if item.truth in monomials]
                if 1 < len(indices) < len(live):
                    subset = (indices, Codebook([live[i].truth for i in indices],size=size))
            for requested, (name, truth) in enumerate(remaining):
                if requested in deferred_copies:
                    continue
                if (preserve_future and retired is not None and
                        not _future_quadratic_coverage(code,truth,
                            [other_truth for i,(_,other_truth) in enumerate(remaining)
                             if i!=requested])):
                    continue
                updates = [] if force_in_place else [(False, truth)]
                if retired is not None:
                    updates.append((True, truth ^ old[retired].truth))
                for in_place, update_truth in updates:
                    plan = code.represent(update_truth)
                    if plan is None:
                        continue
                    if subset is not None:
                        indices, subcode = subset
                        candidate = subcode.represent(update_truth)
                        if candidate is not None and candidate.and_count < plan.and_count:
                            plan = _embed_plan(candidate, indices, code.width)
                    key = (plan.and_count, name, '' if retired is None else old[retired].name,
                           not in_place)
                    if choice is None or key < choice[0]:
                        choice = (key, retired, requested, live, code, plan, in_place, update_truth)
        if choice is None:
            raise ValueError(f'No certified bounded-width quadratic transition after{len(steps)} steps; '
                             f'{len(remaining)} outputs remain.')
        _, retired, requested, live, code, naive, in_place, update_truth = choice
        name, truth = remaining[requested]
        plan = code.represent(update_truth, trials=trials, seed=seed+len(steps), initial_plan=naive)
        if kernel_trials and code.width <= 28:
            alternative, _ = code.represent_kernel(update_truth, trials=kernel_trials,
                                                    seed=seed+1000+len(steps))
            if alternative is not None and alternative.and_count < plan.and_count:
                plan = alternative
        if preserving_rounds and code.width >= 25 and plan.and_count >= preserving_min_products:
            plan = code.improve_preserving_kernel(plan, rounds=preserving_rounds,
                                                   seed=seed+2000+len(steps))
        basis_mix=None
        if basis_search_products and plan.and_count>1 and len(remaining)>1:
            # This is a task-written exact search.  It accepts only coefficient
            # truth vectors, never circuit files or precomputed gate plans.
            from minrank_lookup import natural_subspace_decoder,subspace_decoder
            targets=[value for _,value in remaining]
            basis_choice=None
            updates=[] if force_in_place else [(False,0)]
            if retired is not None:updates.append((True,old[retired].truth))
            for products in range(1,min(int(basis_search_products),plan.and_count-1)+1):
                for candidate_in_place,old_truth in updates:
                    candidate,mask,search=natural_subspace_decoder(
                        code.functions,targets,products=products,size=size,
                        update_constant=old_truth,subset_limit=basis_natural_limit,
                        complete_update_space=basis_complete_in_place)
                    if candidate is None or candidate.and_count>=plan.and_count:continue
                    if (preserve_future and not _future_quadratic_coverage(code,
                            parity_function(mask,targets),targets)):
                        continue
                    basis_choice=(candidate,mask,search,candidate_in_place)
                    break
                if basis_choice is not None:break
            if basis_choice is None and basis_random_trials and plan.and_count>4:
                for products in range(4,min(int(basis_random_max_products),plan.and_count-1)+1):
                    for candidate_in_place,old_truth in updates:
                        candidate,mask,search=subspace_decoder(
                            code.functions,targets,products=products,trials=basis_random_trials,
                            seed=seed+10000+len(steps)+(products-4)*100000,
                            size=size,update_constant=old_truth,
                            complete_update_space=basis_complete_in_place)
                        if candidate is not None and candidate.and_count<plan.and_count:
                            if (preserve_future and not _future_quadratic_coverage(code,
                                    parity_function(mask,targets),targets)):
                                continue
                            basis_choice=(candidate,mask,search,candidate_in_place)
                            break
                    if basis_choice is not None:break
            if basis_choice is not None:
                candidate,mask,search,in_place=basis_choice
                previous=list(remaining)
                combined_truth=parity_function(mask,[value for _,value in previous])
                combined_formal=parity_function(mask,[formal[label] for label,_ in previous])
                pivot=requested if mask >> requested&1 else next(bits(mask))
                if pivot!=requested:
                    pivot_name=remaining[pivot][0]
                    remaining[pivot]=(pivot_name,truth)
                    formal[pivot_name]=formal[name]
                remaining[requested]=(name,combined_truth)
                formal[name]=combined_formal
                truth=combined_truth
                update_truth=truth^(old[retired].truth if in_place else 0)
                plan=candidate
                if plan.evaluate_factored_functions(code.functions,code.full)!=update_truth:
                    raise AssertionError('A target-basis decoder failed its complete truth certificate.')
                basis_mix={'source_labels':[previous[i][0] for i in bits(mask)],
                           'formal_output_mask':combined_formal,'pivot_label':previous[pivot][0],
                           'search':search}
        name,truth=remaining.pop(requested)
        if retired is None:
            target = builder.alloc_qubits(1)[0]
            old_name = None
        else:
            item = old.pop(retired)
            target = item.wire
            old_name = item.name
            if not in_place:
                phase_debts.erase(builder, _word_table([item.truth],size), [target])
        if builder.num_allocated_qubits > builder.max_qubits:
            raise AssertionError('The scheduled conversion exceeded its width limit.')
        emit_xor(builder, [item.wire for item in live], target, plan)
        if transition_trace is not None:
            if not in_place:
                raise ValueError('A reversible transition trace requires every update to be in place.')
            transition_trace.append(('xor',tuple(item.wire for item in live),target,plan))
        replacement = LiveFunction(name, target, truth)
        kept.append(replacement)
        produced[name] = replacement
        produced_formal[name]=formal.pop(name)
        total_ands += plan.and_count
        steps.append({'name': name, 'products': plan.and_count,
                      'initial_products': naive.and_count,
                      'action': ('allocate' if retired is None else
                                 'in_place_xor' if in_place else 'measure_and_reuse'),
                      'old_name': old_name, 'code_width': code.width,
                      'quadratic_feature_rank': len(code.span.pivots),
                      'basis_mix':basis_mix,
                      'all_addresses_checked': size})
    if old:
        if surplus_functions is not None:surplus_functions.extend(old)
        phase_debts.erase(builder, _word_table([item.truth for item in old],size),
                          [item.wire for item in old])
        builder.free(km.array([item.wire for item in old]))
    frame_cnots=0
    if basis_search_products:
        # Restore the requested numeric output bits from their synthesized
        # invertible target-space basis. Physical row swaps are just ownership
        # relabelings; all remaining operations are exact CNOTs.
        names=[name for name,_ in original_desired]
        rows=[produced_formal[name] for name in names]
        wires=[produced[name].wire for name in names]
        truths=[produced[name].truth for name in names]
        if len(BinarySpan(rows).pivots)!=len(names):
            raise AssertionError('The synthesized target basis is singular.')
        for bit in range(len(names)):
            pivot=next(i for i in range(bit,len(names)) if rows[i] >> bit&1)
            rows[bit],rows[pivot]=rows[pivot],rows[bit]
            wires[bit],wires[pivot]=wires[pivot],wires[bit]
            truths[bit],truths[pivot]=truths[pivot],truths[bit]
            for i in range(len(names)):
                if i!=bit and rows[i] >> bit&1:
                    builder.cx(wires[bit],wires[i])
                    if transition_trace is not None:
                        transition_trace.append(('cx',wires[bit],wires[i]))
                    rows[i]^=rows[bit]
                    truths[i]^=truths[bit]
                    frame_cnots+=1
        for i,(name,truth) in enumerate(original_desired):
            if rows[i] != 1 << i or truths[i]!=truth:
                raise AssertionError('The final Clifford frame did not restore a requested function.')
            produced[name]=LiveFunction(name,wires[i],truth)
    return produced, {'and_count': total_ands, 'steps': steps,
                      'output_basis_cnots':frame_cnots,
                      'reversible_in_place':bool(force_in_place),
                      'qubits_after': builder.num_allocated_qubits}

