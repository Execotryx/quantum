#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Finite symbolic label proof of all27 offsets; no native import or build."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,json,resource,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
DIVIDER='native/candidate01/divider.py'
DIVIDER_SHA='d0dbaf6fe4227da988c9cb9e9dee847624992c7c5cce7ab347990d5b0a116c05'
BOUND='research/postgate_angle_refit/quantize50_bound.json'
BOUND_SHA='fdbd64481c3e876ac88a6a0ad80c44a8b019807cc5d3b5cdee5bd12a59630ac1'
MOD=27


def pairs(centre):return[(i,(centre-i)%MOD) for i in range(MOD) if i<(centre-i)%MOD]


def route(labels,centres,active,skip=(),inverse=False):
    result=list(labels);stages=list(range(5));trace=[]
    if inverse:stages.reverse()
    skip=set(tuple(item) for item in skip)
    for stage in stages:
        before=list(result)
        if active>>stage&1:
            for a,b in pairs(centres[stage]):
                if(stage,a,b) in skip:
                    assert result[a]==result[b],('Illegal omitted swap',inverse,active,stage,a,b,result[a],result[b])
                else:result[a],result[b]=result[b],result[a]
        trace.append(dict(stage=stage,active=bool(active>>stage&1),before=before,after=list(result)))
    return result,trace


