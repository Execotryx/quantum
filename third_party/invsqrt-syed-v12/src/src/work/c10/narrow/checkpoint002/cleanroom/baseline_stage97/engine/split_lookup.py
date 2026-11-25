# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Static-L coefficient scheduling for the full-R split curvature kernel.

All synthesis inputs are mathematical coefficient values.  The address may be
measured while its information remains in the untouched L0 codeword.  Phases
from every measured table function are retained in one logical-address ledger.
"""
from __future__ import annotations

import kickmix as km
from codebook import Codebook, emit_xor, word_functions
from fusion.lookup import load_table
from return_from_low import helper_plan, _place_address
from transition_codebook import LiveFunction, convert_codebook, retire_table_bits


def table_words(data):
    rows = data['coefficients']
    low_width = int(data['low_width'])
    return {
        'low': [(int(row['low_constant']) + (1 << (low_width-1))) % (1 << low_width) for row in rows],
        'high': [int(row['high_anchor'])-1 for row in rows],
        'blo': [int(row['b']) % (1 << 11) for row in rows],
        'bhi': [int(row['b']) >> 11 for row in rows],
        'curvature': [int(row['c']) >> int(data['c_storage_shift']) for row in rows],
    }


def live_word(name, wires, values, *, bit_indices=None):
    indices = list(range(len(wires))) if bit_indices is None else list(bit_indices)
    if len(indices) != len(wires):
        raise ValueError('Wrong partial-word index count.')
    functions = word_functions(values,max(indices,default=-1)+1)
    return [LiveFunction(f'{name}{bit}',wire,functions[bit]) for bit,wire in zip(indices,wires)]


def desired_word(name, values, width):
    return [(f'{name}{i}', function) for i, function in enumerate(word_functions(values, width))]


def output_word(produced, name, width):
    return km.array([produced[f'{name}{i}'].wire for i in range(width)])


def unique_live(items):
    """Coalesce explicit physical aliases, checking their complete truths."""
    out=[]
    by_wire={}
    for item in items:
        previous=by_wire.get(item.wire)
        if previous is not None:
            if previous.truth!=item.truth:
                raise ValueError('A shared physical wire has conflicting table functions.')
            continue
        by_wire[item.wire]=item
        out.append(item)
    return out


def _seed_monomials(builder, address, groups=(tuple(range(4)), tuple(range(4, 8)))):
    af = word_functions(range(256), 8)
    helpers = []
    for group in groups:
        wires = {1 << j: address[bit] for j, bit in enumerate(group)}
        truths = {1 << j: af[bit] for j, bit in enumerate(group)}
        for mask in range(1, 1 << len(group)):
            if mask.bit_count() < 2:
                continue
            last = mask.bit_length()-1
            parent = mask ^ (1 << last)
            target = builder.alloc_qubits(1)[0]
            builder.ccx(wires[parent], address[group[last]], target)
            wires[mask] = target
            truths[mask] = truths[parent] & af[group[last]]
            helpers.append(LiveFunction(f'seed{group[0]}_{mask}', target, truths[mask]))
    return helpers


def initial_split_lookup(builder, data, address, phase_debts, high_phase,
                         *, seed_basis=True, initial_blo_bits=3,
                         decoder_trials=400, rank_rounds=0):
    """Load L20/Blo11 with a temporary H8 phase word at peak<=62.

    The first31 outputs use either a from-ANF load or a 22-AND 4+4 monomial
    codebook followed by bounded conversion.  After H's phase, its retained
    bits help decode the last8 Blo bits before H is measured and released.
    """
    if len(address) != 8 or not 0 <= initial_blo_bits <= 11:
        raise ValueError('Expected an 8-bit address and a valid Blo prefix.')
    values = table_words(data)
    desired = desired_word('high', values['high'], 8)
    desired += desired_word('low', values['low'], 20)
    desired += desired_word('blo', values['blo'], initial_blo_bits)
    address_live = live_word('address', address, range(256))
    if seed_basis:
        seeds = _seed_monomials(builder, address)
        produced, first = convert_codebook(builder, address_live, seeds, desired, phase_debts,
                                           trials=decoder_trials, seed=20261105,
                                           preserving_rounds=rank_rounds)
        first = {'seed_ands': len(seeds), 'conversion': first,
                 'and_count': len(seeds)+first['and_count']}
        high = output_word(produced, 'high', 8)
        low = output_word(produced, 'low', 20)
        blo_prefix = output_word(produced, 'blo', initial_blo_bits)
    else:
        high, low, blo_prefix = (builder.alloc_qubits(n) for n in (8, 20, initial_blo_bits))
        table = [h | (l << 8) | ((s & ((1 << initial_blo_bits)-1)) << 28)
                 for h, l, s in zip(values['high'], values['low'], values['blo'])]
        first = load_table(builder, table, address, km.array([*high, *low, *blo_prefix]))
    before_phase = builder.num_allocated_qubits
    high_phase(builder, high)
    if builder.num_allocated_qubits != before_phase:
        raise ValueError('High phase must restore its temporary allocation.')
    retained = address_live + live_word('low', low, values['low'])
    retained += live_word('blo', blo_prefix, values['blo'])
    hf = live_word('high', high, values['high'])
    tail = desired_word('blo', values['blo'], 11)[initial_blo_bits:]
    produced, second = convert_codebook(builder, retained, hf, tail, phase_debts,
                                        trials=decoder_trials, seed=20261106,
                                        preserving_rounds=rank_rounds)
    blo = km.array([*blo_prefix, *(produced[f'blo{i}'].wire for i in range(initial_blo_bits, 11))])
    return low, blo, {'initial': first, 'deferred_blo': second,
                       'and_count': first['and_count']+second['and_count'],
                       'qubits_at_high_phase': before_phase,
                       'qubits_after': builder.num_allocated_qubits}


def initial_split_with_curvature(builder, data, address, phase_debts, high_phase,
                                  *, decoder_trials=400, rank_rounds=0,
                                  groups=(tuple(range(4)), tuple(range(4, 8))),
                                  share_low_blo0=False,basis_options=None):
    """Fuse all initial coefficient materialization around the high phase.

    H8 is first decoded while22 monomial seeds and the address remain live.
    The phase therefore starts with53 wires in the packed-normalization
    setting.  Afterwards the entire static code is consumed into L20/Blo11/C9,
    so neither H nor address must coexist with the final coefficient words.
    """
    values = table_words(data)
    low_width = int(data['low_width'])
    seeds = _seed_monomials(builder, address, groups=groups)
    retained = live_word('address', address, range(256))+seeds
    produced, high_meta = convert_codebook(builder, retained, [],
                                            desired_word('high', values['high'], 8),
                                            phase_debts, trials=decoder_trials,
                                            seed=20261201, preserving_rounds=rank_rounds,
                                            structured_subsets=True,**(basis_options or {}))
    high = output_word(produced, 'high', 8)
    before_phase = builder.num_allocated_qubits
    high_phase(builder, high)
    if builder.num_allocated_qubits != before_phase:
        raise ValueError('High phase must restore its temporary allocation.')
    consumed = retained+live_word('high', high, values['high'])
    desired = desired_word('low', values['low'], low_width)
    if share_low_blo0:
        if any((l^b)&1 for l,b in zip(values['low'],values['blo'])):
            raise ValueError('Requested L0/Blo0 physical alias is not a table identity.')
        desired=desired[1:]
    desired += desired_word('blo', values['blo'], 11)
    desired += desired_word('curvature', values['curvature'], 9)
    produced, conversion = convert_codebook(builder, [], consumed, desired, phase_debts,
                                             trials=decoder_trials, seed=20261202,
                                             preserving_rounds=rank_rounds,
                                             structured_subsets=True,**(basis_options or {}))
    if share_low_blo0:
        produced['low0']=LiveFunction('low0',produced['blo0'].wire,produced['blo0'].truth)
    meta = {'seed_ands': len(seeds), 'high_decode': high_meta, 'conversion': conversion,
            'and_count': len(seeds)+high_meta['and_count']+conversion['and_count'],
            'qubits_at_high_phase': before_phase,
            'qubits_after': builder.num_allocated_qubits,
            'shared_low_blo0':bool(share_low_blo0)}
    # convert_codebook transfers ownership when a requested function is an
    # existing address bit.  Numerical aliases therefore use the SAME wire,
    # with no copy and no extra allocation.
    aliases=[]
    for name,width in (('low',low_width),('blo',11),('curvature',9)):
        for bit in range(width):
            wire=produced[f'{name}{bit}'].wire
            for address_bit,address_wire in enumerate(address):
                if (wire==address_wire and all(((value>>bit)&1)==((index>>address_bit)&1)
                                              for index,value in enumerate(values[name]))):
                    aliases.append({'word':name,'bit':bit,'address_bit':address_bit})
    meta['physical_aliases'] = aliases
    return (output_word(produced, 'low', low_width), output_word(produced, 'blo', 11),
            output_word(produced, 'curvature', 9), meta)


def address_to_curvature(builder, data, address, low, blo, phase_debts,
                         *, decoder_trials=400, rank_rounds=0):
    values = table_words(data)
    retained = live_word('low', low, values['low'])+live_word('blo', blo, values['blo'])
    consumed = live_word('address', address, range(256))
    desired = desired_word('curvature', values['curvature'], 9)
    produced, meta = convert_codebook(builder, retained, consumed, desired, phase_debts,
                                      trials=decoder_trials, seed=20261107,
                                      preserving_rounds=rank_rounds)
    return output_word(produced, 'curvature', 9), meta


def curvature_to_high(builder, data, curvature, low, saved_blo10, phase_debts,
                       *, decoder_trials=400, rank_rounds=64, static_blo0=None,
                       basis_options=None):
    values = table_words(data)
    retained = live_word('low', low, values['low'])
    retained += live_word('saved', [saved_blo10], [v >> 10 for v in values['blo']])
    if static_blo0 is not None:
        retained += live_word('blo0', [static_blo0], values['blo'])
    retained=unique_live(retained)
    consumed = live_word('curvature', curvature, values['curvature'])
    desired = desired_word('bhi', values['bhi'], 7)
    produced, meta = convert_codebook(builder, retained, consumed, desired, phase_debts,
                                      trials=decoder_trials, seed=20261108,
                                      kernel_trials=15000,
                                      preserving_rounds=rank_rounds,**(basis_options or {}))
    return output_word(produced, 'bhi', 7), meta


def restore_saved_blo10(builder, data, low, phase_debts,
                         *, decoder_trials=400, rank_rounds=64, static_blo0=None,
                         basis_options=None):
    values = table_words(data)
    target_truth = word_functions(values['blo'], 11)[10]
    variables = list(low)
    helper_values = list(values['low'])
    if static_blo0 is not None and static_blo0 not in variables:
        helper_values = [l | ((s&1) << len(low)) for l, s in zip(helper_values, values['blo'])]
        variables.append(static_blo0)
    helpers = helper_plan(helper_values, [target_truth], width=len(variables),
                           maximum=builder.max_qubits-builder.num_allocated_qubits-1)
    lf = word_functions(helper_values, len(variables))
    retained = live_word('low', low, values['low'])
    if static_blo0 is not None:
        retained += live_word('blo0', [static_blo0], values['blo'])
    retained=unique_live(retained)
    consumed = []
    for i, j in helpers['pairs']:
        target = builder.alloc_qubits(1)[0]
        builder.ccx(variables[i], variables[j], target)
        consumed.append(LiveFunction(f'helper{i}_{j}', target, lf[i]&lf[j]))
    produced, transition = convert_codebook(builder, retained, consumed,
                                            [('saved_blo10', target_truth)], phase_debts,
                                            trials=decoder_trials, seed=20261109,
                                            kernel_trials=15000,
                                            preserving_rounds=rank_rounds,**(basis_options or {}))
    return produced['saved_blo10'].wire, {'helpers': helpers, 'transition': transition,
                                         'and_count': helpers['and_count']+transition['and_count'],
                                         'qubits_after': builder.num_allocated_qubits}


def restore_saved_blo_bits(builder,data,low,phase_debts,*,bits=(5,10),
                            static_blo0=None,decoder_trials=400,rank_rounds=64,
                            basis_options=None):
    """Jointly restore original low-derivative boundary bits from static L0.

    A shared helper code is built once for every requested boundary. The
    returned dictionary maps each logical B bit index to its new quantum wire.
    Existing restore_saved_blo10 remains unchanged for earlier integrations.
    """
    positions = list(map(int,bits))
    if len(set(positions)) != len(positions) or any(not 0 <= bit < 11 for bit in positions):
        raise ValueError('Requested original Blo indices must be distinct and lie in0..10.')
    values = table_words(data)
    target_functions = word_functions(values['blo'],11)
    targets = [target_functions[bit] for bit in positions]
    variables = list(low)
    helper_values = list(values['low'])
    if static_blo0 is not None and static_blo0 not in variables:
        helper_values = [l | ((s&1) << len(low)) for l,s in zip(helper_values,values['blo'])]
        variables.append(static_blo0)
    helpers = helper_plan(helper_values,targets,width=len(variables),
                           maximum=builder.max_qubits-builder.num_allocated_qubits-len(positions))
    functions = word_functions(helper_values,len(variables))
    retained = live_word('low',low,values['low'])
    if static_blo0 is not None:
        retained += live_word('blo0',[static_blo0],values['blo'])
    retained=unique_live(retained)
    consumed = []
    for i,j in helpers['pairs']:
        target = builder.alloc_qubits(1)[0]
        builder.ccx(variables[i],variables[j],target)
        consumed.append(LiveFunction(f'helper{i}_{j}',target,functions[i]&functions[j]))
    desired = [(f'saved_blo{bit}',target_functions[bit]) for bit in positions]
    produced,transition = convert_codebook(builder,retained,consumed,desired,phase_debts,
                                            trials=decoder_trials,seed=20261401,
                                            kernel_trials=15000,preserving_rounds=rank_rounds,
                                            structured_subsets=True,**(basis_options or {}))
    return ({bit:produced[f'saved_blo{bit}'].wire for bit in positions},
            {'helpers':helpers,'transition':transition,'bits':positions,
             'and_count':helpers['and_count']+transition['and_count'],
             'qubits_after':builder.num_allocated_qubits})


def high_to_curvature(builder, data, high, low, saved_blo10, phase_debts,
                       *, decoder_trials=400, rank_rounds=64, static_blo0=None,
                       extra_static_blo=None,basis_options=None):
    values = table_words(data)
    retained = live_word('low', low, values['low'])
    retained += live_word('saved', [saved_blo10], [v >> 10 for v in values['blo']])
    if static_blo0 is not None:
        retained += live_word('blo0', [static_blo0], values['blo'])
    for bit,wire in sorted((extra_static_blo or {}).items()):
        if not 0 <= int(bit) < 11:
            raise ValueError('An additional static Blo bit must lie in0..10.')
        if wire==saved_blo10 or wire==static_blo0:
            continue
        retained += live_word(f'extra_blo{bit}_',[wire],[value >> int(bit) for value in values['blo']])
    retained=unique_live(retained)
    consumed = live_word('bhi', high, values['bhi'])
    desired = desired_word('curvature', values['curvature'], 9)
    produced, meta = convert_codebook(builder, retained, consumed, desired, phase_debts,
                                      trials=decoder_trials, seed=20261110,
                                      kernel_trials=15000,
                                      preserving_rounds=rank_rounds,**(basis_options or {}))
    return output_word(produced, 'curvature', 9), meta


def restore_address(builder, data, low, blo, curvature, phase_debts,
                    *, address_destination=None, preserved=None,
                    decoder_trials=400, rank_rounds=0, low_bits=None,
                    basis_options=None):
    values = table_words(data)
    consumed = live_word('low', low, values['low'],bit_indices=low_bits)+live_word('blo', blo, values['blo'])
    consumed += live_word('curvature', curvature, values['curvature'])
    consumed=unique_live(consumed)
    desired = desired_word('address', range(256), 8)
    produced, meta = convert_codebook(builder, [], consumed, desired, phase_debts,
                                      trials=decoder_trials, seed=20261111,
                                      preserving_rounds=rank_rounds,**(basis_options or {}))
    address = output_word(produced, 'address', 8)
    returned = {'address': address, **(preserved or {})}
    if address_destination is not None:
        returned = _place_address(builder, address, address_destination, [], preserved or {})
        del returned['curvature']
    return {name: km.array(wires) for name, wires in returned.items()}, meta


def retire_low_bits(builder,data,low,phase_debts,*,count=6,remove=None,bit_indices=None):
    return retire_table_bits(builder,table_words(data)['low'],low,phase_debts,
                              bit_indices=bit_indices,remove=remove,count=count)
