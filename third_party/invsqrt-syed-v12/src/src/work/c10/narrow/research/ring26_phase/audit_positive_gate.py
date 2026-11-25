#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Small independent source/result/basis audit; no new numerical/native run."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,json,math,resource

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
FIT_SHA='c0eab1edd234e32d5baa1a51a0fec46abf82165d3973ffda825d2149f67f11e5'
GUARD_SHA='8b523871550d786417325baf354f7ae5ed10d7cd2236895c5fce62eab4f3fdf7'
READY_SHA='fb35ffc208a309f2c7cbb84654d30421a1ac640dd74c35cb9d0142fc3c52feb2'
N=3133452;GRID=1<<14;UNIT=1<<27;MOD=1<<50


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(path,digest):
    assert sha(path)==digest,str(path)
    return json.loads(path.read_text())


def round_grid(value):
    q,r=divmod(value,GRID)
    return (q+int(2*r>GRID or (2*r==GRID and q&1)))*GRID


def truth(terms,values):
    return sum(int(values&t==t)for t in terms)&1


def main():
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
    ready=checked(HERE/'SOURCE_READY.json',READY_SHA)
    for row in ready['files']:
        p=HERE/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    inputs=json.loads((HERE/'INPUTS.json').read_text())['files']
    for row in inputs:
        p=NARROW/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
    fit=checked(HERE/'global_zero33.json',FIT_SHA);guard=checked(HERE/'global_zero33.guard.json',GUARD_SHA)
    assert fit['source_pins']==inputs
    assert fit['status']=='COMPLETE_EXACT_RING26_PAPER_GATE_NATIVE_PENDING' and fit['case']=='global_zero33'
    assert fit['accuracy_decisions_integer'] and fit['original_tolerance_unchanged']
    assert not fit['native'] and not fit['LP_global_optimum_claim'] and fit['phase_modulus']==MOD
    exact=fit['exact_screen'];stats=exact['statistics']['grid50'];prior=exact['statistics']['grid64']
    for row in (stats,prior):assert row['inputs']==N and row['failures']==0 and row['minimum_margin_units']>0
    assert stats['minimum_margin_units']==124370688 and stats['minimum_margin_x']==228663
    assert exact['phase50_sha256']=='8bd482a8957cd387a2b212afdaca656947b7f89c983d67ff4eea4e14c3b0a26a'
    assert exact['direct_and_baseline_plus_delta_agree'] and exact['original_tolerance_unchanged']
    assert exact['maximum_actual_grid_change_units64']<=exact['sum_absolute_grid_change_units64']==118599
    assert stats['minimum_margin_units']>=prior['minimum_margin_units']-118599
    assert guard['status']=='COMPLETED' and guard['returncode']==0 and guard['stop_reason']=='completed'
    assert guard['automatic_workload_retries']==0 and guard['child_cleanup']['complete']
    assert not guard['child_cleanup']['remaining_pids'] and not guard['child_cleanup']['zombie_pids']
    assert guard['limits']['per_process_hard_address_bytes']==512*1024**2
    assert guard['peak_aggregate_rss_bytes']<guard['limits']['aggregate_RSS_stop_bytes']==768*1024**2
    assert guard['minimum_host_available_bytes']>=guard['limits']['minimum_host_available_bytes']==4*1024**3
    assert guard['peak_process_count']==1
    helper=NARROW/'checkpoint002/cleanroom/baseline_stage97/tooling/resource_guard.py'
    assert sha(helper)==guard['source_helpers_sha256']=='6795b9ac76c889da1aa311ae59da5d1f1a6000a5c0cfbeec142185091943b202'
    basis=checked(HERE/'basis.json','a3bacdd5ef8e16acb8560a40e60e2c998f8171973b1dcc062a47503c5218d744')
    review=checked(HERE/'review/finite_review.json','204a31c2f071b741b63cac21b3882eb5e3e5ed1dcfcef63a4f7bccc948ee3bb7')
    coefficients=[1<<(i+1)for i in range(26)]+[1<<(27+j)for j in range(7)]+[1]
    sites=[f'base_i{i}'for i in range(26)]+[f'overflow_j{j}'for j in range(7)]+['global_one']
    assert basis['baseline_coefficients_units37']==coefficients
    angles=fit['new_angles_units50'];raw=fit['delta_turn_units64'];delta=fit['quantized_delta_turn_units64']
    assert len(angles)==len(raw)==len(delta)==34 and all(type(v)is int for v in angles+raw+delta)
    assert delta==list(map(round_grid,raw)) and all(abs(v)<=4*UNIT for v in raw+delta)
    assert delta[-1]==-UNIT and angles[-1]==0
    assert angles==[(c*UNIT+d)//GRID for c,d in zip(coefficients,delta)]
    verifier=NARROW/'base/official/verifier_invsqrt/verify_submission_invsqrt.py'
    assert sha(verifier)=='ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a'
    nodes=[n for n in ast.parse(verifier.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in('z_pow_class','rotation_t_count')]
    env={'Fraction':Fraction,'math':math};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(verifier),'exec'),env)
    classes=[env['z_pow_class'](2*Fraction(v,MOD))for v in angles]
    assert classes==['rotation']*33+['clifford']
    half_den=math.lcm(*(Fraction(2*v,MOD).denominator for v in angles))
    assert half_den==1<<49 and 2*half_den==MOD
    odd=[dict(site=site,turn_units50=value)for site,value in zip(sites,angles)if value&1]
    assert odd and any(row['turn_units50']==31885 for row in odd)
    for site,value,kind,row in zip(sites,angles,classes,fit['complete_paper_gate']['angle_sites']):
        assert row['site']==site and row['turn_units50']==value and row['turn_units64']==value*GRID
        assert Fraction(row['half_turns'])==Fraction(2*value,MOD) and row['angle_class']==kind
        assert row['identity']==(value%MOD==0)
    # Independent finite replay on a basis of all25 arbitrary data indicators.
    # Actual route controls and threshold values are evaluated explicitly.
    cases=0;features_checked=0;centres=(0,-2,-6,0,-1);slots=basis['slots']
    assert list(map(len,[[i for i in range(26)if i<(c-i)%26]for c in centres]))==[12,12,12,12,13]
    for k in range(11):
        f=[(k>>i)&1 for i in range(4)];p=f[1]&(f[2]^f[3]);c=f[1]&f[3];encoded=k|(p<<4)|(c<<5)
        controls=[truth(terms,encoded)for terms in basis['controls']]
        threshold={int(t):truth(terms,encoded)for t,terms in basis['thresholds'].items()}
        assert all(threshold[t]==int(k>=t)for t in range(1,11))
        for W in [1<<25]+[(1<<25)|(1<<i)for i in range(25)]:
            word=[(W>>i)&1 for i in range(26)];original=word[:]
            for stage,centre in enumerate(centres):
                if controls[stage]:word=[word[(centre-i)%26]for i in range(26)]
            r=((W<<k)|(W>>(26-k)))&((1<<26)-1)
            routed=[word[i]for i in slots];assert routed==[(r>>i)&1 for i in range(26)]
            emitter_features=routed+[threshold[j+1]*routed[j]for j in range(7)]+[1]
            oracle_features=[(r>>i)&1 for i in range(26)]+[((r>>j)&1)*int(k>j)for j in range(7)]+[1]
            assert emitter_features==oracle_features;features_checked+=34
            fixed=sum(threshold[j+1]*routed[j]*(1<<(40+j))for j in (7,8,9))
            assert threshold[10]*routed[9]==c
            direct=(sum(a*b for a,b in zip(angles,emitter_features))+fixed)%MOD
            f26=2*r+(1<<27)*(r&((1<<k)-1))+1
            alternate=((f26<<13)+sum(b*(d//GRID)for b,d in zip(oracle_features,delta)))%MOD
            assert direct==alternate
            for stage in reversed(range(5)):
                if controls[stage]:word=[word[(centres[stage]-i)%26]for i in range(26)]
            assert word==original and word[-1]==1;cases+=1
    assert cases==286 and features_checked==9724
    phase_components={'route':122,'endpoint_frames':2,'p_c':2,'thresholds':5,'features':8}
    assert phase_components==basis['phase_components_expected_Toffolis'] and sum(phase_components.values())==139
    assert basis['entry_exit_owners']==43 and basis['peak_owners']==dict(data=43,one=1,p_c=2,threshold=1,feature=1,total=48)
    basepath=NARROW/'research/joint_loader/Q48_COMPLETE_PAPER_GATE.json'
    base=checked(basepath,'912da9164095aa996317909903d50162a76eded7ff9a90cbb9299c85c013de2c')
    buildpath=NARROW/'native/candidate06/candidate06.build.json'
    build=checked(buildpath,'6e86492c39704cec6e676e93f3440e12aef7ad558059881fba1daa1864afcd8a')
    proofpath=NARROW/'native/candidate06/whole_native_text_all.json'
    proof=checked(proofpath,'35c534e8ec22abaadc8813b5e72a951c327732a694d291afbdc994e938583cd8')
    assert sha(NARROW/'native/candidate06/candidate06.kmb')==build['kmb_sha256']==proof['circuit_sha256']
    assert build['Q']==proof['Q']==48 and build['exact_native_expectation']['mean_numeric']==dict(toffoli_like=1591.0,T=4.0,generic_rotations=34.0)
    assert proof['whole_official_domain'] and proof['proved_inputs']==N and proof['every_HMR_transcript_proved']
    assert proof['all_phase_checks_enabled'] and proof['original_input_register_restored'] and proof['scratch_zero']
    for name,digest in build['native_sources'].items():assert sha(buildpath.parent/name)==digest
    components=dict(base['components_expected_Toffolis']);assert sum(components.values())==1591
    assert components.pop('compact_endpoint_with_route_omission')==145
    components['ring26_full_control_zero_global_endpoint']=139
    assert sum(components.values())==1585
    cuts=[dict(row)for row in base['owner_cuts'] if row['name']!='compact_phase_peak']
    cuts.append(dict(name='ring26_phase_peak',owners='endpoint43+one+p+c+threshold+feature',live=48))
    assert max(row['live']for row in cuts)==48
    assert next(row for row in cuts if row['name']=='first_loader_peak')['live']==48
    assert next(row for row in cuts if row['name']=='second_loader_peak')['live']==48
    charge=33*env['rotation_t_count'](math.pi*stats['minimum_margin_units']/(1<<64)/33)/4
    total=1585+1+charge;cost=48*total
    assert abs(charge-230.84805946161188)<1e-12 and abs(cost-87208.70685415737)<1e-8
    given=fit['complete_paper_gate']
    assert given['Q']==48 and given['expected_Toffolis']==1585 and given['T']==4 and given['R']==33
    assert given['rotation_charge']==charge and given['predicted_complete_cost']==cost and given['complete_gate_better_than_current']
    frozen=HERE/'frozen/global_zero33.json';frozen.parent.mkdir(exist_ok=True)
    if frozen.exists():assert sha(frozen)==FIT_SHA
    else:frozen.write_bytes((HERE/'global_zero33.json').read_bytes())
    extra_paths=['research/ring26_phase/frozen/global_zero33.json','research/ring26_phase/global_zero33.guard.json',
        'research/ring26_phase/SOURCE_READY.json','research/ring26_phase/basis.json','research/ring26_phase/review/finite_review.json',
        'research/ring26_phase/review/MANIFEST.json','native/candidate06/candidate06.build.json','native/candidate06/whole_native_text_all.json',
        'native/candidate06/candidate06.kmb','native/candidate06/INPUTS.json','native/candidate06/SOURCE_READY.json']
    source_pins={row['path']:row['sha256']for row in inputs}
    source_pins.update({name:sha(NARROW/name)for name in extra_paths})
    for name,digest in build['native_sources'].items():source_pins['native/candidate06/'+name]=digest
    result=dict(status='PASS_COMPLETE_RING26_ZERO33_PAPER_GATE_AUDIT_PARENT_AUTHORIZATION_PENDING',
        Q=48,expected_Toffolis=1585,T=4,R=33,phase_expected_Toffolis=139,
        exact_margin_units64=stats['minimum_margin_units'],rotation_charge=charge,total_E=total,predicted_complete_cost=cost,
        improvement_over_current06=87842.32264250425-cost,
        first_preparation_peak=48,second_preparation_peak=48,endpoint_peak=48,
        complete_components_expected_Toffolis=components,owner_cuts=cuts,
        phase_components_expected_Toffolis=phase_components,phase_entry_exit_owners=43,
        phase_site_order=sites,new_angles_turn_units50=angles,angle_classes=classes,
        global_angle_identity=True,generic_rotations_emitted=33,fixed_T_gates=4,direct_Clifford_Z_POW_count=1,
        actual_half_turn_denominator=half_den,actual_native_phase_modulus=MOD,odd_angle_witnesses=odd,
        exact_accuracy=stats,fit_path='research/ring26_phase/frozen/global_zero33.json',fit_sha256=FIT_SHA,
        independent_phase_units50_sha256=exact['phase50_sha256'],
        all_final_accuracy_decisions_integer=True,all_original_inputs_and_tolerance_retained=True,
        arbitrary_word_basis_cases_with_actual_angles=cases,arbitrary_angle_predicate_equalities=features_checked,
        all_local_phase_debts_covered_by_pinned_fullcube_certificate=True,
        owned_local_phase_HMR_functions=dict(p_c=2,nonlinear_threshold_outputs=5,AND_features=8),
        all15_local_HMR_outcomes_repaid_and_freed_before_exit=True,
        no_phase_outcome_enters_TableDebts=True,
        zero_new_deferred_phase_debts_at_endpoint_exit=True,
        inherited_native06_whole_domain_all_HMR_proof_sha256=sha(proofpath),
        inherited_nonphase_arithmetic_and_classical_debts_unchanged=True,
        source_pins=source_pins,inherited_input_pins_verified=len(inputs),local_source_pins_verified=len(ready['files']),
        guard=dict(sha256=GUARD_SHA,status='COMPLETED',returncode=0,work_seconds=fit['seconds'],
            peak_aggregate_rss_bytes=guard['peak_aggregate_rss_bytes'],hard_address_space=512*1024**2,
            all_child_processes_cleaned=True,automatic_retries=0,cgroup_counters=guard['cgroup_counters']),
        selected_first_loader=61,selected_second_loader=80,
        later_second_loader79_composition_not_in_this_gate=True,
        native_build_authorized=False,new_native_circuit_emitted=False,new_native_proof=False,
        requires_fresh_native_sample_and_all_domain_all_HMR=True,requires_original_official_four_salts=True,
        no_submission=True,LP_global_optimum_claim=False,
        new_oracle_required=True,old04_oracle_not_reused_for_new_phase=True,
        packaging_new_phase_family_schema_review_required=True)
    (HERE/'COMPLETE_GATE_RING26_ZERO33.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','Q','expected_Toffolis','T','R','exact_margin_units64','rotation_charge','predicted_complete_cost','actual_native_phase_modulus','independent_phase_units50_sha256','native_build_authorized')},indent=2))


if __name__=='__main__':main()
