# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Independent scalar interface/phase audit before the first positive gate.

No native circuit is emitted. Parent's all-input bitset certificates remain
separately pinned; these checks use scalar selectors, payload basis vectors,
and algebraic phase identities rather than that bitset simulation.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import json,hashlib,resource,sys,itertools
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
sys.path.insert(0,str(NARROW/'checkpoint002/cleanroom/baseline_stage97/engine'))
from stage94_bit_routing_math import operations
from seed_cleanup_screen import cb

PINS={
 'research/quantized_producer/pair_normalization.py':'6af7fc14bc3c904efe480e2e23aee2fcbd97ad23f0a7ba324d8c05e1c8ec17fe',
 'research/quantized_producer/pair_normalization.json':'16ae519e925ce8964c93329ba34928a954dfe6efa5f353062f369a8f78a4e619',
 'research/recompute_root/initializer_u12/u12_certificate.json':'3da759edf4c93ef6fc94b6a373661d7729fcba2bfbedccfc34de1bf55f1517c0',
 'research/recompute_root/initializer_u12/model_interface.json':'876246eb40158ad9695302f68dd413b0991ba6be423aad9abe6200528204be29',
 'research/joint_loader/frozen/loader16_first62.json':'c8af534ce6f86ef977dfe7c88306f6eb8610584d9571f3b14424539777e32213',
 'research/joint_loader/frozen/loader16_second76.json':'f29768cfb6f79251c715761fc832feb491f48c729ddb874b725f9926ee5be322',
 'research/joint_loader/frozen/loader16_first62.replay.json':'fe0355e50b440452cc34cea35bd6dcf349ea76137b9556c9b3f43e814de885a6',
 'research/joint_loader/frozen/loader16_second76.replay.json':'9c45213ac89d250f9511da5bf9bb47fb983fe14fc15c1ae68535b018e45ef019',
 'research/joint_loader/frozen/loader16_first60.json':'3bcbd49ad53c0e2661bbc1112d172c854d4bf50ba4ea1f9a119a077f8e6cd9fd',
 'research/joint_loader/frozen/loader16_second73.json':'52db753c9efef945c9194ed4a39ec3b250221b69eb10e0030dc2a283f659eafc',
 'research/joint_loader/frozen/loader16_first60.replay.json':'4fbeaff1419fc647498f7762c2e5bed4170c8d2e785c617b9470699d692177b3',
 'research/joint_loader/frozen/loader16_second73.replay.json':'ee4748459fb24a847f7ed3e2952aa4b26595c144f5a1162e1725fc125ac068ec',
}


def asplan(d):
    return cb.QuadraticCodePlan(**{**d,'edges':tuple(map(tuple,d['edges'])),'products':tuple(map(tuple,d['products']))})


