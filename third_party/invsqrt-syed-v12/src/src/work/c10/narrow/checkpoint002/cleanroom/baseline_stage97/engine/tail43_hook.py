# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Early high-phase hook for the certified43-rotation finite-tail pass.

All sparse functions are synthesized from the mathematical coefficient table.
The existing4+4 monomial seed bank and high coefficient are restored exactly.
No new table bit or persistent quantum allocation is introduced.
"""
from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction

import numpy as np
import merged_phase
from affine_labels import emit_address_frame
from affine_table_layout import original_address_seed_factory
from balanced_model import balanced_state
from codebook import BinarySpan,word_functions,parity_function
from split_lookup import _seed_monomials
from rare_phase_pass import zero_residual_words,_require_geometry
from controlled_table_delta import compile_delta,apply_delta
from high_increment import make_threshold,erase_threshold


def _original_seed_truths():
    address=word_functions(range(256),8)
    result=[]
    for start in (0,4):
        for mask in range(1,16):
            if mask.bit_count()<2:continue
            truth=(1 << 256)-1
            for bit in range(4):
                if mask >> bit&1:truth&=address[start+bit]
            result.append(truth)
    return result


def _affine_care_mask(values,care,functions):
    cm=sum(1 << a for a in care)
    wanted=sum(int(values[a]) << a for a in care)
    span=BinarySpan([cm]+[f&cm for f in functions])
    answer=span.solve(wanted)
    if answer is None:raise ValueError('The sparse tail is not affine in the raw address.')
    best=None
    for assignment in range(1 << len(span.nullspace)):
        candidate=answer
        for bit,relation in enumerate(span.nullspace):
            if assignment >> bit&1:candidate^=relation
        # A nonzero linear part supplies an existing physical pivot.
        if not candidate>>1:continue
        key=((candidate>>1).bit_count(),int(candidate&1),candidate)
        if best is None or key<best[0]:best=(key,candidate)
    if best is None:raise ValueError('The sparse tail needs a literal constant wire.')
    mask=best[1]
    actual=(cm if mask&1 else 0)^(parity_function(mask>>1,functions)&cm)
    if actual!=wanted:raise AssertionError('The affine sparse-tail certificate failed.')
    return mask


@contextmanager
def borrow_affine(builder,wires,mask):
    """Temporarily expose an affine bit on its highest existing input wire."""
    selected=[i for i in range(len(wires)) if mask >> (i+1)&1]
    if not selected:raise ValueError('A borrowed affine bit needs a physical linear pivot.')
    pivot=wires[selected[-1]]
    for i in selected[:-1]:builder.cx(wires[i],pivot)
    if mask&1:builder.x(pivot)
    try:yield pivot
    finally:
        if mask&1:builder.x(pivot)
        for i in reversed(selected[:-1]):builder.cx(wires[i],pivot)


class Tail43HighPhaseHook:
    """Bind to the existing initial_lookup callback and seed-factory APIs.

    ``model`` is the original mathematical address order, before
    prepare_lookup_view. ``address`` contains the current physical framed
    address. Supply the same frame returned by prepare_lookup_view.

        phase_pass = PackedThresholdPhasePass()
        hook = Tail43HighPhaseHook(model, angles, packed, address, frame,
                                  phase_pass=phase_pass)
        with phase_pass.install():
            initial_lookup(..., high_phase=hook,
                           seed_factory=hook.seed_factory())
            ...
            packed.unpack()  # repays all threshold phases

    A surrounding region wrapper may call ``hook(builder, high)`` and retain
    its returned metadata. It must preserve the captured seed allocations
    until that callback. The hook restores both affine address frames.
    """
    def __init__(self,model,angles,packed,address,address_frame,*,phase_pass):
        if model.get('lookup_view_only'):
            raise ValueError('The hook requires the original mathematical table order.')
        _require_geometry(model,angles)
        if (angles.get('rare_phase_pass')!='zero-residual-tail-from-8-v1' or
                angles.get('high_mode')!='complement' or angles.get('high_width')!=8 or
                angles.get('high_fraction_bits')!=18 or angles.get('status')!='PASS'):
            raise ValueError('The high hook requires the certified43-tail angle geometry.')
        self.packed=packed;self.address=list(address);self.frame=address_frame
        self.phase_pass=phase_pass;self.seeds=None;self.last_metadata=None
        if len(self.address)!=8:raise ValueError('The mathematical coefficient address has8 bits.')
        words=zero_residual_words(model)
        care9=sorted(set(map(int,balanced_state(np.arange(1,16,dtype=np.int64),model)['address'])))
        care10=sorted(set(map(int,balanced_state(np.arange(1,4,dtype=np.int64),model)['address'])))
        address_functions=word_functions(range(256),8)
        self.seed_truths=_original_seed_truths()
        self.functions=address_functions+self.seed_truths
        self.delta=compile_delta([row['high'] for row in words],
            [(row['output_unsigned']>>19)&1 for row in words],care9,self.functions)
        self.tail_mask=_affine_care_mask([(row['output_unsigned']>>18)&1 for row in words],
            care10,address_functions)
        self.certificate=dict(delta_care_addresses=care9,tail_care_addresses=care10,
            delta_masks=list(self.delta.masks),tail18_affine_mask=self.tail_mask,
            delta_ands_each=self.delta.and_count,new_table_wires=0,
            original_bank_functions=len(self.functions))
        offsets=[Fraction(0)]*18
        for row in angles['features']:
            if row['kind']=='high_complement_base':index=row['bit']
            elif row['kind']=='high_complement_overflow':index=8+row['bit']
            else:continue
            offsets[index]=Fraction(row['nudge_turn_numerator'],angles['turn_denominator'])
        self.offsets=tuple(offsets)

    def bind_seeds(self,items):
        items=list(items)
        if len(items)!=22:raise ValueError('This hook expects the existing22 monomial helpers.')
        permutation=([self.frame.transform(a) for a in range(256)]
                     if self.frame is not None else list(range(256)))
        for item,truth in zip(items,self.seed_truths):
            original=sum(((int(item.truth)>>permutation[a])&1) << a for a in range(256))
            if original!=truth:
                raise ValueError('The captured seed ordering or affine truth frame is inconsistent.')
        self.seeds=items
        return items

    def seed_factory(self,factory=None):
        """Wrap the existing factory; its numerical table conversion is unchanged."""
        if factory is None:factory=original_address_seed_factory(self.frame) or _seed_monomials
        def capture(builder,address):
            if list(address)!=self.address:raise ValueError('The initializer changed the bound address wires.')
            return self.bind_seeds(factory(builder,address))
        return capture

    def __call__(self,builder,high):
        high=list(high)
        if self.seeds is None:raise ValueError('Capture the initializer seed bank before the phase callback.')
        if len(high)!=8:raise ValueError('The high phase requires the existing8-bit word.')
        variables=self.address+[item.wire for item in self.seeds]
        if self.frame is not None:emit_address_frame(builder,self.address,self.frame,inverse=True)
        try:
            with self.packed.higher_nonzero() as u:
                threshold=make_threshold(builder,self.packed,9,u=u)
                apply_delta(builder,high,threshold.control,variables,self.delta)
                with borrow_affine(builder,self.address,self.tail_mask) as tail18:
                    with self.phase_pass.reuse_threshold(self.packed,9,threshold.control):
                        old_threshold=merged_phase._threshold
                        merged_phase._threshold=self.phase_pass.threshold
                        try:
                            phase=merged_phase.merged_packed_cyclic_scale_phase(
                                builder,high,self.packed,18,turn_offsets=self.offsets,
                                complement_overflow=True,tail_bits={18:tail18},tail_first_removed=8)
                        finally:merged_phase._threshold=old_threshold
                apply_delta(builder,high,threshold.control,variables,self.delta)
                erase_threshold(builder,threshold,u=u,ledger=self.phase_pass.ledger(self.packed))
        finally:
            if self.frame is not None:emit_address_frame(builder,self.address,self.frame)
        extra_ands=2*self.delta.and_count+2
        self.last_metadata=dict(phase,tail43_hook=True,certificate=self.certificate,
            and_products=phase['and_products']+extra_ands,
            expected_toffolis=phase['expected_toffolis']+extra_ands,
            hook_extra_ands=extra_ands,
            shared_u_setup_ands=2,threshold_phases_deferred=True,
            static_bank_restored=True,affine_address_frame_restored=True)
        return self.last_metadata
