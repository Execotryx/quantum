# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""From-mathematical-model compiler integrating independently proved passes."""
from contextlib import nullcontext
from functools import partial
import hashlib,io
import scheduled_generator as base
import merged_phase
from merged_phase import merged_packed_cyclic_scale_phase
from conditioned_terminal import use_conditioned_terminals
from window_resynthesis import optimize
from universal_phase_basis import flush_universal
from conditional_bank import flush_conditional
from threshold_phase_ledger import PackedThresholdPhasePass
from phase_aware_partitions import use_phase_aware_partitions

def build(model,angles,*,conditioned_terminals=True,window_pass=True,universal_flush=True,
          threshold_ledger=True,omit_table_top=True,initial_retention=False,
          address_retention=True,phase_aware_partitions=True,conditional_phase_bank=True,
          high_product_sharing=False,early_high_retirement=False,
          ternary_c5_phase=False,crt_c10_phase=False,c4_high_phase=False,reencoded_c20_phase=False,
          blo9_pauli_inverse=False,**options):
    if conditional_phase_bank and not universal_flush:
        raise ValueError('Conditional phase bank requires universal phase repayment.')
    if high_product_sharing and not initial_retention:
        raise ValueError('High product sharing requires the selected retained-product initializer.')
    mode=angles.get('rare_phase_pass')
    if reencoded_c20_phase and (ternary_c5_phase or crt_c10_phase):
        raise ValueError('The reencoded C20 route must be the unique selected low-phase replacement.')
    if reencoded_c20_phase and (mode!='zero-residual-tail-from-8-v1' or
            not threshold_ledger or not options.get('packed_phase',True)):
        raise ValueError('Reencoded C20 requires the selected packed tail43 phase and merged threshold ledger.')
    if ternary_c5_phase and crt_c10_phase:
        raise ValueError('Choose exactly one low-phase routing replacement.')
    if crt_c10_phase and (mode!='zero-residual-tail-from-8-v1' or
            not threshold_ledger or not options.get('packed_phase',True)):
        raise ValueError('CRT C10 routing requires the selected packed tail43 phase and threshold ledger.')
    if ternary_c5_phase and (mode!='zero-residual-tail-from-8-v1' or
            not threshold_ledger or not options.get('packed_phase',True)):
        raise ValueError('Joint C5 routing requires the selected packed tail43 phase and threshold ledger.')
    if early_high_retirement and (not initial_retention or mode!='zero-residual-tail-from-8-v1'):
        raise ValueError('Early H7f retirement requires the selected retained initializer and tail43 phase.')
    if blo9_pauli_inverse and not (
            reencoded_c20_phase and c4_high_phase and conditioned_terminals and window_pass
            and initial_retention and address_retention and high_product_sharing
            and early_high_retirement and threshold_ledger and universal_flush
            and conditional_phase_bank and phase_aware_partitions
            and options.get('qubit_limit') in ((56,57) if options.get('consuming_main') else (57,))
            and options.get('fourier_result_bits')==2
            and options.get('joint_inverse_sharing') is True
            and options.get('packed_phase',True) is True):
        raise ValueError('Blo9 requires the selected57-qubit reencoded-C20/C4/two-bit-Fourier integration.')
    if mode not in (None,'singleton-high-or-k10-v1','zero-residual-tail-from-8-v1'):
        raise ValueError('Unsupported numerical phase transformation')
    if c4_high_phase and (mode!='zero-residual-tail-from-8-v1' or
            not early_high_retirement or not threshold_ledger or not options.get('packed_phase',True)):
        raise ValueError('C4 high routing requires the proved packed tail43 early-H ownership cut.')
    from high_c4_phase import install_high_c4
    old_phase=base.packed_cyclic_scale_phase
    def phase(builder,value,packed,fractional_bits,**kwargs):
        if mode is None:return old_phase(builder,value,packed,fractional_bits,**kwargs)
        if mode=='zero-residual-tail-from-8-v1':
            if len(value)==20 and fractional_bits==37:
                if reencoded_c20_phase:
                    from reencoded_c20_phase import low_phase_reencoded
                    return low_phase_reencoded(builder,value,packed,fractional_bits,
                        threshold=threshold_pass.threshold,**kwargs)
                if crt_c10_phase:
                    from crt_c10_phase import low_phase_crt
                    return low_phase_crt(builder,value,packed,fractional_bits,
                        threshold=threshold_pass.threshold,**kwargs)
                if ternary_c5_phase:
                    from ternary_c5 import low_phase_joint
                    return low_phase_joint(builder,value,packed,fractional_bits,
                        threshold=threshold_pass.threshold,**kwargs)
                return merged_packed_cyclic_scale_phase(builder,value,packed,fractional_bits,
                    skip_overflow=(8,9),**kwargs)
            raise ValueError('The tail43 high phase needs its bound table hook')
        if len(value)==8 and fractional_bits==18:
            return merged_packed_cyclic_scale_phase(builder,value,packed,fractional_bits,
                or_features={2:10},**kwargs)
        if len(value)==20 and fractional_bits==37:
            return merged_packed_cyclic_scale_phase(builder,value,packed,fractional_bits,
                skip_overflow=(9,),**kwargs)
        raise ValueError('Unexpected phase geometry')
    old_flush=base.DeferredTablePhases.flush
    old_initial=base.initial_lookup
    old_address=base.restore_address
    old_threshold=merged_phase._threshold
    threshold_pass=PackedThresholdPhasePass() if threshold_ledger else None
    if mode=='zero-residual-tail-from-8-v1':
        if threshold_pass is None:raise ValueError('The tail43 pass requires the exact threshold phase ledger')
        if early_high_retirement:
            from high_ownership import EarlyHigh7fHook as HighHook
        else:
            from tail43_hook import Tail43HighPhaseHook as HighHook
        options['high_phase_hook_factory']=lambda model,angles,shift,address,frame:HighHook(
            model,angles,shift,address,frame,phase_pass=threshold_pass)
    audit=[];base.packed_cyclic_scale_phase=phase
    if initial_retention:
        from initial_retained import initial_retained
        if high_product_sharing:
            from high_product_share import convert_shared_high
            base.initial_lookup=partial(initial_retained,high_decoder=convert_shared_high)
        else:
            base.initial_lookup=initial_retained
    if address_retention:
        from retained_address import restore_address_retained
        base.restore_address=restore_address_retained
    if universal_flush:
        flush=flush_conditional if conditional_phase_bank else flush_universal
        base.DeferredTablePhases.flush=lambda self,builder,address:flush(builder,address,self)
    context=use_conditioned_terminals(audit=audit) if conditioned_terminals else nullcontext()
    try:
        if threshold_pass:merged_phase._threshold=threshold_pass.threshold
        with context, (use_phase_aware_partitions(enable_overflow_search=True)
                       if phase_aware_partitions and conditioned_terminals else nullcontext()), \
                (threshold_pass.install() if threshold_pass else nullcontext()), \
                (install_high_c4() if c4_high_phase else nullcontext()):
            circuit,metadata,snapshots=base.build(model,angles,omit_table_top=omit_table_top,
                blo9_pauli_inverse=blo9_pauli_inverse,**options)
    finally:
        base.packed_cyclic_scale_phase=old_phase
        base.DeferredTablePhases.flush=old_flush
        base.initial_lookup=old_initial
        base.restore_address=old_address
        merged_phase._threshold=old_threshold
    metadata['conditioned_terminal_pass']=audit
    metadata['numerical_phase_pass']=mode
    metadata['universal_phase_bank']=bool(universal_flush)
    metadata['conditional_phase_bank']=bool(conditional_phase_bank)
    metadata['initial_product_retention']=bool(initial_retention)
    metadata['high_product_sharing']=bool(high_product_sharing)
    metadata['early_high_retirement']=bool(early_high_retirement)
    metadata['ternary_c5_low_phase']=bool(ternary_c5_phase)
    metadata['crt_c10_low_phase']=bool(crt_c10_phase)
    metadata['c4_high_phase']=bool(c4_high_phase)
    metadata['reencoded_c20_low_phase']=bool(reencoded_c20_phase)
    metadata['blo9_pauli_inverse']=bool(blo9_pauli_inverse)
    metadata['address_product_retention']=bool(address_retention)
    metadata['phase_aware_inverse_partitions']=bool(phase_aware_partitions and conditioned_terminals)
    metadata['threshold_phase_ledger']=bool(threshold_ledger)
    if window_pass:
        circuit,proof=optimize(circuit)
        metadata['window_resynthesis']=proof
    raw=io.BytesIO();circuit.to_file(raw,format='kmb')
    metadata['circuit_sha256']=hashlib.sha256(raw.getvalue()).hexdigest()
    metadata['static_toffolis']=int(circuit.operation_statistics().num_toffoli_like)
    metadata['num_qubits']=circuit.num_qubits
    return circuit,metadata,snapshots
