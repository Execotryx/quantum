# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""From-source integration with L0 retained through split curvature rows.

Research entry point. Acceptance requires independent official verification;
the generator does not substitute resource estimates for that verification.
"""
from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[0].parent
sys.path[:0]=[str(ROOT/'official'),str(ROOT/'engine'),str(ROOT/'tests'),str(ROOT)]
import kickmix as km
from fusion.normalization import semilog_align,ShiftFlags
from normalization_fused import normalize
from packed_shift import PackedShift
from staged_arithmetic import bounded_rows_plan
from split_bounded import (forward_bounded_low,forward_bounded_high,
                            inverse_bounded_high,inverse_bounded_low)
from cyclic_phase import cyclic_scale_phase
from packed_phase import packed_cyclic_scale_phase
from nested_virtual import forward_nested_virtual_low,inverse_nested_virtual_low
from virtual_main import (virtual_main_plan,forward_virtual_main_low,
                          inverse_virtual_main_low)
from top_virtual_main import (omit_complement_top,restore_complement_top,
    forward_full_virtual_rows,inverse_full_virtual_rows,
    reconstruct_top,erase_reconstructed_top)
from paired_arithmetic import release_saved_bit,repay_saved_bit
from deferred_phase import DeferredTablePhases
from r17_lookup import (table_words,initial_lookup,complete_low,curvature_to_high,
                        high_to_curvature,restore_address,restore_saved_blo_bits,retire_low_bits,
                        stored_low_labels)
from affine_table_layout import (prepare_lookup_view,begin_lookup_frame,
                                finish_lookup_frame,original_address_seed_factory)


def build(data,angles,*,qubit_limit=59,decoder_trials=80,rank_rounds=0,
          record_snapshots=False,seed_basis=True,retire_count=6,packed_phase=True,
          defer_top=False,virtual_top=False,top_phase_frame=False,initial_basis=False,
          staggered_snapshots=False,omit_table_top=False,residual_transitions=False,
          high_phase_hook_factory=None,joint_inverse_sharing=False,fourier_result_bits=0,
          blo9_pauli_inverse=False,consuming_main=False):
    p=data['parameters']
    precision=p['output_fraction_bits'];low_width=data['low_width']
    c_shift=int(data['c_storage_shift'])
    if (p['n_p'],p['residual_bits'],p['derivative_fraction_bits'],data['r_storage_width'],
        precision,low_width,data['r_storage_shift'])!=(10,14,25,17,26,20,1) or c_shift not in (2,3,4):
        raise ValueError('This schedule is certified for balanced F26/G25/C7-C9/R17 profiles.')
    if data['model_schema']!='balanced-guard-main-v1':
        raise ValueError('The balanced main arithmetic needs its own integer model.')
    if joint_inverse_sharing and not (
            residual_transitions and staggered_snapshots and omit_table_top
            and defer_top and virtual_top and retire_count==6
            and qubit_limit in ((56,57) if consuming_main else (57,))
            and c_shift==3 and int(data['c_storage_width'])==8):
        raise ValueError('Joint inverse sharing requires the selected57-qubit C8/R17 schedule with five disposable physical L bits.')
    if fourier_result_bits not in (0,1,2):
        raise ValueError('Only one or two additional Fourier-measured result bits are supported.')
    if fourier_result_bits and not (joint_inverse_sharing and top_phase_frame and packed_phase):
        raise ValueError('Shortened main inversion requires the joint inverse and the selected top phase frame.')
    if blo9_pauli_inverse and not (
            qubit_limit in ((56,57) if consuming_main else (57,))
            and fourier_result_bits==2 and joint_inverse_sharing
            and top_phase_frame and packed_phase and initial_basis):
        raise ValueError('Blo9 requires the selected joint C8/two-bit-Fourier cut at57 qubits.')
    if consuming_main != bool(data.get('consuming_odd_last_row')):
        raise ValueError('The consuming main and the A-even consuming table belong together.')
    if consuming_main and not (
            virtual_top and top_phase_frame and omit_table_top and packed_phase
            and joint_inverse_sharing and fourier_result_bits==2):
        raise ValueError('The consuming main requires the selected literal-top Fourier schedule.')
    # Logical labels of the stored low wires: L0..18, or L1..18 for the
    # A-even consuming table. first_low is the lowest stored label.
    low_labels=stored_low_labels(data)
    first_low=low_labels[0]
    offsets={kind:[Fraction(0)]*width for kind,width in
             [('high_base',8),('high_overflow',10),('low_base',low_width),('low_overflow',10)]}
    complement=angles.get('high_mode')=='complement'
    for item in angles['features']:
        kind=item['kind'].replace('high_complement_','high_')
        offsets[kind][item['bit']]=Fraction(item['nudge_turn_numerator'],angles['turn_denominator'])
    if angles['status']!='PASS':
        raise ValueError('Numerical profile has no certified synthesis margin.')
    original_model=data
    data,address_frame=prepare_lookup_view(data)
    values=table_words(data)
    if virtual_top:
        if not defer_top or any(((v>>19)^(v>>18))&1 != 1 for v in values['low']):
            raise ValueError('Virtual top arithmetic requires the certified nearest-anchor complement relation.')
    if top_phase_frame and not virtual_top:
        raise ValueError('Top phase-frame cleanup requires virtual top arithmetic.')
    initial_options={'preserve_future':True} if qubit_limit<=58 else {}
    if initial_basis:
        initial_options.update(basis_search_products=3,basis_natural_limit=256,
            basis_random_trials=256,basis_random_max_products=5,preserve_future=True)
    rows=data['coefficients']
    builder=km.CircuitBuilder();builder.set_max_qubits(qubit_limit)
    regions=[];snapshots=[];tables={}
    @contextmanager
    def region(name):
        before=builder.finish_circuit();entry=builder.num_allocated_qubits
        with builder.mark(name):
            yield
        after=builder.finish_circuit()
        item=dict(name=name,qubits_on_entry=entry,qubits_on_exit=builder.num_allocated_qubits,
                  peak_so_far=after.num_qubits,
                  static_toffolis=int(after.operation_statistics().num_toffoli_like-before.operation_statistics().num_toffoli_like),
                  operations=len(after)-len(before))
        regions.append(item)
        if after.num_qubits>qubit_limit:
            raise AssertionError('Quantum width exceeded the explicit acceptance gate.')
        print(f"{name}: {item['static_toffolis']} static Toffolis, {item['qubits_on_exit']} live, peak {after.num_qubits}",file=sys.stderr,flush=True)
    def snapshot(name,**words):
        if record_snapshots:
            snapshots.append(dict(name=name,circuit=builder.finish_circuit(),
                                  words={key:list(value) for key,value in words.items()}))
    x=list(builder.alloc_qubits(22));original_address=x[14:]
    flags=ShiftFlags(builder.alloc_qubits(4),10)
    with region('normalization'):
        original_input_max=3*(2**int(p['n_p'])-2)**2
        normalize(builder,x,flags,original_input_max=original_input_max)
        semilog_align(builder,x)
    shift=PackedShift(builder,x[:14],flags)
    with region('pack_shift'):
        shift.pack()
    debts=DeferredTablePhases(8)
    phase_meta={}
    high_hook=(high_phase_hook_factory(original_model,angles,shift,original_address,address_frame)
               if high_phase_hook_factory is not None else None)
    if high_hook is not None:
        from high_ownership import bind_high_table_ledger
        bind_high_table_ledger(high_hook,debts)
    def high_phase(b,word):
        with region('high_phase'):
            if high_hook is not None:
                from high_ownership import split_high_callback_result
                phase_meta['high'],ownership=split_high_callback_result(high_hook(b,word))
                return ownership
            elif packed_phase:
                phase_meta['high']=packed_cyclic_scale_phase(b,word,shift,18,
                    turn_offsets=offsets['high_base']+offsets['high_overflow'],complement_overflow=complement)
            else:
                with shift.unpacked() as f:
                    phase_meta['high']=cyclic_scale_phase(b,word,f,18,
                        turn_offsets=offsets['high_base']+offsets['high_overflow'],complement_overflow=complement)
    with region('initial_lookup_and_address_retirement'):
        begin_lookup_frame(builder,original_address,address_frame)
        seed_factory=original_address_seed_factory(address_frame)
        if high_hook is not None:seed_factory=high_hook.seed_factory(seed_factory)
        words,tables['initial']=initial_lookup(
            builder,data,original_address,debts,high_phase,
            decoder_trials=decoder_trials,rank_rounds=rank_rounds,
            seed_factory=seed_factory,
            basis_options=initial_options,
            deferred_low_bits=(19,) if defer_top else ())
        result,blo,curv=map(list,(words['low'],words['blo'],words['curvature']))
    snapshot('coefficient_start',low=result,blo=blo,c=curv,residual=shift.residual)
    curvature_plan=virtual_main_plan(bounded_rows_plan(digits=14,source_min=min(values['curvature']),
        source_max=max(values['curvature']),source_fraction=25-c_shift,target_fraction=25,first_shift=c_shift-15,first=4))
    if curvature_plan.window!=10:
        raise ValueError('Virtual curvature correction does not fit the ten-bit physical word.')
    with region('forward_curvature_low'):
        children=[virtual_main_plan(bounded_rows_plan(digits=14,source_min=min(values['curvature']),
            source_max=max(values['curvature']),source_fraction=25-c_shift,target_fraction=25,
            first_shift=c_shift-15,first=a,last=b)) for a,b in [(4,9),(9,14)]]
        curv_token=forward_nested_virtual_low(builder,shift,curv,blo,curvature_plan,children,parity_before=0)
        if curv_token.parity_after:
            raise AssertionError('The omitted derivative bit did not return to zero.')
        child=curv_token.children[0]
    if defer_top and not omit_table_top:
        with region('complete_constant_top_bit'):
            result,tables['complete_low']=complete_low(builder,data,result,curv,debts,
                low_bits=words['low_bits'],nearest_relation=True,
                extra_saved_blo={4:child.saved_bit,9:curv_token.saved_bit},
                decoder_trials=decoder_trials,rank_rounds=rank_rounds)
            result=list(result)
    with region('curvature_to_derivative_high'):
        if residual_transitions:
            if not omit_table_top:raise ValueError('Residual transitions require the redundant-top omission')
            from new_lookup_design import forward_residual_high
            bhi,tables['curvature_to_high']=forward_residual_high(
                builder,data,curv,result,curv_token.saved_bit,debts,
                saved_inner=child.saved_bit,decoder_trials=decoder_trials,basis_options={})
            if not tables['curvature_to_high']['erased_inner_boundary']:
                raise AssertionError('The forward transition must declare its exact inner-boundary debt')
            child.saved_bit=None
        elif omit_table_top:
            from reduced_low_lookup import forward_high
            bhi,tables['curvature_to_high']=forward_high(
                builder,data,curv,result,curv_token.saved_bit,debts,
                saved_inner=child.saved_bit,decoder_trials=decoder_trials,rank_rounds=rank_rounds)
        else:
            bhi,tables['curvature_to_high']=curvature_to_high(
                builder,data,curv,result,curv_token.saved_bit,debts,
                decoder_trials=decoder_trials,rank_rounds=rank_rounds,
                extra_saved_blo={4:child.saved_bit})
        bhi=list(bhi)
    with region('forward_curvature_high'):
        forward_bounded_high(builder,shift,blo,bhi,curv_token)
        debts.erase(builder,[(v>>9)&1 for v in values['blo']],[curv_token.saved_bit])
        builder.free(curv_token.saved_bit);curv_token.saved_bit=None
        if child.saved_bit is not None:
            debts.erase(builder,[(v>>4)&1 for v in values['blo']],[child.saved_bit])
            builder.free(child.saved_bit);child.saved_bit=None
    r=blo+bhi
    snapshot('curvature_done',low=result,r=r,residual=shift.residual)
    if omit_table_top:
        result=restore_complement_top(builder,result)
    if consuming_main:
        # The even table word stores no bit zero. Its literal top stays live:
        # the consumed last sign wire becomes result bit zero inside the
        # first group, so no original-top snapshot is taken.
        groups=[(10,14),(0,6),(6,10)]
        if len(result)!=low_width-1:
            raise AssertionError('The stored even low word and its literal top must have nineteen wires.')
        saved_original_top=None
    elif virtual_top:
        groups={57:[(6,14),(0,6)],58:[(10,14),(0,6),(6,10)],
                59:[(12,14),(0,5),(5,9),(9,12)]}[qubit_limit]
        if top_phase_frame:
            groups={57:[(10,14),(0,6),(6,10)],
                    58:[(12,14),(0,5),(9,12),(5,9)]}[qubit_limit]
        result,saved_original_top=omit_complement_top(builder,result)
    else:
        groups={58:[(0,6),(6,11),(11,14)],59:[(0,6),(10,14),(6,10)],
                60:[(0,5),(5,9),(11,14),(9,11)]}[qubit_limit]
    main=[]
    parity=int(data['virtual_initial_parity_source_mask'])
    final_parity=0
    if consuming_main:
        # The odd last row is consumed outside the virtual-bottom rows, whose
        # omitted bit therefore starts at zero and ends at the fine-sum parity.
        parity,final_parity=0,parity
    with region('forward_result'):
        for first,last in groups:
            plan=virtual_main_plan(bounded_rows_plan(digits=14,source_min=min(row['r_min'] for row in rows),
                source_max=max(row['r_max'] for row in rows),source_fraction=24,target_fraction=precision+1,
                first=first,last=last,first_shift=-int(data['main_first_logical_shift'])))
            lo,hi=result[:plan.window],result[plan.window:]
            if hi:
                token=forward_virtual_main_low(builder,shift,r,lo,plan,parity_before=parity)
                forward_bounded_high(builder,shift,lo,hi,token)
            else:
                token=forward_full_virtual_rows(builder,shift,r,lo,plan,parity_before=parity)
                if consuming_main:
                    result=list(token.literal_target);lo=result
            main.append((lo,hi,token))
            parity=token.parity_after
    if parity!=final_parity:
        raise AssertionError('The final virtual result bit differs from its certified source parity.')
    fourier_debt=None
    with region('low_phase'):
        if consuming_main:
            if len(result)!=low_width or result[0]!=shift.residual[-1]:
                raise AssertionError('The literal result must start at the consumed last sign wire.')
            phase_result=result
            # No original-top snapshot exists. The unchanged fixed-code
            # repayment keeps its ledger coordinate through a stored zero.
            original_top_debt=builder.alloc_bits(1)[0]
            builder.bit_store(original_top_debt,False)
        elif virtual_top:
            phase_top=reconstruct_top(builder,saved_original_top,result[-1],shift.residual[-1])
            phase_result=result+[phase_top]
            if top_phase_frame:
                original_top_debt=release_saved_bit(builder,saved_original_top)
        else:
            phase_result=result
        snapshot('result_done',r=r,low=phase_result,residual=shift.residual)
        if packed_phase:
            phase_meta['low']=packed_cyclic_scale_phase(builder,phase_result,shift,precision+11,
                turn_offsets=offsets['low_base']+offsets['low_overflow'])
        else:
            with shift.unpacked() as f:
                phase_meta['low']=cyclic_scale_phase(builder,phase_result,f,precision+11,
                    turn_offsets=offsets['low_base']+offsets['low_overflow'])
        if consuming_main:
            from fourier_main import measure_literal_suffix
            result,fourier_debt=measure_literal_suffix(builder,result,original_top_debt)
        elif virtual_top:
            if top_phase_frame:
                if fourier_result_bits:
                    from fourier_main import measure_result_suffix
                    result,fourier_debt=measure_result_suffix(builder,result,phase_top,
                        original_top_debt,removed=fourier_result_bits)
                else:
                    top_phase_debt=release_saved_bit(builder,phase_top)
            else:
                erase_reconstructed_top(builder,phase_top,saved_original_top,result[-1],shift.residual[-1])
    with region('backward_result'):
        if virtual_top and not top_phase_frame:
            original_top_debt=release_saved_bit(builder,saved_original_top)
        if fourier_debt is not None:
            from fourier_main import inverse_main_groups
            phase_meta['fourier_main']=inverse_main_groups(builder,shift,r,result,main,fourier_debt)
            if consuming_main:
                # The inverse restored the last sign wire in result position
                # zero. The static regions own the stored low word above it.
                if result[0]!=shift.residual[-1]:
                    raise AssertionError('The consumed sign wire was not returned to the residual.')
                result=result[1:]
        else:
            overflow_phase=top_phase_debt if top_phase_frame else None
            for lo,hi,token in reversed(main):
                if hi:
                    inverse_bounded_high(builder,shift,lo,hi,token,overflow_phase=overflow_phase)
                    inverse_virtual_main_low(builder,shift,r,lo,token)
                else:
                    inverse_full_virtual_rows(builder,shift,r,lo,token,overflow_phase=overflow_phase)
        if virtual_top and fourier_debt is None:
            repay_saved_bit(builder,result[-1],original_top_debt)
            if top_phase_frame:
                builder.z(top_phase_debt)
                repay_saved_bit(builder,result[-1],top_phase_debt)
            if not omit_table_top:
                result=restore_complement_top(builder,result)
    snapshot('result_restored',r=r,low=result,residual=shift.residual)
    with region('restore_curvature_carry'):
        if fourier_debt is not None:
            if len(result)!=19-first_low-fourier_result_bits:
                raise AssertionError('The shortened result ownership changed before outer restoration.')
            saved,tables['restore_carry']=restore_saved_blo_bits(
                builder,data,result,debts,bits=(9,),low_bits=range(first_low,first_low+len(result)),
                decoder_trials=decoder_trials,rank_rounds=rank_rounds,basis_options={})
        elif omit_table_top:
            if not staggered_snapshots:raise ValueError('Omitted-table-top schedule requires staggered snapshots')
            from reduced_low_lookup import restore_outer
            saved,tables['restore_carry']=restore_outer(builder,data,result,debts,
                decoder_trials=decoder_trials,rank_rounds=rank_rounds)
        else:
            saved,tables['restore_carry']=restore_saved_blo_bits(
                builder,data,result,debts,bits=(9,) if staggered_snapshots else (9,4),
                decoder_trials=decoder_trials,rank_rounds=rank_rounds)
        curv_token.saved_bit=saved[9]
        curv_token.children[0].saved_bit=saved.get(4)
    with region('backward_curvature_high'):
        inverse_bounded_high(builder,shift,blo,bhi,curv_token,release_saved=False)
    blo9_outer_placeholder=None
    with region('derivative_high_to_curvature'):
        if residual_transitions:
            if joint_inverse_sharing:
                from joint_inverse_lookup import reverse_joint_quadratic
                curv,inner,result,tables['high_to_curvature']=reverse_joint_quadratic(
                    builder,data,bhi,result,curv_token.saved_bit,debts,fourier_debt=fourier_debt)
                result=list(result)
                kept_after_inverse=list(range(1,16)) if consuming_main else list(range(14))
                if (len(result)!=len(kept_after_inverse)
                        or tables['high_to_curvature']['low_bits']!=kept_after_inverse
                        or tables['high_to_curvature']['early_low_retirement']['retired_bits']
                            !=list(range(kept_after_inverse[-1]+1,19-fourier_result_bits))):
                    raise AssertionError('The joint inverse did not return its exact partial-L ownership contract.')
            else:
                from new_lookup_design import reverse_residual_curvature
                curv,inner,tables['high_to_curvature']=reverse_residual_curvature(
                    builder,data,bhi,result,curv_token.saved_bit,debts,
                    decoder_trials=decoder_trials,basis_options={})
            curv_token.children[0].saved_bit=inner
            if not tables['high_to_curvature']['erased_outer_boundary']:
                raise AssertionError('The reverse transition must declare its exact outer-boundary debt')
            curv_token.saved_bit=None
            # The table ledger already owns the HMR sign of the original
            # Blo9 witness.  The existing inverse-row API expects a classical
            # record for any remaining debt; here that debt is exactly zero.
            curv_token.saved_measurement=builder.alloc_bits(1)[0]
            builder.bit_store(curv_token.saved_measurement,False)
            if blo9_pauli_inverse:
                # The actual original-Blo9 measurement is already owned by
                # debts. Retain only the new zero placeholder's identity;
                # the earlier real owner must never be merged/freed again.
                blo9_outer_placeholder=curv_token.saved_measurement
        elif staggered_snapshots:
            if omit_table_top:
                from reduced_low_lookup import return_curvature as high_to_curvature_and_inner
            else:
                from staggered_restore import high_to_curvature_and_inner
            curv,inner,tables['high_to_curvature']=high_to_curvature_and_inner(
                builder,data,bhi,result,curv_token.saved_bit,debts,
                decoder_trials=decoder_trials,rank_rounds=rank_rounds)
            curv_token.children[0].saved_bit=inner
        else:
            curv,tables['high_to_curvature']=high_to_curvature(
                builder,data,bhi,result,curv_token.saved_bit,debts,
                decoder_trials=decoder_trials,rank_rounds=rank_rounds,
                extra_saved_blo={4:curv_token.children[0].saved_bit})
        curv=list(curv)
    low_bits=list(range(first_low,first_low+len(result)))
    if retire_count:
        with region('retire_constant_workspace'):
            if joint_inverse_sharing:
                # Only the present upper table bits were measured before the joint
                # decoder. Their complete phase debts already belong to the
                # shared ledger. Measuring their reused wires here would be
                # incorrect; transfer the existing ownership certificate.
                late_retirement=None
                if consuming_main:
                    # The fixed inverse code kept L15 instead of a product
                    # helper. It is retired here, before the curvature inverse,
                    # so that the late code is L1..14 at the usual live count.
                    if low_bits!=list(range(1,16)):
                        raise AssertionError('Unexpected partial-L layout after the consuming joint inverse.')
                    result,low_bits,late_retirement=retire_low_bits(
                        builder,data,result,debts,remove=[15],bit_indices=low_bits)
                    result=list(result)
                if len(result)!=14 or low_bits!=list(range(first_low,first_low+14)):
                    raise AssertionError('Unexpected partial-L layout after the joint inverse.')
                retired=tables['high_to_curvature']['early_low_retirement']
                tables['low_retirement']=dict(and_count=0,retired_bits=retired['retired_bits'],
                    retained_bits=low_bits,qubits_after=builder.num_allocated_qubits,
                    already_erased_by_joint_inverse=True,
                    early_retirement_certificate=retired,additional_measurements=0,
                    late_retirement_after_joint_inverse=late_retirement,
                    Fourier_removed_bits=list(range(19-fourier_result_bits,19+int(consuming_main))))
            else:
                result,low_bits,tables['low_retirement']=retire_low_bits(builder,data,result,debts,count=retire_count-int(omit_table_top))
                result=list(result)
    blo9_debt=None
    with region('backward_curvature_low'):
        if blo9_pauli_inverse:
            from blo9_pauli import inverse_nested_blo9
            incoming_table_records=tuple(
                (tuple(coefficients),tuple(outcomes)) for coefficients,outcomes in debts.pending)
            incoming_table_counters=(debts.address_bits,debts.erased_words,debts.erased_qubits)
            incoming_table_owners=tuple(outcome for _,word in incoming_table_records for outcome in word)
            if (blo9_outer_placeholder is None
                    or curv_token.saved_measurement!=blo9_outer_placeholder
                    or blo9_outer_placeholder in incoming_table_owners
                    or len(set(incoming_table_owners))!=len(incoming_table_owners)):
                raise AssertionError('The new zero placeholder must be distinct from every earlier table owner.')
            inverse_entry_live=builder.num_allocated_qubits
            blo,blo9_debt=inverse_nested_blo9(builder,shift,curv,blo,curv_token)
            if (tuple((tuple(coefficients),tuple(outcomes)) for coefficients,outcomes in debts.pending)
                    !=incoming_table_records
                    or (debts.address_bits,debts.erased_words,debts.erased_qubits)!=incoming_table_counters):
                raise AssertionError('The Blo9 inverse modified an already-owned table phase.')
            if curv_token.stage!='consumed' or blo9_debt.stage!='low_reversed':
                raise AssertionError('The Blo9 inverse did not finish its curvature-debt handoff.')
            tables['blo9_inverse']=dict(
                status='EMITTED_OWNERSHIP_ASSERTIONS_NOT_COMPLETE_PROOF',
                inverse_entry_live=inverse_entry_live,inverse_exit_live=builder.num_allocated_qubits,
                retained_original_Blo_bits=list(range(9)),
                original_outer_snapshot_already_table_owned=True,
                token_outer_snapshot_is_stored_zero_placeholder=True,
                zero_placeholder_id=str(blo9_outer_placeholder),new_Blo9_owner_id=str(blo9_debt.outcome),
                incoming_table_entries=len(incoming_table_records),
                incoming_table_owner_count=len(incoming_table_owners),
                original_pending_table_ledger_unchanged_by_inverse=True,
                original_curvature_token_consumed=True,
                complete_generator_semantic_and_combined_bank_proofs_required=True)
        else:
            inverse_nested_virtual_low(builder,shift,curv,blo,curv_token)
    snapshot('curvature_restored',low=result,blo=blo,c=curv,residual=shift.residual)
    with region('restore_address_and_erase_coefficients'):
        if blo9_pauli_inverse:
            from blo9_pauli import restore_address_blo9
            returned,tables['restore_address']=restore_address_blo9(
                builder,data,result,blo,curv,debts,blo9_debt,
                address_destination=original_address,preserved={'residual':shift.residual,'packed_t':[shift.t]},
                decoder_trials=decoder_trials,rank_rounds=rank_rounds,low_bits=low_bits)
            if (blo9_debt.stage!='table_owned'
                    or tuple((tuple(coefficients),tuple(outcomes))
                             for coefficients,outcomes in debts.pending[:len(incoming_table_records)])
                    !=incoming_table_records):
                raise AssertionError('Address return must retain every earlier owner and transfer the new Blo9 sign.')
            tables['blo9_inverse']['new_Blo9_debt_transferred_to_same_table_ledger']=True
            tables['blo9_inverse']['original_pending_table_prefix_preserved_through_address_return']=True
        else:
            returned,tables['restore_address']=restore_address(builder,data,result,blo,curv,debts,
                address_destination=original_address,preserved={'residual':shift.residual,'packed_t':[shift.t]},
                decoder_trials=decoder_trials,rank_rounds=rank_rounds,low_bits=low_bits)
        address=list(returned['address']);shift.residual=list(returned['residual'])
        shift._t=returned['packed_t'][0]
    with region('repay_table_measurements'):
        if fourier_debt is not None and fourier_debt.stage!='consumed':
            raise AssertionError('A Fourier outcome or non-Pauli initial suffix remains unpaid.')
        tables['phase_flush']=debts.flush(builder,address)
        if blo9_pauli_inverse:
            if debts.pending or debts.erased_words or debts.erased_qubits:
                raise AssertionError('The complete Blo9 integration retained table-phase owners after flush.')
            tables['blo9_inverse']['complete_table_ledger_flushed']=True
        finish_lookup_frame(builder,address,address_frame)
    with region('restore_input'):
        flags=shift.unpack()
        if shift.pending_measurements:
            raise AssertionError('Packed-shift phase records remain unpaid.')
        semilog_align(builder,x,inverse=True)
        normalize(builder,x,flags,inverse=True,cleanup='thermometer')
        builder.free(km.array(flags))
    header=km.Circuit('\n'.join([f'APPEND_TO_REGISTER {q} r0' for q in x]+['REGISTER r0 "x"']))
    circuit=header+builder.finish_circuit()
    for cp in snapshots:cp['circuit']=header+cp['circuit']
    raw=io.BytesIO();circuit.to_file(raw,format='kmb')
    metadata=dict(model_schema=data['model_schema'],parameters=p,num_qubits=circuit.num_qubits,
        circuit_sha256=hashlib.sha256(raw.getvalue()).hexdigest(),regions=regions,tables=tables,
        static_toffolis=int(circuit.operation_statistics().num_toffoli_like),
        phase=phase_meta,main_groups=groups,decoder_trials=decoder_trials,rank_rounds=rank_rounds,
        numerical_validation=angles,deferred_top_bit=bool(defer_top),virtual_top_bit=bool(virtual_top),
        top_measurement_phase_frame=bool(top_phase_frame),initial_target_basis=bool(initial_basis),
        staggered_reverse_snapshots=bool(staggered_snapshots),
        omitted_table_top=bool(omit_table_top),
        joint_inverse_sharing=bool(joint_inverse_sharing),
        fourier_result_bits=fourier_result_bits,
        result_restored_low_bits=list(range(first_low,19-fourier_result_bits)),
        consuming_main=bool(consuming_main),stored_low_labels=list(low_labels),
        address_affine_rows=list(address_frame.rows) if address_frame else None)
    return circuit,metadata,snapshots


