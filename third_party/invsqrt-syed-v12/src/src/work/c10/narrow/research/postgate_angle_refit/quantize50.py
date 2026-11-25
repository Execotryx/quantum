#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Independent exact full-domain2^-50-turn quantization screen; no native.

Prepared for the parent's serial guarded slot. It streams bounded chunks,
uses exact integer rounding/comparisons, and preserves every baseline file.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
from fractions import Fraction
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,sys,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
GRID64=1<<14;BASE_UNIT64=1<<27;MASK37=(1<<37)-1
PINS={
 'research/postgate_angle_refit/refit.py':'4f19919c27cd6a0a24bb827fe94982460c974f7b3148aaa03041fafcdd683edd',
 'research/postgate_angle_refit/refit.json':'ac5ee39daa12bcd3046ae4445b4bbf464e30c7d39d40f713f2eb51331717bb19',
 'research/postgate_angle_refit/feature_map.py':'df11494fac08e4e0403325327ab25f500ffa696a592e6d7dfb40aa3d379b7fd5',
 'research/postgate_angle_refit/feature_map.json':'19a5668492a76f5d16c6656f198951939ce5a678fc80c0d214bf7e3c9e945bde',
 'native/candidate01/whole_model.py':'740b3530990003de29fc3a29726c1ac7f97aa29467fc14fd7608f5c5f58bfca4',
 'native/candidate01/common.py':'9872e64213a4219522a87efc49d1aa549a04e43ae3fb51c9d5b762b1ea6535ab',
 'native/candidate01/divider.py':'d0dbaf6fe4227da988c9cb9e9dee847624992c7c5cce7ab347990d5b0a116c05',
 'base/official/verifier_invsqrt/verify_submission_invsqrt.py':'ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a',
 'research/recompute_root/models/phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json':'24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219',
 'native/candidate03/candidate03.build.json':'151eb2dea6f0158e9923e9a50376a3522418135626d467e41bd168e74913cb1e',
 'native/candidate03/whole_native_text_all.json':'7514b738b6494f57dc0569bae72ee9495bb21819db2d51130f11599cf6a28a96',
 'native/candidate03/candidate03.kmb':'e60699395ff7868de45b996bee8314238cac33f3ef7eff2f4dc17eb6cc70e094',
}
# The feature-map source pin is checked before importing any candidate source.


def checked_sources():
    for relative,expected in PINS.items():
        actual=hashlib.sha256((NARROW/relative).read_bytes()).hexdigest()
        assert actual==expected,(relative,actual,expected)


def round_to_grid(value):
    """Nearest integer multiple, ties to even; exact for negative values too."""
    assert type(value)is int
    q,r=divmod(value,GRID64)
    if 2*r>GRID64 or (2*r==GRID64 and q&1):q+=1
    return q*GRID64


