# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Packed phase routing with mathematically certified rare-feature merges.

A requested ordinary feature h may be replaced by h OR [k>=threshold].
The predicate is shared with its existing overflow phase. A separate pass
may omit specified overflow features only when the numerical fitter has
certified the resulting complete phase on every benchmark input.
All local AND erasures pay their phase for both HMR outcomes.
"""
from fractions import Fraction
from packed_phase import _flag,_threshold
from cyclic_phase import rotation_pairs,_pow2

def _or_phase(builder,a,b,angle):
    t=builder.alloc_qubits(1)[0]
    builder.ccx(a,b,t);builder.cx(a,t);builder.cx(b,t)
    builder.z_pow(t,angle)
    builder.cx(b,t);builder.cx(a,t)
    builder.del_and(a,b,t);builder.free(t)

def _mux_phase(builder,old,alternate,control,angle):
    """Phase old when control0, alternate when control1; restore every input."""
    t=builder.alloc_qubits(1)[0];builder.cx(old,t)
    builder.cx(alternate,old);builder.ccx(control,old,t);builder.cx(alternate,old)
    builder.z_pow(t,angle)
    builder.cx(old,t);builder.cx(alternate,old)
    builder.del_and(control,old,t);builder.cx(alternate,old);builder.free(t)

def merged_packed_cyclic_scale_phase(builder,value,packed,fractional_bits,*,beta=1,
        turn_offsets=None,complement_overflow=False,or_features=None,skip_overflow=(),
        tail_bits=None,tail_first_removed=None):
    value=list(value);width=len(value);or_features=dict(or_features or {})
    skipped=set(map(int,skip_overflow))
    if not packed.is_packed or packed.max_k!=10:raise ValueError('Packed k range must be0..10')
    if len(set(value+list(packed.residual)+[packed.t]))!=width+len(packed.residual)+1:raise ValueError('Distinct phase inputs required')
    if any(i<0 or i>=width or k<1 or k>10 for i,k in or_features.items()):raise ValueError('Invalid merged feature')
    if any(j<0 or j>=10 for j in skipped):raise ValueError('Invalid overflow feature')
    offsets=[Fraction(0)]*(width+10) if turn_offsets is None else list(map(Fraction,turn_offsets))
    if len(offsets)!=width+10:raise ValueError('Wrong phase offsets')
    beta=Fraction(beta)
    base=[beta*_pow2(i-fractional_bits+1) for i in range(width)]
    overflow=[beta*((1 << width)-1)*_pow2(j-fractional_bits+1) for j in range(10)]
    if complement_overflow:
        for j,angle in enumerate(overflow):base[j%width]+=angle
    tail_bits=dict(tail_bits or {})
    if tail_bits and (not complement_overflow or width!=8 or tail_first_removed not in (6,7,8)):
        raise ValueError('Tail fusion needs complemented8-bit high geometry and cutoff6..8')
    angles=[];products=swaps=conditional=0;records=[]
    with packed.higher_nonzero() as u:
        tail_routes=[];alternates={}
        if tail_bits:
            required=list(range(tail_first_removed+10,19))
            if sorted(tail_bits)!=required or len(set(tail_bits.values()))!=len(required):
                raise ValueError('Tail wires must be the required distinct coefficient bits')
            if len(required)==3:
                rotated=[tail_bits[18],tail_bits[16],tail_bits[17]]
                for control,amount in [(packed.residual[2],1),(packed.residual[0],2)]:
                    pairs=rotation_pairs(3,amount)
                    for a,b in pairs:builder.cswap(control,rotated[a],rotated[b])
                    tail_routes.append((control,pairs,rotated));swaps+=len(pairs)
            elif len(required)==2:
                rotated=[tail_bits[18],tail_bits[17]]
                builder.cswap(packed.residual[0],*rotated)
                tail_routes.append((packed.residual[0],((0,1),),rotated));swaps+=1
            else:rotated=[tail_bits[18]]
            alternates=dict(zip(range(tail_first_removed+1,10),rotated))
        routes=[]
        for index in reversed(range(4)):
            pairs=rotation_pairs(width,1 << index)
            if pairs:
                with _flag(builder,packed,u,index) as flag:
                    for a,b in pairs:builder.cswap(flag,value[a],value[b])
                products+=1
            swaps+=len(pairs);routes.append((index,pairs))
        for i,wire in enumerate(value):
            if i in or_features:continue
            angle=base[i]+2*offsets[i];builder.z_pow(wire,angle)
            angles.append(angle);records.append(('base',i))
        for j in range(10):
            merged=[i for i,k in sorted(or_features.items()) if k==j+1]
            if j in skipped and not merged:continue
            with _threshold(builder,packed,u,j+1) as (control,cost,ccz):
                products+=cost;conditional+=ccz
                if j not in skipped:
                    angle=overflow[j]*(-1 if complement_overflow else 1)+2*offsets[width+j]
                    if j in alternates:
                        _mux_phase(builder,value[j%width],alternates[j],control,angle)
                    else:
                        if complement_overflow:builder.x(control)
                        t=builder.alloc_qubits(1)[0];builder.ccx(control,value[j%width],t)
                        builder.z_pow(t,angle);builder.del_and(control,value[j%width],t);builder.free(t)
                        if complement_overflow:builder.x(control)
                    products+=1;angles.append(angle);records.append(('overflow',j))
                    if j in alternates:
                        if j==9:builder.cz(control,alternates[j])
                        else:
                            t=builder.alloc_qubits(1)[0];builder.ccx(control,alternates[j],t)
                            fix=_pow2(j-9);builder.z_pow(t,fix)
                            builder.del_and(control,alternates[j],t);builder.free(t)
                            products+=1;angles.append(fix);records.append(('tail_compensation',j))
                for i in merged:
                    angle=base[i]+2*offsets[i]
                    _or_phase(builder,value[i],control,angle)
                    products+=1;angles.append(angle);records.append(('base_or_threshold',i,j+1))
        for index,pairs in reversed(routes):
            if pairs:
                with _flag(builder,packed,u,index) as flag:
                    for a,b in reversed(pairs):builder.cswap(flag,value[a],value[b])
                products+=1
        for control,pairs,rotated in reversed(tail_routes):
            for a,b in reversed(pairs):builder.cswap(control,rotated[a],rotated[b])
    return dict(width=width,max_k=10,direct_packed=True,
        complement_overflow=bool(complement_overflow),cswaps=2*swaps,
        and_products=products+2,hmr_conditioned_ccz=conditional,
        expected_toffolis=2*swaps+products+2+conditional/2,
        z_pow_calls=len(angles),half_turn_angles=list(map(str,angles)),
        turn_offsets=list(map(str,offsets)),or_features=or_features,
        skipped_overflow=sorted(skipped),feature_order=records,
        tail_first_removed=tail_first_removed,tail_bits=sorted(tail_bits))
