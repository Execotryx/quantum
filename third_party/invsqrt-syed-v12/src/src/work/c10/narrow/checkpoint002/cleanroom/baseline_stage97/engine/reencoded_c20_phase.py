# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Experimental native C20 phase using a temporary reversible remainder code."""
from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction
import kickmix as km
from cyclic_phase import _pow2,_erase_polynomial
from quadratic_terms import compile_polynomial,xor_polynomial
from threshold_phase_ledger import PackedThresholdPhasePass
from reencode_synthesis import mathematics,synthesize


def emit_affine(builder,wires,matrix,offset=0):
    """Apply an invertible four-bit affine frame using only CX/SWAP/X gates."""
    wires=list(wires);rows=list(map(int,matrix));operations=[]
    math4,_=mathematics()
    if len(wires)!=4 or len(set(wires))!=4 or len(rows)!=4 or math4.rank(rows)!=4:
        raise ValueError('The encoding requires four distinct quantum wires and an invertible frame.')
    for column in range(4):
        pivot=next(i for i in range(column,4) if rows[i]>>column&1)
        if pivot!=column:
            rows[column],rows[pivot]=rows[pivot],rows[column]
            operations.append(('SWAP',column,pivot))
        for index in range(4):
            if index!=column and rows[index]>>column&1:
                rows[index]^=rows[column];operations.append(('CX',column,index))
    if rows!=[1,2,4,8]:raise AssertionError('The affine frame did not reduce to identity.')
    # Row elimination implements M^-1; reversing its involutions implements M.
    for kind,a,b in reversed(operations):
        if kind=='SWAP':builder.swap(wires[a],wires[b])
        else:builder.cx(wires[a],wires[b])
    for bit in range(4):
        if int(offset)>>bit&1:builder.x(wires[bit])


def emit_encoding(builder,wires,program,*,inverse=False,negative=False):
    """Realize the freshly synthesized total four-bit permutation in place."""
    wires=list(wires);math4,_=mathematics()
    sequence=[math4.inverse_operation(item) for item in reversed(program)] if inverse else list(program)
    products=0
    for operation in sequence:
        if operation['kind']=='affine':
            emit_affine(builder,wires,operation['matrix'],operation['offset']);continue
        if operation['kind']!='shear_frame':raise ValueError('Unknown mathematical encoding primitive.')
        if operation.get('inverse',False):
            emit_affine(builder,wires,math4.invert_matrix(operation['matrix']))
        frame,unframe=math4.primitive_shear_frame(operation['direction'],operation['left'],operation['right'])
        emit_affine(builder,wires,frame)
        if not (negative and products==0):builder.ccx(wires[0],wires[1],wires[2])
        emit_affine(builder,wires,unframe);products+=1
        if not operation.get('inverse',False):emit_affine(builder,wires,operation['matrix'])
    return dict(Toffolis=products,quantum_helpers=0,total_four_bit_permutation=True,inverse=bool(inverse))


def encoded_flag_terms(mask):
    """u*parity(mask & encoded_r) XOR mask0*(t XOR u), on six variables."""
    if not 0<int(mask)<8:raise ValueError('An encoded C5 flag is a nonzero three-bit form.')
    terms=[(1<<5)|(1<<bit) for bit in range(3) if int(mask)>>bit&1]
    if int(mask)&1:terms.extend((1<<4,1<<5))
    return tuple(terms)


