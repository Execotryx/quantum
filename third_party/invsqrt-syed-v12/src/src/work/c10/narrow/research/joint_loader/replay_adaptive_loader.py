# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Independent exhaustive Boolean/linear-owner replay of a saved loader.

No synthesis/codebook routines are imported. This checks source SHA pins,
every affine frame's invertibility, every factor frame's distinct pivots, every
owner transition, all128 truth rows and each individual HMR debt function.
This remains a mathematical replay, not a quantum-native circuit proof.
"""
from pathlib import Path
import argparse
import hashlib
import json
import resource
import signal
from atomic_io import atomic_text

HERE=Path(__file__).resolve().parent
MODEL='phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json'
MODEL_SHA='24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219'
FULL=(1<<128)-1


def parity(mask,values):
    result=0
    while mask:
        bit=(mask&-mask).bit_length()-1;mask&=mask-1;result^=values[bit]
    return result


def rank(rows):
    pivots={}
    for row in rows:
        while row:
            bit=row.bit_length()-1
            if bit not in pivots:pivots[bit]=row;break
            row^=pivots[bit]
    return len(pivots)


def solve(columns,target):
    pivots={}
    for index,column in enumerate(columns):
        value=column;expression=1<<index
        while value:
            bit=value.bit_length()-1
            if bit not in pivots:pivots[bit]=(value,expression);break
            v,e=pivots[bit];value^=v;expression^=e
    expression=0
    while target:
        bit=target.bit_length()-1
        if bit not in pivots:return None
        v,e=pivots[bit];target^=v;expression^=e
    return expression


def evaluate_plan(plan,inputs):
    assert len(inputs)==plan['width']
    factored=(FULL if plan['constant'] else 0)^parity(plan['product_linear'],inputs)
    for left,right,i,j in plan['products']:
        assert i!=j and left>>i&1 and right>>j&1 and not left>>j&1 and not right>>i&1
        assert left<(1<<len(inputs)) and right<(1<<len(inputs))
        factored^=parity(left,inputs)&parity(right,inputs)
    ordinary=(FULL if plan['constant'] else 0)^parity(plan['linear'],inputs)
    for i,j in plan['edges']:
        assert i<j<len(inputs);ordinary^=inputs[i]&inputs[j]
    assert ordinary==factored
    return factored,len(plan['products'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('certificate');args=ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(60)
    path=Path(args.certificate);data=json.loads(path.read_text())
    assert data['status']=='COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
    model_path=HERE/'inputs'/MODEL;assert hashlib.sha256(model_path.read_bytes()).hexdigest()==MODEL_SHA==data['model_sha256']
    model=json.loads(model_path.read_text());raw=[sum(((row>>bit)&1)<<row for row in range(128)) for bit in range(7)]
    outputs=[sum(((value>>bit)&1)<<row for row,value in enumerate(model['A'])) for bit in range(13)]
    outputs += [sum(((value>>bit)&1)<<row for row,value in enumerate(model['stored_slope'])) for bit in range(4)]
    work=[];debts=[];toffolis=0;peak=0;frame_rows=0;and_rows=0;dependent_cleanups=0
    for item in data['steps']:
        kind=item['kind']
        if kind=='bank':
            truth,count=evaluate_plan(item['plan'],raw+work);assert truth==int(item['truth'],16);assert count==1
            work.append(truth);toffolis+=count;and_rows+=128
        elif kind=='Clifford_zero_dependent_coordinate':
            index=item['index'];assert work[index]==int(item['truth'],16)
            assert parity(item['expression'],[FULL]+raw+work[:index])==work[index]
            assert item['retained_before']==[hex(t) for t in work[:index]]
            work.pop(index);dependent_cleanups+=1
        elif kind=='Clifford_frame_then_HMR':
            assert item['old_work']==[hex(t) for t in work]
            rows=item['full_affine_rows'];assert len(rows)==len(work)
            assert rank([row>>8 for row in rows])==len(work)==item['frame_matrix_rank']
            transformed=[parity(row,[FULL]+raw+work) for row in rows]
            kept=item['retained_count'];assert item['retained_truths']==[hex(t) for t in transformed[:kept]]
            assert item['discarded_truths']==[hex(t) for t in transformed[kept:]]
            debts.extend(transformed[kept:]);work=transformed[:kept];frame_rows+=128*len(rows)
        elif kind=='virtual_affine_product':
            assert parity(item['expression'],[FULL]+raw+work)==int(item['truth'],16)
        elif kind=='CCX_new_coordinate':
            assert item['inputs']==[hex(t) for t in raw+work]
            truth,count=evaluate_plan(item['plan'],raw+work);assert truth==int(item['truth'],16)
            assert count==1;work.append(truth);toffolis+=count;and_rows+=128
        elif kind=='XOR_product_existing_coordinate':
            index=item['target_index'];assert index==0 and work[index]==int(item['old_truth'],16)
            variables=raw+work[1:];assert item['inputs']==[hex(t) for t in variables]
            truth,count=evaluate_plan(item['plan'],variables);assert truth==int(item['product_truth'],16)
            work[index]^=truth;toffolis+=count;and_rows+=128*count
        elif kind=='final_output_Clifford_frame':
            rows=item['matrix_rows'];assert len(rows)==len(work) and rank(rows)==len(work)
            work=[parity(row,work) for row in rows]
            assert work==[outputs[bit] for bit in item['output_bits']]
            frame_rows+=128*len(rows)
        else:raise AssertionError(f'Unknown operation {kind}')
        peak=max(peak,len(work));assert len(work)<=data['work_cap']
    assert peak==data['work_peak'] and toffolis==data['Toffolis']
    assert work==[outputs[bit] for bit in data['output_bits']]
    # Replay every deferred phase as a separate linear generator of the HMR
    # outcome space. This proves all transcripts, without sampling outcomes.
    final_chart=raw+outputs[:16]
    columns=[FULL]+final_chart+[a&b for i,a in enumerate(final_chart) for b in final_chart[i+1:]]
    assert rank(columns)==128
    phase_plans=[]
    for truth in debts:
        expression=solve(columns,truth);assert expression is not None
        repayment=parity(expression,columns);assert truth==repayment
        for outcome in (0,1):assert (truth if outcome else 0)^(repayment if outcome else 0)==0
        phase_plans.append(hex(expression))
    result=dict(status='INDEPENDENT_EXACT_MATHEMATICAL_REPLAY_PASS',certificate=str(path),
                certificate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),model_sha256=MODEL_SHA,
                Toffolis=toffolis,T=0,rotations=0,work_peak=peak,work_cap=data['work_cap'],output_bits=data['output_bits'],
                exact_domain_rows=128,AND_truth_row_checks=and_rows,Clifford_frame_row_checks=frame_rows,
                affine_dependency_cleanups=dependent_cleanups,HMR_debts=len(debts),HMR_generator_outcome_row_checks=256*len(debts),
                HMR_transcripts='All transcripts by linearity in independently retained measurement outcomes.',
                restored_raw_A13_H0_H1_H2_chart_rank=128,HMR_repayment_expressions=phase_plans,
                physical_native_proof=False,official_verifier=False)
    outpath=path.with_suffix('.replay.json');atomic_text(outpath,json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','Toffolis','work_peak','AND_truth_row_checks','Clifford_frame_row_checks','HMR_debts','HMR_generator_outcome_row_checks')},indent=2))


if __name__=='__main__':main()