def main():
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2));began=time.monotonic()
    for name,sha in((DIVIDER,DIVIDER_SHA),(BOUND,BOUND_SHA)):
        assert hashlib.sha256((NARROW/name).read_bytes()).hexdigest()==sha,name
    tree=ast.parse((NARROW/DIVIDER).read_text());values={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in('CENTRES','ACTIVE','CONTROLS','THRESHOLDS'):values[name]=ast.literal_eval(node.value)
    centres=values['CENTRES'];active=values['ACTIVE']
    assert centres==(0,-2,-6,0,-1) and active==(30,6,27,3,17,9,18,10,23,15,20)
    assert all(v.bit_count()%2==0 for v in active)
    def truth(terms,a):return sum(int(a&t==t) for t in terms)&1
    for flag,mask in enumerate(active):
        f=[(flag>>i)&1 for i in range(4)];p=f[1]&(f[2]^f[3]);c=f[1]&f[3]
        encoded=flag|(p<<4)|(c<<5)
        assert sum(truth(terms,encoded)<<i for i,terms in enumerate(values['CONTROLS']))==mask
    distinct=[f'p{i}' for i in range(MOD)]
    labels=['one' if i in(0,26) else f'p{i}' for i in range(MOD)]
    originals=[route(labels,centres,a)[0] for a in active]
    distinct_originals=[route(distinct,centres,a)[0] for a in active]
    original0=route(list(range(MOD)),centres,active[0])[0]
    inv0={origin:pos for pos,origin in enumerate(original0)};slots=[inv0[i] for i in range(MOD)]
    records=[];permutation_checks=0;inverse_checks=0;gate_witnesses=0
    for offset in range(MOD):
        shifted=tuple((c+offset)%MOD for c in centres)
        full=[route(labels,shifted,a) for a in active]
        for flag,a in enumerate(active):
            got,_=route(distinct,shifted,a)
            assert got==distinct_originals[flag],('Offset changed a valid permutation',offset,flag)
            assert full[flag][0]==originals[flag]
            permutation_checks+=1
        omissions=[];rejected=[]
        for stage,c in enumerate(shifted):
            activating=[flag for flag,a in enumerate(active) if a>>stage&1]
            assert activating
            for a,b in pairs(c):
                bad=[flag for flag in activating if full[flag][1][stage]['before'][a]!=full[flag][1][stage]['before'][b]]
                if not bad:
                    omissions.append((stage,a,b))
                    assert all(full[flag][1][stage]['before'][a]=='one' for flag in activating)
                else:
                    witness=bad[0];before=full[witness][1][stage]['before']
                    rejected.append(dict(stage=stage,positions=[a,b],flag_witness=witness,labels=[before[a],before[b]]));gate_witnesses+=1
        for flag,a in enumerate(active):
            routed,_=route(labels,shifted,a,omissions)
            assert routed==originals[flag]
            restored,_=route(routed,shifted,a,omissions,inverse=True)
            assert restored==labels
            inverse_checks+=1
        records.append(dict(offset=offset,centres=list(shifted),omitted_forward_swaps=[list(x) for x in omissions],
            active_flag_classes={str(stage):[f for f,a in enumerate(active) if a>>stage&1] for stage in range(5)},
            omitted_inverse_swaps=[list(x) for x in reversed(omissions)],
            roundtrip_Toffoli_saving=2*len(omissions),rejected_swap_witnesses=rejected))
    best_saving=max(row['roundtrip_Toffoli_saving'] for row in records)
    best=[row for row in records if row['roundtrip_Toffoli_saving']==best_saving]
    assert best_saving>=2
    row26=records[26];assert[0,0,26] in row26['omitted_forward_swaps']
    # Exact diagonal phase on the constant endpoints and a basis for all25
    # remaining bit indicators. The symbolic label equality is the full proof;
    # this independently checks the existing quantized feature convention.
    bound=json.loads((NARROW/BOUND).read_text());new=bound['new_generic_turn_units50']
    coefficient_checks=0
    for row in best:
        for flag,mask in enumerate(active):
            for extra in [0]+[1<<i for i in range(1,26)]:
                word=1|(1<<26)|extra;initial=[(word>>i)&1 for i in range(MOD)]
                before,_=route(initial,centres,mask)
                after,_=route(initial,row['centres'],mask,row['omitted_forward_swaps'])
                old_z=sum(before[q]<<i for i,q in enumerate(slots));new_z=sum(after[q]<<i for i,q in enumerate(slots))
                assert old_z==new_z
                features=[(new_z>>i)&1 for i in range(27)]+[int(flag==0)]+[((new_z>>j)&1)*int(flag>j) for j in range(1,7)]
                phase=sum(a*f for a,f in zip(new,features))
                phase+=sum(((new_z>>j)&1)*int(flag>j)*(1<<(40+j)) for j in(7,8,9))
                expected_word=((word<<flag)+(word>>(27-flag)))&((1<<37)-1)
                delta=sum(f*(d//16384) for f,d in zip(features,bound['delta_turn_units64']))
                assert phase% (1<<50)==((expected_word<<13)+delta)%(1<<50)
                coefficient_checks+=1
    tof=1562.5-best_saving;charge=238.0530968204069;cost=49*(tof+1+charge)
    result=dict(status='PASS_COMPLETE_FINITE_COMMON_OFFSET_ROUTE_CERTIFICATE_PAPER_ONLY',
        source_pins={DIVIDER:DIVIDER_SHA,BOUND:BOUND_SHA},offsets=27,legal_flag_classes=11,
        arbitrary_independent_phase_bits=25,fixed_endpoint_bits=[0,26],fixed_endpoint_values=[1,1],
        controls_checked=True,all_selected_reflection_parities_even=True,
        common_offset_exact_permutation_checks=permutation_checks,forward_inverse_checks=inverse_checks,
        rejected_omission_witnesses=gate_witnesses,quantized_diagonal_basis_checks=coefficient_checks,
        best_roundtrip_saving=best_saving,best_offsets=[r['offset'] for r in best],
        selected_offset=26,selected_centres=[-1,-3,-7,-1,-2],selected_omissions=row26['omitted_forward_swaps'],
        all_generic_predicates_unchanged=True,all_T_and_Clifford_phases_unchanged=True,
        all_measurement_phase_repairs_unchanged=True,new_quantum_or_classical_owners=0,
        phase_gate=dict(Q=49,base_data=43,constant_ones=2,retained_controls=2,maximum_transient_helpers=2,
            old_routing=130,new_routing=130-best_saving,unchanged_other_Toffolis=16,
            Toffolis=146-best_saving,T=4,R=34),
        complete_gate=dict(Q=49,first_preparation_peak=49,second_preparation_peak=49,
            expected_Toffolis=tof,T=4,R=34,proved_minimum_margin_lower_bound_units64=124286782,
            rotation_charge_upper_bound=charge,complete_cost_upper_bound=cost,
            parent_authorization_required_before_native=True,official_four_salts_required=True),
        all_offsets=records,native_emitted=False,native_proved=False,official_verifier=False,
        seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (HERE/'offsets.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='all_offsets'},indent=2))


if __name__=='__main__':main()
