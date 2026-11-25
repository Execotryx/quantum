# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Conditional paper ledger for the actual two 78-E, 16-output loaders.

This version includes the r5/h3 metadata chart, 21-E root decoder, 9-E
shared table cleanup, 17.5-E seed, and 12-E consuming u11 initializer.
No native circuit is built. Q48 is explicitly blocked by the loader peaks.
The inherited122-E normalization allowance is NOT a certified pair-normalizer.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['OMP_NUM_THREADS']='1'
import json, hashlib, resource
from pathlib import Path
from types import SimpleNamespace
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
from paired_product import ledger
from virtual_producer import PaperCounter, ar, carry_setup, carry_clear
from slope_h3_h4_retirement_v3 import certificate as metadata_certificate
from seed_phase_cleanup_conditional import plans as seed_plans, paper as seed_paper
from growing_seed import paper_seed

HERE=Path(__file__).resolve().parent; NARROW=HERE.parents[1]
PINS={
 'research/recompute_root/models/phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json':'24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219',
 'research/recompute_root/decoder_k8/endpoint_reuse.json':'334ba08ff4baa68f8a7622334320ead48bf811d03aeea3b56430ce02e4de04ac',
 'research/quantized_producer/framed_retained5_best21_snapshot.json':'3b6fa7059bee77bb9abe6c7395cd8ff2f2899843523188c60d513e6c5d381def',
 'research/quantized_producer/u11_hmr_initializer.json':'b9e3183ad1291f0805d352ddd6efb37bb7be89d8af68f859ec8c80b76bfda15b',
 'research/joint_loader/search/subspace16_cap23_s3_raw.json':'8c0f15847a70c68b910f97b3f78c86f64fd55cab7ff4ddf90c3891bec5385a15',
 'research/joint_loader/search/subspace16_cap18_s2_raw.json':'f5f872c90a48192e08928266fe307a9802e965e58d489f2127e4fcefb16d1916',
 'research/joint_loader/retained_table_cleanup.json':'6a48b472433918d2c51f30e6eeb1d9933fdf1aa4ae9f83b93129fd8ac103b6b5',
}


def producer_pair(cap,product_bits,retire_five):
    """Expand the literal bounded producer on the actual r5/h3 owner chart.

    The separately priced H3/H4 preparation is represented by allocation.
    H3 must be created before retiring raw a6. All five H bits are restored
    before the inverse; no coefficient source is granted away.
    """
    b=PaperCounter(cap)
    v=list(b.alloc_qubits(12)); p=list(b.alloc_qubits(product_bits))
    flags=list(b.alloc_qubits(4)); D=list(b.alloc_qubits(13))
    H=list(b.alloc_qubits(3)); lookup_data=b.num_allocated_qubits
    H.append(b.alloc_qubits(1)[0])
    before_retirement=b.num_allocated_qubits
    if retire_five:
        for i in (5,6,7,9,11): b.free(v[i])
    livev=[q for q in v if q in b.live]
    H.append(b.alloc_qubits(1)[0]); S=[v[8]]+H
    data=b.num_allocated_qubits
    snap=b.alloc_qubits(1)[0]; b.cx(D[6],snap)
    token=ar.DeferredBoundedToken(SimpleNamespace(last=5,signed_source=False),snap,7,[])
    fs=b.count; rows=[]
    for i in range(5):
        k=4-i; before=b.count; carry=carry_setup(b,S,v[i],k,'and')
        for q in D[:7]: b.cx(v[i],q)
        token.row_debts.append(ar.forward_add(b,S[k+1:],D[:7],carry_in=carry))
        for q in D[:7]: b.cx(v[i],q)
        carry_clear(b,S,v[i],k,'and',carry)
        rows.append(dict(i=i,k=k,forward=float(b.count-before)))
    before=b.count; ar._deferred_overflow(b,v[:5],S,D,token,inverse=False)
    fhigh=float(b.count-before); forward=float(b.count-fs); fpeak=b.peak
    b.peak=b.num_allocated_qubits; start=b.count
    before=b.count; ar._deferred_overflow(b,v[:5],S,D,token,inverse=True)
    ihigh=float(b.count-before); saved=ar.release_saved_bit(b,snap)
    for i in reversed(range(5)):
        k=4-i; before=b.count; carry=carry_setup(b,S,v[i],k,'and')
        for q in D[:7]: b.cx(v[i],q)
        ar.inverse_add(b,S[k+1:],D[:7],token.row_debts[i],carry_in=carry,dirty_wires=livev+flags+p)
        for q in D[:7]: b.cx(v[i],q)
        carry_clear(b,S,v[i],k,'and',carry)
        rows[i]['inverse']=float(b.count-before)
    ar.repay_saved_bit(b,D[6],saved)
    return dict(status='SOURCE_EXPANDED_PAPER_NOT_NATIVE',Q=cap,
        product_bits=product_bits,retired_raw_high_bits=[0,1,2,4,6] if retire_five else [],
        lookup_data=lookup_data,H3_prepare_before_root_retirement_data=before_retirement,
        coefficient_data=data,snapshot_data=data+1,forward=forward,inverse=float(b.count-start),
        forward_high=fhigh,inverse_high=ihigh,forward_peak=fpeak,inverse_peak=b.peak,rows=rows)


