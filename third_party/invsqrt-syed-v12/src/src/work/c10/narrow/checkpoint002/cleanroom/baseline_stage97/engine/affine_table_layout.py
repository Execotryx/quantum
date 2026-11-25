# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Reindex fitted tables into a proved Clifford address frame.

The numerical model remains indexed by its original mantissa segments.
This separate compiler view changes only the physical lookup convention.
The low coefficient bits become literal address wires when the fitter's
allowed-residue certificate supplies the declared affine aliases.
"""
from __future__ import annotations
from affine_labels import _make_plan,permute_table,emit_address_frame
from split_lookup import _seed_monomials
from transition_codebook import LiveFunction


def prepare_lookup_view(model):
    rows=model.get('address_affine_rows')
    if rows is None:return model,None
    low_aliases={int(bit):int(address_bit) for bit,address_bit in model.get('shared_L',{}).items()}
    curvature_aliases={int(bit):int(address_bit)
                       for bit,address_bit in model.get('shared_C_from_address',{}).items()}
    labels=list(low_aliases.values())+list(curvature_aliases.values())
    # A refitted table may keep the original frame while using only part of
    # its alias prefix; the frame's own prefix length is then declared.
    count=int(model.get('address_frame_alias_bits',len(labels)))
    if (len(set(labels))!=len(labels) or not set(labels)<=set(range(count)) or not 1<=count<=3
            or (len(labels)!=count and 'address_frame_alias_bits' not in model)):
        raise ValueError('Distinct coefficient aliases must lie in the frame prefix of the physical address.')
    rows=list(map(int,rows))
    if len(rows)!=8:raise ValueError('The mantissa lookup requires an invertible eight-bit frame.')
    plan=_make_plan(rows[:count],8,count,0)
    if list(plan.rows)!=rows:
        raise ValueError('The supplied full address frame differs from its deterministic completion.')
    original=list(model['coefficients'])
    if len(original)!=256:raise ValueError('The affine table view requires256 original segments.')
    view=dict(model)
    view['coefficients']=permute_table(original,plan)
    for key,value in model.items():
        if key.startswith('physical_table_words') and isinstance(value,list):
            view[key]=permute_table(value,plan)
    for physical,row in enumerate(view['coefficients']):
        low=(int(row['low_constant'])+(1 << (int(model['low_width'])-1)))%(1 << int(model['low_width']))
        curvature=int(row['c'])>>int(model['c_storage_shift'])
        if any(((low>>bit)^(physical>>address_bit))&1 for bit,address_bit in low_aliases.items()):
            raise ValueError('A fitted low coefficient does not satisfy its declared address alias.')
        if any(((curvature>>bit)^(physical>>address_bit))&1
               for bit,address_bit in curvature_aliases.items()):
            raise ValueError('A fitted curvature coefficient does not satisfy its declared address alias.')
    view['lookup_view_only']=True
    view['physical_address_alias_bits']=count
    return view,plan


def begin_lookup_frame(builder,address,plan):
    if plan is not None:emit_address_frame(builder,address,plan)


def finish_lookup_frame(builder,address,plan):
    """Use only after all framed-address phase debts have been repaid."""
    if plan is not None:emit_address_frame(builder,address,plan,inverse=True)


def original_address_seed_factory(plan):
    """Preserve the mathematical4+4 seed basis under an affine address map."""
    if plan is None:return None
    permutation=[plan.transform(address) for address in range(256)]
    def build(builder,address):
        emit_address_frame(builder,address,plan,inverse=True)
        original=_seed_monomials(builder,address)
        emit_address_frame(builder,address,plan)
        return [LiveFunction(item.name,item.wire,
                  sum(((item.truth>>old)&1)<<new for old,new in enumerate(permutation)))
                for item in original]
    return build
