# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Preserve the exact redundant-top omission through coefficient transitions.

The nearest-anchor mathematical certificate gives L19=1 XORL18. Keeping both
physical wires during lookup adds no information and restricts workspace. The
interfaces below accept the numeric L[0:19] word; arithmetic reconstructs its
top only when its global product snapshot becomes necessary.
"""
from codebook import word_functions
from r17_lookup import table_words,_low_live,_saved_live,restore_saved_blo_bits
from split_lookup import live_word,desired_word,output_word,unique_live
from transition_codebook import convert_codebook


def require_relation(data,low):
    values=table_words(data)
    if len(low)!=19 or any(((v >> 19)^(v >> 18))&1 != 1 for v in values['low']):
        raise ValueError('The omitted physical top needs the certified nearest-anchor relation.')
    return values


def forward_high(builder,data,curvature,low,saved_outer,debts,*,saved_inner,
                 decoder_trials=80,rank_rounds=0):
    values=require_relation(data,low)
    retained=unique_live(_low_live(low,values,range(19))+
                         _saved_live(values,saved_outer,{4:saved_inner}))
    produced,meta=convert_codebook(builder,retained,
        live_word('curvature',curvature,values['curvature']),
        desired_word('bhi',values['bhi'],7),debts,trials=decoder_trials,
        seed=20261904,kernel_trials=15000,preserving_rounds=rank_rounds)
    return output_word(produced,'bhi',7),meta


def restore_outer(builder,data,low,debts,*,decoder_trials=80,rank_rounds=0):
    require_relation(data,low)
    return restore_saved_blo_bits(builder,data,low,debts,bits=(9,),low_bits=range(19),
        decoder_trials=decoder_trials,rank_rounds=rank_rounds)


def return_curvature(builder,data,high,low,saved_outer,debts,*,decoder_trials=80,
                     rank_rounds=0,low_bits=None,helpers=()):
    values=table_words(data)
    indices=list(range(19)) if low_bits is None else list(low_bits)
    retained=unique_live(_low_live(low,values,indices)+_saved_live(values,saved_outer))
    desired=desired_word('curvature',values['curvature'],8)
    desired.append(('inner_boundary',word_functions(values['blo'],10)[4]))
    produced,meta=convert_codebook(builder,retained,
        live_word('bhi',high,values['bhi'])+list(helpers),desired,debts,
        trials=decoder_trials,seed=20261906,kernel_trials=15000,
        preserving_rounds=rank_rounds,preserve_future=True)
    return output_word(produced,'curvature',8),produced['inner_boundary'].wire,meta