def main():
    values={}
    for path,sha in PINS.items():
        raw=(NARROW/path).read_bytes(); assert hashlib.sha256(raw).hexdigest()==sha,(path,'hash mismatch')
        values[path]=json.loads(raw)
    model=values[next(p for p in PINS if '/models/' in p)]
    endpoint=values['research/recompute_root/decoder_k8/endpoint_reuse.json']
    selected=next(r for r in endpoint['results'] if r['sha256']==PINS[next(p for p in PINS if '/models/' in p)])
    assert selected['prefix_failures']==selected['endpoint_frame_failures']==selected['physical_u14_overflows']==0
    init=values['research/quantized_producer/u11_hmr_initializer.json']
    core={r['Q_cap']:r['new_core'] for r in init['rows']}
    decoder=values['research/quantized_producer/framed_retained5_best21_snapshot.json']
    assert decoder['complete'] and decoder['Toffolis']==21 and decoder['peak_data']==44
    loader1=values['research/joint_loader/search/subspace16_cap23_s3_raw.json']
    loader2=values['research/joint_loader/search/subspace16_cap18_s2_raw.json']
    for loader in (loader1,loader2):
        assert loader['status']=='COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
        assert loader['output_bits']==list(range(16)) and not loader['framed_address']
        assert loader['Toffolis']==78 and loader['T']==loader['rotations']==0
    cleanup=next(c for c in values['research/joint_loader/retained_table_cleanup.json']['cases'] if c['output_count']==16)
    assert cleanup['Toffolis']==9 and cleanup['initial_quadratic_rank']==128
    phase_path=NARROW/'research/stream_phase/alias_ring/phase_ledger.json'
    phase={r['Q']:r for r in json.loads(phase_path.read_text())['rows'] if r.get('status')=='SOURCE_EXPANDED_PHASE_PAPER_NOT_NATIVE' and r['m']==37 and r['N']==27 and r['approximate_cyclic']}
    metadata=metadata_certificate(); sc=seed_plans(); rows=[]
    for q in range(48,53):
        f1=producer_pair(q,10,False); f2=producer_pair(q,15,True); inv=producer_pair(q,10,True)
        assert f1['forward']==f2['forward']==inv['inverse']==41
        assert f2['coefficient_data']==44 and f2['forward_peak']==48
        prod=ledger(q,1,3,5,1); seed=seed_paper(sc,q,5,3); fseed=paper_seed(q,1)
        assert prod['inverse_data']==44 and sum(fseed['forward_rows'])==9
        assert seed['complete_seed_lifecycle_expected_E']==17.5
        components=dict(consuming_root=206,normalization_allowance_unverified_interface=122,product=prod['total'],
            divider_with_u11_HMR=core[q],phase_direct=phase[q]['direct_E'],rotation_charge=model['rotation_charge'],
            coefficient_rows=123,coefficient_R_frames=4,seed=17.5,
            H3_H4_preparation_and_restoration=7,retired_root_decoder=21,pure_table_cleanup=9)
        known=sum(components.values()); complete=known+loader1['Toffolis']+loader2['Toffolis']
        peak1=26+loader1['work_peak']; peak2=31+loader2['work_peak']; width_ok=max(peak1,peak2)<=q
        rows.append(dict(Q=q,status='CONDITIONAL_NORMALIZATION_GATE_ALSO_FAILS_COST' if width_ok else 'ACTUAL_LOADERS_EXCEED_Q_CAP',
            components=components,known_E_before_two_loaders=known,
            first_loader=dict(Toffolis=78,fixed_owners=26,work_peak=loader1['work_peak'],peak=peak1),
            second_loader=dict(Toffolis=78,fixed_owners=31,work_peak=loader2['work_peak'],peak=peak2),
            actual_loader_E=156,total_E=complete,paper_total_cost=q*complete,width_legal=width_ok,
            required_further_E_saving={name:complete-threshold/q for name,threshold in [('beat_stage97',92278.95),('target',89987),('stretch',82740)]},
            remaining_two_loader_E={name:threshold/q-known for name,threshold in [('beat_stage97',92278.95),('target',89987),('stretch',82740)]},
            inverse_product=dict(P15_cut_data=43,restored_redundant_sign_wire=1,arithmetic_data=44,
                owners='word16+D13+root7+flags4+Hlow3+oldA6snapshot',forward_E=prod['forward'],inverse_E=prod['inverse'],peak=prod['peak']),
            seed_cleanup=seed,first_seed_peak=fseed['peak'],
            producer_passes=dict(first_forward=f1,second_forward=f2,final_inverse=inv),
            phase=dict(R=phase[q]['R'],T=phase[q]['T'],Toffolis=phase[q]['Toffolis'],peak=phase[q]['peak'])))
    out=dict(status='CONDITIONAL_PAIR_NORMALIZATION_LEDGER_NO_NATIVE_PASS',source_pins=PINS,
        model_margin=model['minimum_margin_units'],normalized_endpoint_inputs=selected['normalized_inputs'],
        endpoint_alias_bit_checks=selected['alias_bit_checks'],rows=rows,
        metadata_certificate=metadata,
        table_cleanup_scope=values['research/joint_loader/retained_table_cleanup.json']['scope'],
        unresolved_normalization='The inherited122-E Stage94 charge is a semilog-alignment adapter, not yet a proved standard pair-normalizer for the consuming root. Parent is deriving a standalone pair-normalizer. No complete gate is asserted until that exact interface and roundtrip charge are certified.',
        native_obligations=[
            'Resolve the pair-normalization interface and replace the inherited122-E allowance with its certified forward/inverse cost and actual peak before judging the complete construction gate.',
            'Emit and natively prove both actual raw-address loader DAGs, their invertible output basis, and all deferred pure-table helper phases. Their peaks are49, so no Q48 claim.',
            'Compute initialH3 while rawa6 is live, then R-only frame and retire exactlyrawa0,a1,a2,a4,a6; retain raw a5. ComputeH4 before coefficient rows.',
            'Keep second oldA6 snapshot through inverseproduct. Repay first snapshot at second Aload. Combine identical first/second forward coefficient carry outcomes and repay in matching final inverse.',
            'Erase H4 thenH3 only at currentD chart; immediately repay their exact quadratic phases. Restore H3 thenH4 after seed cleanup before ANY coefficient inverse mutation.',
            'Use the exact17.5-E conditional seed cleanup, including old forward carry phases and the measurement-conditioned fifth helper; constants receive their classical-outcome phase.',
            'Use the paired consuming-product owner handoff, implicit C0=0, reconstituted coefficient, and restored product controls. Arithmetic requires16 word owners in inverse, not15.',
            'Use the u11 HMR initializer in the rotated j10 wire-label frame; recreate the b14 owner on inverse, repay all11 affine carry signs, then erase u high tolow.',
            'Apply endpoint phase and unroute with exact alias/root frames; restore divider, product, root and normalization; retire no quotient information for free.',
            'Restore initialA/H and rawaddress before table cleanup; repay dynamic/root/seed debts separately before the9-E puretable cleanup.',
            'Run complete native proofs and official verifier saltsdefault,1,2,3 at unchanged tolerance. None has run for this branch.'
        ],native=False,official_verifier=False,no_submission=True)
    (HERE/'post008_gate_v3.json').write_text(json.dumps(out,indent=2)+'\n')
    for r in rows:
        print(json.dumps({k:r[k] for k in ('Q','status','known_E_before_two_loaders','actual_loader_E','total_E','paper_total_cost','required_further_E_saving')}))

if __name__=='__main__': main()
