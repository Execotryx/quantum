# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Conditional generation of phase-only table helpers.

The phase expression is solved in a basis ordered by helper birth. A helper
is needed only when a phase coefficient involving it or any dependent helper
is nonzero. Those coefficients are exact XORs of existing HMR outcomes. Their
OR is classical, so testing it does not cost a quantum AND.

Every helper still has its full HMR correction when its branch executes.
Inactive helper slots remain zero. This pass does not condition a decoder
whose Boolean data output is required by subsequent arithmetic.
"""
from fractions import Fraction
import kickmix as km
from codebook import BinarySpan,bits,word_functions,parity_function,emit_xor,emit_phase
from deferred_phase import _anf
from universal_phase_basis import universal_plan,product_plan


def ordered_bank(address_bits=8):
    plan=universal_plan(address_bits);size=1 << address_bits;full=(1 << size)-1
    functions=word_functions(range(size),address_bits)
    monomials=[()]+[(i,) for i in range(address_bits)]
    monomials +=[(i,j) for i in range(address_bits) for j in range(i+1,address_bits)]
    columns=[full]+list(functions)+[functions[i]&functions[j]
        for i in range(address_bits) for j in range(i+1,address_bits)]
    polynomials=[];parents=[]
    for item in plan['steps']:
        index=len(functions);poly=product_plan(index,item['left'],item['right'])
        truth=poly.evaluate_factored_functions(functions,full)
        if truth!=item['truth'] or poly.and_count!=1:
            raise AssertionError('The generated phase helper differs from its certificate.')
        monomials.append((index,));columns.append(truth)
        for j,f in enumerate(functions):monomials.append((j,index));columns.append(f&truth)
        functions.append(truth);polynomials.append(poly)
        parents.append([j-address_bits for j in bits(item['left']|item['right']) if j>=address_bits])
    span=BinarySpan(columns)
    if len(span.pivots)!=size:raise AssertionError('The birth-ordered bank is not universal.')
    return functions,polynomials,parents,monomials,columns,span


def compile_ledger(debts):
    functions,polynomials,parents,monomials,columns,span=ordered_bank(debts.address_bits)
    outcomes=[];truths=[]
    for coefficients,word in debts.pending:
        outcomes.extend(word);truths.extend(word_functions(_anf(coefficients),len(word)))
    if len(set(outcomes))!=len(outcomes):raise ValueError('A measurement result is owned twice.')
    terms={}
    for j,truth in enumerate(truths):
        expression=span.solve(truth)
        if expression is None or parity_function(expression,columns)!=truth:
            raise AssertionError('A pending phase has no exact birth-ordered representation.')
        for k in bits(expression):terms[monomials[k]]=terms.get(monomials[k],0)^(1 << j)
    terms={key:value for key,value in terms.items() if value}
    direct=[set() for _ in polynomials]
    for monomial,mask in terms.items():
        for variable in monomial:
            if variable>=debts.address_bits:direct[variable-debts.address_bits].add(mask)
    closure=[set(group) for group in direct]
    for i in range(len(closure)-1,-1,-1):
        for parent in parents[i]:closure[parent].update(closure[i])
    bases=[]
    for masks in closure:
        linear=BinarySpan();basis=[]
        for mask in sorted(masks):
            if linear.add(mask):basis.append(mask)
        bases.append(basis)
    return {'functions':functions,'polynomials':polynomials,'parents':parents,
        'terms':terms,'outcomes':outcomes,'truths':truths,'activation_bases':bases,
        'activation_ranks':[len(x) for x in bases],
        'phase_function_rank':len(BinarySpan(truths).pivots)}


def _parity(builder,mask,outcomes,target):
    builder.bit_store(target,False)
    for i in bits(mask):builder.cx(outcomes[i],target)


def emit_compiled(builder,address,compiled,*,conditional_rank_limit=4,
                  omit_conditional_cleanup=False,conditional_helpers=None):
    """Emit one exact phase polynomial without consuming the caller's bits."""
    address=list(address);n=len(address);outcomes=compiled['outcomes']
    polynomials=compiled['polynomials'];basis=compiled['activation_bases']
    wires=list(address)+list(builder.alloc_qubits(len(polynomials)))
    parity=builder.alloc_bits(1)[0];conditions={};expected=Fraction(0)
    for i,mask_basis in enumerate(basis):
        rank=len(mask_basis)
        if rank<=conditional_rank_limit and (conditional_helpers is None or i in conditional_helpers):
            condition=builder.alloc_bits(1)[0];builder.bit_store(condition,False)
            for mask in mask_basis:
                _parity(builder,mask,outcomes,parity)
                builder.bit_store(condition,True,control=parity)
            conditions[i]=condition;expected+=1-Fraction(1,1 << rank)
        else:expected+=1
    for i,poly in enumerate(polynomials):
        if i in conditions:builder.push_condition(conditions[i])
        emit_xor(builder,wires[:n+i],wires[n+i],poly)
        if i in conditions:builder.pop_condition()
    for monomial,mask in sorted(compiled['terms'].items()):
        _parity(builder,mask,outcomes,parity)
        if not monomial:builder.z(parity)
        else:
            builder.push_condition(parity)
            if len(monomial)==1:builder.z(wires[monomial[0]])
            else:builder.cz(wires[monomial[0]],wires[monomial[1]])
            builder.pop_condition()
    for i in range(len(polynomials)-1,-1,-1):
        measured=builder.alloc_bits(1)[0];builder.bit_store(measured,False)
        if i in conditions:builder.push_condition(conditions[i])
        builder.hmr(wires[n+i],measured)
        if not(omit_conditional_cleanup and i in conditions):
            emit_phase(builder,wires[:n+i],measured,polynomials[i])
        if i in conditions:builder.pop_condition()
        builder.free(measured);builder.free(wires[n+i])
    builder.free(parity)
    for condition in conditions.values():builder.free(condition)
    return {'and_count':len(polynomials),'mean_and_numerator':expected.numerator,
        'mean_and_denominator':expected.denominator,'mean_and_count':float(expected),
        'activation_ranks':compiled['activation_ranks'],
        'conditioned_helpers':[i+1 for i in conditions],
        'conditional_rank_limit':conditional_rank_limit,'workspace_qubits':len(polynomials)}


def flush_conditional(builder,address,debts,*,conditional_rank_limit=4):
    address=list(address)
    if len(address)!=debts.address_bits or len(set(address))!=len(address):
        raise ValueError('Wrong restored logical address for conditional repayment.')
    if not debts.pending:return {'and_count':0,'mean_and_count':0,'workspace_qubits':0}
    compiled=compile_ledger(debts)
    helpers=len(compiled['polynomials'])
    if builder.max_qubits-builder.num_allocated_qubits < helpers:
        raise ValueError('Insufficient workspace for conditional phase repayment.')
    metadata=emit_compiled(builder,address,compiled,conditional_rank_limit=conditional_rank_limit,
        conditional_helpers={helpers-1})
    metadata.update(helpers_erased_for_all_outcomes=True,
        bank='birth-ordered affine-product DAG with conditional final helper')
    metadata.update(erased_words=debts.erased_words,erased_qubits=debts.erased_qubits,
        phase_function_rank=compiled['phase_function_rank'],phase_monomials=len(compiled['terms']))
    for _,outcomes in debts.pending:builder.free(outcomes)
    debts.pending.clear();debts.erased_words=debts.erased_qubits=0
    return metadata
