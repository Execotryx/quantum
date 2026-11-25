# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Cyclic scaled phase directly on PackedShift, with three helper qubits.

The packed residual and its t flag remain encoded throughout. A single
temporary u=[k>=2] is retained; binary routing flags are computed one at a
time. Thresholds are derived from exhaustive quadratic extensions of their
truth values on the nine valid u=1 codes. All HMR phases are repaid exactly.
The outer u phase is retained by PackedShift's ledger until final unpack.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

import kickmix as km
from cyclic_phase import rotation_pairs,_pow2,_erase_polynomial
from quadratic_terms import compile_polynomial,xor_polynomial


@dataclass(frozen=True)
class PackedThresholdPlan:
    threshold:int
    terms:tuple
    products:int


def _code(k):
    f=[(k >> i)&1 for i in range(4)]
    return f[1]|((f[2]^f[3]) << 1)|(f[0] << 2)|(f[3] << 3)


@lru_cache(maxsize=8)
def packed_threshold_plan(threshold):
    """Enumerate every quadratic extension on the exact valid code domain."""
    if not 3<=threshold<=10:
        raise ValueError('This synthesis handles thresholds3..10.')
    monomials=tuple(mask for mask in range(16) if mask.bit_count()<=2)
    best=None
    for selection in range(1 << len(monomials)):
        terms=tuple(mask for i,mask in enumerate(monomials) if selection >> i&1)
        if any((sum(int(_code(k)&mask==mask) for mask in terms)&1)!=int(k>=threshold)
               for k in range(2,11)):
            continue
        plan=compile_polynomial(4,terms)
        key=(len(plan.products),len(terms),terms)
        if best is None or key<best[0]:
            best=(key,terms)
    if best is None:
        raise ValueError('No quadratic threshold extension exists.')
    return PackedThresholdPlan(threshold,best[1],best[0][0])


def _phase_masked_polynomial(builder,u,variables,terms,outcome):
    """Repay u*g using one CCZ per product-rank factor, without a helper."""
    plan=compile_polynomial(len(variables),terms)
    builder.push_condition(outcome)
    for term in plan.affine:
        if term:
            builder.cz(u,variables[term.bit_length()-1])
        else:
            builder.z(u)
    for left,right,i,j in plan.products:
        frames=[(variables[k],variables[i]) for k in range(plan.width)
                if k!=i and left >> k&1]
        frames += [(variables[k],variables[j]) for k in range(plan.width)
                   if k!=j and right >> k&1]
        for a,b in frames:
            builder.cx(a,b)
        builder.ccz(u,variables[i],variables[j])
        for a,b in reversed(frames):
            builder.cx(a,b)
    builder.pop_condition()


@contextmanager
def _flag(builder,packed,u,index):
    # Variables are q0,q1,q2,q3,t,u. These formulas are certified on all
    # packed states, including arbitrary unused residual bits at k=0/1.
    q=list(packed.residual[:4])
    variables=q+[packed.t,u]
    terms=((16,32,36),(17,),(34,40),(40,))[index]
    target=builder.alloc_qubits(1)[0]
    xor_polynomial(builder,variables,target,terms)
    try:
        yield target
    finally:
        _erase_polynomial(builder,target,variables,terms)


@contextmanager
def _threshold(builder,packed,u,threshold):
    if threshold==1:
        yield packed.t,0,0
        return
    if threshold==2:
        yield u,0,0
        return
    q=list(packed.residual[:4])
    plan=packed_threshold_plan(threshold)
    available=builder.max_qubits-builder.num_allocated_qubits
    if not plan.products:
        # The minimal affine extensions in this domain are literal q1/q3.
        affine=compile_polynomial(4,plan.terms).affine
        linear=[term.bit_length()-1 for term in affine if term]
        if not linear:
            raise AssertionError('Unexpected constant packed threshold.')
        pivot=q[linear[0]]
        frame=[q[index] for index in linear[1:]]
        for wire in frame:
            builder.cx(wire,pivot)
        if 0 in affine:
            builder.x(pivot)
        control=builder.alloc_qubits(1)[0]
        builder.ccx(u,pivot,control)
        try:
            yield control,1,0
        finally:
            builder.del_and(u,pivot,control)
            builder.free(control)
            if 0 in affine:
                builder.x(pivot)
            for wire in reversed(frame):
                builder.cx(wire,pivot)
        return
    helper=builder.alloc_qubits(1)[0]
    xor_polynomial(builder,q,helper,plan.terms)
    control=builder.alloc_qubits(1)[0]
    builder.ccx(u,helper,control)
    compact=available<3
    if compact:
        _erase_polynomial(builder,helper,q,plan.terms)
    try:
        yield control,plan.products+1,plan.products if compact else 0
    finally:
        if compact:
            outcome=builder.alloc_bits(1)[0]
            builder.hmr(control,outcome)
            builder.free(control)
            _phase_masked_polynomial(builder,u,q,plan.terms,outcome)
            builder.free(outcome)
        else:
            builder.del_and(u,helper,control)
            builder.free(control)
            _erase_polynomial(builder,helper,q,plan.terms)


