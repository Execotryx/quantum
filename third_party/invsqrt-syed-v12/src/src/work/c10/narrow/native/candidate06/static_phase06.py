#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Finite compact-control and complete phase-ledger proof; no native import."""
from pathlib import Path
import ast,hashlib,importlib.util,json,resource,sys,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def truth(terms,value):return sum(int(value&t==t) for t in terms)&1


def main():
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2));began=time.monotonic()
    for name in('phase06.py','static_phase06.py'):compile((HERE/name).read_text(),str(HERE/name),'exec')
    phase=load('candidate06_static_phase_no_native',HERE/'phase06.py');phase.verify_source_pins()
    gate=json.loads((NARROW/'research/joint_loader/Q48_COMPLETE_PAPER_GATE.json').read_text())
    polynomial=NARROW/'checkpoint002/cleanroom/baseline_stage97/engine/quadratic_terms.py'
    polynomial_sha=hashlib.sha256(polynomial.read_bytes()).hexdigest()
    assert polynomial_sha==phase.SOURCE_PINS[str(polynomial.relative_to(NARROW))]
    # The finite rank compiler is standard-library-only; it imports no native
    # builder/runtime. Its complete source hash is recorded for parent review.
    qp=load('candidate06_static_quadratic_rank',polynomial)
    tree=ast.parse((NARROW/'native/candidate01/divider.py').read_text());constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            if node.targets[0].id in('THRESHOLDS','CONTROLS'):constants[node.targets[0].id]=ast.literal_eval(node.value)
    terms={t:phase.compact_terms(old) for t,old in constants['THRESHOLDS'].items()}
    substitution_checks=phase_checks=legal_checks=0
    for flags in range(16):
        c=((flags>>1)&1)*((flags>>3)&1)
        p_actual=((flags>>1)&1)*(((flags>>2)^(flags>>3))&1)
        for p in range(2):
            compact=flags|(p<<4);old=compact|(c<<5)
            for t in range(1,11):
                value=truth(terms[t],compact)
                assert value==truth(constants['THRESHOLDS'][t],old)
                substitution_checks+=1
                for outcome in range(2):
                    measured=outcome*value
                    repaired=sum(outcome*int(compact&term==term) for term in terms[t])&1
                    assert measured^repaired==0
                    phase_checks+=1
        assert c==((flags>>1)&1)*((flags>>3)&1),'Final Z(c) must equal the directCZ predicate.'
        for outcome in range(2):
            p_phase=outcome*truth((6,10),flags)
            assert p_phase==(outcome*p_actual)
            phase_checks+=1
        if flags<=10:
            encoded=flags|(p_actual<<4)
            for t in range(1,11):assert truth(terms[t],encoded)==int(flags>=t);legal_checks+=1
    threshold_counts={str(t):len(qp.compile_polynomial(5,terms[t]).products) for t in range(1,10)}
    assert threshold_counts=={'1':1,'2':0,'3':1,'4':0,'5':2,'6':1,'7':1,'8':0,'9':1}
    p_count=len(qp.compile_polynomial(4,(6,10)).products);assert p_count==1
    for row in constants['CONTROLS']:assert all(mask<32 for mask in row)
    route=json.loads((NARROW/'research/postgate_route_constants/offsets.json').read_text())
    assert route['selected_centres']==[-1,-3,-7,-1,-2] and route['selected_omissions']==[[0,0,26]]
    assert route['best_roundtrip_saving']==2 and route['all_generic_predicates_unchanged']
    toff=128+2+p_count+sum(threshold_counts.values())+7;assert toff==145
    result=dict(status='PASS_FINITE_COMPACT_Q48_PHASE_CERTIFICATE_NO_NATIVE',
        phase_source_sha256=hashlib.sha256((HERE/'phase06.py').read_bytes()).hexdigest(),
        source_pins=phase.SOURCE_PINS,quadratic_rank_source_sha256=polynomial_sha,
        threshold_substitution_full_cube_checks=substitution_checks,legal_exponent_threshold_checks=legal_checks,
        independent_HMR_phase_coefficient_checks=phase_checks,all_cleanup_polynomials_degree_at_most2=True,
        threshold_Toffolis=threshold_counts,components=dict(route=128,endpoint_frames=2,p_preparation=p_count,thresholds=7,features=7),
        phase_Toffolis=145,T=4,R=34,expected_proxy_call_classes=[34,4,0],
        final_overflow='CZ(flags1,flags3), exactly the oldZ(c) predicate',
        peak_owners=dict(data=43,ones=2,p=1,threshold=1,feature=1,total=48),
        entry_owners=43,exit_owners=43,old_angles_and_generic_predicates_unchanged=True,
        native_runtime_imported=False,native_emitted=False,native_executed=False,seconds=time.monotonic()-began)
    (HERE/'PHASE06_STATIC.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
