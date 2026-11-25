# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Final raw-address recovery with reusable product factors."""
import kickmix as km
from r17_lookup import table_words,_low_live
from split_lookup import live_word,desired_word,output_word,unique_live
from return_from_low import _place_address
from retained_products import convert_retained_products


def restore_address_retained(builder,data,low,blo,curvature,debts,*,low_bits=None,
        address_destination=None,preserved=None,decoder_trials=80,rank_rounds=0,
        basis_options=None,retained_helpers=None,direction_limit=4):
    if rank_rounds:raise ValueError('The retained-address pass uses its own deterministic rank search.')
    values=table_words(data)
    consumed=unique_live(_low_live(low,values,low_bits)+live_word('blo',blo,values['blo'])+
        live_word('curvature',curvature,values['curvature']))
    produced,meta=convert_retained_products(builder,consumed,
        desired_word('address',range(256),8),debts,trials=decoder_trials,seed=2026110617,
        direction_limit=direction_limit,structured_functions=tuple(x.truth for x in consumed),
        basis_trials=256,retained_helpers=retained_helpers)
    address=output_word(produced,'address',8)
    returned={'address':address,**(preserved or {})}
    if address_destination is not None:
        returned=_place_address(builder,address,address_destination,[],preserved or {})
        returned.pop('curvature')
    return {name:km.array(wires) for name,wires in returned.items()},meta
