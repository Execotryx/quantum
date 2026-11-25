#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Full original-domain identity, symbolic phases, exact source cost."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,resource,signal,time
HERE=Path(__file__).resolve().parent
for rec in json.loads((HERE/'SOURCE_READY_006.json').read_text())['files']:
    p=HERE/rec['path'];raw=p.read_bytes()
    assert len(raw)==rec['bytes']and hashlib.sha256(raw).hexdigest()==rec['sha256'],rec['path']
import top12_study as proof
import boundary_phase_screen_v2 as model
import history12_kernel as proposed
np=proof.np;d=proof.d
signal.alarm(115)


def initial_signs(v,P,u):
    sig=(u>>13)&1;prev=(P>>12)&1;cur=(P>>11)&1;low=v&1
    cin=low^prev^(low&prev)^(low&cur)^(prev&cur)^(prev&sig)^(cur&sig)
    target=u&8191;framed=target^((1-sig)*8191)
    next_target=(((framed+(v>>1)+cin+2048)&8191)^((1-sig)*8191))
    actual=(prev^low^sig^cur)+(next_target<<1)
    signed=np.where(u>=8192,u-16384,u)
    direct=(2*signed+(2*sig-1)*(4096+v)+sig+cur-prev)&16383
    assert np.array_equal(actual,direct)
    next_sig=(actual>>13)&1
    decoded=((v>>11)&1)^((v>>10)&1)^(((v>>10)&1)&next_sig)
    return sig,next_sig,decoded


def source_run(vv,pp,ff,*,trace=False):
    b=proof.TruthCounter(48,len(vv));v,P,flags=[list(b.alloc_qubits(n))for n in(12,15,4)]
    for arr,values in((v,vv),(P,pp),(flags,ff)):
        for i,q in enumerate(arr):b.values[q]=proof.truth((values>>i)&1)
    original_v=[b.val(q)for q in v];original_P=[b.val(q)for q in P]
    original_flags=[b.val(q)for q in flags]
    token=d.compute_divider(b,v,P,flags);forward=b.count
    endpoint=(tuple(token.v),tuple(token.flags),tuple(token.u),dict(token.history))
    assert b.num_allocated_qubits==43
    row_records=[];cuts=[];original_inverse=d.inverse_add;row_number=35
    def inverse(builder,source,target,debt,**kwargs):
        nonlocal row_number
        before=builder.count;data=builder.num_allocated_qubits
        dirty=list(kwargs.get('dirty_wires',()))
        assert len(dirty)==len(set(dirty))
        result=original_inverse(builder,source,target,debt,**kwargs)
        if trace:row_records.append(dict(j=row_number,source_width=len(source),target_width=len(target),
            entry_owners=data,clean_owners=48-data,dirty_owners=len(dirty),
            inverse_arithmetic_E=float(builder.count-before),released_feed_carry=bool(result)))
        row_number-=1;return result
    def cut(name,j,k):
        if trace:cuts.append(dict(name=name,j=j,k=k,current_expected_E=float(b.count),owners=b.num_allocated_qubits))
    d.inverse_add=inverse
    try:result=proposed.cleanup_divider(d,b,token,trace=cut)
    finally:d.inverse_add=original_inverse
    assert [b.val(q)for q in v]==original_v
    assert [b.val(q)for q in result]==original_P
    assert [b.val(q)for q in flags]==original_flags
    assert not b.phase and not b.bits and not b.stack and b.num_allocated_qubits==31
    assert all(debt.consumed and not debt.measurements for _,_,debt in token.rows)
    assert len(set(v+result+flags))==31
    return dict(inputs=len(vv),forward_E=float(forward),cleanup_E=float(b.count-forward),
        total_E=float(b.count),T=b.T,R=b.R,peak=b.peak,return_owners=31,
        endpoint_owners=len(set(endpoint[0]+endpoint[1]+endpoint[2]+tuple(endpoint[3].values()))),
        all24_CarryDebts_consumed=True,all_quantum_data_restored=True,all_scratch_zero=True,
        every_HMR_phase_coefficient_zero=True,independent_HMR_variables=b.measurements,
        conditional_HMR_variables=b.conditional_measurements,phase_only_joins=b.classical_joins,
        inverse_rows=row_records,cuts=cuts)