def make_stats():
    return dict(inputs=0,failures=0,minimum_margin_units=(1<<63)-1,
                minimum_margin_x=None,worst_error_over_tolerance=0.0,worst_ratio_x=None)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--chunk',type=int,default=16384)
    ap.add_argument('--output',default='quantize50.json');args=ap.parse_args()
    assert 256<=args.chunk<=65536
    checked_sources();began=time.monotonic()
    refit=json.loads((HERE/'refit.json').read_text())
    formal=json.loads((HERE/'feature_map.json').read_text())
    build=json.loads((NARROW/'native/candidate03/candidate03.build.json').read_text())
    native=json.loads((NARROW/'native/candidate03/whole_native_text_all.json').read_text())
    assert formal['status']=='PASS_FORMAL_GENERIC_FEATURE_IDENTITY'
    assert formal['generic_sites']==34 and formal['exponent_classes']==11
    assert refit['status']=='EXACT_ALL_INPUT_ANGLE_REFIT_PAPER_PASS_NATIVE_PENDING'
    assert refit['fixed_R']==34 and refit['fixed_T']==4
    assert native['whole_official_domain'] and native['proved_inputs']==3133452
    assert native['every_HMR_transcript_proved'] and native['circuit_sha256']==build['kmb_sha256']
    counts=build['exact_native_expectation']['mean_numeric']
    assert build['Q']==49 and counts==dict(toffoli_like=1562.5,T=4.0,generic_rotations=34.0)
    old_delta=refit['delta_turn_units64'];assert len(old_delta)==34 and all(type(v)is int for v in old_delta)
    assert max(map(abs,old_delta))<=BASE_UNIT64
    delta=[round_to_grid(v)for v in old_delta]
    assert all(v%GRID64==0 for v in delta)
    change=[a-b for a,b in zip(delta,old_delta)]
    assert max(map(abs,change))<=GRID64//2
    coefficients=[(1<<i)+((1<<27)if i==0 else 0)for i in range(27)]
    coefficients +=[-(1<<27)]+[1<<(27+j)for j in range(1,7)]
    assert coefficients==refit['baseline_generic_feature_coefficients_units37']
    new_angles=[coefficient*BASE_UNIT64+d for coefficient,d in zip(coefficients,delta)]
    names=[f'base_i{i}'for i in range(27)]+['threshold_j0']+[f'overflow_j{j}'for j in range(1,7)]
    sys.path.insert(0,str(NARROW/'native/candidate01'))
    import numpy as np
    from whole_model import phase_units,MAX_X
    sp=importlib.util.spec_from_file_location('quantize50_original_verifier',NARROW/'base/official/verifier_invsqrt/verify_submission_invsqrt.py')
    verifier=importlib.util.module_from_spec(sp);sys.modules[sp.name]=verifier;sp.loader.exec_module(verifier)
    spec=verifier.ProblemSpecInvSqrt.for_n_p(10)
    assert MAX_X==spec.max_x==3133452 and spec.precision_bits==24
    angle_records=[]
    for name,units,d in zip(names,new_angles,delta):
        turns=Fraction(units,1<<64);half=2*turns
        assert verifier.z_pow_class(half)=='rotation',(name,half)
        assert turns.denominator<=(1<<50) and (1<<50)%turns.denominator==0
        angle_records.append(dict(site=name,turn_units64=units,turn_units50=units//GRID64,
                                  delta_turn_units64=d,turns=str(turns),half_turns=str(half),angle_class='rotation'))
    maximum_denominator=max(Fraction(u,1<<64).denominator for u in new_angles)
    old_np=np.array(old_delta,dtype=np.int64);new_np=np.array(delta,dtype=np.int64)
    coeff_np=np.array(coefficients,dtype=np.int64)
    stats={name:make_stats()for name in ('baseline','old_refit','quantized50')}
    max_change=0;max_change_x=None;max_active=0;max_signed=0;feature_sha=hashlib.sha256();phase_sha=hashlib.sha256()

    def add_stats(name,errors,tolerance,xs):
        assert np.all((-1<<62)<errors)and np.all(errors<(1<<62))
        margin=tolerance-np.abs(errors);record=stats[name];record['inputs']+=len(xs)
        record['failures']+=int((margin<0).sum());at=int(margin.argmin())
        if int(margin[at])<record['minimum_margin_units']:
            record['minimum_margin_units']=int(margin[at]);record['minimum_margin_x']=int(xs[at])
        ratios=np.abs(errors)/tolerance;at=int(ratios.argmax())
        if float(ratios[at])>record['worst_error_over_tolerance']:
            record['worst_error_over_tolerance']=float(ratios[at]);record['worst_ratio_x']=int(xs[at])

    for first in range(1,MAX_X+1,args.chunk):
        xs=np.arange(first,min(MAX_X+1,first+args.chunk),dtype=np.int64)
        word,chart=phase_units(xs,return_chart=True);word=word.astype(np.int64);k=chart['flags']
        z=word&((1<<27)-1)
        # Recover the unshifted endpoint independently from the cyclic bits.
        p=(z>>k)|((z&((1<<k)-1))<<(27-k))
        assert np.all((p&1)==1)and np.all(((p>>26)&1)==1)
        assert np.array_equal(((p<<k)+(p>>(27-k)))&MASK37,word)
        F=np.empty((len(xs),34),dtype=np.int64)
        F[:,:27]=(z[:,None]>>np.arange(27,dtype=np.int64)[None,:])&1
        F[:,27]=(k==0)
        for j in range(1,7):F[:,27+j]=((z>>j)&1)*(k>j)
        raw_phase=F@coeff_np
        for j in (7,8,9):raw_phase+=((z>>j)&1)*(k>j)*(1<<(27+j))
        assert np.array_equal(raw_phase&MASK37,word),'Exact native-feature identity'
        packed=np.zeros(len(xs),dtype=np.uint64)
        for i in range(34):packed|=F[:,i].astype(np.uint64)<<np.uint64(i)
        feature_sha.update(packed.astype('<u8',copy=False).tobytes())
        target,tolerance=verifier.reference_values(spec,xs.astype(np.uint64));tol=tolerance.astype(np.int64)
        baseline_units=word.astype(np.uint64)<<np.uint64(27)
        baseline_error=(baseline_units-target).view(np.int64)
        old_shift=F@old_np;new_shift=F@new_np
        assert max(map(abs,old_delta))*34<(1<<62)
        old_error=baseline_error+old_shift;new_error=baseline_error+new_shift
        # An independent modulo2**64 path must match the signed path exactly.
        old_mod=((baseline_units+old_shift.astype(np.uint64))-target).view(np.int64)
        new_mod=((baseline_units+new_shift.astype(np.uint64))-target).view(np.int64)
        assert np.array_equal(old_error,old_mod)and np.array_equal(new_error,new_mod)
        add_stats('baseline',baseline_error,tol,xs);add_stats('old_refit',old_error,tol,xs);add_stats('quantized50',new_error,tol,xs)
        phase50=((word.astype(np.uint64)<<np.uint64(13))+(new_shift//GRID64).astype(np.uint64))&np.uint64((1<<50)-1)
        assert np.array_equal((phase50<<np.uint64(14)),baseline_units+new_shift.astype(np.uint64))
        phase_sha.update(phase50.astype('<u8',copy=False).tobytes())
        actual_change=np.abs(new_shift-old_shift);at=int(actual_change.argmax())
        if int(actual_change[at])>max_change:max_change=int(actual_change[at]);max_change_x=int(xs[at])
        max_active=max(max_active,int(F.sum(axis=1).max()));max_signed=max(max_signed,int(np.abs(new_error).max()))
    assert stats['baseline']['minimum_margin_units']==31966138 and stats['baseline']['failures']==0
    old=refit['exact_original_tolerance']
    for key in ('inputs','failures','minimum_margin_units','minimum_margin_x'):
        assert stats['old_refit'][key]==old[key],(key,stats['old_refit'][key],old[key])
    assert max_change<=sum(map(abs,change))
    final=stats['quantized50'];margin=final['minimum_margin_units']
    assert final['inputs']==MAX_X
    charge=None if margin<=0 else 34*verifier.rotation_t_count(math.pi*margin/(1<<64)/34)/4
    fixed=counts['toffoli_like']+counts['T']/4
    passed=margin>31966138 and final['failures']==0
    result=dict(status='EXACT_ALL_INPUT_QUANTIZE50_PAPER_PASS_NATIVE_PENDING'if passed else'QUANTIZE50_PAPER_CLOSED_NO_GAIN',
                source_pins=PINS,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                inputs=MAX_X,chunk=args.chunk,original_tolerance_unchanged=True,
                quantization='Exact integer nearest multiple of16384, ties to even',
                phase_grid_turns='1/1125899906842624',maximum_generic_turn_denominator=maximum_denominator,
                delta_turn_units64=delta,new_generic_turn_units64=new_angles,
                new_generic_turn_units50=[u//GRID64 for u in new_angles],angle_sites=angle_records,
                exact_statistics=stats,maximum_actual_quantization_change_units=max_change,
                maximum_actual_quantization_change_x=max_change_x,
                sum_absolute_angle_quantization_change_units=sum(map(abs,change)),
                maximum_active_generic_predicates=max_active,maximum_abs_quantized_error_units=max_signed,
                feature_mask_sha256=feature_sha.hexdigest(),quantized_phase50_sha256=phase_sha.hexdigest(),
                all_angle_classes_exactly_generic=True,fixed_T=4,fixed_R=34,Q=49,
                expected_Toffolis=counts['toffoli_like'],rotation_charge=charge,
                predicted_complete_cost=None if charge is None else 49*(fixed+charge),
                predicted_complete_E=None if charge is None else fixed+charge,
                candidate03_arithmetic_native_proved=True,new_phase_native_proved=False,
                official_four_salts_required=True,no_native_emission=True,
                accuracy_decision_uses_only_integer_arithmetic=True,
                LP_global_optimum_claim=False,seconds=time.monotonic()-began,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    out=HERE/args.output;temporary=out.with_suffix(out.suffix+'.tmp');temporary.write_text(json.dumps(result,indent=2)+'\n');temporary.replace(out)
    print(json.dumps({k:result[k]for k in ('status','inputs','expected_Toffolis','rotation_charge','predicted_complete_cost','seconds','peak_rss_kib')}))
    print(json.dumps(final))


if __name__=='__main__':main()