def main():
    data={}
    for path,sha in PINS.items():
        raw=(NARROW/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha,path
        if path.endswith('.json'):data[path]=json.loads(raw)
    norm=data['research/quantized_producer/pair_normalization.json']
    sequence=operations(11);assert len(sequence)==17
    route_checks=0;selectors=0
    for k in range(11):
        thresholds=[int(k>=j)for j in range(1,11)]
        for operation in sequence:
            control=sum(thresholds[j-1]for j in operation['prefix_terms']if j<=10)&1
            assert control==((operation['selector_truth']>>k)&1)
            selectors+=1
        for source in range(22-2*k):
            word=1<<source;old=word
            for operation in sequence:
                control=sum(thresholds[j-1]for j in operation['prefix_terms']if j<=10)&1
                if control:
                    for lane in range(2):
                        a=2*operation['first']+lane;b=2*operation['second']+lane
                        delta=((word>>a)^(word>>b))&1;word^=(delta<<a)|(delta<<b)
            assert word==old<<(2*k)
            for operation in reversed(sequence):
                control=sum(thresholds[j-1]for j in operation['prefix_terms']if j<=10)&1
                if control:
                    for lane in range(2):
                        a=2*operation['first']+lane;b=2*operation['second']+lane
                        delta=((word>>a)^(word>>b))&1;word^=(delta<<a)|(delta<<b)
            assert word==old;route_checks+=1
    odd_checks=0;binary_checks=0;threshold_checks=0
    for ell in range(22):
        k=ell//2;high=1-(ell&1)
        T=lambda j:int(k>=j)
        for bit in range(4):
            assert(sum(T(j)for j in range(1<<bit,11,1<<bit))&1)==((k>>bit)&1)
            binary_checks+=1
        for j in range(1,11):
            actual=int(ell>=2*j-1)
            proposed=T(j-1)^(high&(T(j-1)^T(j)))
            for outcome in range(2):assert(outcome*actual)^(outcome*proposed)==0;odd_checks+=1
    for k in range(11):
        value=k|((((k>>0)&1)&((k>>1)&1))<<4)
        for j,p in enumerate(norm['threshold_plans'],1):
            assert asplan(p).evaluate_bits(value)==int(k>=j)
            threshold_checks+=1
    inverse_phase_checks=0
    for prev,a,b,outcome in itertools.product(range(2),repeat=4):
        target=prev*(1-a)*(1-b)
        correction=prev^(prev*a)^(prev*b)^(prev*a*b)
        assert outcome*target==outcome*correction;inverse_phase_checks+=1
    assert norm['certificate']['original_inputs']==3133452
    assert norm['certificate']['total_independent_HMR_symbols']==31
    assert norm['certificate']['total_expected_E']==18+34+1+6+34+9/2==97.5
    assert norm['certificate']['peak']==22+4+20==46
    abstract=0
    for v,b12,b13,b14 in itertools.product(range(4096),range(2),range(2),range(2)):
        V=4096+v;u10=-1-v
        u11=2*u10+V+1+b13-b14
        assert u11==4095-v+b13-b14
        u12=2*u11-V+b12-b13
        assert u12==4094-3*v+b13-2*b14+b12;abstract+=1
    u12=data['research/recompute_root/initializer_u12/u12_certificate.json']
    for row in u12['rows']:
        assert row['Toffolis']==25 and row['peak']==47 and row['HMR_sign_functions_proved']==38
        assert row['forward']['total_Toffolis']==24 and row['cleanup']['Toffolis']==1
        assert row['all_ancillas_zero'] and row['all_phase_debts_paid']
    actual=data['research/recompute_root/initializer_u12/model_interface.json']
    for row in actual['results']:
        assert row['normalized_inputs']==3145728
        assert all(row[k]==0 for k in('prefix_failures','initializer_mismatches','physical_u14_overflows','previous_bit_failures','consumed_bit_recovery_failures'))
        assert row['next_recurrence_index']==12 and row['previous_input']=='Original product bit b12'
    loader_records=[]
    for name,cost,fixed in [('first60',60,26),('second73',73,31),('first62',62,26),('second76',76,31)]:
        path=f'research/joint_loader/frozen/loader16_{name}.json'
        rpath=f'research/joint_loader/frozen/loader16_{name}.replay.json'
        loader=data[path];replay=data[rpath]
        assert replay['status']=='INDEPENDENT_EXACT_MATHEMATICAL_REPLAY_PASS'
        assert replay['certificate_sha256']==PINS[path]
        assert replay['Toffolis']==loader['Toffolis']==cost
        assert replay['output_bits']==loader['output_bits']==list(range(16))
        assert replay['work_peak']==loader['work_peak'] and fixed+loader['work_peak']==49
        assert replay['restored_raw_A13_H0_H1_H2_chart_rank']==128
        loader_records.append(dict(name=name,Toffolis=cost,fixed_owners=fixed,work_peak=loader['work_peak'],peak=49,
            independent_HMR_generators=replay['HMR_debts'],raw_address=loader['raw_address']))
    out=dict(status='INDEPENDENT_INTERFACE_AND_PHASE_AUDIT_PASSED_NOT_NATIVE',source_pins=PINS,
        pair_normalization=dict(scalar_payload_basis_roundtrips=route_checks,selector_cases=selectors,odd_prefix_outcome_cases=odd_checks,binary_flag_cases=binary_checks,
            threshold_code_cases=threshold_checks,inverse_local_phase_cases=inverse_phase_checks,Toffolis_expected=97.5,T=0,R=0,peak=46,
            source_audit='P2 uses the unchanged x<3*2^20 promise; each lane has at leastk leading zeros. Prefix borrows are restored before measurement. Odd phases retain all even prefixes; g is allocated only after odd retirement. Even repairs are quadratic flags+g; g has its own measured-AND repair. Inverse thresholds are erased longest-first, so each parent remains. All nine conditionalCCZ terms and the first outcome-dependent constant are included.'),
        u12=dict(abstract_recurrence_identities=abstract,actual_normalized_cases_per_model=3145728,Toffolis=25,peak=47,
            source_audit='The lowblock phase identities expressP13/P14 in vlow,P12,u0,u1 and repay their HMR erasure signs. Every local carry phase is repaid immediately. Cleanup recreates those logical P owners, then erasesu high-to-low while each loweru parent survives. It uses rawroot, so all metadata R frames must occur after this cleanup. Return the updatedP array; P14 may occupy a new physicalID.',
            next_index=12,previous_bit='OriginalP12',assumption='sigma10=1 andsigma11=0 are verified on both actual models; the abstract algebra alone does not assert those signs for arbitrary product triples.'),
        loaders=loader_records,native=False,official_verifier=False)
    (HERE/'v4_independent_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items()if k!='source_pins'},indent=2))

if __name__=='__main__':main()
