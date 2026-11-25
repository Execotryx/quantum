# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Independent full owner/truth/debt replay for raw/framed loader v2."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
from replay_adaptive_loader import FULL,MODEL,MODEL_SHA,HERE,parity,rank,solve,evaluate_plan
from atomic_io import atomic_text


def injective(values):
    return len({sum(((truth>>row)&1)<<bit for bit,truth in enumerate(values))for row in range(128)})==128


def main():
    ap=argparse.ArgumentParser();ap.add_argument('certificate');args=ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2));signal.alarm(6)
    path=Path(args.certificate);data=json.loads(path.read_text())
    assert data['status']=='COMPLETE_MATHEMATICAL_LOADER_NOT_NATIVE'
    model_path=HERE/'inputs'/MODEL
    assert hashlib.sha256(model_path.read_bytes()).hexdigest()==MODEL_SHA==data['model_sha256']
    model=json.loads(model_path.read_text())
    original=[sum(((row>>bit)&1)<<row for row in range(128))for bit in range(7)]
    physical=list(original)
    if data['mode']=='second_framed':
        physical[3]=original[3]^original[2]^(original[1]&(original[2]^original[5]))
        fixed,reusable,other=[3,5,6],[0,1,2,4],27
    else:
        assert data['mode']=='first_raw'
        fixed,reusable,other=list(range(7)),[],26
    assert data['fixed_address_slots']==fixed and data['reusable_input_slots']==reusable
    raw=[physical[i]for i in fixed];work=[physical[i]for i in reusable]
    assert data['original_order_fixed_truths']==[hex(t)for t in raw]
    assert data['initial_reusable_input_truths']==[hex(t)for t in work]
    assert injective(raw+work)
    outputs=[sum(((v>>bit)&1)<<row for row,v in enumerate(model['A']))for bit in range(13)]
    outputs += [sum(((v>>bit)&1)<<row for row,v in enumerate(model['stored_slope']))for bit in range(3)]
    debts=[];toffolis=0;peak=len(work);and_rows=0;frame_rows=0;affine_cleanups=0
    for item in data['steps']:
        kind=item['kind']
        if kind=='bank':
            truth,count=evaluate_plan(item['plan'],raw+work)
            assert truth==int(item['truth'],16)and count==1
            work.append(truth);toffolis+=count;and_rows+=128
        elif kind=='Clifford_zero_dependent_coordinate':
            i=item['index'];assert work[i]==int(item['truth'],16)
            assert parity(item['expression'],[FULL]+raw+work[:i])==work[i]
            assert item['retained_before']==[hex(t)for t in work[:i]]
            work.pop(i);affine_cleanups+=1
        elif kind=='Clifford_frame_then_HMR':
            offset=1+len(raw);assert item['affine_fixed_offset']==offset
            assert item['old_work']==[hex(t)for t in work]
            rows=item['full_affine_rows']
            assert len(rows)==len(work)and rank([r>>offset for r in rows])==len(work)==item['frame_matrix_rank']
            transformed=[parity(r,[FULL]+raw+work)for r in rows];kept=item['retained_count']
            assert item['retained_truths']==[hex(t)for t in transformed[:kept]]
            assert item['discarded_truths']==[hex(t)for t in transformed[kept:]]
            assert item['original_rows_distinguished_after']==128
            debts.extend(transformed[kept:]);work=transformed[:kept];frame_rows+=128*len(rows)
        elif kind=='virtual_affine_product':
            assert parity(item['expression'],[FULL]+raw+work)==int(item['truth'],16)
        elif kind=='CCX_new_coordinate':
            assert item['inputs']==[hex(t)for t in raw+work]
            truth,count=evaluate_plan(item['plan'],raw+work)
            assert truth==int(item['truth'],16)and count==1
            work.append(truth);toffolis+=count;and_rows+=128
        elif kind=='XOR_product_existing_coordinate':
            assert item['target_index']==0 and work[0]==int(item['old_truth'],16)
            variables=raw+work[1:];assert item['inputs']==[hex(t)for t in variables]
            truth,count=evaluate_plan(item['plan'],variables)
            assert truth==int(item['product_truth'],16)
            work[0]^=truth;toffolis+=count;and_rows+=128*count
        elif kind=='final_output_Clifford_frame':
            rows=item['matrix_rows'];assert len(rows)==len(work)and rank(rows)==len(work)
            work=[parity(r,work)for r in rows]
            assert work==[outputs[i]for i in item['output_bits']]
            frame_rows+=128*len(rows)
        else:
            raise AssertionError(('UNKNOWN_STEP',kind))
        assert injective(raw+work),('LOST_INPUT_INFORMATION',kind)
        peak=max(peak,len(work));assert len(work)<=data['work_cap']
    assert work==outputs and data['output_bits']==list(range(16))
    assert toffolis==data['Toffolis']and peak==data['work_peak']
    assert other==data['complete_other_owner_count']and other+peak==data['complete_peak']<=49
    final_chart=original+outputs
    columns=[FULL]+final_chart+[a&b for i,a in enumerate(final_chart)for b in final_chart[i+1:]]
    assert rank(columns)==128
    phase_plans=[]
    for truth in debts:
        expression=solve(columns,truth)
        assert expression is not None and parity(expression,columns)==truth
        for outcome in(0,1):assert(outcome*truth)^(outcome*parity(expression,columns))==0
        phase_plans.append(hex(expression))
    result=dict(status='INDEPENDENT_EXACT_LOADER_V2_REPLAY_PASS',mode=data['mode'],
                certificate=str(path),certificate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                model_sha256=MODEL_SHA,Toffolis=toffolis,T=0,rotations=0,work_peak=peak,
                work_cap=data['work_cap'],other_fixed_owners=other,complete_peak=other+peak,
                original_rows=128,initial_existing_input_work_owners=len(reusable),early_retired_inputs=reusable,
                every_intermediate_chart_injective=True,AND_truth_row_checks=and_rows,
                affine_frame_row_checks=frame_rows,affine_dependency_cleanups=affine_cleanups,
                HMR_debts=len(debts),HMR_generator_outcome_row_checks=256*len(debts),
                HMR_repayment_expressions=phase_plans,all_HMR_transcripts_by_linearity=True,
                final_shared_table_cleanup_E_unchanged=9,final_root_value_decoder_E_unchanged=21,
                native_interface='For second_framed, four missing input owners are restored later by the existing decoder without direct raw-bit phase payment; their exact mixed signs are in the table ledger. Existing R-frame charge is moved, not duplicated.',
                physical_native_proof=False,official_verifier=False)
    atomic_text(path.with_suffix('.replay.json'),json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','mode','Toffolis','complete_peak','HMR_debts')},indent=2))


if __name__=='__main__':main()