def main():
    start=time.monotonic();chunks=[];digest=hashlib.sha256();trace=None
    valid_top4095=0;minimum_signed_product_at_root4095=None
    for first in range(1,3133453,65536):
        xs=np.arange(first,min(3133453,first+65536),dtype=np.int64)
        v,flags,P,u=model.initial(xs);a,b,c=initial_signs(v,P,u)
        assert np.array_equal(a,c),int(xs[np.flatnonzero(a!=c)[0]])if np.any(a!=c)else None
        # m=0 is the identity; m=1 phase coefficient is this exact XOR.
        assert not np.any(a^c)
        part=source_run(v,P,flags,trace=trace is None)
        if trace is None:trace=part
        assert part['total_E']==trace['total_E']and part['peak']==48 and part['forward_E']==270
        assert part['T']==0 and part['R']==0 and part['endpoint_owners']==43
        mask=v==4095
        if np.any(mask):
            U=np.where(P[mask]>=16384,P[mask]-32768,P[mask])
            valid_top4095+=len(U);z=int(U.min())
            minimum_signed_product_at_root4095=z if minimum_signed_product_at_root4095 is None else min(z,minimum_signed_product_at_root4095)
        digest.update(np.column_stack((xs,v,P,u,a,b)).astype('<i8').tobytes())
        chunks.append(dict(first=first,stop=int(xs[-1])+1,inputs=len(xs),all_HMR_phase=True,
                           independent_HMR_variables=part['independent_HMR_variables']))
        if len(chunks)%12==0:print(json.dumps(dict(progress='history12_all_domain_source_phase',inputs=sum(r['inputs']for r in chunks),seconds=time.monotonic()-start)),flush=True)
    # Preserve the distinction from an unrestricted root/product promise.
    cases=np.arange(65536,dtype=np.int64);vv=cases>>4;pp=(cases&15)<<11
    uu=(4094-3*vv+((pp>>12)&1)+((pp>>13)&1)-2*((pp>>14)&1))&16383
    aa,bb,cc=initial_signs(vv,pp,uu);bad=np.flatnonzero(aa!=cc)
    assert len(bad)>0 and np.all(vv[bad]==4095)
    witnesses=[dict(v=int(vv[i]),P=int(pp[i]),U=int(pp[i]if pp[i]<16384 else pp[i]-32768),
        u12=int(uu[i]),sigma12=int(aa[i]),sigma13=int(bb[i]),decoded=int(cc[i]))for i in bad]
    count=sum(r['inputs']for r in chunks);assert count==3133452
    new=Fraction(str(trace['total_E']));assert new<Fraction(1173,2)
    whole=Fraction(1584)-Fraction(1175,2)+new
    result=dict(status='COMPLETE_POSITIVE_HISTORY12_PAPER_GATE_NOT_NATIVE',
        original_inputs=count,original_interval=[1,3133453],end_exclusive=True,
        exact_retirement_and_reconstruction_identity=True,both_retirement_HMR_outcomes_proved=True,
        all_source_arithmetic_data_and_HMR_phases_proved=True,every_HMR_transcript_proved=True,
        original_model_sha256='24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219',
        core=trace,original_core_E=587.5,accepted_AR003_core_E=586.5,
        saving_from_original_E=float(Fraction(1175,2)-new),additional_saving_from_AR003_E=float(Fraction(1173,2)-new),
        sigma12_reconstruction_Toffolis=1,sigma12_retirement_Toffolis=0,
        exact_43_owner_phase_interface_unchanged=True,forward_code_unchanged=True,
        inverse_intermediate_owners=42,no_stale_initial_sign_owner=True,
        whole=dict(Q=48,expected_Toffolis=float(whole),T=4,R=33,
            rotation_charge=230.84805946161188,expected_cost=48*(float(whole)+1+230.84805946161188)),
        scope=dict(valid_original_inputs_with_root4095=valid_top4095,
            minimum_actual_U_at_root4095=minimum_signed_product_at_root4095,
            abstract_counterexamples=witnesses,unrestricted_abstract_promise_not_claimed=True),
        input_and_prefix_digest=digest.hexdigest(),chunks=chunks,
        native_circuit_or_simulator=False,native_requires_parent_acceptance=True,
        source_ready_sha256=hashlib.sha256((HERE/'SOURCE_READY_006.json').read_bytes()).hexdigest(),
        elapsed_seconds=time.monotonic()-start,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    path=HERE/'history12_study.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(path)
    print(json.dumps({k:v for k,v in result.items()if k not in('core','chunks')},indent=2),flush=True)


if __name__=='__main__':main()
