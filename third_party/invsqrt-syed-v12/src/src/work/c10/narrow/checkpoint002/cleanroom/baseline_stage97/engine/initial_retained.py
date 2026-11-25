# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""A2/R17/C8 initial lookup using one retained product per decoded bit."""
import kickmix as km
from codebook import word_functions
from r17_lookup import table_words,stored_low_labels
from split_lookup import live_word,desired_word,output_word,_seed_monomials
from transition_codebook import convert_codebook,LiveFunction
from retained_products import convert_retained_products


def initial_retained(builder,data,address,debts,high_phase,*,deferred_low_bits=(19,),
                     decoder_trials=80,rank_rounds=0,basis_options=None,seed_factory=None,
                     retained_helpers=1,direction_limit=4,high_decoder=None):
    if tuple(deferred_low_bits)!=(19,) or int(data['c_storage_width'])!=8:
        raise ValueError('This selected initializer expects omitted L19 and an eight-bit curvature word.')
    if rank_rounds:
        raise ValueError('The selected deterministic product-retention schedule uses zero kernel-search rounds.')
    values=table_words(data)
    seeds=(_seed_monomials(builder,address) if seed_factory is None else list(seed_factory(builder,address)))
    source=live_word('address',address,range(256))+seeds
    structured=tuple(item.truth for item in source)
    options=dict(basis_options or {})
    options.setdefault('basis_search_products',3)
    options.setdefault('basis_natural_limit',256)
    options.setdefault('basis_random_trials',256)
    options.setdefault('basis_random_max_products',5)
    options.setdefault('preserve_future',True)
    options['extra_subset_functions']=tuple(options.get('extra_subset_functions',()))+tuple(x.truth for x in seeds)
    convert_high=convert_codebook if high_decoder is None else high_decoder
    produced,high_meta=convert_high(builder,source,[],desired_word('high',values['high'],8),
        debts,trials=decoder_trials,seed=20261901,preserving_rounds=0,structured_subsets=True,**options)
    high=output_word(produced,'high',8);before=builder.num_allocated_qubits
    high_completion=high_phase(builder,high)
    from high_ownership import assert_high_callback_transition
    assert_high_callback_transition(builder,before,high_completion)
    reloaded=dict(getattr(high_completion,'reloaded_seeds',None) or {})
    if reloaded:
        # A seed recycled around the callback returns on a new wire with its
        # original name, truth and bank position.
        if not set(reloaded)<={item.name for item in seeds}:
            raise AssertionError('A reloaded coordinate is not an original seed.')
        source=[LiveFunction(item.name,reloaded[item.name],item.truth) if item.name in reloaded else item
                for item in source]
        if len({item.wire for item in source})!=len(source):
            raise AssertionError('A reloaded seed aliases another static coordinate.')
    high_items=live_word('high',high,values['high'])
    from high_ownership import consume_high_callback_result
    kept_high,release_audit=consume_high_callback_result(builder,high_items,debts,high_completion)
    if release_audit is not None and len(source+kept_high)!=31:
        raise AssertionError('Early-H retirement must hand 31 coordinates to conversion.')
    # Output names carry the logical bit labels: the A-even consuming table
    # has no stored bit zero, so its low outputs are low1..low18.
    labels=stored_low_labels(data)
    low_functions=word_functions(values['low'],19)
    if data.get('consuming_odd_last_row') and low_functions[0]:
        raise AssertionError('The omitted low bit zero is not identically zero.')
    low_names=[f'low{bit}' for bit in labels]
    desired=[(f'low{bit}',low_functions[bit]) for bit in labels]
    desired+=desired_word('blo',values['blo'],10)
    desired+=desired_word('curvature',values['curvature'],8)
    produced,conversion=convert_retained_products(builder,
        source+kept_high,desired,debts,
        trials=decoder_trials,seed=2026110609,direction_limit=direction_limit,
        structured_functions=structured,basis_trials=256,retained_helpers=retained_helpers)
    result={'low':km.array([produced[name].wire for name in low_names]),'low_bits':list(labels),
            'blo':output_word(produced,'blo',10),'curvature':output_word(produced,'curvature',8)}
    for coefficient_bit,address_bit in data.get('shared_L',{}).items():
        if produced[f'low{int(coefficient_bit)}'].wire!=address[int(address_bit)]:
            raise AssertionError('An exact A2 coefficient/address alias lost its physical wire identity.')
    for coefficient_bit,address_bit in data.get('shared_C_from_address',{}).items():
        if result['curvature'][int(coefficient_bit)]!=address[int(address_bit)]:
            raise AssertionError('An exact curvature/address alias lost its physical wire identity.')
    metadata={'and_count':len(seeds)+high_meta['and_count']+conversion['and_count'],
                  'seed_ands':len(seeds),'high_decode':high_meta,'conversion':conversion,
                  'qubits_at_high_phase':before,'qubits_after':builder.num_allocated_qubits,
                  'deferred_low_bits':[19],'low_bits':list(labels),
                  'retained_products_per_decoder':retained_helpers,
                  'reloaded_seeds':sorted(reloaded)}
    if release_audit is not None:
        metadata['early_high_zero_release']=release_audit
    return result,metadata
