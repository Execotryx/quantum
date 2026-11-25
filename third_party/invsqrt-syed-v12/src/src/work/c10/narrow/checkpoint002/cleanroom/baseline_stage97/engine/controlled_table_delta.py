# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Compile a sparse-care table increment as controlled affine XOR frames.

The inputs are mathematical integer tables and truth functions of available
static coefficient wires. The solver derives its frames anew and validates
every cared row. Its gates preserve all basis wires; applying the same plan
again restores the high word exactly for every data/control state.
"""
from dataclasses import dataclass
from codebook import BinarySpan,word_functions,bits,parity_function


@dataclass(frozen=True)
class ControlledDeltaPlan:
    width:int
    masks:tuple
    care_mask:int
    function_count:int
    domain_size:int
    and_count:int


def compile_delta(high_values,tail_bits,care_addresses,functions,*,width=8):
    high_values=list(map(int,high_values));tail_bits=list(map(int,tail_bits))
    functions=list(map(int,functions));n=len(high_values)
    if len(tail_bits)!=n or any(bit not in (0,1) for bit in tail_bits):
        raise ValueError('High and Boolean increment tables must have equal length.')
    care=tuple(sorted(set(map(int,care_addresses))))
    if any(not 0<=a<n for a in care):raise ValueError('Care address is outside the table.')
    if any(high_values[a]+tail_bits[a]>=1 << width for a in care):
        raise ValueError('The cared mathematical high increment overflows.')
    cm=sum(1 << a for a in care)
    columns=[cm]+[truth&cm for truth in functions]
    span=BinarySpan(columns)
    delta=[(h+b)^h for h,b in zip(high_values,tail_bits)]
    wanted=word_functions(delta,width)
    masks=[]
    for target in wanted:
        mask=span.solve(target&cm)
        if mask is None:raise ValueError('A high-delta bit is not affine in the live code.')
        actual=(cm if mask&1 else 0) ^ (parity_function(mask>>1,functions)&cm)
        if actual!=(target&cm):raise AssertionError('Affine high-delta truth certificate failed.')
        masks.append(mask)
    return ControlledDeltaPlan(width,tuple(masks),cm,len(functions),n,
        sum(bool(mask>>1) for mask in masks))


def apply_delta(builder,word,control,variables,plan):
    """XOR the certified affine vector, controlled by one preserved qubit."""
    word,variables=list(word),list(variables)
    if len(word)!=plan.width or len(variables)!=plan.function_count:
        raise ValueError('The physical word/code widths do not match the delta plan.')
    if len(set(word+variables+[control]))!=len(word)+len(variables)+1:
        raise ValueError('Controlled word, static code and threshold must be disjoint.')
    for target,mask in zip(word,plan.masks):
        linear=mask>>1
        if mask&1:builder.cx(control,target)
        if not linear:continue
        pivots=list(bits(linear));pivot=variables[pivots[0]]
        for index in pivots[1:]:builder.cx(variables[index],pivot)
        builder.ccx(control,pivot,target)
        for index in reversed(pivots[1:]):builder.cx(variables[index],pivot)