class LinearFlagSpace:
    """Own at most two computed flags and repay every replaced value exactly."""
    def __init__(self,builder,variables,terms,*,omit_repayment=False):
        self.builder=builder;self.variables=list(variables);self.terms=terms
        if len(self.variables)!=6 or len(set(self.variables))!=6:
            raise ValueError('Route flags require four distinct packed bits plus t and u.')
        self.wires=[];self.masks=[];self.products=0;self.measurements=0;self.transitions=[]
        self.omit_repayment=bool(omit_repayment)

    @property
    def space(self):
        if not self.masks:return ()
        if len(self.masks)==1:return (self.masks[0],)
        return tuple(sorted((self.masks[0],self.masks[1],self.masks[0]^self.masks[1])))

    def compute(self,mask):
        if len(self.wires)>=2:raise ValueError('The controller exceeded its two quantum flag slots.')
        target=self.builder.alloc_qubits(1)[0];terms=self.terms(mask)
        plan=xor_polynomial(self.builder,self.variables,target,terms)
        if len(plan.products)!=1:raise AssertionError('A route flag is not the promised one-product polynomial.')
        self.wires.append(target);self.masks.append(mask);self.products+=1

    def erase(self,index):
        wire=self.wires[index];terms=self.terms(self.masks[index])
        if self.omit_repayment:
            measured=self.builder.alloc_bits(1)[0];self.builder.hmr(wire,measured)
            self.builder.free(wire);self.builder.free(measured)
        else:_erase_polynomial(self.builder,wire,self.variables,terms)
        del self.wires[index];del self.masks[index];self.measurements+=1

    def move_to(self,space):
        space=tuple(sorted(map(int,space)))
        if (len(space) not in (1,3) or any(not 0<mask<8 for mask in space)
                or len(set(space))!=len(space) or (len(space)==3 and space[0]^space[1]!=space[2])):
            raise ValueError('The selected flag subspace has dimension one or two.')
        before=self.space
        if before==space:return
        common=set(before)&set(space)
        if not common:
            while self.wires:self.erase(len(self.wires)-1)
        else:
            if len(common)!=1:raise AssertionError('Unexpected distinct flag subspace intersection.')
            retained=next(iter(common))
            if len(self.wires)==2 and retained not in self.masks:
                self.builder.cx(self.wires[1],self.wires[0]);self.masks[0]^=self.masks[1]
            for index in reversed(range(len(self.wires))):
                if self.masks[index]!=retained:self.erase(index)
            if self.masks!=[retained]:raise AssertionError('The retained common flag was lost.')
        for mask in space:
            if self.space==space:break
            if mask not in self.space:self.compute(mask)
        if self.space!=space:raise AssertionError('The new flags do not span the requested subspace.')
        self.transitions.append(dict(old=list(before),new=list(space)))

    @contextmanager
    def control(self,mask):
        if mask in self.masks:yield self.wires[self.masks.index(mask)]
        elif len(self.masks)==2 and mask==self.masks[0]^self.masks[1]:
            self.builder.cx(self.wires[1],self.wires[0])
            try:yield self.wires[0]
            finally:self.builder.cx(self.wires[1],self.wires[0])
        else:raise ValueError('The selected control is outside the live flag space.')

    def close(self):
        while self.wires:self.erase(len(self.wires)-1)


def emit_route(builder,value,packed,u,candidate,*,kind,inverse=False,negative=None):
    """Complete one CRT factor, closing every route flag before returning."""
    if kind not in ('c4','c5'):raise ValueError('Only the declared C4 and C5 factors are supported.')
    _,math_search=mathematics();value=list(value)
    if len(value)!=20 or len(set(value))!=20:raise ValueError('The CRT word has twenty distinct bits.')
    operations=candidate['c4_network'] if kind=='c4' else candidate['c5_network']
    spaces=[(1,2,3)]*len(operations) if kind=='c4' else candidate['C5_flag_schedule']['chosen_subspaces']
    terms=math_search.routing_math.flag_terms if kind=='c4' else encoded_flag_terms
    steps=list(zip(operations,spaces))
    if inverse:steps.reverse()
    flags=LinearFlagSpace(builder,list(packed.residual[:4])+[packed.t,u],terms,
        omit_repayment=negative=='missing_route_repayment');swaps=0
    try:
        for operation,space in steps:
            flags.move_to(space)
            with flags.control(operation['control_mask']) as control:
                a,b=operation['swap']
                pairs=([((5*a+16*r)%20,(5*b+16*r)%20) for r in range(5)] if kind=='c4'
                    else [((5*p+16*a)%20,(5*p+16*b)%20) for p in range(4)])
                for left,right in pairs:
                    if not (negative=='missing_route_swap' and swaps==0):
                        builder.cswap(control,value[left],value[right])
                    swaps+=1
    finally:flags.close()
    expected=(20,2) if kind=='c4' else (28,4)
    if (swaps,flags.products)!=expected or flags.measurements!=flags.products:
        raise AssertionError('The native route differs from its complete factor/flag budget.')
    return dict(kind=kind,inverse=bool(inverse),cswaps=swaps,flag_products=flags.products,
        flag_measurements=flags.measurements,flag_transitions=flags.transitions)


@contextmanager
def encoded_threshold(builder,packed,u,threshold,plan,phase_pass,*,negative=None):
    if threshold==1:yield packed.t,0;return
    if threshold==2:yield u,0;return
    if int(plan['threshold'])!=threshold:raise ValueError('The encoded threshold plan has another logical owner.')
    q=list(packed.residual[:4]);helper=builder.alloc_qubits(1)[0]
    compiled=xor_polynomial(builder,q,helper,plan['terms'])
    if len(compiled.products)!=plan['quadratic_products']:
        raise AssertionError('The emitted encoded helper differs from its rank certificate.')
    control=builder.alloc_qubits(1)[0];builder.ccx(u,helper,control)
    if negative=='missing_threshold_helper_repayment':
        measured=builder.alloc_bits(1)[0];builder.hmr(helper,measured)
        builder.free(helper);builder.free(measured)
    else:_erase_polynomial(builder,helper,q,plan['terms'])
    try:yield control,len(compiled.products)+1
    finally:
        if negative=='missing_threshold_ledger':
            measured=builder.alloc_bits(1)[0];builder.hmr(control,measured)
            builder.free(control);builder.free(measured)
        else:
            phase_pass.ledger(packed).erase(builder,control,threshold)