def packed_cyclic_scale_phase(builder,value,packed,fractional_bits,*,beta=1,
                               turn_offsets=None,complement_overflow=False,
                               source_width=None):
    """Apply the same cyclic phase features without unpacking binary flags.

    At most three helper qubits beyond the packed representation suffice.
    With a fourth available, six conditional CCZ cleanups can be avoided.
    Frozen offsets and complemented features follow cyclic_scale_phase's
    exact W+10 ordering. Final PackedShift.unpack() remains mandatory to
    repay its preexisting and newly deferred u measurement phases.

    source_width may certify a high suffix of initially zero padding. Such
    padding prunes impossible overflow features and permits equivalent
    threshold predicates. The compiler chooses the cheapest exact predicate
    on the padded domain, and requires zero offsets for pruned features.
    """
    value=list(value)
    width=len(value)
    source_width=width if source_width is None else int(source_width)
    if not packed.is_packed or packed.max_k!=10 or width<1:
        raise ValueError('This phase kernel requires packed k in0..10 and a nonempty word.')
    if not 0<source_width<=width:
        raise ValueError('The certified source width must lie in1..W.')
    if len(set(value+list(packed.residual)+[packed.t]))!=width+len(packed.residual)+1:
        raise ValueError('Value and packed shift wires must be distinct.')
    beta=Fraction(beta)
    if turn_offsets is None:
        offsets=(Fraction(0),)*(width+10)
    else:
        raw=tuple(turn_offsets)
        if len(raw)!=width+10 or any(isinstance(v,float) for v in raw):
            raise ValueError('Provide W+10 exact rational turn offsets.')
        offsets=tuple(map(Fraction,raw))
    padding=width-source_width
    ordinary_count=min(width,source_width+10)
    overflow_count=max(0,10-padding)
    if any(offsets[ordinary_count:width]) or any(offsets[width+overflow_count:]):
        raise ValueError('Pruned known-zero features must have zero frozen offsets.')
    base=[beta*_pow2(i-fractional_bits+1) for i in range(width)]
    overflow=[beta*((1 << width)-1)*_pow2(j-fractional_bits+1) for j in range(overflow_count)]
    if complement_overflow:
        for j,angle in enumerate(overflow):
            base[j % width]+=angle
    swaps=products=conditional_ccz=0
    angles=[];thresholds=[]
    with packed.higher_nonzero() as u:
        routes=[]
        for index in reversed(range(4)):
            pairs=rotation_pairs(width,1 << index)
            if pairs:
                with _flag(builder,packed,u,index) as flag:
                    for a,b in pairs:
                        builder.cswap(flag,value[a],value[b])
                products+=1
            swaps+=len(pairs)
            routes.append((index,pairs))
        for bit,wire in enumerate(value[:ordinary_count]):
            angle=base[bit]+2*offsets[bit]
            builder.z_pow(wire,angle)
            angles.append(angle)
        for j in range(overflow_count):
            compact=builder.max_qubits-builder.num_allocated_qubits<3
            def predicate_cost(threshold):
                if threshold<=2:return (0,0,threshold)
                rank=packed_threshold_plan(threshold).products
                return (rank+1+(rank/2 if compact else 0),rank,threshold)
            threshold=min(range(j+1,j+padding+2),key=predicate_cost)
            thresholds.append(threshold)
            with _threshold(builder,packed,u,threshold) as (control,and_count,ccz_count):
                if complement_overflow:
                    builder.x(control)
                temporary=builder.alloc_qubits(1)[0]
                builder.ccx(control,value[j % width],temporary)
                angle=overflow[j]*(-1 if complement_overflow else 1)+2*offsets[width+j]
                builder.z_pow(temporary,angle)
                builder.del_and(control,value[j % width],temporary)
                builder.free(temporary)
                if complement_overflow:
                    builder.x(control)
                products+=and_count+1
                conditional_ccz+=ccz_count
                angles.append(angle)
        for index,pairs in reversed(routes):
            if pairs:
                with _flag(builder,packed,u,index) as flag:
                    for a,b in reversed(pairs):
                        builder.cswap(flag,value[a],value[b])
                products+=1
    # The u setup costs two ANDs; its release is a deferred exact phase.
    return dict(width=width,max_k=10,source_width=source_width,direct_packed=True,
                complement_overflow=bool(complement_overflow),cswaps=2*swaps,
                and_products=products+2,hmr_conditioned_ccz=conditional_ccz,
                expected_toffolis=2*swaps+products+2+conditional_ccz/2,
                z_pow_calls=len(angles),half_turn_angles=list(map(str,angles)),
                overflow_thresholds=thresholds,
                turn_offsets=list(map(str,offsets)))
