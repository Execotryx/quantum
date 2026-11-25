# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""From-math coefficient lifecycle for compact curvature and stored-R17 designs.

The physical derivative table contains (B >> 1): its low10 bits and high7
bits. Initial logical B0 is either a specified curvature bit or a constant,
as certified by the mathematical profile. No static derivative LSB is
retained during the main product or its inverse.

All erased functions enter the same exact original-address phase ledger.
The module accepts mathematical coefficient dictionaries, never circuits.
"""
from __future__ import annotations
import kickmix as km
from codebook import Codebook,word_functions
from return_from_low import helper_plan,_place_address
from split_lookup import (_seed_monomials,live_word,desired_word,output_word,
                          unique_live)
from transition_codebook import (LiveFunction,convert_codebook,retire_table_bits,
                                 _word_table)


def stored_low_labels(data):
    """Logical bit labels of the stored low-word wires below the deferred top.

    The A-even consuming table stores no bit zero: its wires are L1..L18.
    Every static decoder keeps the original bit labels of its wires.
    """
    return list(range(1,19)) if data.get('consuming_odd_last_row') else list(range(19))


def table_words(data):
    rows=data['coefficients'];width=int(data['low_width'])
    c_shift=int(data.get('c_storage_shift',1))
    c_width=int(data.get('c_storage_width',10))
    if len(rows)!=256 or width!=20:
        raise ValueError('The R17 lifecycle expects256 rows and logical L20.')
    if (int(data.get('r_storage_shift',1))!=1 or
            int(data.get('r_storage_width',17))!=17 or not 1<=c_width<=10):
        raise ValueError('The R17 lifecycle requires one omitted derivative bit and at most ten curvature bits.')
    result={
        'low':[(int(row['low_constant'])+(1 << (width-1)))%(1 << width) for row in rows],
        'high':[int(row['high_anchor'])-1 for row in rows],
        'blo':[(int(row['b'])>>1)&1023 for row in rows],
        'bhi':[int(row['b'])>>11 for row in rows],
        'curvature':[int(row['c'])>>c_shift for row in rows],
    }
    if (any(not 0 <= value < 256 for value in result['high']) or
            any(not 0 <= value < 128 for value in result['bhi']) or
            any(not 0 <= value < 1 << c_width for value in result['curvature'])):
        raise ValueError('A coefficient exceeds the declared physical word width.')
    if any(int(row['c']) % (1 << c_shift) for row in rows):
        raise ValueError('The omitted curvature bits must be zero.')
    if data.get('consuming_odd_last_row') and any(value&1 for value in result['low']):
        raise ValueError('The consuming table requires an even low word.')
    parity_bit=data.get('kernel_parameters',{}).get('initial_derivative_lsb_from_curvature_bit')
    if parity_bit is None:
        expected=[int(data.get('known_derivative_lsb',0)) & 1]*len(rows)
    else:
        expected=[(int(row['c'])>>int(parity_bit))&1 for row in rows]
    if any((int(row['b'])&1)!=bit for row,bit in zip(rows,expected)):
        raise ValueError('Initial virtual B0 does not match its profile certificate.')
    return result


def _curvature_width(data):
    return int(data.get('c_storage_width',10))


def _low_live(low,values,low_bits=None):
    return live_word('low',low,values['low'],bit_indices=low_bits)


def _saved_live(values,saved_blo9,extra_saved_blo=None):
    items=live_word('saved9',[saved_blo9],[value>>9 for value in values['blo']])
    for bit,wire in sorted((extra_saved_blo or {}).items()):
        if not 0 <= int(bit) < 10:
            raise ValueError('Saved physical Blo indices must lie in0..9.')
        items+=live_word(f'saved{bit}_',[wire],[value>>int(bit) for value in values['blo']])
    return unique_live(items)


def initial_lookup(builder,data,address,debts,high_phase,*,deferred_low_bits=(),
                   decoder_trials=80,rank_rounds=0,basis_options=None,seed_factory=None):
    """Return physical coefficient words and explicit logical low-bit indices."""
    values=table_words(data)
    deferred=set(map(int,deferred_low_bits))
    if not deferred <= set(range(20)):
        raise ValueError('A deferred L bit lies outside0..19.')
    low_bits=[bit for bit in range(20) if bit not in deferred]
    seeds=(_seed_monomials(builder,address) if seed_factory is None
           else list(seed_factory(builder,address)))
    decoder_options=dict(basis_options or {})
    if seed_factory is not None:
        decoder_options['extra_subset_functions']=tuple(decoder_options.get('extra_subset_functions',()))+tuple(
            item.truth for item in seeds)
    source=live_word('address',address,range(256))+seeds
    produced,high_meta=convert_codebook(builder,source,[],desired_word('high',values['high'],8),debts,
        trials=decoder_trials,seed=20261901,preserving_rounds=rank_rounds,
        structured_subsets=True,**decoder_options)
    high=output_word(produced,'high',8)
    before_phase=builder.num_allocated_qubits
    high_phase(builder,high)
    if builder.num_allocated_qubits!=before_phase:
        raise ValueError('High phase did not return its temporary quantum workspace.')
    desired=[item for bit,item in enumerate(desired_word('low',values['low'],20))
             if bit not in deferred]
    desired+=desired_word('blo',values['blo'],10)
    desired+=desired_word('curvature',values['curvature'],_curvature_width(data))
    produced,conversion=convert_codebook(builder,[],source+live_word('high',high,values['high']),
        desired,debts,trials=decoder_trials,seed=20261902,preserving_rounds=rank_rounds,
        structured_subsets=True,**decoder_options)
    result={'low':km.array([produced[f'low{bit}'].wire for bit in low_bits]),
            'low_bits':low_bits,'blo':output_word(produced,'blo',10),
            'curvature':output_word(produced,'curvature',_curvature_width(data))}
    meta={'seed_ands':len(seeds),'high_decode':high_meta,'conversion':conversion,
          'and_count':len(seeds)+high_meta['and_count']+conversion['and_count'],
          'deferred_low_bits':sorted(deferred),'low_bits':low_bits,
          'qubits_at_high_phase':before_phase,'qubits_after':builder.num_allocated_qubits}
    return result,meta


def _materialize(builder,retained,desired,debts,*,decoder_trials,rank_rounds,
                 seed,basis_options=None):
    """Add just enough certified product helpers to cover requested functions."""
    retained=unique_live(retained)
    functions=[item.truth for item in retained]
    code=Codebook(functions)
    if all(code.span.solve(truth) is not None for _,truth in desired):
        helpers={'pairs':[],'and_count':0,'ranks':[{'variables':len(functions),
                 'quadratic_rank':len(code.span.pivots),'targets_covered':len(desired)}]}
    else:
        # Later outputs can reuse a measured helper after the first output
        # joins the code. Reserving every output in advance needlessly loses
        # a useful rank-generating helper at narrow widths.
        helpers=helper_plan(_word_table(functions),[truth for _,truth in desired],
            width=len(functions),maximum=builder.max_qubits-builder.num_allocated_qubits-bool(desired))
    consumed=[]
    for index,(i,j) in enumerate(helpers['pairs']):
        target=builder.alloc_qubits(1)[0]
        builder.ccx(retained[i].wire,retained[j].wire,target)
        consumed.append(LiveFunction(f'helper{index}',target,functions[i]&functions[j]))
    produced,conversion=convert_codebook(builder,retained,consumed,desired,debts,
        trials=decoder_trials,seed=seed,kernel_trials=15000,preserving_rounds=rank_rounds,
        structured_subsets=True,**(basis_options or {}))
    return produced,{'helpers':helpers,'conversion':conversion,
                     'and_count':helpers['and_count']+conversion['and_count'],
                     'qubits_after':builder.num_allocated_qubits}


def complete_low(builder,data,low,curvature,debts,*,low_bits,extra_saved_blo=None,
                 nearest_relation=False,decoder_trials=80,rank_rounds=0,
                 basis_options=None):
    """Complete static L after forward curvature and before its high correction."""
    values=table_words(data);indices=list(map(int,low_bits))
    if len(indices)!=len(low) or len(set(indices))!=len(indices):
        raise ValueError('A partial L word requires distinct logical indices.')
    missing=sorted(set(range(20))-set(indices))
    if not missing:
        return km.array(low),{'and_count':0,'restored_bits':[],
                              'qubits_after':builder.num_allocated_qubits}
    mapping=dict(zip(indices,low))
    if nearest_relation:
        if missing!=[19] or 18 not in mapping:
            raise ValueError('Nearest-anchor completion requires only missing L19.')
        if any(((value>>19)^(value>>18))&1 !=1 for value in values['low']):
            raise ValueError('The mathematical table does not certify L19 XOR L18 =1.')
        wire=builder.alloc_qubits(1)[0]
        builder.x(wire);builder.cx(mapping[18],wire)
        mapping[19]=wire
        meta={'and_count':0,'nearest_anchor_identity_checked':256,
              'qubits_after':builder.num_allocated_qubits}
    else:
        retained=_low_live(low,values,indices)+live_word('curvature',curvature,values['curvature'])
        for bit,wire in sorted((extra_saved_blo or {}).items()):
            retained+=live_word(f'saved{bit}_',[wire],[value>>int(bit) for value in values['blo']])
        desired=[item for bit,item in enumerate(desired_word('low',values['low'],20)) if bit in missing]
        produced,meta=_materialize(builder,retained,desired,debts,
            decoder_trials=decoder_trials,rank_rounds=rank_rounds,seed=20261903,
            basis_options=basis_options)
        mapping.update({bit:produced[f'low{bit}'].wire for bit in missing})
    meta['restored_bits']=missing
    return km.array([mapping[bit] for bit in range(20)]),meta


def curvature_to_high(builder,data,curvature,low,saved_blo9,debts,*,
                      low_bits=None,extra_saved_blo=None,decoder_trials=80,
                      rank_rounds=0,basis_options=None):
    values=table_words(data)
    retained=_low_live(low,values,low_bits)+_saved_live(values,saved_blo9,extra_saved_blo)
    produced,meta=convert_codebook(builder,unique_live(retained),
        live_word('curvature',curvature,values['curvature']),desired_word('bhi',values['bhi'],7),
        debts,trials=decoder_trials,seed=20261904,kernel_trials=15000,
        preserving_rounds=rank_rounds,**(basis_options or {}))
    return output_word(produced,'bhi',7),meta


def restore_saved_blo_bits(builder,data,low,debts,*,bits=(4,9),low_bits=None,
                           decoder_trials=80,rank_rounds=0,basis_options=None):
    positions=list(map(int,bits))
    if len(set(positions))!=len(positions) or any(not 0<=bit<10 for bit in positions):
        raise ValueError('Saved physical Blo indices must be distinct and lie in0..9.')
    values=table_words(data);functions=word_functions(values['blo'],10)
    desired=[(f'saved{bit}',functions[bit]) for bit in positions]
    produced,meta=_materialize(builder,_low_live(low,values,low_bits),desired,debts,
        decoder_trials=decoder_trials,rank_rounds=rank_rounds,seed=20261905,
        basis_options=basis_options)
    meta['physical_blo_bits']=positions
    return {bit:produced[f'saved{bit}'].wire for bit in positions},meta


def high_to_curvature(builder,data,high,low,saved_blo9,debts,*,
                      low_bits=None,extra_saved_blo=None,decoder_trials=80,
                      rank_rounds=0,basis_options=None):
    values=table_words(data)
    retained=_low_live(low,values,low_bits)+_saved_live(values,saved_blo9,extra_saved_blo)
    produced,meta=convert_codebook(builder,unique_live(retained),live_word('bhi',high,values['bhi']),
        desired_word('curvature',values['curvature'],_curvature_width(data)),debts,trials=decoder_trials,
        seed=20261906,kernel_trials=15000,preserving_rounds=rank_rounds,**(basis_options or {}))
    return output_word(produced,'curvature',_curvature_width(data)),meta


def retire_low_bits(builder,data,low,debts,*,count=6,remove=None,bit_indices=None):
    return retire_table_bits(builder,table_words(data)['low'],low,debts,
        count=count,remove=remove,bit_indices=bit_indices)


def restore_address(builder,data,low,blo,curvature,debts,*,low_bits=None,
                    address_destination=None,preserved=None,decoder_trials=80,
                    rank_rounds=0,basis_options=None):
    values=table_words(data)
    consumed=_low_live(low,values,low_bits)+live_word('blo',blo,values['blo'])
    consumed+=live_word('curvature',curvature,values['curvature'])
    produced,meta=convert_codebook(builder,[],unique_live(consumed),
        desired_word('address',range(256),8),debts,trials=decoder_trials,seed=20261907,
        preserving_rounds=rank_rounds,**(basis_options or {}))
    address=output_word(produced,'address',8)
    returned={'address':address,**(preserved or {})}
    if address_destination is not None:
        returned=_place_address(builder,address,address_destination,[],preserved or {})
        returned.pop('curvature')
    return {name:km.array(wires) for name,wires in returned.items()},meta
