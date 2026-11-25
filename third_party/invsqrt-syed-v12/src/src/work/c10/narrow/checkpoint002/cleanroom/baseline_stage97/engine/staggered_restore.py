# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Decode a late curvature-boundary bit together with the curvature word.

The first boundary is needed by the high correction; the inner boundary is
needed only after the high word has been consumed.  Moving that second decode
past the high correction frees one carry qubit without changing arithmetic.
All synthesis inputs are mathematical coefficient truth tables.
"""
from codebook import word_functions
from r17_lookup import table_words, _low_live, _saved_live, _curvature_width
from split_lookup import live_word,desired_word,output_word,unique_live
from transition_codebook import convert_codebook


def high_to_curvature_and_inner(builder,data,high,low,saved_outer,debts,*,
                                decoder_trials=80,rank_rounds=0,inner_bit=4):
    values=table_words(data)
    retained=unique_live(_low_live(low,values)+_saved_live(values,saved_outer))
    desired=desired_word('curvature',values['curvature'],_curvature_width(data))
    desired.append(('inner_boundary',word_functions(values['blo'],10)[inner_bit]))
    produced,meta=convert_codebook(builder,retained,
        live_word('bhi',high,values['bhi']),desired,debts,
        trials=decoder_trials,seed=20261906,kernel_trials=15000,
        preserving_rounds=rank_rounds,preserve_future=True)
    return (output_word(produced,'curvature',_curvature_width(data)),
            produced['inner_boundary'].wire,meta)