def low_phase_reencoded(builder,value,packed,fractional_bits,*,turn_offsets,threshold,
                        beta=1,negative=None):
    """Same twenty base/eight overflow features through a temporary q encoding."""
    if negative not in (None,'missing_route_repayment','missing_route_swap',
            'missing_threshold_helper_repayment','missing_threshold_ledger','missing_encoding_Toffoli'):
        raise ValueError('Unknown deliberately incorrect component-proof control.')
    value=list(value);offsets=tuple(map(Fraction,turn_offsets));beta=Fraction(beta)
    if len(value)!=20 or fractional_bits!=37 or len(offsets)!=30 or packed.max_k!=10 or not packed.is_packed:
        raise ValueError('This experiment requires the selected packed word20/F37/k0..10/tail43 geometry.')
    if len(set(value+list(packed.residual)+[packed.t]))!=20+len(packed.residual)+1:
        raise ValueError('The phase data and packed residual variables must be distinct.')
    phase_pass=getattr(threshold,'__self__',None)
    if not isinstance(phase_pass,PackedThresholdPhasePass) or not phase_pass.merge_external_t:
        raise ValueError('Require the exact bound threshold owner with merged external-t repayment.')
    import packed_phase
    unpack=type(packed).unpack
    closure={name:cell.cell_contents for name,cell in zip(unpack.__code__.co_freevars,unpack.__closure__ or ())}
    if getattr(packed_phase._threshold,'__self__',None) is not phase_pass or closure.get('self') is not phase_pass:
        raise ValueError('The bound threshold owner must currently own the installed unpack repayment scope.')
    if packed._cached_u is not None:
        raise ValueError('The declared135-E kernel requires a fresh shared-u lifecycle, with no borrowed cached u.')
    candidate,certificate=synthesize();q=list(packed.residual[:4]);routes=[];angles=[]
    plans={int(plan['threshold']):plan for plan in candidate['threshold_plans']}
    threshold_products=0;encoding=[]
    with packed.higher_nonzero() as u:
        routes.append(emit_route(builder,value,packed,u,candidate,kind='c4',negative=negative))
        encoding.append(emit_encoding(builder,q,candidate['encode_program'],negative=negative=='missing_encoding_Toffoli'))
        routes.append(emit_route(builder,value,packed,u,candidate,kind='c5',negative=negative))
        for bit,wire in enumerate(value):
            angle=beta*_pow2(bit-fractional_bits+1)+2*offsets[bit]
            builder.z_pow(wire,angle);angles.append(angle)
        for bit in range(8):
            with encoded_threshold(builder,packed,u,bit+1,plans.get(bit+1),phase_pass,
                    negative=negative) as (control,cost):
                threshold_products+=cost;temporary=builder.alloc_qubits(1)[0]
                builder.ccx(control,value[bit],temporary)
                angle=beta*((1<<20)-1)*_pow2(bit-fractional_bits+1)+2*offsets[20+bit]
                builder.z_pow(temporary,angle);angles.append(angle)
                builder.del_and(control,value[bit],temporary);builder.free(temporary)
        routes.append(emit_route(builder,value,packed,u,candidate,kind='c5',inverse=True,negative=negative))
        encoding.append(emit_encoding(builder,q,candidate['encode_program'],inverse=True))
        routes.append(emit_route(builder,value,packed,u,candidate,kind='c4',inverse=True,negative=negative))
    swaps=sum(item['cswaps'] for item in routes)
    products=sum(item['flag_products'] for item in routes)+sum(item['Toffolis'] for item in encoding)+threshold_products+8+2
    if threshold_products!=11 or swaps!=96 or products!=39:
        raise AssertionError('The complete native low-phase construction differs from135 E.')
    return dict(width=20,max_k=10,reencoded_C20=True,cswaps=swaps,and_products=products,
        expected_toffolis=swaps+products,expected_extra_T=0,expected_generic_rotations=28,
        z_pow_calls=len(angles),half_turn_angles=list(map(str,angles)),turn_offsets=list(map(str,offsets)),
        skipped_overflow=[8,9],route_controllers=routes,encoding=encoding,
        threshold_compute_ANDs=threshold_products,encoded_thresholds_deferred=6,
        shared_u_and_external_t_ledger_contract_preserved=True,
        source_synthesis=certificate,negative_control=negative,
        complete_generator_and_official_verification_pending=True)
